# File Sorter v1.2.1

File Sorter automatically organizes files based on configurable filename patterns, watched folders, and destination directories. The x86-64 Linux AppImage bundles the Sorter, Config editor, and Updater into one executable.

## Run

```bash
chmod +x File-Sorter-v1.2.1-x86_64.AppImage
./File-Sorter-v1.2.1-x86_64.AppImage
```

Select **Start Sorter**, **Configure**, or **Check for Updates**. The launcher remains open while the other windows run. Click **Back to Menu** from either application to return without closing it; the running sorter continues sorting. Select an application again to restore its existing window. Closing the launcher ends the applications it launched. When invoked directly using `--sorter` or `--config` instead of from the launcher, use the AppImage normally to open the menu; the Back to Menu button will not hide the standalone window.

## Command-line options

```bash
./File-Sorter-v1.2.1-x86_64.AppImage --help
./File-Sorter-v1.2.1-x86_64.AppImage --sorter
./File-Sorter-v1.2.1-x86_64.AppImage --sorter --autostart
./File-Sorter-v1.2.1-x86_64.AppImage --config
./File-Sorter-v1.2.1-x86_64.AppImage --check-updates
./File-Sorter-v1.2.1-x86_64.AppImage --update
```

## Settings

Saved in `~/.config/sorter-config/` (or `$XDG_CONFIG_HOME/sorter-config/`): `rules.tsv`, `directories.txt`, and auto-update preferences. Existing settings are preserved across updates.

## Compatibility and source

Targets x86-64 Linux systems with glibc 2.34+ and X11/XWayland. The included source files and `build_local_appimage.sh` can rebuild the FUSE-free self-extracting AppImage on a compatible Linux build host. Python 3 is required for GitHub update checks, but is not required for normal file sorting.

## Safety

Files are moved, not copied. Verify rules and paths before starting the sorter. External drives must be mounted and writable. Avoid monitoring output destinations.

## Build from source

On a compatible x86-64 Linux system with GCC, Xlib development headers, zlib development headers, Python 3, and Bash:

```bash
bash src/build.sh
bash make_appdir.sh
bash build_local_appimage.sh ./File-Sorter-v1.2.1-x86_64.AppImage
```

The final command creates the AppImage in the current directory. The build workflow uses a custom FUSE-free runtime that extracts to a temporary directory and cleans up when the launcher closes.
