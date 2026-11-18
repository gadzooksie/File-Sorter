First repo, so expect discrepancies from regular repos.

# File Sorter

File Sorter runs on Linux x86-64 (tested with Xvfb/X11; intended for SteamOS Desktop Mode).
It has two graphical applications and a Python 3 update helper:

- `Sorter` - GUI that starts/stops the file sorter and shows activity.
- `Sorter.Config` - GUI for choosing watched folders, patterns and destination folders.
- `Sorter.Updater` - local updater used by both GUIs.

## Install

Keep all three files **together in one folder** and make them executable:

```bash
chmod +x Sorter Sorter.Config Sorter.Updater
./Sorter.Config
./Sorter --autostart
```

_(Note: Not needed if your OS supports automatic executable permissions)_

Python 3 (standard library only) is required for update functionality; no API key is needed.
The user must be able to write to the folder containing the executables.

## Automatic updates

The applications automatically check for a new stable release **at most once every six hours** when launched. Automatic updates are initially enabled and can be disabled in `Sorter.Config` with **AUTO UPDATE: ON/OFF**. You can also select **UPDATE NOW** in either GUI.

The updater uses https://api.github.com/repos/gadzooksie/File-Sorter/releases/latest and expects two release assets with the **exact** names `Sorter` and `Sorter.Config`. The files must be Linux x86-64 ELF executables. GitHub's asset SHA-256 digest and size are checked before replacement. Both files are staged before either is replaced; the updater attempts to roll back if a replacement fails. If a release does not have those two valid assets, installation is refused.

An optional asset named `Sorter.Updater` is not currently updated automatically. To replace the helper, distribute an updated copy with a future release as needed.

The update mechanism cannot be added retroactively to v1.0.0: users need to **install this updated package once**. Thereafter the running applications can update their own `Sorter` and `Sorter.Config` executables from new published stable GitHub releases. Restart the applications after an update to use the new binaries; the currently running sorter continues using the old version until restarted.

The updater does not modify any user sorting rules or watched-folder settings.

## Configuration and migration

Config files are stored in `~/.config/sorter-config/` (or `$XDG_CONFIG_HOME/sorter-config/`):

- `directories.txt` - watched paths, one per line.
- `rules.tsv` - ordered sorting rules, four tab-separated fields: scope, pattern, destination, mode.
- `auto-update.txt` - `on` or `off` (missing means on).
- `installed-release.json` - latest installed release tag, maintained by the updater.

On first launch, settings from `~/.config/general-cleanup-gui/` are copied to `~/.config/sorter-config/` **only when the new files do not yet exist**. The old settings are left intact. Changes made by an older app after migration are not merged automatically; close older versions before migrating.

## Build from source

Sources are in `src/`. To build them with gcc and Xlib headers:

```bash
cd src
bash build.sh
```

The `Sorter_Embedded.sh` file is included for reference. The Bash sorter is embedded in the C main app as a byte array and should be regenerated after editing the shell script.

## Release publishing

Create a **new GitHub release with a new tag** for every published version. Each release must include executable assets named exactly `Sorter` and `Sorter.Config`. Use GitHub Releases, not arbitrary links or a moving `Update` tag, as the update channel.

The repository's original release is tagged `initial-release`, title `Version 1.0.0`. A GitHub release can reference only one Git tag. A separate `Update` tag cannot be attached as a second tag to that release.

## Troubleshooting

For a manual check from the folder with the programs:

```bash
./Sorter.Updater --app-dir . --check
```

To install the latest release:

```bash
./Sorter.Updater --app-dir . --install
```

If the updater reports missing assets or checksums, correct the assets in the newest GitHub release. If an executable is not writable, move the three program files to a folder owned by your user and run them from there.

_`src` Is included with releases in File-Sorter-x.x.x.-OS.zip/File-Sorter-x.x.x.-OS/src/ (Will be added to main soon)_
