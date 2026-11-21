# File Sorter v1.3.10 — Per-Rule Subfolder Searching

Changes since v1.3.9 for Linux, Windows, and macOS.

## New: Search subfolders checkbox

- Every sorting rule has its own **Search subfolders** checkbox, **unchecked by default** for both new and pre-existing rules.
- The Sorting Rules list displays `[ ]` / `[x]` next to every rule. On Linux you can click the checkbox directly in the list or use the Priority / Sources editor. Windows/macOS also support clicking the list marker or using the rule editor checkbox.
- Only checked rules descend into nested directories; unchecked rules continue to inspect files directly inside their watched folders.
- Recursion respects each rule's **All Watched Folders** or custom source-folder selection and the list-position precedence (`1/N` highest).
- Rule output destinations are excluded from recursive scanning to avoid self-sorting loops. Nested symbolic-link directories are not followed.
- Scan behavior reloads the checkbox state from configuration on the next scan.

## Compatibility

- Older four-column and six-column `rules.tsv` files still load. Existing rules get recursive searching OFF until explicitly enabled.
- New saves use seven tab-separated columns, with `recursive` (`0` or `1`) appended after the existing six columns.
- Existing priorities, rule-specific watched folders, destination modes, archive aging, opt-in first-use, overwriting preference, and caret editing remain available.
- Downgrading to older versions may cause them to skip seven-column rules. Back up `rules.tsv` before downgrading.

## Distribution

- **Publish the Linux AppImage, Windows portable ZIP, macOS portable ZIP, and `SHA256SUMS.txt` individually on GitHub Releases.**
- The additional `File-Sorter-v1.3.10-Complete-Release.zip` is solely a maintainer-convenience archive that includes the separately publishable files plus source ZIP, README, and these notes.

## Testing

Regression tests cover default-OFF migration, mixed recursive and top-level rules, rule-specific source isolation, output-directory exclusion, symbolic-link traversal, and priority behavior. Linux AppImage and Windows/macOS Python engine suites are run on Linux; native Windows/macOS verification is recommended before publishing.
