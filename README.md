First repo, so expect discrepancies from regular repos.

# File Sorter

**File Sorter** is a configurable, automatic file organizer for Linux. It monitors folders you choose and moves matching files to destinations based on filename patterns or extensions.

Starting with v1.2.1, the application is distributed as **one AppImage** containing the sorter, configuration editor, and updater. In v1.2.2 and later, **Menu, Sorter, and Config share one application window**. Version 1.2.3 adds portable `~/` paths so the default configuration is not tied to the `deck` username.

## Features

- **Automatic sorting:** Monitors configured directories and moves matching files to your chosen destinations.
- **Custom rules:** Add, edit, prioritize, or remove filename patterns and extensions, with a separate destination for each rule.
- **Drag and drop:** Drop a sample file into Config to detect its extension, or drop a folder to select a destination.
- **Flexible destinations:** Use folders anywhere you have write access, not just a `Sorted` directory. Missing destination subfolders are created as needed.
- **Archive organization:** Optionally separate archives into `New/` and `Old/` folders based on a 72-hour threshold.
- **Collision protection:** Existing destination files are not overwritten.
- **Single-window interface:** Switch between the Menu, Sorter, and Config pages without opening duplicate application windows.
- **Background operation:** Sorting continues when you select **Back to Menu**, and stops when you stop the sorter or close the main window.
- **GitHub updates:** Check for newer stable AppImage releases from within the app.

## Download and install

