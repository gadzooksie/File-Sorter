import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from sorter_core import (Rule, SortEngine, ConfigurationError, archive_target, expand_path,
                         file_can_move, load_directories, load_rules, move_without_overwrite,
                         portable_path, save_directories, save_rules, setup_defaults,
                         validate_rule)
from file_sorter_app import detect_pattern, parse_semver

DEFAULTS = Path(__file__).resolve().parent.parent / 'defaults' / 'sorter-config'


class SorterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config'
        self.watch = self.root / 'watched'
        self.watch.mkdir()
        self.dest = self.root / 'new destination'
        self.logs = []
        setup_defaults(self.config, DEFAULTS)
        save_directories(self.config / 'directories.txt', [str(self.watch)])

    def engine(self):
        return SortEngine(self.config, log=self.logs.append)

    def test_default_rules(self):
        rules = load_rules(self.config / 'rules.tsv')
        self.assertEqual(len(rules), 36)
        self.assertEqual(load_directories(DEFAULTS / 'directories.txt'), ['~/Downloads', '~/Documents'])
        self.assertEqual(rules[-1].pattern, '*.AppImage')

    def test_custom_destination_and_case(self):
        save_rules(self.config / 'rules.tsv', [Rule('watch','*.abc',str(self.dest),'move')])
        source = self.watch / 'example.abc'
        source.write_text('safe example')
        self.engine().scan_once()
        self.assertFalse(source.exists())
        self.assertEqual((self.dest / source.name).read_text(), 'safe example')
        self.assertTrue(any('Moved:' in msg for msg in self.logs))

    def test_no_overwrite(self):
        save_rules(self.config / 'rules.tsv', [Rule('watch','*.abc',str(self.dest),'move')])
        self.dest.mkdir()
        (self.dest / 'same.abc').write_text('existing')
        (self.watch / 'same.abc').write_text('incoming')
        self.engine().scan_once()
        self.assertEqual((self.dest / 'same.abc').read_text(), 'existing')
        self.assertEqual((self.watch / 'same.abc').read_text(), 'incoming')

    def test_priority(self):
        another = self.root / 'other'
        save_rules(self.config / 'rules.tsv', [Rule('watch','*.txt',str(self.dest)),
                                                       Rule('watch','*',str(another))])
        (self.watch / 'readme.txt').write_text('text')
        self.engine().scan_once()
        self.assertTrue((self.dest / 'readme.txt').exists())
        self.assertFalse(another.exists())

    def test_archive_reclassification(self):
        archive = self.root / 'archives'
        save_rules(self.config / 'rules.tsv', [Rule('watch','*.zip',str(archive),'archive')])
        recent = self.watch / 'new.zip'
        old = self.watch / 'old.zip'
        recent.write_bytes(b'new')
        old.write_bytes(b'old')
        now = time.time()
        os.utime(old, (now - 80 * 3600, now - 80 * 3600))
        self.engine().scan_once(now)
        self.assertTrue((archive / 'New' / 'zip' / 'new.zip').exists())
        self.assertTrue((archive / 'Old' / 'zip' / 'old.zip').exists())
        os.utime(archive / 'New' / 'zip' / 'new.zip', (now - 82 * 3600, now - 82 * 3600))
        self.engine().scan_once(now)
        self.assertTrue((archive / 'Old' / 'zip' / 'new.zip').exists())

    def test_symlink_skipped(self):
        (self.watch / 'real.txt').write_text('x')
        try:
            (self.watch / 'linked.txt').symlink_to(self.watch / 'real.txt')
        except (OSError, NotImplementedError):
            self.skipTest('Cannot create symlink')
        save_rules(self.config / 'rules.tsv', [Rule('watch','*.txt',str(self.dest))])
        self.engine().scan_once()
        self.assertTrue((self.watch / 'linked.txt').is_symlink())
        self.assertFalse((self.dest / 'linked.txt').exists())

    def test_defaults_not_overwritten(self):
        save_rules(self.config / 'rules.tsv', [Rule('watch', '*.foo', str(self.dest))])
        save_directories(self.config / 'directories.txt', [])
        setup_defaults(self.config, DEFAULTS)
        self.assertEqual(load_directories(self.config / 'directories.txt'), [])
        self.assertEqual(load_rules(self.config / 'rules.tsv')[0].pattern, '*.foo')

    def test_invalid_inputs(self):
        for bad in ('relative/path', 'foo'):
            with self.assertRaises(ConfigurationError):
                expand_path(bad)
        for bad in ('*../something', '../evil', '*.foo/bar'):
            with self.assertRaises(ConfigurationError):
                validate_rule(Rule('watch',bad,'~/Sorted'))
        with self.assertRaises(ConfigurationError):
            validate_rule(Rule('watch', '*.zip', '~/Sorted', 'unknown'))

    def test_parse_and_detect(self):
        self.assertEqual(detect_pattern('backup.tar.gz'), '*.tar.gz')
        self.assertEqual(detect_pattern('Install.zip'), '*.zip')
        self.assertEqual(detect_pattern('noextension'), None)
        self.assertEqual(parse_semver('v1.3.0-Windows'), (1,3,0))

    def test_home_path(self):
        with patch('pathlib.Path.home', return_value=self.root):
            self.assertEqual(expand_path('~/Downloads'), self.root / 'Downloads')
            self.assertEqual(portable_path(self.root / 'Documents'), '~/Documents')
            self.assertEqual(portable_path(self.root / 'Something' / 'Else'), '~/Something/Else')

    def test_live_configuration_reload(self):
        engine = self.engine()
        engine.interval = 0.05
        engine.start()
        try:
            save_rules(self.config / 'rules.tsv', [Rule('watch','*.foo',str(self.dest))])
            f = self.watch / 'live.foo'
            f.write_text('live')
            for _ in range(60):
                if (self.dest / 'live.foo').exists():
                    break
                time.sleep(0.04)
            self.assertTrue((self.dest / 'live.foo').exists())
        finally:
            engine.stop()


if __name__ == '__main__':
    unittest.main()
