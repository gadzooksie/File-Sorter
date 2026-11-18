#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
# Requires gcc and Xlib development headers (libx11-dev on Debian).
gcc -std=c11 -O2 -Wall -Wextra -Wno-misleading-indentation -Wno-unused-function -o ../Sorter Sorter_Source.c -lX11
gcc -std=c11 -O2 -Wall -Wextra -Wno-misleading-indentation -Wno-unused-function -o ../Sorter.Config Sorter_Config_Source.c -lX11
chmod +x ../Sorter ../Sorter.Config ../Sorter.Updater
printf 'Built ../Sorter and ../Sorter.Config\n'
