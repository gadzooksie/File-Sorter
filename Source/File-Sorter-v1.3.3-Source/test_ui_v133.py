import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import tkinter as tk

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'macos'/'File Sorter.app'/'Contents'/'Resources'/'src'
sys.path.insert(0,str(SRC))
import file_sorter_app as a

def check(platform):
    with tempfile.TemporaryDirectory() as home:
        with patch.dict(os.environ,{'HOME':home,'APPDATA':str(Path(home)/'AppData'/'Roaming')},clear=False),patch.object(a.sys,'platform',platform), patch.object(a.messagebox,'askyesno',return_value=True):
            root=tk.Tk()
            app=a.FileSorterApp(root)
            root.update()
            app.show('config'); root.update()
            assert app.overwrite_button.cget('text')=='OVERWRITE FILES: OFF'
            app.toggle_overwrite(); root.update()
            assert app.overwrite_files.get() and app.overwrite_button.cget('text')=='OVERWRITE FILES: ON'
            assert (app.config/'overwrite-files.txt').read_text()=='on\n'
            app.toggle_overwrite();root.update()
            assert not app.overwrite_files.get()
            assert (app.config/'overwrite-files.txt').read_text()=='off\n'
            app.show('sorter');root.update()
            assert 'SKIP existing files' in app.collision_message.get()
            app.show('menu');root.update()
            app.on_close()
            print('PASS GUI',platform)

for platform in ('darwin','win32'):
    check(platform)
