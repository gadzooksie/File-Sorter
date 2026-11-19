# File Sorter v1.2.2 — Single-Window Navigation

This update changes File Sorter from a launcher with separate application windows to a **single-window interface** with menu, sorter, and configuration pages.

## Added

### Unified Window

- **One desktop window** contains the menu, Sorter, and Config views.
- **Back to Menu** switches pages inside the same window instead of displaying a second window.
- Returning to Sorter or Config restores its existing session without launching a duplicate.
- The main window's title reflects the active page.

## Improved

- **Background sorting continues** while the menu or Config page is displayed.
- The configuration editor retains unsaved text and the currently selected rule when switching pages.
- File and folder drag-and-drop, sorting destinations, updater controls, and the existing 36 default rules remain available.
- Closing the unified window stops the background sorter and cleans up child processes.
- User preferences are preserved in `~/.config/sorter-config/`.

## Installation

1. Download `File-Sorter-v1.2.2-x86_64.AppImage`.
2. Give it executable permission: `chmod +x File-Sorter-v1.2.2-x86_64.AppImage`.
3. Open the AppImage and choose **Start Sorter** or **Configure**.
4. Use **Back to Menu** to switch pages.

_The sorter keeps working while its page is hidden. Exiting the complete application stops the sorter._

## Compatibility

- **Linux:** x86-64 with glibc 2.34 or newer
- **Display:** X11 / XWayland
- **Packaging:** FUSE-free AppImage
- **Configuration:** `~/.config/sorter-config/`

_Compatibility with every Linux distribution is not guaranteed._
