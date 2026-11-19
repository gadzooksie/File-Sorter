# File Sorter v1.2.2 — Single-Window AppImage

File Sorter now has **one top-level window** with three views: **Menu**, **Sorter**, and **Config**. No separate Sorter and Config windows appear when you navigate using the launcher. The underlying processes remain separate to preserve their sorting engine, configuration editor and automatic updater.

## Installation

```bash
chmod +x File-Sorter-v1.2.2-x86_64.AppImage
./File-Sorter-v1.2.2-x86_64.AppImage
```

The existing setting directory `~/.config/sorter-config/` and custom sorting rules are preserved.

## Navigation

- On the menu, choose **Start Sorter** or **Configure**.
- Use **Back to Menu** from either view.
- Returning to a page shows the *same instance*, including any active sorting and editor state.
- Closing the single main window stops its sorter worker and exits both child programs.
- The Config view still supports dragged files and folders. A graphical folder picker opens as a normal system dialog.

## Compatibility

Linux x86-64, glibc 2.34+, X11/XWayland, FUSE-free AppImage runtime. Python 3 is required for online updates, not sorting. This is not guaranteed to run on every distribution or CPU architecture.

## Standalone entry points

`--sorter`, `--config`, `--update`, and `--check-updates` remain available; standalone `--sorter` and `--config` run as individual windows for scripting compatibility.
