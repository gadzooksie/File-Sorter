#!/usr/bin/env python3
"""Exact-filename precedence, wildcard fallback, and competing worker regression."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'windows'/'src'))
from sorter_core import Rule, SortEngine, filename_matches, save_rules


class NamePrecedence(unittest.TestCase):
    def create(self, base: Path, exact_first: bool):
        home=base/'home';home.mkdir(parents=True,exist_ok=True)
        watched=home/'Downloads';watched.mkdir(parents=True, exist_ok=True)
        config=home/'.config'/'sorter-config';config.mkdir(parents=True,exist_ok=True)
        (config/'directories.txt').write_text(str(watched)+'\n')
        (config/'scan-interval.txt').write_text('0.1\n')
        specific=base/'specific'; general=base/'general'
        rules=[Rule('watch','Filename.AppImage',str(specific)),Rule('watch','*.AppImage',str(general))]
        if not exact_first:rules.reverse()
        save_rules(config/'rules.tsv',rules)
        (watched/'Filename.AppImage').write_text('input')
        return home,watched,config,specific,general

    def run_worker(self,home,config):
        env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),
             'SORTER_DIRS_FILE':str(config/'directories.txt'),
             'SORTER_RULES_FILE':str(config/'rules.tsv'),
             'SORTER_SCAN_INTERVAL_FILE':str(config/'scan-interval.txt'),
             'SORTER_OVERWRITE_FILE':str(config/'overwrite-files.txt'),
             'SORTER_DESTINATION_MODE_FILE':str(config/'destination-mode.txt')}
        return subprocess.Popen(['bash',str(ROOT/'linux/src/Sorter_Embedded.sh')], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True)

    def test_python_exact_first(self):
        with tempfile.TemporaryDirectory() as t:
            home,watched,config,specific,general=self.create(Path(t),True)
            logs=[];SortEngine(config,logs.append).scan_once()
            self.assertTrue((specific/'Filename.AppImage').exists(), logs)
            self.assertFalse((general/'Filename.AppImage').exists())
            self.assertTrue(any('rule 1/2: Filename.AppImage' in s for s in logs),logs)

    def test_linux_exact_first(self):
        with tempfile.TemporaryDirectory() as t:
            home,watched,config,specific,general=self.create(Path(t),True)
            p=self.run_worker(home,config)
            try:
                for _ in range(40):
                    if (specific/'Filename.AppImage').exists() or (general/'Filename.AppImage').exists():break
                    time.sleep(.05)
            finally:
                p.terminate();out,err=p.communicate(timeout=4)
            self.assertTrue((specific/'Filename.AppImage').exists(),(out,err))
            self.assertFalse((general/'Filename.AppImage').exists())
            self.assertIn('rule 1/2: Filename.AppImage',out)

    def test_linux_glob_first(self):
        with tempfile.TemporaryDirectory() as t:
            home,watched,config,specific,general=self.create(Path(t),False)
            p=self.run_worker(home,config)
            try:
                for _ in range(40):
                    if (specific/'Filename.AppImage').exists() or (general/'Filename.AppImage').exists():break
                    time.sleep(.05)
            finally:
                p.terminate();out,err=p.communicate(timeout=4)
            self.assertTrue((general/'Filename.AppImage').exists(),(out,err))
            self.assertFalse((specific/'Filename.AppImage').exists())
            self.assertIn('rule 1/2: *.AppImage',out)

    def test_literal_bracket_filename(self):
        self.assertTrue(filename_matches('Filename[1].AppImage','Filename[1].AppImage'))
        self.assertFalse(filename_matches('Filename2.AppImage','Filename[1].AppImage'))

    def test_linux_prevents_second_worker(self):
        with tempfile.TemporaryDirectory() as t:
            home, watched, config, _, _=self.create(Path(t),True)
            # Unmatched file: first worker keeps running without moving it.
            (watched/'Filename.AppImage').unlink()
            first=self.run_worker(home,config)
            try:
                time.sleep(.2)
                second=self.run_worker(home,config)
                out,err=second.communicate(timeout=4)
                self.assertEqual(second.returncode,2,(out,err))
                self.assertIn('already running',err)
            finally:
                first.terminate();first.communicate(timeout=4)

    def test_python_prevents_second_worker(self):
        with tempfile.TemporaryDirectory() as t:
            home, watched, config, _, _=self.create(Path(t),True)
            (watched/'Filename.AppImage').unlink()
            first=SortEngine(config)
            second=SortEngine(config)
            try:
                self.assertTrue(first.start())
                self.assertFalse(second.start())
            finally:
                first.stop(); second.stop()
            self.assertTrue(second.start())
            second.stop()


if __name__=='__main__':
    unittest.main(verbosity=2)
