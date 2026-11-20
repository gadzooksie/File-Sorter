from pathlib import Path
import importlib.util
import os, sys, tkinter as tk, plistlib
from PIL import Image
ROOT=Path(__file__).resolve().parent
with Image.open(ROOT/'windows/assets/file-sorter.ico') as img:
    assert img.format=='ICO' and img.size==(256,256)
with Image.open(ROOT/'macos/assets/File-Sorter.icns') as img:
    assert img.format=='ICNS' and img.size==(1024,1024)
with (ROOT/'macos/File Sorter.app/Contents/Info.plist').open('rb') as f:
    p=plistlib.load(f)
assert p['CFBundleIconFile']=='File-Sorter.icns' and p['CFBundleVersion']=='1.3.5'
with Image.open(ROOT/'linux/assets/file-sorter.png') as img:
    assert img.getpixel((0,0))[3]==0
for platform,source in [
    ('Windows',ROOT/'windows/src'),
    ('macOS',ROOT/'macos/File Sorter.app/Contents/Resources/src')]:
    sys.path.insert(0,str(source))
    spec=importlib.util.spec_from_file_location('file_sorter_app_'+platform,source/'file_sorter_app.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root=tk.Tk();root.withdraw()
    try:
        assert mod.apply_file_sorter_icon(root), platform
        icon=root._file_sorter_icon
        assert icon.width()==1024 and icon.height()==1024
        print('PASS',platform,'Tk icon has size',icon.width(),'x',icon.height())
    finally:
        root.destroy()
print('PASS format/native icon checks')
