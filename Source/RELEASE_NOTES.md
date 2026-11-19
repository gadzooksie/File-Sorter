# File Sorter v1.2.1 — Return to Menu

## Added

- **Back to Menu** buttons in both the Sorter and Sorter.Config windows.
- A persistent launcher that stays available while the other windows are open.
- The ability to return to the already-running Sorter or Config window without creating duplicate instances.

## Improved

- **Sorting continues in the background** when the Sorter window is hidden using Back to Menu.
- The configuration editor retains its open state while the menu is displayed.
- Closing the launcher also closes its child applications, preventing an invisible sorting process from remaining active.
- The AppImage preserves all settings in `~/.config/sorter-config/`.

## Installation

1. Download `File-Sorter-v1.2.1-x86_64.AppImage`.
2. Make it executable: `chmod +x File-Sorter-v1.2.1-x86_64.AppImage`.
3. Open it and choose **Start Sorter** or **Configure**.
4. Use **Back to Menu** in either application to navigate without closing it.

_Note: Closing the Sorter window itself still stops sorting; Back to Menu does not._

## Compatibility

This AppImage targets **Linux x86-64 with glibc 2.34 or newer** and an X11/XWayland desktop. It uses a FUSE-free extraction runtime and includes all three programs: `Sorter`, `Sorter.Config`, and `Sorter.Updater`.

Testing included the X11 navigation behavior, ongoing sorting while the menu is open, restoration of the same application window, and the existing updater and sorting regression tests. Direct hardware testing on all Linux distributions has not been performed.
