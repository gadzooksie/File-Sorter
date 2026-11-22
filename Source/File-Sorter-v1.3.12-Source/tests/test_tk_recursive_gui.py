"""Tk rule-list and editor recursive toggle test under Xvfb."""
import os, subprocess, tempfile, time, types
from pathlib import Path
from dataclasses import replace

with tempfile.TemporaryDirectory(prefix='tk-recursive-') as t:
    os.environ['HOME']=t
    os.environ['XDG_CONFIG_HOME']=str(Path(t)/'.config')
    os.environ['DISPLAY']=':146'
    os.environ['XAUTHORITY']=str(Path(t)/'.Xauthority')
    Path(os.environ['XAUTHORITY']).touch()
    proc=subprocess.Popen(['Xvfb',':146','-screen','0','1600x1000x24','-nolisten','tcp'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    root=None
    try:
        time.sleep(.4)
        import sys,tkinter as tk
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows/src'))
        from file_sorter_app import FileSorterApp
        from sorter_core import Rule,save_rules,load_rules
        root=tk.Tk();app=FileSorterApp(root)
        app.show('config');app.config_page('rules')
        app.rules=[Rule('watch','*.zip','~/Sorted/Zips'),Rule('watch','*.txt','~/Sorted/Text')]
        save_rules(app.config/'rules.tsv',app.rules)
        app.refresh_rules();root.update()
        assert '[ ]' in app.rule_list.get(0)
        bbox=app.rule_list.bbox(0);assert bbox
        fake=types.SimpleNamespace(x=11,y=bbox[1]+3)
        assert app._toggle_list_rule_flag(fake)=='break'
        assert '[R]' in app.rule_list.get(0)
        assert load_rules(app.config/'rules.tsv')[0].recursive is True
        assert load_rules(app.config/'rules.tsv')[1].recursive is False
        app.new_rule();assert app.rule_recursive.get() is False
        app.pattern.set('*.cbz');app.destination.set('~/Sorted/CBZ');app.rule_recursive.set(True)
        app.save_rule()
        assert load_rules(app.config/'rules.tsv')[-1].recursive is True
        print('PASS Tk GUI: row checkbox changes only its own rule and new-rule checkbox defaults OFF')
    finally:
        if root:
            try:root.destroy()
            except Exception:pass
        proc.terminate();proc.wait(timeout=3)
