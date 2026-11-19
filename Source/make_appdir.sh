#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APPDIR="$HERE/File-Sorter.AppDir"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/file-sorter/defaults" "$APPDIR/usr/share/licenses/File-Sorter"
cp "$HERE/Sorter" "$HERE/Sorter.Config" "$HERE/Sorter.Updater" "$HERE/File-Sorter-Launcher" "$APPDIR/usr/bin/"
cp -r "$HERE/defaults/sorter-config" "$APPDIR/usr/share/file-sorter/defaults/"
cp "$HERE/LICENSE" "$APPDIR/usr/share/licenses/File-Sorter/LICENSE"
cp "$HERE/assets/file-sorter.png" "$APPDIR/file-sorter.png"
cp "$HERE/assets/file-sorter.desktop" "$APPDIR/file-sorter.desktop"
cp "$HERE/assets/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/Sorter" "$APPDIR/usr/bin/Sorter.Config" "$APPDIR/usr/bin/Sorter.Updater" "$APPDIR/usr/bin/File-Sorter-Launcher"
ln -sfn file-sorter.png "$APPDIR/.DirIcon"
cat > "$APPDIR/usr/share/file-sorter/VERSION" <<'EOF'
1.2.3
EOF
printf 'Prepared %s\n' "$APPDIR"
