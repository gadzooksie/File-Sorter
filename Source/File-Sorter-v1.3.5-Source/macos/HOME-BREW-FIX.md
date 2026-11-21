# File Sorter v1.3.2 - macOS Homebrew Compatibility Fix

## Fixed

- The macOS launcher recognizes Homebrew Python on Apple Silicon (`/opt/homebrew`) and Intel (`/usr/local`), including versioned executables.
- Finds Homebrew Python even when Finder does not inherit the Terminal PATH.
- Verifies Tk by creating a window before starting the File Sorter GUI.
- Checks matching versions of Homebrew Python and Tkinter and reports actionable installation commands when none work.
- Preserves python.org and custom interpreter support using `FILE_SORTER_PYTHON`.
- Records the attempted interpreter paths and Tk errors in `~/Library/Logs/File-Sorter/launcher.log`.

## Requirements

- macOS 12+ and Python 3.11+ with working Tkinter.
- For Homebrew Python 3.14, install `python@3.14` and `python-tk@3.14` together. Adjust the version suffix for the Python version actually in use.

## Notes

This is a Python-dependent macOS portable application, not a signed standalone binary. A Tcl/Tk build incompatible with the host's macOS runtime cannot be repaired by the launcher itself. It will be logged and another available interpreter will be tried.
