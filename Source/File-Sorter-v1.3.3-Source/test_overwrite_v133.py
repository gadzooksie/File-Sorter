"""Offline collision policy regressions: both Python ports and Linux Bash worker."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SRC = ROOT/'macos'/'File Sorter.app'/'Contents'/'Resources'/'src'
sys.path.insert(0, str(SRC))
import sorter_core as c

class FileCollisionPolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = self.root/'config'; self.cfg.mkdir()
        self.src = self.root/'in'; self.src.mkdir()
        self.out = self.root/'out'; self.out.mkdir()
        c.save_rules(self.cfg/'rules.tsv',[c.Rule('watch','*.abc',str(self.out),'move')])
        c.save_directories(self.cfg/'directories.txt',[str(self.src)])

    def engine(self):return c.SortEngine(self.cfg)
    def test_default_off_and_switch_live(self):
        source=self.src/'same.abc'; target=self.out/'same.abc'
        source.write_text('NEW'); target.write_text('OLD')
        self.assertFalse(c.load_overwrite_setting(self.cfg))
        e=self.engine();e.scan_once()
        self.assertEqual(target.read_text(),'OLD');self.assertEqual(source.read_text(),'NEW')
        c.save_overwrite_setting(self.cfg,True)
        self.assertEqual((self.cfg/'overwrite-files.txt').read_text(),'on\n')
        e.scan_once();self.assertEqual(target.read_text(),'NEW');self.assertFalse(source.exists())
        c.save_overwrite_setting(self.cfg,False)
        source.write_text('NEWER');e.scan_once()
        self.assertEqual(target.read_text(),'NEW');self.assertEqual(source.read_text(),'NEWER')

    def test_symlink_and_directory_protected(self):
        victim=self.root/'victim';victim.write_text('protected')
        (self.out/'same.abc').symlink_to(victim)
        source=self.src/'same.abc';source.write_text('NEW')
        c.save_overwrite_setting(self.cfg,True)
        self.engine().scan_once()
        self.assertEqual(victim.read_text(),'protected')
        self.assertTrue((self.out/'same.abc').is_symlink());self.assertTrue(source.exists())
        (self.out/'same.abc').unlink();(self.out/'same.abc').mkdir()
        self.engine().scan_once();self.assertTrue((self.out/'same.abc').is_dir())
        self.assertTrue(source.exists())

    def test_archive_new_and_reclassified_replace(self):
        archive=self.root/'archives'
        c.save_rules(self.cfg/'rules.tsv',[c.Rule('watch','*.zip',str(archive),'archive')])
        new=archive/'New'/'zip';old=archive/'Old'/'zip'
        new.mkdir(parents=True);old.mkdir(parents=True)
        incoming=self.src/'same.zip';incoming.write_text('NEW')
        (new/'same.zip').write_text('OLD')
        c.save_overwrite_setting(self.cfg,True)
        e=self.engine(); now=time.time();e.scan_once(now)
        self.assertEqual((new/'same.zip').read_text(),'NEW')
        os.utime(new/'same.zip',(now-85*3600,now-85*3600))
        (old/'same.zip').write_text('OLDER')
        e.scan_once(now)
        self.assertEqual((old/'same.zip').read_text(),'NEW')
        self.assertFalse((new/'same.zip').exists())

    def test_cross_volume_fallback_is_staged(self):
        src=self.src/'same.abc';src.write_bytes(b'N'*100)
        target=self.out/'same.abc';target.write_bytes(b'OLD')
        c.save_overwrite_setting(self.cfg,True)
        orig=c.os.replace
        def fake_replace(a,b):
            if Path(a)==src: raise OSError(c.errno.EXDEV,'cross volume')
            return orig(a,b)
        with mock.patch.object(c.os,'replace',side_effect=fake_replace):
            self.engine().scan_once()
        self.assertEqual(target.read_bytes(),b'N'*100)
        self.assertFalse(src.exists())
        self.assertFalse(list(self.out.glob('.sorter-overwrite-*')))

    def test_reject_malformed_policy(self):
        (self.cfg/'overwrite-files.txt').write_text('1\n')
        self.assertFalse(c.load_overwrite_setting(self.cfg))
        (self.cfg/'overwrite-files.txt').write_text('ON\n')
        self.assertTrue(c.load_overwrite_setting(self.cfg))

class BashPolicy(unittest.TestCase):
    def test_live_settings_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); home=root/'home';home.mkdir()
            cfg=root/'xdg'/'sorter-config';cfg.mkdir(parents=True)
            incoming=home/'Downloads';incoming.mkdir()
            output=home/'out';output.mkdir()
            (cfg/'directories.txt').write_text('~/Downloads\n')
            (cfg/'rules.tsv').write_text('watch\t*.abc\t~/out\tmove\n')
            target=output/'same.abc';source=incoming/'same.abc'
            source.write_text('NEW');target.write_text('OLD')
            env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(root/'xdg'),'SCAN_INTERVAL':'0.15'}
            process=subprocess.Popen(['bash',str(ROOT/'linux'/'src'/'Sorter_Embedded.sh')],env=env,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                time.sleep(0.7)
                self.assertEqual(target.read_text(),'OLD');self.assertTrue(source.exists())
                (cfg/'overwrite-files.txt').write_text('on\n')
                for i in range(40):
                    if not source.exists():break
                    time.sleep(.1)
                self.assertFalse(source.exists())
                self.assertEqual(target.read_text(),'NEW')
                (cfg/'overwrite-files.txt').write_text('off\n')
                source.write_text('NEWER');time.sleep(.7)
                self.assertTrue(source.exists());self.assertEqual(target.read_text(),'NEW')
                source.unlink();target.unlink()
                victim=root/'victim';victim.write_text('victim')
                target.symlink_to(victim);source.write_text('BAD')
                (cfg/'overwrite-files.txt').write_text('on\n');time.sleep(.7)
                self.assertTrue(source.exists());self.assertEqual(victim.read_text(),'victim')
            finally:
                process.terminate()
                out,err=process.communicate(timeout=5)
                self.assertIn('Moved (overwrite enabled)',out)

if __name__=='__main__':unittest.main(verbosity=2)
