"""Regression checks for per-rule overwrite v1.3.12 and legacy global migration."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PY_CORES = [ROOT/'windows/src/sorter_core.py', ROOT/'macos/File Sorter.app/Contents/Resources/src/sorter_core.py']

def load_platform(path:Path):
    name = 'sorter_core_' + ('windows' if 'windows' in str(path) else 'macos')
    spec = importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

class PerRuleOverwriteTests(unittest.TestCase):
    def setUp(self):
        self.working=tempfile.TemporaryDirectory(prefix='overwrite-rule-test-')
        self.addCleanup(self.working.cleanup)
        self.base=Path(self.working.name)
        self.config=self.base/'sorter-config';self.config.mkdir()
        self.watch=self.base/'watched';self.watch.mkdir()
        self.dest=self.base/'sorted';self.dest.mkdir()
        (self.config/'overwrite-files.txt').write_text('off\n')
        self.platforms=[load_platform(p) for p in PY_CORES]

    def setup(self, c, rules):
        c.save_directories(self.config/'directories.txt',[str(self.watch)])
        c.save_rules(self.config/'rules.tsv',rules)
        return c.SortEngine(self.config)

    def test_new_rules_default_off_and_eighth_column(self):
        for c in self.platforms:
            r=c.Rule('watch','*.txt',str(self.dest))
            self.assertFalse(r.overwrite)
            self.setup(c,[r])
            self.assertEqual((self.config/'rules.tsv').read_text().splitlines()[-1].split('\t')[-1],'0')
            self.assertEqual(len((self.config/'rules.tsv').read_text().splitlines()[-1].split('\t')),8)
            self.assertFalse(c.load_rules(self.config/'rules.tsv')[0].overwrite)

    def test_enabled_rule_replaces_but_disabled_rule_skips(self):
        for c in self.platforms:
            for name, rule_overwrite in (('a.zip', True), ('b.txt',False)):
                (self.watch/name).write_text('incoming '+name)
                (self.dest/name).write_text('existing '+name)
            engine=self.setup(c,[c.Rule('watch','*.zip',str(self.dest),overwrite=True),
                                 c.Rule('watch','*.txt',str(self.dest),overwrite=False)])
            engine.scan_once()
            self.assertEqual((self.dest/'a.zip').read_text(),'incoming a.zip')
            self.assertEqual((self.dest/'b.txt').read_text(),'existing b.txt')
            self.assertFalse((self.watch/'a.zip').exists())
            self.assertTrue((self.watch/'b.txt').exists())
            (self.watch/'a.zip').write_text('incoming a.zip')
            (self.dest/'a.zip').write_text('existing a.zip')

    def test_rule_flag_overrides_legacy_global_setting(self):
        for c in self.platforms:
            (self.config/'overwrite-files.txt').write_text('on\n')
            (self.watch/'same.zip').write_text('incoming')
            (self.dest/'same.zip').write_text('existing')
            engine=self.setup(c,[c.Rule('watch','*.zip',str(self.dest),overwrite=False)])
            engine.scan_once()
            self.assertEqual((self.dest/'same.zip').read_text(),'existing')
            self.assertTrue((self.watch/'same.zip').exists())
            (self.config/'overwrite-files.txt').write_text('off\n')
            self.setup(c,[c.Rule('watch','*.zip',str(self.dest),overwrite=True)]).scan_once()
            self.assertEqual((self.dest/'same.zip').read_text(),'incoming')
            (self.dest/'same.zip').write_text('existing')
            (self.watch/'same.zip').write_text('incoming')

    def test_overwrite_of_lower_priority_does_not_bypass_higher_rule(self):
        for c in self.platforms:
            source=self.watch/'name.zip';source.write_text('incoming')
            target=self.dest/'name.zip';target.write_text('existing')
            self.setup(c,[c.Rule('watch','*.zip',str(self.dest),overwrite=False),
                          c.Rule('watch','name.zip',str(self.dest),overwrite=True)]).scan_once()
            self.assertEqual(target.read_text(),'existing')
            self.assertEqual(source.read_text(),'incoming')

    def test_legacy_global_settings_migrate_for_4_6_7_columns(self):
        for c in self.platforms:
            (self.config/'overwrite-files.txt').write_text('on\n')
            rows=[f'watch\t*.zip\t{self.dest}\tmove',
                  f'watch\t*.txt\t{self.dest}\tmove\t5\t-',
                  f'watch\t*.pdf\t{self.dest}\tmove\t4\t-\t1']
            (self.config/'rules.tsv').write_text('# rule-order: position; first listed rule wins (1/N is highest)\n'+'\n'.join(rows)+'\n')
            loaded=c.load_rules(self.config/'rules.tsv')
            self.assertEqual(len(loaded),3)
            self.assertTrue(all(r.overwrite for r in loaded))
            self.assertEqual([r.recursive for r in loaded],[False,False,True])
            c.save_rules(self.config/'rules.tsv',loaded)
            self.assertTrue(all(len(s.split('\t'))==8 for s in (self.config/'rules.tsv').read_text().splitlines() if not s.startswith('#')))
            (self.config/'overwrite-files.txt').write_text('off\n')
            self.assertTrue(all(r.overwrite for r in c.load_rules(self.config/'rules.tsv')))
            (self.config/'overwrite-files.txt').write_text('off\n')
            (self.config/'rules.tsv').write_text(rows[0]+'\n')
            self.assertFalse(c.load_rules(self.config/'rules.tsv')[0].overwrite)

    def test_invalid_overwrite_is_rejected(self):
        for c in self.platforms:
            for bad in ('maybe','2','-1',''):
                (self.config/'rules.tsv').write_text(f'watch\t*.zip\t{self.dest}\tmove\t1\t-\t0\t{bad}\n')
                self.assertEqual(c.load_rules(self.config/'rules.tsv'),[])
            with self.assertRaises(c.ConfigurationError):
                c.save_rules(self.config/'rules.tsv',[c.Rule('watch','*.zip',str(self.dest),overwrite=1)])

    def test_archive_reclassification_uses_archive_rule_flag(self):
        for c in self.platforms:
            self.setup(c,[c.Rule('watch','*.zip',str(self.dest),'archive',overwrite=False)])
            newdir=self.dest/'New'/'zip';newdir.mkdir(parents=True,exist_ok=True)
            olddir=self.dest/'Old'/'zip';olddir.mkdir(parents=True,exist_ok=True)
            source=newdir/'example.zip';source.write_text('incoming')
            target=olddir/'example.zip';target.write_text('existing')
            ancient=time.time()-90*3600
            os.utime(source,(ancient,ancient))
            engine=c.SortEngine(self.config)
            engine.scan_once()
            self.assertEqual(target.read_text(),'existing')
            self.assertTrue(source.exists())
            self.setup(c,[c.Rule('watch','*.zip',str(self.dest),'archive',overwrite=True)]).scan_once()
            self.assertEqual(target.read_text(),'incoming')
            self.assertFalse(source.exists())

    def test_symlink_destination_not_replaced(self):
        if os.name=='nt':self.skipTest('Symlink permissions on Windows')
        for c in self.platforms:
            source=self.watch/'link.zip';source.write_text('incoming')
            protected=self.base/'protected';protected.write_text('safe')
            link=self.dest/'link.zip'
            link.unlink(missing_ok=True)
            link.symlink_to(protected)
            self.setup(c,[c.Rule('watch','*.zip',str(self.dest),overwrite=True)]).scan_once()
            self.assertTrue(link.is_symlink());self.assertEqual(protected.read_text(),'safe')
            self.assertTrue(source.exists())

class LinuxBashOverwriteTests(unittest.TestCase):
    def test_worker_honors_rule_flags_and_legacy_global(self):
        script=ROOT/'linux/src/Sorter_Embedded.sh'
        with tempfile.TemporaryDirectory(prefix='linux-overwrite-') as temp:
            base=Path(temp);home=base/'home';home.mkdir()
            config=home/'.config'/'sorter-config';config.mkdir(parents=True)
            watch=home/'incoming';watch.mkdir()
            output=home/'out';output.mkdir()
            (config/'directories.txt').write_text(str(watch)+'\n')
            (config/'scan-interval.txt').write_text('0.1\n')
            (config/'destination-mode.txt').write_text('shared\n')
            global_file=config/'overwrite-files.txt'
            rules=config/'rules.tsv'
            env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config')}
            def run():
                proc=subprocess.Popen(['bash',str(script)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    time.sleep(.35)
                finally:
                    proc.terminate()
                    try:proc.communicate(timeout=3)
                    except subprocess.TimeoutExpired:proc.kill();proc.communicate()
            def files():
                (watch/'a.zip').write_text('incoming')
                (watch/'b.txt').write_text('incoming')
                (output/'a.zip').write_text('existing')
                (output/'b.txt').write_text('existing')
            rules.write_text('# rule-order: position; first listed rule wins (1/N is highest)\n'+
                             f'watch\t*.zip\t{output}\tmove\t2\t-\t0\t1\n'+
                             f'watch\t*.txt\t{output}\tmove\t1\t-\t0\t0\n')
            global_file.write_text('on\n');files();run()
            self.assertEqual((output/'a.zip').read_text(),'incoming')
            self.assertEqual((output/'b.txt').read_text(),'existing')
            self.assertTrue((watch/'b.txt').exists())
            # Older four-column rules inherit the global legacy value until saved.
            rules.write_text(f'watch\t*.txt\t{output}\tmove\n')
            (watch/'a.zip').unlink(missing_ok=True)
            global_file.write_text('on\n');run()
            self.assertEqual((output/'b.txt').read_text(),'incoming')
            global_file.write_text('off\n')
            files();run()
            self.assertEqual((output/'b.txt').read_text(),'existing')

if __name__=='__main__':unittest.main()
