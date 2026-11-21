First repo, so expect discrepancies from regular repos.

# File Sorter

**File Sorter v1.3.9** is a configurable, automatic file organizer for Linux, Windows, and macOS. It organizes files by extension or filename pattern, with a single application window containing **Menu**, **Sorter**, and **Config** pages.

## Interface and keyboard navigation

File Sorter includes visual hover feedback and keyboard navigation on all three platforms.
The Linux AppImage also features a **scrollable activity history** with a **Latest** button
so older sorting events are not drawn outside the activity panel.

### Linux shortcuts

- **Main menu:** Tab or Up/Down selects a card; Enter opens it. Keys `1`, `2`, `3` open Sorter, Config, and update check.
- **Sorter:** `Ctrl+M` returns to the menu without stopping sorting; `Ctrl+L` clears the log. Scroll the activity panel with the mouse wheel, Page Up/Down, and press End or **Latest** to see the newest events.
- **Config:** `Ctrl+1` opens Watched Folders, `Ctrl+2` opens Sorting Rules, `Ctrl+R` reloads saved configuration, and `Ctrl+M` returns to the menu. With a text field unfocused, Up/Down selects rows.

### Windows and macOS shortcuts

Use `Ctrl+1/2/3` (Windows) or `Command+1/2/3` (macOS) to switch between Menu, Sorter, and Config; `Ctrl/Command+L` clears the activity log, and `Ctrl/Command+R` reloads configuration when Config is open. Buttons also retain their keyboard focus and mouse-hover feedback.

_The program never starts sorting merely because a page is opened. First-use folder monitoring remains opt-in._

## Position-based rule priorities and watched folders (v1.3.9)

Rule **priority now equals its position in the Sorting Rules list**, shown as `1/N`, `2/N`, ... `N/N`. **Position 1 is the highest priority.** The first matching rule wins, and the displayed ranking updates automatically whenever you add, remove, or reorder rules.

- Select a rule and use **Move Up** or **Move Down** to adjust its priority. There is no separate numeric priority to enter.
- For example, if `*.zip` is `1/79` and `filename.zip` is `79/79`, `filename.zip` is handled by the higher-ranked `*.zip` rule, even though both patterns match.
- A newly created rule starts at the bottom of the list. Moving it up gives it higher priority.
- **All Watched Folders** is the default for each rule and follows the main watched-folder selection.
- **Rule-specific watched folders** can override that default. Add one or several directories with **Add Folder**, or separate typed paths with `|`, e.g. `~/Pictures|~/Desktop`. A custom-only folder doesn't activate unrelated rules.
- Changing a rule's position or watched folders affects the next scan. Already-sorted files are not moved again solely because the priority changes.

**Migration from v1.3.8:** Numeric priorities are applied once on first loading an older configuration, then converted into the corresponding list order. Ties keep their previous relative order. Old four-column configurations remain supported; their existing row order is preserved. New saves use six tab-separated fields: `scope`, `pattern`, `destination`, `mode`, `position-rank`, `sources`. The stored rank is derived from the position, not separately editable. A `# rule-order: position` header tells the engine to use list order rather than legacy numeric priorities.

### Text entry on Linux

Linux text fields now show a **blinking insertion caret** and an I-beam pointer. You can use Left/Right, Home/End, Backspace/Delete, and Ctrl+V to edit at the caret instead of only appending text.

## Downloads and installation

