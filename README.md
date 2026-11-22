First repo, so expect discrepancies from regular repos.

# File Sorter

**File Sorter v1.3.11** is a configurable, automatic file organizer for Linux, Windows, and macOS. It organizes files by extension or filename pattern, with a single application window containing **Menu**, **Sorter**, and **Config** pages.

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

## Overwrite existing files per rule (v1.3.11)

Every sorting rule has its own **Overwrite existing files** checkbox, **OFF by default for new rules**. It works independently of **Search subfolders** and other rules. If a file matches multiple rules, the **first matching rule** (highest position) decides the destination *and* whether a same-named destination file may be replaced. If overwriting is disabled for the winning rule, the original destination file is preserved and the incoming file stays in place.

- **Linux:** In Config > Sorting Rules, each row has **R** (search subfolders) and **O** (overwrite) checkboxes. Enabling overwrite directly from the list requires a second click to confirm. The **Priority / Sources** editor also offers **Overwrite for this rule**; click **Save Rule** to apply it.
- **Windows/macOS:** The list shows `[R]` and `[O]` when enabled. Click the respective marker or use the corresponding editor checkbox; enabling overwrite prompts for confirmation.
- **Bulk toggle:** The original top-level Overwrite Files control now changes **all existing rules** at once, showing `OFF`, `ON`, or `MIXED`. Individual checkboxes override the last bulk choice without being disabled by it.
- **Migration:** For older 4-, 6-, or 7-column rules, File Sorter uses the saved `overwrite-files.txt` setting as the initial overwrite value. Previously enabled global overwrite settings are thus preserved for existing rules. Newly created rules default OFF. Saves use an eighth `overwrite` column (`0`/`1`), which takes precedence over the legacy global preference.
- **Safety:** Overwriting can replace only regular destination files, not directories or symlinks. Replaced files may be unrecoverable.

## Search subfolders per rule (v1.3.10)

Every sorting rule now has its own **Search subfolders** checkbox. It is **OFF by default**, including when loading old rules. A rule without this option checks files directly inside its watched folder only; a checked rule searches all nested directories under its assigned sources. Enable or disable the checkbox when creating/editing a rule, or click the `[ ]` / `[x]` marker at the start of the rule row in the sorting-rules list. Changes are saved per rule and reloaded by the sorter on its next scan.

- Recursive searching honors each rule's **All Watched Folders** or custom source directory selection. A recursive custom rule does not activate unrelated global rules.
- **Priority still follows list position (1/N highest).** For a nested file, only recursive rules are eligible, in that same priority order. For top-level files, all applicable rules are eligible.
- Symlinked subdirectories are not traversed; known destination/output trees under watched folders are skipped so already-sorted files aren't ingested again.
- Searching a very large directory tree may increase scan time and disk activity. Use the checkbox only where needed.
- Existing four-column/six-column `rules.tsv` files load unchanged. v1.3.10 saves added a seventh `recursive` field (`0` or `1`), preserving the existing first six columns. Older versions may not understand the additional field.

### Release downloads

Publish the Linux AppImage, Windows portable ZIP, macOS portable ZIP, and `SHA256SUMS.txt` as **individual GitHub Release assets**. The `File-Sorter-v1.3.11-Complete-Release.zip` bundles these same files together with source code, README, and release notes for the maintainer's convenience; it is not a replacement for individual release assets.

## Position-based rule priorities and watched folders (v1.3.9)

Rule **priority now equals its position in the Sorting Rules list**, shown as `1/N`, `2/N`, ... `N/N`. **Position 1 is the highest priority.** The first matching rule wins, and the displayed ranking updates automatically whenever you add, remove, or reorder rules.

- Select a rule and use **Move Up** or **Move Down** to adjust its priority. There is no separate numeric priority to enter.
- For example, if `*.zip` is `1/79` and `filename.zip` is `79/79`, `filename.zip` is handled by the higher-ranked `*.zip` rule, even though both patterns match.
- A newly created rule starts at the bottom of the list. Moving it up gives it higher priority.
- **All Watched Folders** is the default for each rule and follows the main watched-folder selection.
- **Rule-specific watched folders** can override that default. Add one or several directories with **Add Folder**, or separate typed paths with `|`, e.g. `~/Pictures|~/Desktop`. A custom-only folder doesn't activate unrelated rules.
- Changing a rule's position or watched folders affects the next scan. Already-sorted files are not moved again solely because the priority changes.

