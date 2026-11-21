#!/usr/bin/env python3
"""Regenerate embedded Bash array in Sorter_Source.c from Sorter_Embedded.sh."""
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent
worker = (root / 'Sorter_Embedded.sh').read_bytes()
source = root / 'Sorter_Source.c'
content = source.read_text(encoding='utf-8')
chunks = [
    '    ' + ', '.join(map(str, worker[start:start + 24])) + ','
    for start in range(0, len(worker), 24)
]
result, changed = re.subn(
    r'static const unsigned char embedded_script\[\] = \{.*?\};',
    lambda _: 'static const unsigned char embedded_script[] = {\n' + '\n'.join(chunks) + '\n};',
    content, count=1, flags=re.S,
)
if changed != 1:
    raise SystemExit('Expected to find exactly one embedded_script array')
if result != content:
    source.write_text(result, encoding='utf-8')
print(f'Embedded {len(worker)} Bash bytes in Sorter_Source.c')
