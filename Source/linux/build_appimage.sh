#!/usr/bin/env bash
# Build a type-2 AppImage from the verified AppDir using the official AppImage tools.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
"$HERE/src/build.sh"
"$HERE/make_appdir.sh"
VERSION="$(cat "$HERE/File-Sorter.AppDir/usr/share/file-sorter/VERSION")"
OUT="${1:-$HERE/File-Sorter-v${VERSION}-x86_64.AppImage}"
TOOL="${APPIMAGETOOL:-appimagetool}"
if [[ "$TOOL" == */* ]]; then
  if [[ ! -x "$TOOL" ]]; then
    echo "AppImage tool not executable: $TOOL" >&2
    exit 1
  fi
elif ! command -v "$TOOL" >/dev/null 2>&1; then
  echo "AppImage packaging tool is missing." >&2
  echo "Download the official appimagetool-x86_64.AppImage from:" >&2
  echo "https://github.com/AppImage/appimagetool/releases/tag/1.9.1" >&2
  echo "and set APPIMAGETOOL=/absolute/path/to/appimagetool-x86_64.AppImage" >&2
  echo "For FUSE-free packaging, set APPIMAGE_EXTRACT_AND_RUN=1." >&2
  exit 1
fi
ARCH=x86_64 "$TOOL" "$HERE/File-Sorter.AppDir" "$OUT"
chmod +x "$OUT"
file "$OUT"
echo "Created $OUT"
