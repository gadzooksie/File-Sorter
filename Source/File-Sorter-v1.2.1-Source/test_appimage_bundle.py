#!/usr/bin/env python3
"""Offline AppDir and AppImage-updater regression checks using synthetic resources."""
import ast
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import types
import unittest

ROOT=Path(__file__).resolve().parent
APPDIR=ROOT/'File-Sorter.AppDir'


def load_updater():
    loader=importlib.machinery.SourceFileLoader('appimage_updater',str(ROOT/'Sorter.Updater'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def fake_appimage(char=b'A'):
    header=bytearray(20)
    header[0:4]=b'\x7fELF'
    header[4:6]=b'\x02\x01'
    header[8:11]=b'AI\x02'
    header[18:20]=b'\x3e\x00'
    return bytes(header)+char*2048


class Response:
    def __init__(self,data):self.io=io.BytesIO(data)
    def __enter__(self):return self.io
    def __exit__(self,*_):pass


class Checks(unittest.TestCase):
    def test_entrypoints(self):
        env={**os.environ,'APPDIR':str(APPDIR)}
        for args,expect in [(['--help'],'File Sorter v1.2.1'),(['--sorter','--help'],'File Sorter v1.2.1'),(['--config','--help'],'File Sorter Config GUI v1.2.1'),(['--updater','--version'],'v1.2.1')]:
            p=subprocess.run([str(APPDIR/'AppRun')]+args,env=env,capture_output=True,text=True,timeout=6)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn(expect,p.stdout)

    def test_embedded_updater_matches_file(self):
        header=(ROOT/'src/sorter_updater_embedded.h').read_text().split('static const char su_embedded_updater[] =\n',1)[1]
        embedded=''.join(ast.literal_eval(line.strip().removesuffix(';')) for line in header.splitlines() if line.strip())
        self.assertEqual(embedded,(ROOT/'Sorter.Updater').read_text())
        self.assertIn('BUILD_VERSION = (1, 2, 1)',embedded)

    def test_bundle_file_layout(self):
        for path in ['AppRun','file-sorter.desktop','file-sorter.png','usr/bin/Sorter','usr/bin/Sorter.Config','usr/bin/Sorter.Updater','usr/bin/File-Sorter-Launcher','usr/share/file-sorter/defaults/sorter-config/rules.tsv']:
            self.assertTrue((APPDIR/path).is_file(),path)
        self.assertEqual((APPDIR/'usr/share/file-sorter/VERSION').read_text().strip(),'1.2.1')
        self.assertEqual(len([x for x in (ROOT/'defaults/sorter-config/rules.tsv').read_text().splitlines() if x and not x.startswith('#')]),36)

    def test_get_latest_finds_appimage(self):
        updater=load_updater()
        name='File-Sorter-v1.2.1-x86_64.AppImage'
        url='https://github.com/gadzooksie/File-Sorter/releases/download/v1.2.1/'+name
        metadata={'tag_name':'v1.2.1','draft':False,'prerelease':False,'assets':[{'name':name,'size':98765,'digest':'sha256:'+'a'*64,'browser_download_url':url}]}
        updater.request=lambda url:Response(json.dumps(metadata).encode())
        version,asset=updater.latest_appimage()
        self.assertEqual(version,(1,2,1))
        self.assertEqual(asset['name'],name)

    def test_latest_zip_without_appimage_does_not_error(self):
        updater=load_updater()
        metadata={'tag_name':'v1.1.2','draft':False,'prerelease':False,'assets':[{'name':'File-Sorter-v1.1.2-Arch-Linux.zip'}]}
        updater.request=lambda url:Response(json.dumps(metadata).encode())
        self.assertIsNone(updater.latest_appimage())

    def test_good_appimage_swap_and_backup(self):
        updater=load_updater()
        old=fake_appimage(b'A');new=fake_appimage(b'B')
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'My File Sorter.AppImage'
            dest.write_bytes(old)
            updater.request=lambda url:Response(new)
            updater.install_appimage(dest,{'url':'https://example.com/image','size':len(new),'digest':hashlib.sha256(new).hexdigest()})
            self.assertEqual(dest.read_bytes(),new)
            self.assertEqual((Path(directory)/'My File Sorter.AppImage.previous').read_bytes(),old)
            self.assertTrue(os.access(dest,os.X_OK))

    def test_reject_corruption_without_modifying_original(self):
        updater=load_updater()
        old=fake_appimage(b'A');new=fake_appimage(b'B')
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'File-Sorter.AppImage';dest.write_bytes(old)
            updater.request=lambda url:Response(new)
            with self.assertRaises(updater.UpdateError):
                updater.install_appimage(dest,{'url':'https://example.com/image','size':len(new),'digest':'0'*64})
            self.assertEqual(dest.read_bytes(),old)
            self.assertFalse((Path(directory)/'File-Sorter.AppImage.previous').exists())

    def test_reject_symlink_install(self):
        updater=load_updater()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'original.AppImage';target.write_bytes(fake_appimage())
            link=Path(directory)/'redirect.AppImage';link.symlink_to(target)
            with self.assertRaises(updater.UpdateError):
                updater.install_appimage(link,{'url':'x','size':100,'digest':'0'*64})
            self.assertEqual(target.read_bytes(),fake_appimage())

    def test_update_invocation_header_is_appimage_aware(self):
        h=(ROOT/'src/sorter_update.h').read_text()
        self.assertIn('getenv("APPIMAGE")',h)
        self.assertIn('"--appimage"',h)
        self.assertIn('"--app-dir"',h)

    def test_worker_sorting_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';home.mkdir()
            (home/'Downloads').mkdir();(home/'Documents').mkdir()
            (home/'Downloads'/'test.AppImage').write_text('sample data')
            (home/'Documents'/'sample.pdf').write_text('sample data')
            env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'SCAN_INTERVAL':'1'}
            p=subprocess.Popen(['/usr/bin/bash',str(ROOT/'src/Sorter_Embedded.sh')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                for _ in range(45):
                    if (home/'Sorted/AppImages/test.AppImage').exists() and (home/'Sorted/PDFs/sample.pdf').exists():break
                    time.sleep(0.10)
                self.assertTrue((home/'Sorted/AppImages/test.AppImage').is_file())
                self.assertTrue((home/'Sorted/PDFs/sample.pdf').is_file())
            finally:
                p.terminate();p.communicate(timeout=5)

if __name__=='__main__':unittest.main(verbosity=2)
