# File Sorter v1.2.3 — User-Independent Home Paths

This update makes monitored directory settings portable across Linux user accounts by using **`~/`** instead of hard-coded `/home/<username>/` paths.

## Fixed

### Home Directory Portability

- The initial monitored directories are now **`~/Downloads`** and **`~/Documents`** rather than machine-specific absolute paths.
- The Sorter explicitly expands `~/` to the current user’s `$HOME` when loading watched directories.
- The Config editor accepts, displays, and saves **`~/...`** paths, including folders selected through Browse or drag-and-drop.
- Previously saved absolute paths under the **current** user’s home directory are converted to `~/...` on loading the Config editor, without moving or deleting files.
- Destinations saved beneath the current user’s home directory also use `~/...`; arbitrary absolute paths outside the home directory remain supported.
- Fixed the watched-directory duplicate check to recognize that `~/Downloads` and its absolute equivalent are the same directory.

## Preserved

- The **single-window Menu, Sorter, and Config interface** from v1.2.2.
- Background sorting while switching pages.
- Existing file-pattern rules, custom destinations, archive age sorting, drag-and-drop, and automatic updates.
- The 36 default sorting rules, with their home-relative destinations.
- Configuration stored in `~/.config/sorter-config/`.

## Installation

1. Download `File-Sorter-v1.2.3-x86_64.AppImage`.
2. Make it executable:

   ```bash
   chmod +x File-Sorter-v1.2.3-x86_64.AppImage
   ```

3. Launch it:

   ```bash
   ./File-Sorter-v1.2.3-x86_64.AppImage
   ```

_Existing user settings are preserved. If you copied a configuration file from a different user's account, review any old absolute paths and replace them with `~/...` as needed._

## Compatibility

**Linux x86-64**, glibc 2.34 or newer, and X11/XWayland. The AppImage uses a FUSE-free extraction runtime. Python 3 is needed for online updates, not normal sorting.

_This change makes default paths portable; it does not guarantee that the AppImage runs on every Linux distribution or architecture._
