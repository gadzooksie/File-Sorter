"""Regression coverage for v1.3.11 per-rule opt-in recursion."""
from pathlib import Path
import importlib.util
import os
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'windows/src'))
from sorter_core import Rule, ConfigurationError, SortEngine, save_rules, load_rules, save_directories

class RecursiveRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='recursion-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.config=self.base/'sorter-config';self.config.mkdir()
        (self.config/'overwrite-files.txt').write_text('off\n')
        self.a=self.base/'incoming';self.a.mkdir()
        self.b=self.base/'special';self.b.mkdir()
        self.out=self.base/'target'
        save_directories(self.config/'directories.txt',[str(self.a)])
        self.engine=SortEngine(self.config)
    def rules(self,*rules):save_rules(self.config/'rules.tsv',rules)
    def test_existing_file_format_defaults_unchecked(self):
        old=self.config/'rules.tsv'
        old.write_text('watch\t*.txt\t'+str(self.out)+'\tmove\n')
        self.assertFalse(load_rules(old)[0].recursive)
        self.rules(*load_rules(old))
        self.assertEqual(old.read_text().splitlines()[-1].split('\t')[-1],'0')
    def test_recursive_only_for_opted_in_rule(self):
        deep=self.a/'x'/'y';deep.mkdir(parents=True)
        (deep/'a.zip').write_text('a');(deep/'b.txt').write_text('b')
        (self.a/'top.txt').write_text('t')
        self.rules(Rule('watch','*.zip',str(self.out/'zip'),'move',recursive=True),
                   Rule('watch','*.txt',str(self.out/'text')))
        self.engine.scan_once()
        self.assertTrue((self.out/'zip'/'a.zip').exists())
        self.assertTrue((deep/'b.txt').exists())
        self.assertTrue((self.out/'text'/'top.txt').exists())
    def test_priority_still_applies_in_subfolders(self):
        deep=self.a/'folder';deep.mkdir()
        (deep/'filename.zip').write_text('one')
        self.rules(Rule('watch','filename.zip',str(self.out/'low'),'move',recursive=False),
                   Rule('watch','*.zip',str(self.out/'high'),'move',recursive=True))
        self.engine.scan_once()
        self.assertTrue((self.out/'high'/'filename.zip').exists())
        self.assertFalse((self.out/'low'/'filename.zip').exists())
    def test_custom_folder_recursive_not_global(self):
        deep=self.b/'folder';deep.mkdir()
        (deep/'special.zip').write_text('a');(deep/'special.txt').write_text('b')
        self.rules(Rule('watch','*.zip',str(self.out/'zip'),'move',sources=str(self.b),recursive=True),
                   Rule('watch','*.txt',str(self.out/'txt'),'move',recursive=True))
        self.engine.scan_once()
        self.assertTrue((self.out/'zip'/'special.zip').exists())
        self.assertTrue((deep/'special.txt').exists())
    def test_do_not_reenter_destination_or_symlink_subtree(self):
        output=self.a/'Sorted'/'Files';output.mkdir(parents=True)
        (output/'already.txt').write_text('preserve')
        (self.a/'nested').mkdir()
        (self.a/'nested'/'new.txt').write_text('move')
        (self.a/'symlink').symlink_to(self.b, target_is_directory=True)
        (self.b/'external.txt').write_text('external')
        self.rules(Rule('watch','*.txt',str(output),'move',recursive=True))
        self.engine.scan_once()
        self.assertTrue((output/'already.txt').exists())
        self.assertTrue((output/'new.txt').exists())
        self.assertTrue((self.b/'external.txt').exists())
    def test_invalid_recursion_value_rejected(self):
        p=self.config/'rules.tsv';p.write_text('watch\t*.zip\t'+str(self.out)+'\tmove\t1\t-\tmaybe\n')
        self.assertEqual(load_rules(p),[])
        with self.assertRaises(ConfigurationError):
            self.rules(Rule('watch','*.zip',str(self.out), recursive=1))

if __name__=='__main__':unittest.main()
