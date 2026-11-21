# File Sorter v1.3.7 — Interface and Navigation Improvements

This release focuses on **visual feedback, keyboard navigation, and easier interaction**, especially in the Linux AppImage. Sorting behavior, the default opt-in setup, and existing configurations are unchanged.

## Linux AppImage

### Improved Visual Feedback

- Added hover highlighting and pointer cursors to clickable buttons across the main menu, Sorter, and Config.
- Highlighted the hovered row in the watched-folder and sorting-rule lists, without changing the selected item.
- Added visible keyboard selection to the main menu, with Tab/Up/Down navigation and Enter activation.

### Scrollable Activity Log

- Fixed the Sorter activity panel so a long history stays inside its visible area.
- Added mouse-wheel and Page Up/Page Down history scrolling, a **Latest** button, an event counter, and a history of up to 256 events.
- Kept live sorting and the existing log/session behavior intact while reading older events.

### Keyboard Shortcuts

- **Menu:** Tab, Up/Down, Enter, and direct `1` / `2` / `3` navigation.
- **Sorter:** `Ctrl+M` for Menu, `Ctrl+L` to clear the activity log, Page Up/Down to scroll, and End for the latest entries.
- **Config:** `Ctrl+1` / `Ctrl+2` to switch tabs, `Ctrl+R` to reload, `Ctrl+M` for Menu, and Up/Down to select a row when not editing.
- Added on-screen shortcut hints.

## Windows and macOS

- Added global Menu/Sorter/Config navigation shortcuts: `Ctrl+1/2/3` on Windows and `Command+1/2/3` on macOS.
- Added `Ctrl/Command+L` for clearing the activity log and `Ctrl/Command+R` for refreshing Config.
- Retained the existing interactive buttons, macOS Homebrew Python support, and single-window layout.

## Compatibility and Installation

- **Linux:** `File-Sorter-v1.3.7-x86_64.AppImage` — x86-64, glibc 2.34+, X11/XWayland.
- **Windows:** `File-Sorter-v1.3.7-Windows-Portable.zip` — Python 3 with Tkinter.
- **macOS:** `File-Sorter-v1.3.7-macOS-Portable.zip` — Python 3 with Tkinter, including Homebrew-compatible launching.

User settings in `sorter-config` remain in their platform-specific locations. Existing watched directories, rules, scan interval, destination mode, and overwrite preferences are preserved.

## Testing

Builds and automated tests were run on Linux, including the X11 single-window/navigation tests and cross-platform sorting tests. _The Windows/macOS shortcut changes have not been tested on native hardware._
