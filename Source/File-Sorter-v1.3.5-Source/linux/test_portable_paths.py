#!/usr/bin/env python3
"""Ensure HOME-relative watcher defaults work on multiple Linux home names."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parent
APP=Path('/mnt/data/File-Sorter-v1.3.5-x86_64.AppImage')


def environment(home):
    return {**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),
            'SCAN_INTERVAL':'1'}


class PortableHomes(unittest.TestCase):
    def test_packaged_default_paths(self):
        self.assertEqual((ROOT/'defaults/sorter-config/directories.txt').read_text(),
                         '~/Downloads\n~/Documents\n')
        self.assertEqual((ROOT/'File-Sorter.AppDir/usr/share/file-sorter/defaults/sorter-config/directories.txt').read_text(),
                         '~/Downloads\n~/Documents\n')
        self.assertNotIn('/home/deck', (ROOT/'src/Sorter_Config_Source.c').read_text())

    def test_different_user_home_names_and_sorting(self):
        for name in ('alex','taylor'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                home=Path(tmp)/name;home.mkdir()
                (home/'Downloads').mkdir();(home/'Documents').mkdir()
                (home/'Downloads'/'example.pdf').write_text('hello')
                (home/'Documents'/'example.json').write_text('world')
                env=environment(home)
                # First-run of sorter bootstraps config itself.
                worker=subprocess.Popen(['/bin/bash',str(ROOT/'src/Sorter_Embedded.sh')],env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    for _ in range(55):
                        if ((home/'Sorted/PDFs/example.pdf').is_file() and
                            (home/'Sorted/JSONs/example.json').is_file()):break
                        time.sleep(.12)
                    self.assertTrue((home/'Sorted/PDFs/example.pdf').is_file())
                    self.assertTrue((home/'Sorted/JSONs/example.json').is_file())
                    self.assertEqual((home/'.config/sorter-config/directories.txt').read_text(),
                                     '~/Downloads\n~/Documents\n')
                finally:
                    worker.terminate()
                    worker.communicate(timeout=4)

    def test_gui_first_run_and_absolute_path_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'different-username';home.mkdir()
            (home/'Downloads').mkdir();(home/'Documents').mkdir()
            env=environment(home)
            # First run makes portable defaults.
            p=subprocess.run([str(APP),'--config','--dump-config'],env=env,
                capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            watch=home/'.config/sorter-config/directories.txt'
            self.assertEqual(watch.read_text(),'~/Downloads\n~/Documents\n')
            outside=Path(tmp)/'external-volume';outside.mkdir()
            # Existing config: convert only paths beneath current HOME.
            watch.write_text(f'{home}/Downloads\n{home}/Documents\n{outside}\n')
            p=subprocess.run([str(APP),'--config','--dump-config'],env=env,
                capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(watch.read_text(),f'~/Downloads\n~/Documents\n{outside}\n')
            # Idempotent on a second read.
            subprocess.run([str(APP),'--config','--dump-config'],env=env,
                capture_output=True,text=True,timeout=15,check=True)
            self.assertEqual(watch.read_text(),f'~/Downloads\n~/Documents\n{outside}\n')

    def test_explicit_absolute_external_watch_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';home.mkdir()
            (home/'Downloads').mkdir();(home/'Documents').mkdir()
            outside=Path(tmp)/'outside';outside.mkdir()
            (outside/'outside.txt').write_text('external')
            cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
            (cfg/'directories.txt').write_text(str(outside)+'\n')
            (cfg/'rules.tsv').write_text('watch\t*.txt\t~/Sorted/Texts\tmove\n')
            worker=subprocess.Popen(['/bin/bash',str(ROOT/'src/Sorter_Embedded.sh')],
                env=environment(home),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                for _ in range(55):
                    if (home/'Sorted/Texts/outside.txt').exists():break
                    time.sleep(.12)
                self.assertTrue((home/'Sorted/Texts/outside.txt').is_file())
            finally:
                worker.terminate();worker.communicate(timeout=4)

if __name__=='__main__':unittest.main(verbosity=2)
