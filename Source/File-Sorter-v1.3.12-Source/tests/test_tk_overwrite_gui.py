"""Exercise per-rule overwrite in both identical portable GUI source bundles."""
from pathlib import Path
import os, subprocess, sys, tempfile, time, types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
server=subprocess.Popen(['Xvfb',':148','-screen','0','1600x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    time.sleep(.4)
    os.environ['DISPLAY']=':148'
    for label,folder in [('Windows',ROOT/'windows/src'),('macOS',ROOT/'macos/File Sorter.app/Contents/Resources/src')]:
        with tempfile.TemporaryDirectory(prefix='tk-overwrite-') as temp:
            os.environ['HOME']=temp;os.environ['XDG_CONFIG_HOME']=str(Path(temp)/'.config')
            config=Path(temp)/'.config/sorter-config';config.mkdir(parents=True)
            (config/'auto-update.txt').write_text('off\n')
            sys.path.insert(0,str(folder))
            import tkinter as tk
            import file_sorter_app as ui
            from sorter_core import Rule,save_rules,load_rules
            save_rules(config/'rules.tsv',[Rule('watch','*.zip','~/Sorted/Zips'),Rule('watch','*.txt','~/Sorted/Text')])
            window=tk.Tk()
            try:
                app=ui.FileSorterApp(window)
                app.show('config');app.config_page('rules');window.update()
                assert all(not rule.overwrite for rule in app.rules)
                assert '[ ] [ ]' in app.rule_list.get(0)
                bbox=app.rule_list.bbox(0);assert bbox
                event=types.SimpleNamespace(x=43,y=bbox[1]+3)
                with patch.object(ui.messagebox,'askyesno',return_value=True) as confirm:
                    assert app._toggle_list_rule_flag(event)=='break'
                    confirm.assert_called_once()
                assert '[O]' in app.rule_list.get(0)
                assert load_rules(config/'rules.tsv')[0].overwrite is True
                assert load_rules(config/'rules.tsv')[1].overwrite is False
                # Editor has its own persisted checkbox and defaults it OFF.
                app.new_rule(); assert app.rule_overwrite.get() is False
                app.pattern.set('*.cbz');app.destination.set('~/Sorted/CBZ');app.rule_overwrite.set(True)
                with patch.object(ui.messagebox,'askyesno',return_value=True):
                    app.save_rule()
                assert load_rules(config/'rules.tsv')[-1].overwrite is True
                # Bulk action enables all; individual override turns one off.
                with patch.object(ui.messagebox,'askyesno',return_value=True):
                    app.toggle_overwrite()
                assert all(r.overwrite for r in load_rules(config/'rules.tsv'))
                app.rule_list.selection_clear(0,'end');app.rule_list.selection_set(1);app._select_rule()
                app.rule_overwrite.set(False);app.save_rule()
                assert [r.overwrite for r in load_rules(config/'rules.tsv')]==[True,False,True]
                assert 'MIXED' in app.overwrite_button.cget('text')
                app.on_close()
            finally:
                try:window.destroy()
                except Exception:pass
                for name in ('file_sorter_app','sorter_core'):sys.modules.pop(name,None)
                sys.path.pop(0)
            print('PASS Tk',label,'per-rule row, editor and bulk overwrite controls')
finally:
    server.terminate();server.wait(timeout=4)
