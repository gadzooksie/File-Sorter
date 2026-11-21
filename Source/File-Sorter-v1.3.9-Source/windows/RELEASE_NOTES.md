# File Sorter v1.3.9 — Position-Based Sorting Priorities

This release changes how sorting rule priority is chosen in **Linux, Windows, and macOS**. These notes cover changes since v1.3.8.

## Rule priority follows list position

- Rules are now ranked **1/N, 2/N, ... N/N**, where **1/N is the highest priority**.
- The first matching rule in the list determines the destination; there is no separately editable priority number.
- Use the existing **Move Up** and **Move Down** controls to reorder rules and change their precedence immediately for subsequent scans.
- Creating a new rule puts it at the end of the list. Deleting or reordering rules recalculates all visible ranks.
- For example, `*.zip` at `1/79` takes precedence over `filename.zip` at `79/79` when both match.
- A selected rule's rank is also shown in the options editor.

## Configuration migration and compatibility

- Existing v1.3.8 files with manually assigned numeric priorities retain their effective precedence: rules are first ordered by descending old priority, stably, and then assigned their new positional ranks.
- Existing four-column configurations keep their original row order.
- New rule files retain six tab-separated fields, including custom watched folders. The numeric rank column is **derived automatically** from the rule's list position.
- A `# rule-order: position` header distinguishes new positional files from older numeric-priority files; other versions' installations may not understand these new positional semantics.
- Custom watched folders, first-run opt-in monitoring, destination modes, archive handling, and text caret behavior remain available.

## Distribution

- `File-Sorter-v1.3.9-Complete-Release.zip` contains the Linux AppImage, Windows/macOS portable ZIPs, source ZIP, root README, these notes, and SHA-256 checksums.
- Existing user configuration is stored outside the application and is not removed during installation.

## Verification

Sorting precedence, migration of older configurations, source folder isolation, legacy four-column rules, and the Linux native build were tested. Windows/macOS engine tests ran under Linux; native Windows and macOS testing remains recommended.
