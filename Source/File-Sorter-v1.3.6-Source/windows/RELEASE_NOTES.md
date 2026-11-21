# File Sorter v1.3.6 — First-Run Safety and Destination Mode

## Added

### Choose where sorted files go

- Added a **Destination Mode** switch in **Config > Watched Directories** on Linux, Windows, and macOS.
- **Shared mode:** Keep existing `~/Sorted/<category>/` destinations.
- **Per-folder mode:** Use `<watched directory>/Sorted/<category>/` independently for each watched directory.
- Only redirect rules whose destinations are within `~/Sorted/`. Explicitly chosen locations, including mounted drives and archive directories outside `~/Sorted/`, are unchanged.
- Mode changes are applied on subsequent scans without restarting or moving previously organized files.

### Opt-in watched directories

- **New installations start with no folders watched.** Files are not moved until users select a folder and start the sorter.
- Added quick **Add Downloads** and **Add Documents** suggestions to Config; additional directories can still be browsed or entered manually.
- Existing installations preserve their monitored folders and sorting rules.

### macOS setup guidance

- The portable macOS launcher now includes a detected Python version in Tkinter failure messages and gives a version-specific Homebrew installation suggestion rather than a generic placeholder.

## Compatibility

- **Linux:** `File-Sorter-v1.3.6-x86_64.AppImage`
- **Windows:** `File-Sorter-v1.3.6-Windows-Portable.zip` (Python 3.11+ and Tkinter)
- **macOS:** `File-Sorter-v1.3.6-macOS-Portable.zip` (Python 3.11+ and Tkinter)
- **Source:** `File-Sorter-v1.3.6-Source.zip` with an updated root-level README and build workflow.

_This release preserves all existing sorting features and settings. Overwrite Files remains disabled unless explicitly enabled. Existing sorted files are not migrated when switching destination modes._
