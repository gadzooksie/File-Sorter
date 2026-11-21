"""Smoke-test Windows/macOS Tk rule-position UI under a Linux virtual display."""
from pathlib import Path
import os, subprocess, sys, tempfile
root=Path(__file__).resolve().parents[1]
for platform,folder in (('Windows',root/'windows/src'),('macOS',root/'macos/File Sorter.app/Contents/Resources/src')):
    sys.path.insert(0,str(folder))
    import tkinter as tk
    import file_sorter_app as ui
    from sorter_core import Rule, save_rules
    with tempfile.TemporaryDirectory() as tmp:
        home=Path(tmp);os.environ['HOME']=str(home);os.environ['XDG_CONFIG_HOME']=str(home/'.config')
        config=home/'.config/sorter-config';config.mkdir(parents=True)
        (config/'auto-update.txt').write_text('off\n')
        save_rules(config/'rules.tsv',[Rule('watch','*.zip','~/Sorted/Archives'),Rule('watch','filename.zip','~/Sorted/Special')])
        parent=tk.Tk();app=ui.FileSorterApp(parent)
        assert app.position_label.get().startswith('New rule:'),app.position_label.get()
        app.show('config');app.config_page('rules')
        assert app.rule_list.get(0).startswith('1/2'), app.rule_list.get(0)
        assert app.rule_list.get(1).startswith('2/2'), app.rule_list.get(1)
        app.rule_list.selection_set(1);app._select_rule()
        assert app.position_label.get().startswith('2/2'),app.position_label.get()
        app.move_rule(-1)
        assert app.position_label.get().startswith('1/2'),app.position_label.get()
        assert app.rule_list.get(0).startswith('1/2'),app.rule_list.get(0)
        assert (config/'rules.tsv').read_text().index('filename.zip') < (config/'rules.tsv').read_text().index('*.zip')
        app.on_close()
    sys.modules.pop('sorter_core',None);sys.modules.pop('file_sorter_app',None);sys.path.pop(0)
    print(platform,'Tk positional priority GUI PASS')
