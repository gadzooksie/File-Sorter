# File Sorter

**File Sorter** is a configurable, automatic file organizer for Linux, Windows, and macOS. It monitors directories you choose and moves files to destinations based on filename extensions or patterns. Its **Menu**, **Sorter**, and **Config** pages share one window, and sorting can continue while you edit configuration or return to the menu.

**Current prepared version: v1.3.4.** The latest public GitHub version before this update was **v1.2.3**; the Windows/macOS work and the new overwrite option are included in the v1.3.4 release package. **Publishing the new release and updating this repository are separate steps.**

## Features

- Monitor user-selected folders, checking for matching files about every two seconds while sorting is enabled.
- Add, remove, reorder, and edit sorting rules; choose custom output folders, including mounted external drives.
- Create missing destination directories automatically, subject to filesystem permissions.
- Drag a sample file into the configuration editor to detect its extension on Linux. Windows/macOS offer a sample-file picker; file drag-and-drop is optional with `tkinterdnd2`.
- Use `~/Downloads` and similar portable paths relative to the current user's home directory; absolute paths are also accepted.
- Split archive files between `New/<extension>/` and `Old/<extension>/` using their last-modified time and a 72-hour threshold.
- Show a live activity log, start/stop sorting, and switch between **Menu**, **Sorter**, and **Config** without opening additional top-level windows.
- **Overwrite Files** option, **OFF by default**, described below.

## Downloads and installation

