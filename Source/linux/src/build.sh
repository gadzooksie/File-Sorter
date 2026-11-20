#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 sync_embedded.py
python3 sync_updater.py
FLAGS=(-std=c11 -O2 -Wall -Wextra -Wno-misleading-indentation -Wno-unused-function)
gcc "${FLAGS[@]}" -o ../Sorter Sorter_Source.c -lX11
gcc "${FLAGS[@]}" -o ../Sorter.Config Sorter_Config_Source.c -lX11
gcc "${FLAGS[@]}" -o ../File-Sorter-Launcher File_Sorter_Launcher.c -lX11
chmod +x ../Sorter ../Sorter.Config ../File-Sorter-Launcher ../Sorter.Updater
printf 'Built File Sorter v1.3.5: Sorter, Sorter.Config, File-Sorter-Launcher\n'
