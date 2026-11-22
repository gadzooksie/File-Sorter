# File Sorter v1.3.11 — Per-Rule Overwrite Controls

Changes since **v1.3.10** for Linux, Windows, and macOS.

## New: overwrite option for each rule

- Every sorting rule now has an **Overwrite existing files** checkbox. New rules start **unchecked**.
- In the Linux Sorting Rules list, column **R** toggles recursive subfolder searching and **O** toggles overwriting. The editor also offers both checkboxes separately. Enabling overwrite directly from the Linux list requires a second confirmation click; an explicit rule edit is confirmed by saving.
- Windows and macOS show both `[R]` and `[O]` indicators in the rule list. They can be clicked individually, or controlled from the rule editor. Enabling overwrite prompts for confirmation.
- Only the **first matching rule** determines whether a destination file may be replaced. Another rule with overwrite enabled cannot override a higher-priority rule's OFF setting.
- Archive New/Old reclassification uses that archive rule's overwrite setting as well.
- Existing collision safeguards remain: an overwrite rule never replaces directories, symbolic links or special files, and an OFF rule skips existing targets.

## Previous global toggle and migration

- The old global Overwrite Files toggle is now **Overwrite All Rules**, a bulk shortcut for enabling or disabling all existing rules. Individual rules remain independent afterwards; mixed settings are shown clearly.
- For existing 4-, 6-, or 7-column rule files, the prior `overwrite-files.txt` global ON/OFF setting is honored as the initial value for those old rules when loaded. Thus users who opted into global overwriting retain that behavior until they customize their rules.
- New rule files include an eighth tab-separated `overwrite` column (`0` or `1`); per-rule settings take precedence over the old global file. Missing/invalid overwrite flags on a new 8-column row are rejected; new rules start OFF.
- The previous seventh-column **Search subfolders** setting and all rule ranks, per-rule source folders, and destination settings remain intact.

## Release format

- Publish the **Linux AppImage**, **Windows portable ZIP**, **macOS portable ZIP**, and **SHA256SUMS.txt** as **separate GitHub release assets**. The source ZIP can also be published separately.
- `File-Sorter-v1.3.11-Complete-Release.zip` is an additional convenience bundle containing these same distributable files, the source ZIP, main README, and these notes; it does not replace individual release assets.

## Verification

- Cross-platform Python sorting tests cover mixed overwrite settings, old-setting migration, collisions and archive aging.
- Linux worker, AppImage, GUI interactions, and regression tests cover per-rule overwrite independently of the global legacy setting.
- Native Windows/macOS device verification is still recommended before public release.
