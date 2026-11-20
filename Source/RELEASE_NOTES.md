# File Sorter v1.3.4 — Cross-Platform Release, Overwrite Files, and Icon

This is the first unified release for **Linux, Windows, and macOS**. It includes work completed since the previously published Linux **v1.2.3** release; the intermediate Windows/macOS v1.3.x builds were development and portable previews, not separate updates to the repository.

## What's New

### Overwrite Files (all three platforms)

- Added **Config → Overwrite Files**, a persistent global toggle.
- **OFF by default:** Existing destination files are preserved and colliding source files stay in place.
- **ON:** A matching source file may replace a regular destination file with the same name.
- Added a confirmation before enabling overwriting, since replaced contents may be permanently lost.
- Protected directories and symbolic links against replacement.
- Applied the setting to regular sorting and archive placement/reclassification, with changes loaded while sorting is running.
- Stores the setting as `overwrite-files.txt` (`on` or `off`) without changing the four-column `rules.tsv` format.

### Windows and macOS Editions

- Introduced portable Python/Tkinter applications with the same **Menu**, **Sorter**, and **Config** pages in one window.
- Preserved configurable watched directories, custom rules and destinations, archive aging, and background sorting across page changes.
- Added a sample-file picker for detecting filename extensions. File drag-and-drop is available if optional `tkinterdnd2` is installed.
- Included Homebrew-compatible macOS Python discovery and Tkinter startup checks.
- Corrected macOS Aqua button colors, sizing, selector appearance, and focus-border rendering.
- Added platform-specific configuration directories and portable `~/` paths.

### Linux

- Updated the existing x86-64 AppImage to v1.3.4 with the overwrite toggle and its matching Bash sorting behavior.
- Preserved the single-window interface, verified AppImage updating, and existing configuration.

## Application Icon

- Uses the **exact white folder-and-document silhouette from the supplied screenshot**, with the screenshot checkerboard removed to create real transparency. The document remains half above the folder.
- Uses the same design for the Linux AppImage, Windows `.ico`, and macOS `.icns` icon, including the application window where supported.
- Updated file-pattern examples in every Config interface to start with **`e.g.,`**.

## Download and Installation

- **Linux:** `File-Sorter-v1.3.4-x86_64.AppImage` (executable AppImage; X11/XWayland, glibc 2.34+).
- **Windows:** `File-Sorter-v1.3.4-Windows-Portable.zip` (Python 3.11+ with Tkinter required; run `File Sorter.cmd`).
- **macOS:** `File-Sorter-v1.3.4-macOS-Portable.zip` (Python 3.11+ with Tkinter required; run `File Sorter.app`).
- **Source:** `File-Sorter-v1.3.4-Source.zip`, including an updated root `README.md`.

The Windows/macOS portable ZIPs are **not yet self-contained, signed native binaries**. They can check GitHub for updates but do not automatically install them.

## Existing Settings

All versions preserve existing user rules, monitored folders, and destination settings. **Overwrite Files starts OFF** if the setting is missing. This release does not require deleting configuration directories.

## Testing and Compatibility

Collision, archive, settings, GUI, and updater regression tests were exercised in a Linux test environment. The Linux AppImage was built and checked there. Native Windows/macOS behavior and package appearance still require testing on those operating systems.

_This release includes a feature capable of permanently replacing files. Back up important destinations before enabling Overwrite Files._
