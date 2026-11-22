# File Sorter v1.3.12 — Rule-Matching Diagnostics and Worker Safety

Changes since **v1.3.11** for Linux, Windows, and macOS.

## Matching and priority verification

- Confirmed with integration tests that an exact-name rule `Filename.AppImage` above `*.AppImage` wins, and the reverse order selects the wildcard rule. List position (`1/N` highest), rule-specific source folders and recursive behavior remain unchanged.
- Successful sorting log entries now display the winning rule's **position and pattern**, making it easier to identify which rule handled a file.
- Explicit literal filename matching handles names containing bracket characters; wildcard filename patterns remain available.
- The Linux sorter now prevents two **v1.3.12** workers sharing the same configuration from running simultaneously. Windows and macOS have the same per-configuration single-worker protection. Older versions without this lock must be closed manually.

## Important behavior clarification

Priority changes apply to **newly encountered files only**. Files already moved to a generic `*.AppImage` destination are not moved again automatically when a more specific rule is placed higher. A named rule must also match the file's complete actual filename (case-sensitive on Linux), apply to the watched folder and be eligible for that file's depth.

## Compatibility

- No configuration migration needed. Existing eight-column rules and legacy four/six/seven-column configurations continue to load.
- Per-rule overwrite, recursive scanning, custom source folders, destination modes and current app icon are retained.

## Release packaging

The Linux AppImage, Windows portable ZIP, macOS portable ZIP, source ZIP and SHA256SUMS file are suitable for **individual GitHub Release assets**. `File-Sorter-v1.3.12-Complete-Release.zip` contains the release files together for the maintainer's convenience; it does not replace separate uploads.

## Verification

- Linux worker end-to-end priority and duplicate-worker regression tests passed.
- Python cross-platform engine exact-rule priority and lock tests passed under Linux.
- Native Windows/macOS hardware verification remains recommended.
