#!/usr/bin/env python3
"""Real X11 UI test: 1 WM top-level, navigation, worker continuity, cleanup."""
import os
from pathlib import Path
import shutil,signal,subprocess,tempfile,time
from Xlib import X,display as xdisplay,protocol

ROOT=Path(__file__).resolve().parent
APP=Path(os.environ.get('FILE_SORTER_BINARY', str(ROOT/'File-Sorter.AppDir/AppRun')))

def eventually(test,label,seconds=12):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        try:
            r=test()
            if r:return r
        except (Exception,) as e:
            # Allow races while the X server creates and removes child windows.
            pass
        time.sleep(.12)
    raise AssertionError('Timed out: '+label)

def wm_windows(d):
    return [(w,w.get_wm_name() or '') for w in d.screen().root.query_tree().children]

def app_windows(d):return [(w,n) for w,n in wm_windows(d) if 'File Sorter' in n]

def descendants_named(window,needle):
    return [w for w in window.query_tree().children if needle in (w.get_wm_name() or '')]

def click(d,w,x,y):
    ev=protocol.event.ButtonPress(time=X.CurrentTime,root=d.screen().root,window=w,child=X.NONE,
        same_screen=1,root_x=x,root_y=y,event_x=x,event_y=y,state=0,detail=1)
    w.send_event(ev,event_mask=X.ButtonPressMask,propagate=False);d.flush()

def visible(window):return window.get_attributes().map_state==X.IsViewable

with tempfile.TemporaryDirectory(prefix='single-window-') as tmp:
    base=Path(tmp)
    home=base/'home';home.mkdir();(home/'Downloads').mkdir();(home/'Documents').mkdir()
    cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
    (cfg/'auto-update.txt').write_text('off\n')
    (cfg/'directories.txt').write_text(str(home/'Downloads')+'\n'+str(home/'Documents')+'\n')
    shutil.copy(ROOT/'defaults/sorter-config/rules.tsv',cfg/'rules.tsv')
    xauth=base/".Xauthority";xauth.touch();os.environ["XAUTHORITY"]=str(xauth)
    env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'SCAN_INTERVAL':'1','DISPLAY':':138'}
    env['APPDIR']=str(ROOT/'File-Sorter.AppDir')
    if APP.suffix=='.AppImage':env.pop('APPDIR',None)
    xvfb=subprocess.Popen(['Xvfb',':138','-screen','0','1600x1000x24','-nolisten','tcp'],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    app=None
    try:
        time.sleep(.45)
        app=subprocess.Popen([str(APP)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=os.setsid)
        d=xdisplay.Display(':138')
        main=eventually(lambda: next((w for w,n in app_windows(d) if n=='File Sorter v1.3.5'),None),'main menu')
        print('Main toplevel XID:',hex(main.id))
        assert len(app_windows(d))==1,app_windows(d)
        click(d,main,125,357) # Open Config first
        config=eventually(lambda: next(iter(descendants_named(main,'Configuration Editor')),None),'Config embedded')
        eventually(lambda:visible(config),'config mapped')
        assert len(app_windows(d))==1,app_windows(d)
        print('Config embedded child:',hex(config.id),'single WM window')
        click(d,config,1000,43) # Back
        eventually(lambda:not visible(config),'menu appears after config')
        eventually(lambda:main.get_wm_name()=='File Sorter v1.3.5','menu title')
        click(d,main,125,357)
        eventually(lambda:visible(config),'config restored')
        assert len(descendants_named(main,'Configuration Editor'))==1
        click(d,config,1000,43)
        eventually(lambda:not visible(config),'config hidden second time')
        click(d,main,125,211)  # Sorter
        sorter=eventually(lambda: next((w for w in main.query_tree().children if w.get_wm_name()=="File Sorter"),None),"Sorter embedded")
        eventually(lambda:visible(sorter),'sorter mapped')
        assert len(app_windows(d))==1,app_windows(d)
        print('Sorter embedded child:',hex(sorter.id),'single WM window')
        click(d,sorter,105,244) # start sorter
        (home/'Downloads'/'initial.txt').write_text('sample')
        eventually(lambda:(home/'Sorted/Text Files/txt/initial.txt').is_file(),'file sorted inside sorter page')
        click(d,sorter,846,43)
        eventually(lambda:not visible(sorter),'sorter hidden from menu')
        assert main.get_wm_name()=='File Sorter v1.3.5'
        (home/'Downloads'/'second.txt').write_text('sample')
        eventually(lambda:(home/'Sorted/Text Files/txt/second.txt').is_file(),'sorting continues in menu')
        click(d,main,125,357)
        eventually(lambda:visible(config),'config page mapped')
        (home/'Downloads'/'third.txt').write_text('sample')
        eventually(lambda:(home/'Sorted/Text Files/txt/third.txt').is_file(),'sorting continues while Config visible')
        assert not visible(sorter)
        assert len(app_windows(d))==1,app_windows(d)
        click(d,config,1000,43)
        eventually(lambda:not visible(config),'back menu from Config')
        click(d,main,125,211)
        eventually(lambda:visible(sorter),'sorter restored')
        assert len([w for w in main.query_tree().children if w.get_wm_name()=="File Sorter"])==1,"duplicate child window!"
        print('PASS: Same child instance; sorter kept working across all pages')
        wm_prot=d.intern_atom('WM_PROTOCOLS');wm_del=d.intern_atom('WM_DELETE_WINDOW')
        main.send_event(protocol.event.ClientMessage(window=main,client_type=wm_prot,
            data=(32,[wm_del,X.CurrentTime,0,0,0])),event_mask=X.NoEventMask,propagate=False)
        d.flush()
        eventually(lambda:app.poll() is not None,'launcher exit')
        (home/'Downloads'/'after-close.txt').write_text('stay')
        time.sleep(1.5)
        assert (home/'Downloads'/'after-close.txt').is_file(),'sorter worker leaked after main window closed'
        print('PASS: launcher close terminates worker and all child processes')
    finally:
        if app and app.poll() is None:
            os.killpg(app.pid,signal.SIGTERM)
            try:app.communicate(timeout=4)
            except subprocess.TimeoutExpired:os.killpg(app.pid,signal.SIGKILL);app.communicate(timeout=3)
        xvfb.terminate()
        try:xvfb.wait(timeout=3)
        except subprocess.TimeoutExpired:xvfb.kill();xvfb.wait(timeout=3)
