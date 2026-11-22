"""Portable File Sorter engine (Windows, macOS, Linux).

Compatible with File Sorter v1.2.3's rules.tsv and directories.txt format.
It never executes rules as shell commands. Each first-matching rule moves a file
with optional, explicit overwriting of existing regular files.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
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

VERSION = '1.3.12'
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
    priority: int = 0
    sources: str = '-'  # '-' means all folders from directories.txt; otherwise '|' separated paths.
    recursive: bool = False  # Explicit opt-in: descend into subdirectories for this rule only.
    overwrite: bool = False  # Opt-in per rule; legacy global setting is a one-time fallback.


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
    if type(rule.recursive) is not bool:
        raise ConfigurationError('Search subfolders must be enabled or disabled.')
    if type(rule.overwrite) is not bool:
        raise ConfigurationError('Overwrite files must be enabled or disabled.')
    if not isinstance(rule.priority, int) or isinstance(rule.priority, bool) or not 0 <= rule.priority <= 9999:
        raise ConfigurationError('Priority must be a whole number between 0 and 9999.')
    if rule.sources != '-':
        if rule.scope != 'watch':
            raise ConfigurationError('Custom watched directories are available for watched-folder rules only.')
        parts = rule.sources.split('|')
        if not parts or len(parts) > 32 or any(not x.strip() for x in parts):
            raise ConfigurationError('Choose 1 to 32 watched directories for the rule.')
        for raw in parts:
            if any(c in raw for c in ('\t', '\r', '\n', '\0')) or len(raw) >= 4096:
                raise ConfigurationError('Invalid source directory.')
            folder = expand_path(raw)
            if folder == Path(folder.anchor):
                raise ConfigurationError('Cannot scan the filesystem root.')
    return rule


def load_rules(path: Path) -> list[Rule]:
    rules = []
    if not path.is_file():
        return rules
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    positional = any(line.startswith('# rule-order: position') for line in lines)
    # Old rule rows had no per-rule overwrite field. Preserve an ON global setting
    # for those rows until Config saves them with an explicit eighth column.
    legacy_overwrite = load_overwrite_setting(path.parent)
    for raw in lines:
        if not raw or raw.startswith('#'):
            continue
        columns = raw.split('\t')
        if len(columns) not in (4, 6, 7, 8):
            continue
        try:
            if len(columns) >= 7 and columns[6] not in ('0', '1'):
                continue
            if len(columns) == 8 and columns[7] not in ('0', '1'):
                continue
            if len(columns) >= 6:
                r = Rule(*columns[:4], int(columns[4]), columns[5],
                         columns[6] == '1' if len(columns) >= 7 else False,
                         columns[7] == '1' if len(columns) == 8 else legacy_overwrite)
            else:
                r = Rule(*columns, overwrite=legacy_overwrite)
            r = validate_rule(r)
        except (ConfigurationError, ValueError):
            continue
        rules.append(r)
        if len(rules) >= MAX_RULES:
            break
    # One-time compatibility: preserve v1.3.8 numeric-priority ordering.
    # From v1.3.9 onward, only the position in rules.tsv determines precedence.
    if not positional:
        rules.sort(key=lambda rule: -rule.priority)
    return normalize_positions(rules)


def normalize_positions(rules: list[Rule]) -> list[Rule]:
    size = len(rules)
    return [replace(rule, priority=size-index) for index, rule in enumerate(rules)]


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
    body = '# rule-order: position; first listed rule wins (1/N is highest)\n'
    body += '# scope<TAB>pattern<TAB>destination<TAB>mode<TAB>position-rank<TAB>source-folders<TAB>recursive(0/1)<TAB>overwrite(0/1)\n'
    body += ''.join(f'{r.scope}\t{r.pattern}\t{r.destination}\t{r.mode}\t{len(rules)-i}\t{r.sources}\t{int(r.recursive)}\t{int(r.overwrite)}\n' for i, r in enumerate(rules))
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


DEFAULT_SCAN_INTERVAL = Decimal('2')
SCAN_INTERVAL_STEP = Decimal('0.1')


def parse_scan_interval(value: str | Decimal) -> Decimal:
    """Positive finite decimal seconds (no fixed minimum or maximum)."""
    value = str(value).strip()
    if not value or len(value) > 64 or not all(ch in '0123456789.' for ch in value):
        raise ConfigurationError('Enter a positive number of seconds, e.g., 0.1 or 2.5.')
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ConfigurationError('Enter a valid positive number of seconds.') from error
    if not result.is_finite() or result <= 0:
        raise ConfigurationError('Scan interval must be greater than zero.')
    return result


def load_scan_interval(config: Path) -> Decimal:
    try:
        file = config / 'scan-interval.txt'
        if not file.is_file() or file.is_symlink():
            return DEFAULT_SCAN_INTERVAL
        return parse_scan_interval(file.read_text(encoding='utf-8').strip())
    except (ConfigurationError, OSError, UnicodeError):
        return DEFAULT_SCAN_INTERVAL


def save_scan_interval(config: Path, value: str | Decimal) -> Decimal:
    interval = parse_scan_interval(value)
    atomic_text(config / 'scan-interval.txt', format(interval, 'f') + '\n')
    return interval


def setup_defaults(config: Path | None = None, defaults: Path | None = None) -> Path:
    """Seed a new configuration only; never overwrite user settings."""
    config = config or config_dir()
    defaults = defaults or defaults_dir()
    config.mkdir(parents=True, exist_ok=True)
    for name in ('rules.tsv', 'directories.txt', 'scan-interval.txt'):
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


# Global destination mode is deliberately independent of user-defined rules.
# Only destinations under ~/Sorted are remapped; custom absolute paths are not.
DESTINATION_MODE_FILE = 'destination-mode.txt'

def load_destination_mode(config: Path) -> str:
    try:
        path = config / DESTINATION_MODE_FILE
        if path.is_symlink():
            return 'shared'
        mode = path.read_text(encoding='utf-8').strip()
        return mode if mode in ('shared', 'per-folder') else 'shared'
    except (OSError, UnicodeError):
        return 'shared'

def save_destination_mode(config: Path, mode: str) -> None:
    if mode not in ('shared', 'per-folder'):
        raise ConfigurationError('Invalid destination mode')
    atomic_text(config / DESTINATION_MODE_FILE, mode + '\n')

def destination_for_folder(rule: Rule, watched: Path, mode: str) -> Path:
    dest = safe_directory(rule.destination)
    if mode != 'per-folder':
        return dest
    shared = Path.home() / 'Sorted'
    try:
        suffix = dest.relative_to(shared)
    except ValueError:
        return dest  # Explicit custom destination, including external volumes.
    if watched == Path.home():
        return dest  # ~/Sorted stays ~/Sorted for a home-root watch.
    return watched / 'Sorted' / suffix

def filename_matches(name: str, pattern: str) -> bool:
    # Exact names are compared literally, including brackets; only patterns
    # with glob metacharacters use shell-style wildcard matching.
    if os.name == 'nt' or sys.platform == 'darwin':
        name, pattern = name.casefold(), pattern.casefold()
    if name == pattern:
        return True
    if not any(char in pattern for char in '*?['):
        return False
    return fnmatch.fnmatchcase(name, pattern)


def archive_target(file: Path, rule: Rule, now: float | None = None, root: Path | None = None) -> Path:
    now = time.time() if now is None else now
    kind = rule.pattern[2:]
    bucket = 'Old' if now - file.stat().st_mtime >= ARCHIVE_AGE_SECONDS else 'New'
    return (root if root is not None else safe_directory(rule.destination)) / bucket / kind


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


def rule_source_paths(rule: Rule) -> tuple[Path, ...]:
    if rule.sources == '-':
        return ()
    try:
        return tuple(expand_path(raw) for raw in rule.sources.split('|'))
    except ConfigurationError:
        return ()


def ordered_rules(rules: list[Rule]) -> list[Rule]:
    # load_rules migrates legacy priorities once; the list itself is the priority.
    return list(rules)


class SortEngine:
    def __init__(self, config: Path | None = None, log: Callable[[str], None] | None = None):
        self.config = config or config_dir()
        self.log = log or (lambda message: None)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.interval = float(load_scan_interval(self.config))
        self._worker_lock = None

    def _acquire_worker_lock(self) -> bool:
        """Non-blocking per-config OS lock; prevents competing sorter windows."""
        self.config.mkdir(parents=True, exist_ok=True)
        handle = (self.config / '.sorter-worker.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b'\0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            handle.close()
            return False
        self._worker_lock = handle
        return True

    def _release_worker_lock(self) -> None:
        handle = self._worker_lock
        self._worker_lock = None
        if handle is None:
            return
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def start(self) -> bool:
        if self.thread and self.thread.is_alive():
            return False
        setup_defaults(self.config)
        if not self._acquire_worker_lock():
            self.log('Another File Sorter instance is already running for this configuration.')
            return False
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name='FileSorterWorker', daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self._release_worker_lock()
            raise
        return True

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _loop(self) -> None:
        try:
            self.log(f'Sorting started. Scan interval: {load_scan_interval(self.config)} seconds.')
            while not self.stop_event.is_set():
                try:
                    self.scan_once()
                except Exception as e:
                    self.log(f'Scan error: {e}')
                self.interval = float(load_scan_interval(self.config))
                self.stop_event.wait(self.interval)
        finally:
            self._release_worker_lock()
            self.log('Sorting stopped.')

    def _scan_folder(self, folder: Path, scope: str, rules: list[Rule], now: float,
                     destination_mode: str, global_watch: bool = True) -> None:
        """Scan top-level files, then only subfolders eligible for recursive rules.

        Resolve rule sources against the original watched root, not each nested
        subdirectory. Never follow symlink directories or enter known destinations.
        """
        try:
            if not folder.is_dir() or folder == Path(folder.anchor):
                return
        except (OSError, PermissionError) as e:
            self.log(f'Cannot scan {folder}: {e}')
            return

        def applicable(rule: Rule, nested: bool) -> bool:
            if nested and not rule.recursive:
                return False
            if rule.sources != '-':
                return rule.scope == 'watch' and folder in rule_source_paths(rule)
            return global_watch and rule.scope == scope

        candidates = [rule for rule in rules if applicable(rule, False)]
        recursive = [rule for rule in candidates if rule.recursive]
        if not candidates:
            return

        # Protect every configured destination within this watched root,
        # including archive output trees and per-folder ~/Sorted directories.
        excluded = set()
        for rule in rules:
            try:
                target = destination_for_folder(rule, folder, destination_mode)
                if target != folder and folder in target.parents:
                    excluded.add(target)
            except ConfigurationError:
                pass

        def excluded_path(path: Path) -> bool:
            return any(path == root or root in path.parents for root in excluded)

        def move_files(directory: Path, nested: bool) -> None:
            for item in directory.iterdir():
                if self.stop_event.is_set():
                    return
                if not file_can_move(item) or excluded_path(item):
                    continue
                for rule in (recursive if nested else candidates):
                    if not filename_matches(item.name, rule.pattern):
                        continue
                    try:
                        root = destination_for_folder(rule, folder, destination_mode)
                        dest = archive_target(item, rule, now, root) if rule.mode == 'archive' else root
                        if move_with_policy(item, dest, rule.overwrite):
                            self.log(f'{"Moved (overwrite enabled)" if rule.overwrite else "Moved"}: [rule {rules.index(rule)+1}/{len(rules)}: {rule.pattern}]: {item.name} -> {dest}')
                    except (OSError, ConfigurationError) as e:
                        self.log(f'Cannot move {item.name}: {e}')
                    break

        try:
            move_files(folder, False)
            if not recursive or self.stop_event.is_set():
                return
            for current, subdirs, files in os.walk(folder, topdown=True, followlinks=False):
                if self.stop_event.is_set():
                    return
                current_path = Path(current)
                subdirs[:] = [name for name in subdirs
                              if not (current_path / name).is_symlink()
                              and not excluded_path(current_path / name)]
                if current_path != folder:
                    move_files(current_path, True)
        except (OSError, PermissionError) as e:
            self.log(f'Cannot scan {folder}: {e}')

    def _reclassify(self, rules: list[Rule], now: float, watched: list[Path], destination_mode: str) -> None:
        for rule in rules:
            if rule.mode != 'archive':
                continue
            kind = rule.pattern[2:]
            base_root = safe_directory(rule.destination)
            roots = [base_root]
            if destination_mode == 'per-folder' and (base_root == Path.home() / 'Sorted' or
                Path.home() / 'Sorted' in base_root.parents):
                eligible = list(rule_source_paths(rule)) if rule.sources != '-' else watched
                roots = list(dict.fromkeys(destination_for_folder(rule, folder, destination_mode) for folder in eligible))
            for root in roots:
                self._reclassify_root(rule, root, kind, now)

    def _reclassify_root(self, rule: Rule, root: Path, kind: str, now: float) -> None:
        for bucket in ('New', 'Old'):
            folder = root / bucket / kind
            if not folder.is_dir():
                continue
            try:
                for item in folder.iterdir():
                    if not file_can_move(item) or not filename_matches(item.name, rule.pattern):
                        continue
                    destination = archive_target(item, rule, now, root)
                    if move_with_policy(item, destination, rule.overwrite):
                        self.log(f'Archive aged: {item.name} -> {destination}')
            except OSError as e:
                self.log(f'Cannot inspect archive folder: {e}')

    def scan_once(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        setup_defaults(self.config)
        rules = ordered_rules(load_rules(self.config / 'rules.tsv'))
        destination_mode = load_destination_mode(self.config)
        watched = []
        for directory in load_directories(self.config / 'directories.txt'):
            try:
                folder = expand_path(directory)
            except ConfigurationError:
                continue
            watched.append(folder)
            scope = 'home' if folder == Path.home() else 'watch'
            self._scan_folder(folder, scope, rules, now, destination_mode)
        global_watched = list(watched)
        # Explicit per-rule folders are checked even if they are not globally monitored.
        # Deduplicate to avoid scanning a folder twice during the same pass.
        for rule in rules:
            if rule.scope != 'watch' or rule.sources == '-':
                continue
            for folder in rule_source_paths(rule):
                if folder in watched:
                    continue
                watched.append(folder)
                self._scan_folder(folder, 'watch', rules, now, destination_mode, global_watch=False)
        if not watched:
            return  # New installations are opt-in unless an explicit rule source exists.
        # The saves rule scope is compatible with the prior Linux sorter.
        saves = next((safe_directory(r.destination) for r in rules
                      if r.scope == 'watch' and r.pattern == '*.sav' and r.mode == 'move'),
                     Path.home() / 'Sorted' / 'Saves')
        self._scan_folder(saves, 'saves', rules, now, destination_mode)
        self._reclassify(rules, now, global_watched, destination_mode)
