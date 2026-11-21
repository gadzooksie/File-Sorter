#!/bin/sh
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$BASE/File Sorter.app/Contents/MacOS/File Sorter" "$@"
