"""Portable File Sorter engine (Windows, macOS, Linux).

Compatible with File Sorter v1.2.3's rules.tsv and directories.txt format.
It never executes rules as shell commands. Each first-matching rule moves a file
with optional, explicit overwriting of existing regular files.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import errno
import fnmatch
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
from typing import Callable, Iterable

VERSION = '1.3.4'
ARCHIVE_AGE_SECONDS = 72 * 60 * 60
SCOPES = ('watch', 'home', 'saves')
MODES = ('move', 'archive')
MAX_RULES = 256
MAX_DIRECTORIES = 96


@dataclass(frozen=True)
class Rule:
    scope: str
    pattern: str
    destination: str
    mode: str = 'move'


class ConfigurationError(ValueError):
    pass


def config_dir() -> Path:
    """Use conventional per-platform user configuration locations."""
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA') or (Path.home() / 'AppData' / 'Roaming')) / 'sorter-config'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'sorter-config'
    xdg = os.environ.get('XDG_CONFIG_HOME', '')
    return (Path(xdg) if os.path.isabs(xdg) else Path.home() / '.config') / 'sorter-config'


def defaults_dir() -> Path:
    # PyInstaller exposes bundled data under _MEIPASS.
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return base / 'defaults' / 'sorter-config'


def expand_path(s: str) -> Path:
    s = s.strip()
    if s == '~':
        return Path.home()
    if s.startswith('~/') or s.startswith('~\\'):
        return Path.home() / s[2:].replace('\\', os.sep)
    if s.startswith('~'):
        raise ConfigurationError('Only ~/ paths are supported (not ~otheruser).')
    p = Path(s)
    if not p.is_absolute():
        raise ConfigurationError('Please provide an absolute path or a ~/ path.')
    return p


def portable_path(p: str | Path) -> str:
    raw = str(p).strip()
    if raw.startswith('~/'):
        return raw
    path = expand_path(raw)
    try:
        relative = path.relative_to(Path.home())
        return '~' if relative == Path('.') else '~/' + relative.as_posix()
    except ValueError:
        return str(path)


def safe_directory(s: str) -> Path:
    path = expand_path(s)
    if path == Path(path.anchor) or path == Path.home():
        raise ConfigurationError('The filesystem root or home root is not a valid destination.')
    if any(part in ('.', '..') for part in Path(s).parts):
        raise ConfigurationError('Destinations cannot contain dot-dot segments.')
    if '\t' in s or '\r' in s or '\n' in s or '\0' in s:
        raise ConfigurationError('Invalid character in destination.')
    return path


def validate_rule(rule: Rule) -> Rule:
    if rule.scope not in SCOPES or rule.mode not in MODES:
        raise ConfigurationError('Invalid rule scope or mode.')
    if (not rule.pattern or len(rule.pattern) > 255 or
            any(c in rule.pattern for c in ('/', '\\', '\r', '\n', '\t', '\0'))):
        raise ConfigurationError('Invalid filename pattern.')
    if rule.mode == 'archive':
        suffix = rule.pattern[2:] if rule.pattern.startswith('*.') else ''
        if not suffix or not all(c.isalnum() or c in '._-' for c in suffix):
            raise ConfigurationError('Archive rules require patterns like *.zip or *.tar.gz.')
    safe_directory(rule.destination)
    return rule


def load_rules(path: Path) -> list[Rule]:
    rules = []
    if not path.is_file():
        return rules
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        if not raw or raw.startswith('#'):
            continue
        columns = raw.split('\t')
        if len(columns) != 4:
            continue
        try:
            r = validate_rule(Rule(*columns))
        except ConfigurationError:
            continue
        rules.append(r)
        if len(rules) >= MAX_RULES:
            break
    return rules


def load_directories(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        raw = raw.strip()
        if not raw or '\0' in raw:
            continue
        try:
            expand_path(raw)
        except ConfigurationError:
            continue
        if raw not in out:
            out.append(raw)
        if len(out) >= MAX_DIRECTORIES:
            break
    return out


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.sorter-', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_rules(path: Path, rules: Iterable[Rule]) -> None:
    rules = list(rules)
    if len(rules) > MAX_RULES:
        raise ConfigurationError('Too many rules.')
    for rule in rules:
        validate_rule(rule)
    body = '# File Sorter rules: scope<TAB>pattern<TAB>destination<TAB>mode\n'
    body += ''.join(f'{r.scope}\t{r.pattern}\t{r.destination}\t{r.mode}\n' for r in rules)
    atomic_text(path, body)


def save_directories(path: Path, dirs: Iterable[str]) -> None:
    dirs = list(dirs)
    if len(dirs) > MAX_DIRECTORIES:
        raise ConfigurationError('Too many directories.')
    cleaned = []
    for d in dirs:
        expand_path(d)
        if '\n' in d or '\r' in d or '\t' in d:
            raise ConfigurationError('Invalid watched directory.')
        d = portable_path(d)
        if d not in cleaned:
            cleaned.append(d)
    atomic_text(path, ''.join(d + '\n' for d in cleaned))


def setup_defaults(config: Path | None = None, defaults: Path | None = None) -> Path:
    """Seed a new configuration only; never overwrite user settings."""
    config = config or config_dir()
    defaults = defaults or defaults_dir()
    config.mkdir(parents=True, exist_ok=True)
    for name in ('rules.tsv', 'directories.txt'):
        dest = config / name
        if dest.exists() or dest.is_symlink():
            continue
        template = defaults / name
        if not template.is_file():
            raise FileNotFoundError(f'Bundled default missing: {template}')
        # Exclusive create: do not clobber a file written by another process.
        try:
            with dest.open('x', encoding='utf-8') as f:
                f.write(template.read_text(encoding='utf-8'))
        except FileExistsError:
            pass
    return config


def filename_matches(name: str, pattern: str) -> bool:
    # Windows filenames are normally case-insensitive; emulate this behaviour.
    if os.name == 'nt' or sys.platform == 'darwin':
        return fnmatch.fnmatchcase(name.casefold(), pattern.casefold())
    return fnmatch.fnmatchcase(name, pattern)


def archive_target(file: Path, rule: Rule, now: float | None = None) -> Path:
    now = time.time() if now is None else now
    kind = rule.pattern[2:]
    bucket = 'Old' if now - file.stat().st_mtime >= ARCHIVE_AGE_SECONDS else 'New'
    return safe_directory(rule.destination) / bucket / kind


def file_can_move(path: Path) -> bool:
    try:
        st = path.lstat()
    except (FileNotFoundError, OSError):
        return False
    return stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)


def load_overwrite_setting(config: Path) -> bool:
    """Collision overwrites are opt-in and reloaded once per scan."""
    try:
        return (config / 'overwrite-files.txt').read_text(encoding='utf-8').strip().lower() == 'on'
    except (OSError, UnicodeError):
        return False


def save_overwrite_setting(config: Path, enabled: bool) -> None:
    atomic_text(config / 'overwrite-files.txt', 'on\n' if enabled else 'off\n')


def move_with_overwrite(source: Path, destination_dir: Path) -> bool:
    """Replace a same-named regular file, never a symlink or directory.

    On another volume, copy to a temporary file in the destination directory,
    flush it and then atomically replace the destination. Source is removed only
    on success; failure keeps the old target untouched.
    """
    if not file_can_move(source):
        return False
    tmp_path = None
    try:
        if source.parent.resolve() == destination_dir.resolve():
            return False
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / source.name
        if target.is_symlink() or (target.exists() and not file_can_move(target)):
            return False
        if target.exists() and os.path.samefile(source, target):
            return False
        try:
            os.replace(source, target)  # atomic when both files share a volume
            return True
        except OSError as exc:
            if exc.errno != errno.EXDEV:
                raise
        # A cross-volume move must not modify the existing target until the
        # entire new file is safely staged in that destination directory.
        fd, temp = tempfile.mkstemp(prefix='.sorter-overwrite-', dir=str(destination_dir))
        tmp_path = Path(temp)
        with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        shutil.copystat(source, tmp_path, follow_symlinks=False)
        # Recheck before replacing; in particular, refuse link/directory targets.
        if target.is_symlink() or (target.exists() and not file_can_move(target)):
            return False
        os.replace(tmp_path, target)
        tmp_path = None
        source.unlink()
        return True
    except OSError:
        return False
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def move_with_policy(source: Path, destination_dir: Path, overwrite: bool) -> bool:
    return (move_with_overwrite if overwrite else move_without_overwrite)(source, destination_dir)


def move_without_overwrite(source: Path, destination_dir: Path) -> bool:
    """Reserve the destination atomically, including across filesystem boundaries."""
    if not file_can_move(source):
        return False
    try:
        if source.parent.resolve() == destination_dir.resolve():
            return False
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / source.name
        if target.exists() or target.is_symlink():
            return False
        try:
            os.link(source, target)
        except FileExistsError:
            return False
        except OSError:
            # Cross-volume, unsupported hard links, or filesystem permission:
            # exclusive creation avoids the overwrite hazard of shutil.move.
            try:
                with source.open('rb') as inp, target.open('xb') as out:
                    try:
                        shutil.copyfileobj(inp, out, length=1024 * 1024)
                        out.flush()
                        os.fsync(out.fileno())
                    except BaseException:
                        out.close()
                        target.unlink(missing_ok=True)
                        raise
                shutil.copystat(source, target, follow_symlinks=False)
            except FileExistsError:
                return False
            except BaseException:
                target.unlink(missing_ok=True)
                raise
        source.unlink()
        return True
    except (OSError, PermissionError):
        return False


class SortEngine:
    def __init__(self, config: Path | None = None, log: Callable[[str], None] | None = None):
        self.config = config or config_dir()
        self.log = log or (lambda message: None)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.interval = 2.0

    def start(self) -> bool:
        if self.thread and self.thread.is_alive():
            return False
        setup_defaults(self.config)
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name='FileSorterWorker', daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _loop(self) -> None:
        self.log('Sorting started. Watching for changes every 2 seconds.')
        while not self.stop_event.is_set():
            try:
                self.scan_once()
            except Exception as e:
                self.log(f'Scan error: {e}')
            self.stop_event.wait(self.interval)
        self.log('Sorting stopped.')

    def _scan_folder(self, folder: Path, scope: str, rules: list[Rule], now: float, overwrite: bool) -> None:
        try:
            if not folder.is_dir() or folder == Path(folder.anchor):
                return
            for item in folder.iterdir():
                if self.stop_event.is_set():
                    return
                if not file_can_move(item):
                    continue
                for rule in rules:
                    if rule.scope != scope or not filename_matches(item.name, rule.pattern):
                        continue
                    try:
                        dest = archive_target(item, rule, now) if rule.mode == 'archive' else safe_directory(rule.destination)
                        if move_with_policy(item, dest, overwrite):
                            self.log(f'{"Moved (overwrite enabled)" if overwrite else "Moved"}: {item.name} -> {dest}')
                    except (OSError, ConfigurationError) as e:
                        self.log(f'Cannot move {item.name}: {e}')
                    break  # Only the first matching rule applies.
        except (OSError, PermissionError) as e:
            self.log(f'Cannot scan {folder}: {e}')

    def _reclassify(self, rules: list[Rule], now: float, overwrite: bool) -> None:
        for rule in rules:
            if rule.mode != 'archive':
                continue
            root = safe_directory(rule.destination)
            kind = rule.pattern[2:]
            for bucket in ('New', 'Old'):
                folder = root / bucket / kind
                if not folder.is_dir():
                    continue
                try:
                    for item in folder.iterdir():
                        if not file_can_move(item) or not filename_matches(item.name, rule.pattern):
                            continue
                        destination = archive_target(item, rule, now)
                        if move_with_policy(item, destination, overwrite):
                            self.log(f'Archive aged: {item.name} -> {destination}')
                except OSError as e:
                    self.log(f'Cannot inspect archive folder: {e}')

    def scan_once(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        setup_defaults(self.config)
        rules = load_rules(self.config / 'rules.tsv')
        overwrite = load_overwrite_setting(self.config)
        for directory in load_directories(self.config / 'directories.txt'):
            try:
                folder = expand_path(directory)
            except ConfigurationError:
                continue
            scope = 'home' if folder == Path.home() else 'watch'
            self._scan_folder(folder, scope, rules, now, overwrite)
        # The saves rule scope is compatible with the prior Linux sorter.
        saves = next((safe_directory(r.destination) for r in rules
                      if r.scope == 'watch' and r.pattern == '*.sav' and r.mode == 'move'),
                     Path.home() / 'Sorted' / 'Saves')
        self._scan_folder(saves, 'saves', rules, now, overwrite)
        self._reclassify(rules, now, overwrite)
