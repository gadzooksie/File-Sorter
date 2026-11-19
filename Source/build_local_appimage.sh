#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-/mnt/data/File-Sorter-v1.2.2-x86_64.AppImage}"
gcc -static -O2 -s -Wall -Wextra -o appimage_runtime appimage_runtime.c -lz
python3 pack_squashfs.py File-Sorter.AppDir appimage.squashfs
python3 - "$OUT" <<'PY'
import pathlib,struct,sys
base=pathlib.Path(__file__).resolve().parent if '__file__' in globals() else pathlib.Path.cwd()
elf=bytearray(pathlib.Path('appimage_runtime').read_bytes())
assert elf[:4]==b'\x7fELF'
elf[8:11]=b'AI\x02'
shoff=struct.unpack_from('<Q',elf,40)[0]
shentsize,shnum=struct.unpack_from('<HH',elf,58)
last=shoff+shentsize*shnum
last_off,last_size=struct.unpack_from('<QQ',elf,shoff+(shnum-1)*shentsize+24)
last=max(last,last_off+last_size)
assert last==len(elf), (last,len(elf))
out=pathlib.Path(sys.argv[1])
out.write_bytes(elf+pathlib.Path('appimage.squashfs').read_bytes())
out.chmod(0o755)
print('AppImage built:',out, 'bytes',out.stat().st_size,'SquashFS offset',last)
PY
file "$OUT"
"$OUT" --appimage-offset
"$OUT" --help
