#!/usr/bin/env python3
"""Use the approved File Sorter icon (PNG and SVG are versioned in assets/).

The icon is deliberately white on a transparent background; do not add a fill.
"""
from pathlib import Path
from PIL import Image
icon=Path(__file__).with_name('file-sorter.png')
assert icon.exists(), f'Missing approved icon: {icon}'
with Image.open(icon) as img:
    assert img.mode == 'RGBA' and img.getpixel((0, 0))[3] == 0
print('Using approved icon:', icon)