**Migration from v1.3.8:** Numeric priorities are applied once on first loading an older configuration, then converted into the corresponding list order. Ties keep their previous relative order. Old four-column configurations remain supported; their existing row order is preserved. Older v1.3.9 saves use six tab-separated fields; v1.3.10 added `recursive` (0/1) as column seven, and v1.3.11 adds `overwrite` (0/1) as column eight. The stored rank is derived from the position, not separately editable. A `# rule-order: position` header tells the engine to use list order rather than legacy numeric priorities.

### Text entry on Linux

Linux text fields now show a **blinking insertion caret** and an I-beam pointer. You can use Left/Right, Home/End, Backspace/Delete, and Ctrl+V to edit at the caret instead of only appending text.

## Downloads and installation

Release assets are distributed through [GitHub Releases](https://github.com/gadzooksie/File-Sorter/releases). This source package supports three versions at the same version number:

### Linux (x86-64)

Download `File-Sorter-v1.3.11-x86_64.AppImage`, give it executable permission, and launch:

```bash
chmod +x File-Sorter-v1.3.11-x86_64.AppImage
./File-Sorter-v1.3.11-x86_64.AppImage
```
_(Note: Not needed if your OS supports applying executable permissions on launch)_

Requires Linux x86-64, glibc 2.34 or newer, and an X11/XWayland desktop. Uses a FUSE-free AppImage runtime. The sorter and config are built in C/Xlib; the sorting worker is embedded Bash.

### Windows

Extract `File-Sorter-v1.3.11-Windows-Portable.zip`, then open **File Sorter.cmd**. The portable package requires Python 3.11+ with Tkinter. A GitHub Actions workflow is included for compiling a native Windows executable.

### macOS

Extract `File-Sorter-v1.3.11-macOS-Portable.zip` and open **File Sorter.app** or **File Sorter.command**. The portable package requires Python 3.11+ with working Tkinter (supported for Homebrew Python and python.org builds). A native app build workflow is included. The Homebrew launcher checks candidate interpreters and reports which matching `python-tk@X.Y` package is needed if no compatible Tk is available.

## First-run setup (opt-in)

**New installations do not automatically start watching Downloads or Documents.** Open **Config > Watched Directories** and choose **Add Downloads**, **Add Documents**, or **Browse** to opt in to the directories you want monitored. You may select neither. Sorting never starts automatically on first launch.

The default file-format rules are available as templates, but they do not move any files unless you choose watched folders and start sorting. Existing configuration and watched directories are preserved during upgrades. _The initial setup suggestions do not modify any files until you select them._

## Destination mode

On **Config > Watched Directories**, use the **Destination Mode** toggle:

- **Shared `~/Sorted/` (default):** All monitored folders use shared destination paths such as `~/Sorted/PDFs/`.
- **Each folder's `Sorted/`:** `~/Downloads/file.pdf` goes to `~/Downloads/Sorted/PDFs/`, and `~/Documents/file.pdf` goes to `~/Documents/Sorted/PDFs/`.

Only rule destinations at or within **`~/Sorted/`** are redirected by this switch. Explicit custom destinations, such as an external drive or `~/Downloads/Archives`, are left unchanged. Archive `New/Old` handling and the `Overwrite Files` option still work. Switching modes affects future file moves; it does **not** relocate files already sorted. Changes take effect on the next scan.

## Sorting options

- **Watched directories:** Add or remove folders through Config. Top-level files are scanned by default; individual rules can opt into subfolder scanning.
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

Configuration files include `directories.txt`, `rules.tsv` (four, six, seven, or eight tab-separated columns; seventh is the per-rule recursive flag and eighth the per-rule overwrite flag), `destination-mode.txt` (`shared` or `per-folder`), `overwrite-files.txt`, `scan-interval.txt`, and the automatic update preferences. User settings are stored outside the application and are preserved during updates.

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