Choose the build for your operating system from [GitHub Releases](https://github.com/gadzooksie/File-Sorter/releases). The three packages share the same **v1.3.4** version, but the Windows and macOS portable editions require Python and Tkinter.

### Linux: AppImage (x86-64)

Download `File-Sorter-v1.3.4-x86_64.AppImage`, then run:

```bash
chmod +x File-Sorter-v1.3.4-x86_64.AppImage
./File-Sorter-v1.3.4-x86_64.AppImage
```

The AppImage contains the GUI, sorter, config editor, and updater. It is intended for **glibc 2.34+** Linux desktops with **X11 or XWayland**, including SteamOS Desktop Mode. It has a FUSE-free extraction runtime. It does not support every Linux distribution or CPU architecture.

### Windows: portable Python edition

Download and extract `File-Sorter-v1.3.4-Windows-Portable.zip`. Install **Python 3.11 or newer with Tkinter** if it is not already installed, then double-click **`File Sorter.cmd`** in the extracted directory.

This edition targets Windows 10 and 11. The portable ZIP contains source and a launcher; **it is not a standalone `.exe`**. Optional file drag-and-drop requires `tkinterdnd2`.

### macOS: portable Python edition

Download and extract `File-Sorter-v1.3.4-macOS-Portable.zip`. Open **`File Sorter.app`** or launch **`File Sorter.command`**. It supports Python 3.11+ with a working Tkinter installation, including Homebrew on Apple Silicon and Intel Macs.

For Homebrew, install the `python-tk` formula corresponding to the installed Python version; for example:

```bash
brew install python@3.14 python-tk@3.14
```

The launcher checks whether the selected Python can actually open a Tk window and tries other installed interpreters if needed. Diagnostics are written to `~/Library/Logs/File-Sorter/launcher.log`. This portable `.app` **is not a self-contained, signed, or notarized macOS binary**. It may require permission to run depending on macOS security settings.

## Configuring sorting

Open the **Config** page to add watched folders and rules, choose destinations, and change the order in which rules are evaluated. The first matching rule is applied. Sorting moves files; **it does not copy them or recursively scan subdirectories**.

Configuration files include:

| File | Purpose |
| --- | --- |
| `directories.txt` | Watched folders, one path per line |
| `rules.tsv` | Ordered rules: `scope`, `pattern`, `destination`, `mode` (four tab-separated fields) |
| `overwrite-files.txt` | Global collision policy: `on` or `off` |
| `auto-update.txt` | Whether to check GitHub for new releases automatically |

The default rule set has **36 rules**. Your existing rules and watched folders are not reset when you install a new version. Linux can migrate settings from its older `general-cleanup-gui` configuration folder if needed.

| Operating system | Configuration directory |
| --- | --- |
| Linux | `~/.config/sorter-config/`, or `$XDG_CONFIG_HOME/sorter-config/` |
| Windows | `%APPDATA%\sorter-config\` |
| macOS | `~/Library/Application Support/sorter-config/` |

### Overwrite Files (introduced in v1.3.3)

**Config → Overwrite Files** controls what happens when a destination contains a file with the same name:

- **OFF (default):** Leave the existing destination file untouched; the matching source file remains in its monitored folder.
- **ON:** Replace an existing **regular file** with the matching source file. The replaced contents can be lost permanently. A confirmation is required before enabling it.
- **Directories and symbolic links are not valid overwrite targets.** The same policy applies to archive placement and 72-hour archive reclassification.

The setting is saved to `overwrite-files.txt` and reloaded on subsequent scans. Removing the file or setting it to `off` restores the non-overwriting behavior. **Review rules and back up important destination files before enabling it.**

## Updates

Use **Check for Updates** in the main menu. Linux's AppImage updater is designed to verify the latest compatible AppImage's GitHub asset digest before installation and keep a previous copy for recovery. Restart the app after installing an update. Windows/macOS portable editions can **check** for releases but require manual installation of the matching ZIP; they do not automatically replace the application.

Do not publish a stable GitHub release that has only Windows or macOS assets while Linux clients depend on the latest release: include an appropriately named Linux AppImage too.

## Source code and building

The v1.3.4 source archive contains three directories, `linux/`, `windows/`, and `macos/`. The Linux application is written in C/Xlib with an embedded Bash worker; Windows/macOS use a shared Python/Tkinter GUI and a Python sorting engine.

**Linux (gcc, Xlib development headers, Python 3, and AppImage packaging dependencies):**

```bash
cd linux
bash src/build.sh
bash build_local_appimage.sh
```

**Windows/macOS portable source (Python 3.11+ with Tkinter):**

```bash
python3 src/file_sorter_app.py
```

The macOS portable `.app` contains those Python files under `File Sorter.app/Contents/Resources/src/`; use its launcher for normal startup. Native, self-contained Windows/macOS binaries need builds on those respective platforms.

### Tests

Regression tests are included with the source archive. The overwrite tests use temporary files and do not need your real watched directories. Linux-specific GUI integration tests require an X11 display (or Xvfb). The Linux AppImage has been tested in a Linux X11 environment; the portable Windows/macOS implementations have not been fully tested on all supported hardware.

## Troubleshooting

- **A file does not move:** Check that sorting is running, its folder is monitored, and a matching rule exists. If a file with the same name is already at the destination and overwriting is OFF, the source is intentionally left alone.
- **Unexpected replacement:** Turn **Overwrite Files** OFF in Config immediately and inspect your destination rules.
- **Permission or missing-drive error:** Make sure the destination is mounted and writable.
- **macOS GUI does not start:** Verify Python and matching Tkinter; consult `~/Library/Logs/File-Sorter/launcher.log`.
- **Update not found:** Check the latest published stable GitHub release for an asset matching your platform and version.

## License and credits

[MIT License](LICENSE). Copyright (c) 2026 gadzooksie. Developed with assistance from ChatGPT-6.

## Application icon

The Linux AppImage, Windows package and macOS app use the same exact **white-outline file and folder** symbol from the approved screenshot with a transparent background. The original PNG and SVG are in each release's `assets/` folder.

- **Linux:** the AppImage uses `file-sorter.png` for the desktop launcher and X11 window icon.
- **Windows:** the portable app sets its Tk window icon from the PNG. Run the bundled `Create File Sorter Shortcut.ps1` on Windows to make a desktop shortcut with the `.ico` artwork. Native PyInstaller builds embed the `.ico` directly in the `.exe`.
- **macOS:** Finder and the Dock use `File-Sorter.icns` in the `.app` bundle; Tk also loads the PNG where supported. Native builds embed the `.icns`.

_The icon is intentionally white and transparent, so visibility may vary on light backgrounds._
