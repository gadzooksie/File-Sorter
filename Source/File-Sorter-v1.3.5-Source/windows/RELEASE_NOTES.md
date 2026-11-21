# File Sorter v1.3.5 — Configurable Scan Interval

## Added

### Check Interval (seconds)

- Added a **Check Interval (seconds)** field in **Config** on Linux, Windows, and macOS.
- Directly enter any positive decimal number of seconds, such as `0.25`, `1`, `2.5`, or `30`.
- Added **+ 0.1** and **- 0.1** buttons to change the setting in increments of exactly one tenth of a second.
- Added an **Apply** action (and Enter keyboard shortcut) for directly entered values.
- Stores the interval in `scan-interval.txt` in the platform's existing `sorter-config` directory.
- **Default: 2 seconds.** Existing configurations and sorting rules are preserved; a missing or invalid setting falls back to the default.
- Running sorters reload the setting between scans without requiring a restart.

## Notes

- The interval controls **how often watched folders are scanned**, not the GitHub automatic-update check cadence (which remains six hours).
- Zero, negative, or malformed values are not accepted. Very small intervals can cause high CPU/disk usage; choose a value appropriate for your system.
- Archive sorting, the Overwrite Files toggle, the one-window UI, the application icon, and the v1.3.4 extension-example wording remain unchanged.

## Downloads

- **Linux (x86-64):** `File-Sorter-v1.3.5-x86_64.AppImage`
- **Windows:** `File-Sorter-v1.3.5-Windows-Portable.zip` (Python 3.11+ with Tkinter)
- **macOS:** `File-Sorter-v1.3.5-macOS-Portable.zip` (Python 3.11+ with Tkinter; Homebrew-supported)
- **Source:** `File-Sorter-v1.3.5-Source.zip`

## Validation

Tested the positive-decimal parser, 0.1-second controls, persistence, missing/invalid-setting fallback, sorting under different intervals, and regression tests in a Linux environment. Actual native Windows/macOS appearance remains unverified.
