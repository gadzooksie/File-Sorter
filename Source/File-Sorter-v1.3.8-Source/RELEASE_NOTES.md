# File Sorter v1.3.8 — Rule Priorities, Individual Watch Folders, and Text Editing

This release introduces rule-level scan locations and numeric sorting priorities across **Linux, Windows, and macOS**, and improves the Linux configuration editor's text input. It includes the changes made **after v1.3.7**, without repeating earlier feature announcements.

## New: Priorities per Sorting Rule

- Add a numeric **Priority** to each rule (0–9999); higher numbers run first.
- When two rules both match a filename, the highest-priority matching rule wins. For example, `*.zip` priority 20 wins over `filename.zip` priority 5.
- Rules with equal priorities keep their existing position in the list as the tie-breaker. **Move Up** and **Move Down** still work.
- Existing rules automatically have priority 0 until changed.

## New: Rule-Specific Watched Directories

- Each new rule defaults to **All Watched Folders**, using the main watched-folders list.
- Add one or multiple independent watched folders for a specific rule, during creation or editing.
- Separate typed custom source directories with `|` or use **Add Folder** repeatedly.
- Custom-only folders do not activate other global rules; each rule scans only the folders that apply to it.
- Custom source folders can be outside the user's home directory. Existing custom output destinations and the shared/per-folder destination setting remain available.
- A custom-sourced rule can operate even when the main watched-folders list is empty.

## Improved: Linux Text Boxes

- Add a blinking **text caret** and I-beam pointer to editable fields, including pattern, destination, scan interval, priority, and source folders.
- Support Left/Right movement, Home/End, Backspace/Delete, and pasting at the caret position.
- Keep visible field focus indicators and the single-window layout.

## Configuration Compatibility

- Existing four-column `rules.tsv` entries are still supported and are interpreted as priority 0 with All Watched Folders.
- Saving rules stores six tab-separated fields: `scope`, `pattern`, `destination`, `mode`, `priority`, and `sources`.
- An unmodified rule has `sources=-`. Multiple custom folders use `|` as the delimiter.
- User settings, scan interval, existing sorting modes, and overwrite preferences are preserved.

## Installation

- **Linux:** `File-Sorter-v1.3.8-x86_64.AppImage` (x86-64, X11/XWayland, glibc 2.34+).
- **Windows:** `File-Sorter-v1.3.8-Windows-Portable.zip` (Python 3 with Tkinter).
- **macOS:** `File-Sorter-v1.3.8-macOS-Portable.zip` (Python 3 with Tkinter; Homebrew-compatible).
- **Source:** `File-Sorter-v1.3.8-Source.zip`.
- **Complete release:** `File-Sorter-v1.3.8-Complete-Release.zip` (contains all release files).

## Testing and Notes

Rule priority ordering, custom-folder isolation, migration of four-column rules, normal sorting, and archive behavior were tested in a Linux environment. Native Windows and macOS hardware testing remains necessary.

_Note: Sorting can move files automatically. Review your source folders, rule priorities, and destinations before enabling sorting._