Release assets are distributed through [GitHub Releases](https://github.com/gadzooksie/File-Sorter/releases). This source package supports three versions at the same version number:

### Linux (x86-64)

Download `File-Sorter-v1.3.9-x86_64.AppImage`, give it executable permission, and launch:

```bash
chmod +x File-Sorter-v1.3.9-x86_64.AppImage
./File-Sorter-v1.3.9-x86_64.AppImage
```
_(Note: Not needed if your OS supports applying executable permissions on launch)_

Requires Linux x86-64, glibc 2.34 or newer, and an X11/XWayland desktop. Uses a FUSE-free AppImage runtime. The sorter and config are built in C/Xlib; the sorting worker is embedded Bash.

### Windows

Extract `File-Sorter-v1.3.9-Windows-Portable.zip`, then open **File Sorter.cmd**. The portable package requires Python 3.11+ with Tkinter. A GitHub Actions workflow is included for compiling a native Windows executable.

### macOS

Extract `File-Sorter-v1.3.9-macOS-Portable.zip` and open **File Sorter.app** or **File Sorter.command**. The portable package requires Python 3.11+ with working Tkinter (supported for Homebrew Python and python.org builds). A native app build workflow is included. The Homebrew launcher checks candidate interpreters and reports which matching `python-tk@X.Y` package is needed if no compatible Tk is available.

## First-run setup (opt-in)

**New installations do not automatically start watching Downloads or Documents.** Open **Config > Watched Directories** and choose **Add Downloads**, **Add Documents**, or **Browse** to opt in to the directories you want monitored. You may select neither. Sorting never starts automatically on first launch.

The default file-format rules are available as templates, but they do not move any files unless you choose watched folders and start sorting. Existing configuration and watched directories are preserved during upgrades. _The initial setup suggestions do not modify any files until you select them._

## Destination mode

On **Config > Watched Directories**, use the **Destination Mode** toggle:

- **Shared `~/Sorted/` (default):** All monitored folders use shared destination paths such as `~/Sorted/PDFs/`.
- **Each folder's `Sorted/`:** `~/Downloads/file.pdf` goes to `~/Downloads/Sorted/PDFs/`, and `~/Documents/file.pdf` goes to `~/Documents/Sorted/PDFs/`.

Only rule destinations at or within **`~/Sorted/`** are redirected by this switch. Explicit custom destinations, such as an external drive or `~/Downloads/Archives`, are left unchanged. Archive `New/Old` handling and the `Overwrite Files` option still work. Switching modes affects future file moves; it does **not** relocate files already sorted. Changes take effect on the next scan.

## Sorting options

- **Watched directories:** Add or remove folders through Config. Only their top-level files are scanned.
- **File formats:** Manage wildcard patterns and destinations in Config. The first matching rule in the list wins; use Move Up / Move Down to set precedence. Dropping sample files detects their extensions when drag-and-drop is available.
- **Custom destinations:** Direct each rule to a directory anywhere your user has write permission. Missing destination directories are created when needed.
- **Archive sorting:** `archive` rules organize files into `New/<type>/` or `Old/<type>/` after 72 hours, and reclassify them later.
- **Overwrite Files:** OFF by default. Enabling it (with confirmation) allows replacing existing regular files with the same name. This is destructive.
- **Check Interval (seconds):** Editable decimal value, with up/down controls in increments of 0.1 seconds. Default is 2 seconds.
- **Background behavior:** Sorting continues when switching between pages, but stops when the application exits.
- **MAKE SURE NO FILES IN SORTER CONFIG ARE FILES YOU DON'T WANT TO BE REMOVED!!!**

## Configuration locations

| Platform | Directory |
| --- | --- |
| Linux | `~/.config/sorter-config/` or `$XDG_CONFIG_HOME/sorter-config/` |
| Windows | `%APPDATA%\sorter-config\` |
| macOS | `~/Library/Application Support/sorter-config/` |

Configuration files include `directories.txt`, `rules.tsv` (four legacy columns, or six columns with `position-rank` and `sources`), `destination-mode.txt` (`shared` or `per-folder`), `overwrite-files.txt`, `scan-interval.txt`, and the automatic update preferences. User settings are stored outside the application and are preserved during updates.

## Updates

The Linux AppImage includes an updater that checks the newest stable GitHub release and verifies downloads before installation. Python is required for the updater, but not normal Linux sorting. The portable Windows/macOS versions can check GitHub Releases but do not automatically install upgrades. A release without a matching asset may not be installable via the automatic updater. Restart the application after an update.

## Building from source

The source archive has `linux/`, `windows/`, and `macos/` folders. On Linux, install GCC and X11 development headers, then run:

```bash
cd linux
bash src/build.sh
bash make_appdir.sh
bash build_local_appimage.sh
```

The Windows/macOS GitHub Actions workflow can build standalone, platform-specific applications from their Python sources. Packaging and runtime behavior should be tested on the target operating systems before publishing.

## Notes

- Always back up important files before enabling **Overwrite Files**.
- Check that external drives are mounted before sorting to them.

## License and credits

[MIT License](LICENSE). Copyright (c) 2026 gadzooksie.

This project was  made possible using OpenAI ChatGPT-6.
