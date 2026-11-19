#!/usr/bin/env python3
"""End-to-end window-navigation check against the real File Sorter AppImage."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from Xlib import X, display as xdisplay, protocol

APP=Path('/mnt/data/File-Sorter-v1.2.2-x86_64.AppImage')

def eventually(test, label, seconds=12):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        val=test()
        if val:return val
        time.sleep(0.14)
    raise AssertionError('Timed out waiting for '+label)

def find_windows(disp, name):
    return [w for w in disp.screen().root.query_tree().children if name in (w.get_wm_name() or '')]

def click(disp, window, x, y):
    event=protocol.event.ButtonPress(time=X.CurrentTime, root=disp.screen().root,
        window=window, child=X.NONE, same_screen=1, root_x=x, root_y=y,
        event_x=x, event_y=y, state=0, detail=1)
    window.send_event(event, propagate=False,event_mask=X.ButtonPressMask)
    disp.flush()

def mapped(window):
    return window.get_attributes().map_state == X.IsViewable

with tempfile.TemporaryDirectory(prefix='sorter-nav-') as tmp:
    base=Path(tmp);home=base/'home';home.mkdir()
    (home/'Downloads').mkdir();(home/'Documents').mkdir()
    cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
    (cfg/'auto-update.txt').write_text('off\n')
    (cfg/'directories.txt').write_text(str(home/'Downloads')+'\n'+str(home/'Documents')+'\n')
    shutil.copy('/mnt/data/fs_appimage_v121/defaults/sorter-config/rules.tsv',cfg/'rules.tsv')
    xauth=base/".Xauthority";xauth.touch();os.environ["XAUTHORITY"]=str(xauth)
    env={**os.environ,'DISPLAY':':129','HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'SCAN_INTERVAL':'1'}
    xvfb=subprocess.Popen(['Xvfb',':129','-screen','0','1366x900x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    app=None
    try:
        time.sleep(0.5)
        app=subprocess.Popen([str(APP)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=os.setsid)
        disp=xdisplay.Display(':129')
        launcher=eventually(lambda: next(iter(find_windows(disp,'File Sorter - Launcher')),None),'launcher')
        print('Launcher:',launcher.id)
        click(disp,launcher,105,233)
        config=eventually(lambda: next(iter(find_windows(disp,'File Sorter - Configuration Editor')),None),'config editor')
        print('Config:',config.id)
        click(disp,config,1000,44)
        eventually(lambda: not mapped(config),'config hidden after back')
        assert mapped(launcher)
        click(disp,launcher,105,233)
        eventually(lambda: mapped(config),'config reopens')
        assert len(find_windows(disp,'File Sorter - Configuration Editor'))==1
        print('Config restores existing window without duplicate')
        click(disp,config,1000,44)
        eventually(lambda: not mapped(config),'config hides second time')
        click(disp,launcher,103,145)
        sorter=eventually(lambda: next(iter(find_windows(disp,'File Sorter')),None) if find_windows(disp,'File Sorter') else None,'sorter')
        # Filter title: launcher and editor also contain prefix.
        sorter=eventually(lambda: next((w for w in find_windows(disp,'File Sorter') if w.get_wm_name()=='File Sorter'),None),'sorter gui')
        print('Sorter:',sorter.id)
        click(disp,sorter,105,244) # start worker
        (home/'Downloads'/'first.txt').write_text('test')
        eventually(lambda: (home/'Sorted/Text Files/txt/first.txt').is_file(),'first file moved')
        click(disp,sorter,846,43)
        eventually(lambda: not mapped(sorter),'sorter hidden after back')
        assert mapped(launcher)
        (home/'Downloads'/'second.txt').write_text('test')
        eventually(lambda: (home/'Sorted/Text Files/txt/second.txt').is_file(),'sorting continues while menu is open')
        print('Sorter worker continues in menu')
        click(disp,launcher,103,145)
        eventually(lambda: mapped(sorter),'sorter window reopens')
        assert len([w for w in find_windows(disp,'File Sorter') if w.get_wm_name()=='File Sorter'])==1
        print('Sorter restores same window without duplicate')
        click(disp,sorter,342,244)  # Stop sorter worker
        print('PASS navigation and sorting integration')
        click(disp,sorter,105,244)  # Start again to test launcher shutdown
        click(disp,sorter,846,43)  # Hide sorter without closing it
        eventually(lambda: not mapped(sorter),'sorter hidden for shutdown')
        wm_prot=disp.intern_atom('WM_PROTOCOLS');wm_del=disp.intern_atom('WM_DELETE_WINDOW')
        event=protocol.event.ClientMessage(window=launcher, client_type=wm_prot,
            data=(32,[wm_del,X.CurrentTime,0,0,0]))
        launcher.send_event(event,event_mask=X.NoEventMask,propagate=False)
        disp.flush()
        eventually(lambda: app.poll() is not None,'launcher shutdown stops children',seconds=10)
        (home/'Downloads'/'after-exit.txt').write_text('should not be moved')
        time.sleep(1.4)
        assert (home/'Downloads'/'after-exit.txt').exists(), 'Background sorter remained after app exit'
        print('PASS closing launcher stops hidden sorter')
    finally:
        if app is not None and app.poll() is None:
            os.killpg(app.pid,signal.SIGTERM)
            try:app.communicate(timeout=4)
            except subprocess.TimeoutExpired:os.killpg(app.pid,signal.SIGKILL);app.communicate(timeout=4)
        xvfb.terminate()
        try:xvfb.communicate(timeout=3)
        except subprocess.TimeoutExpired:xvfb.kill();xvfb.communicate()