Download the latest **`File-Sorter-vX.Y.Z-x86_64.AppImage`** from [GitHub Releases](https://github.com/gadzooksie/File-Sorter/releases/latest).

On Linux, make the downloaded file executable and open it. For example, for v1.2.3:

```bash
chmod +x ~/Downloads/File-Sorter-v1.2.3-x86_64.AppImage
~/Downloads/File-Sorter-v1.2.3-x86_64.AppImage
```

You can also enable **Is executable** in your file manager's file properties, then double-click the AppImage. No separate installation of `Sorter`, `Sorter.Config`, or `Sorter.Updater` is needed.

**Tip:** Consider keeping the AppImage in `~/Applications/` instead of a watched folder such as Downloads, so it does not get moved by an `*.AppImage` sorting rule.

## Using File Sorter

From the main menu:

1. Select **Configure** to choose watched directories, edit sorting rules, and assign destinations.
2. Select **Back to Menu** when finished. Your settings are saved locally.
3. Select **Start Sorter** to open the sorter page, then start sorting if it is not already active.
4. Use **Back to Menu** to switch pages without interrupting active sorting.
5. Stop the sorter explicitly, or close the main application window to exit and stop its background worker.

Changes to rules and watched folders are picked up by the running sorter on its next scan (normally about every two seconds). File and folder selection dialogs may appear as separate system dialogs; the three primary pages stay in one window.

## Configuration

User settings are stored in `~/.config/sorter-config/`, or in `$XDG_CONFIG_HOME/sorter-config/` when `XDG_CONFIG_HOME` is set:

| File | Purpose |
| --- | --- |
| `directories.txt` | Watched directories, one path per line. |
| `rules.tsv` | Ordered sorting rules: `scope`, `pattern`, `destination`, and `mode` (tab-separated). |
| `auto-update.txt` | Automatic-update preference (`on` or `off`). |
| `installed-release.json` | Installed-release information recorded by the updater. |

Fresh installations default to **`~/Downloads`** and **`~/Documents`** as watched folders, with **36 predefined sorting rules**. You can change or remove these defaults in Config.

### Portable paths

File Sorter expands `~/` to the **current user's home directory**, so the same configuration can be used by different Linux users:

| Configuration path | Meaning |
| --- | --- |
| `~/Downloads` | Downloads folder in the current user's home. |
| `~/Documents` | Documents folder in the current user's home. |
| `~/Sorted/PDFs` | Example destination inside the current user's home. |
| `/run/media/deck/ExternalDrive/Files` | Example absolute path to a mounted drive; update it for your system. |

`~` is expanded explicitly by File Sorter when reading its settings; it is not automatically expanded by every program that reads a text file. Absolute paths outside the user's home, such as mounted drives, remain supported. Drives must be mounted and writable when sorting occurs.

### Migrating older settings

On first launch, when a corresponding new configuration file does not exist, File Sorter can copy settings from the legacy `~/.config/general-cleanup-gui/` directory. The original files are not deleted and existing settings in `~/.config/sorter-config/` are not overwritten.

Paths pointing inside the current user's home can be converted to `~/...` when edited in Config. Paths hard-coded for another user must be corrected manually.

## Automatic updates

File Sorter checks the [latest stable GitHub release](https://github.com/gadzooksie/File-Sorter/releases/latest) when automatic updates are enabled, with checks limited to approximately once every six hours. Use **Check for Updates** from the main menu to check manually, or turn automatic checking on or off in Config.

The AppImage updater looks for a versioned release asset such as `File-Sorter-v1.2.3-x86_64.AppImage`. It verifies the downloaded file against the release asset's reported size and SHA-256 digest and checks that it is an executable AppImage before attempting to replace the current file. The previous AppImage is retained as a `.previous` backup. Restart the application to use an installed update.

**Requirements for updating:** Python 3 (standard library), an internet connection, and write access to the directory containing the AppImage. **Ordinary sorting works offline** and does not require a GitHub account or API key. An older three-file installation must be upgraded manually to the AppImage format once.

## Compatibility

- **CPU architecture:** x86-64 (not ARM).
- **System libraries:** glibc 2.34 or newer.
- **Desktop:** X11 or XWayland; intended for SteamOS Desktop Mode and compatible Linux desktops.
- **AppImage runtime:** FUSE-free, extraction-based runtime.
- **Internet access:** Optional for sorting; required for online update checks.

AppImage improves portability but does **not** guarantee support for every Linux distribution, desktop environment, or CPU architecture.

## Command-line options

The AppImage also supports these entry points:

```bash
./File-Sorter-v1.2.3-x86_64.AppImage --sorter
./File-Sorter-v1.2.3-x86_64.AppImage --config
./File-Sorter-v1.2.3-x86_64.AppImage --check-updates
./File-Sorter-v1.2.3-x86_64.AppImage --update
```

**Note:** The `--sorter` and `--config` options open standalone application windows for scripting compatibility. Launch without options for the integrated single-window interface.

## Building from source

The source tree is located in [`Source/`](./Source/). It includes the C/Xlib interface sources, embedded Bash sorter, Python updater and build scripts, AppImage runtime, default rules, and tests.

Building requires GCC, X11 development headers/libraries, Bash, and Python 3. The local FUSE-free AppImage builder also requires static linking support for zlib.

**Current source-tree caveat:** `src/build.sh` expects a `Sorter.Updater` Python script in `Source/`, but that standalone script is not currently tracked in the repository. You can extract it from the published v1.2.3 AppImage before building. From the repository root, with the downloaded AppImage in `~/Downloads`:

```bash
chmod +x ~/Downloads/File-Sorter-v1.2.3-x86_64.AppImage
~/Downloads/File-Sorter-v1.2.3-x86_64.AppImage --appimage-extract
cp squashfs-root/usr/bin/Sorter.Updater Source/Sorter.Updater
cd Source
bash src/build.sh
bash make_appdir.sh
bash build_local_appimage.sh "$PWD/File-Sorter-v1.2.3-x86_64.AppImage"
```

The build produces a single AppImage in `Source/`. The alternative `build_appimage.sh` uses the official `appimagetool` when available. The C sorter contains embedded Bash bytes; the build scripts regenerate them after changes to the shell source.

## Publishing releases

Publish each new version as a **new GitHub Release with a unique tag** and include the versioned x86-64 `.AppImage` asset. Automatic AppImage updates depend on the latest stable release containing a valid AppImage with the expected filename, not on separate `Sorter` and `Sorter.Config` release assets.

## Troubleshooting

- **AppImage will not open:** Confirm it is executable, the system is x86-64 with a compatible glibc version, and X11/XWayland is available.
- **Files are not moving:** Check that sorting is running, the file matches an enabled rule, and the watched folder and destination are accessible.
- **External-drive destination fails:** Mount the drive and verify write permission.
- **Update fails:** Confirm the latest published release contains the correctly named AppImage and that the installation directory is writable. Older non-AppImage versions require a one-time manual upgrade.
- **Configuration appears missing:** Inspect `~/.config/sorter-config/` (or your configured XDG config home), and use Config to review watched folders and rules.

## License and attribution

Licensed under the [MIT License](./LICENSE).

## DISCLAIMER: This project was only made possible using ChatGPT-6.
