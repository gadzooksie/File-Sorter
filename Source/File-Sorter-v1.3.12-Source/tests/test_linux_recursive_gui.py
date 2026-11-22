"""Actual Linux AppImage GUI per-rule checkbox smoke test under Xvfb."""
import os,subprocess,tempfile,time,signal
from pathlib import Path
from Xlib import X,display as xdisplay,protocol

APP=os.environ.get('FILE_SORTER_BINARY','/mnt/data/File-Sorter-v1.3.12-x86_64.AppImage')
def eventually(fn,label,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            r=fn()
            if r:return r
        except Exception:pass
        time.sleep(.12)
    raise AssertionError('Timeout: '+label)
def click(d,w,x,y):
    ev=protocol.event.ButtonPress(time=X.CurrentTime,root=d.screen().root,window=w,child=X.NONE,
        same_screen=1,root_x=x,root_y=y,event_x=x,event_y=y,state=0,detail=1)
    w.send_event(ev,event_mask=X.ButtonPressMask,propagate=False);d.flush();time.sleep(.14)
with tempfile.TemporaryDirectory() as temp:
    home=Path(temp)/'home';home.mkdir();(home/'Downloads').mkdir()
    cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
    (cfg/'auto-update.txt').write_text('off\n')
    (cfg/'directories.txt').write_text('~/Downloads\n')
    (cfg/'rules.tsv').write_text('watch\t*.zip\t~/Sorted/Zips\tmove\nwatch\t*.txt\t~/Sorted/Text\tmove\n')
    env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'DISPLAY':':143'}
    auth=Path(temp)/'.Xauthority';auth.touch();env['XAUTHORITY']=str(auth);os.environ['XAUTHORITY']=str(auth)
    server=subprocess.Popen(['Xvfb',':143','-screen','0','1600x1000x24','-nolisten','tcp'],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    proc=None
    try:
        time.sleep(.4)
        proc=subprocess.Popen([APP],env=env,preexec_fn=os.setsid,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        d=xdisplay.Display(':143')
        main=eventually(lambda:next((w for w in d.screen().root.query_tree().children
                            if w.get_wm_name()=='File Sorter v1.3.12'),None),'menu')
        click(d,main,125,357)
        conf=eventually(lambda:next((w for w in main.query_tree().children
                            if 'Configuration Editor' in (w.get_wm_name() or '')),None),'Config')
        click(d,conf,310,116) # Sorting Rules
        click(d,conf,50,265) # first row [ ] checkbox
        def first_checked():
            lines=[ln.split('\t') for ln in (cfg/'rules.tsv').read_text().splitlines() if not ln.startswith('#')]
            return len(lines)==2 and len(lines[0])==8 and lines[0][6]=='1' and lines[1][6]=='0'
        eventually(first_checked,'first recursive enabled while second stays disabled')
        click(d,conf,50,265)
        def first_unchecked():
            lines=[ln.split('\t') for ln in (cfg/'rules.tsv').read_text().splitlines() if not ln.startswith('#')]
            return len(lines)==2 and lines[0][6]=='0' and lines[1][6]=='0'
        eventually(first_unchecked,'checkbox toggles off')
        click(d,conf,140,265) # select first row
        click(d,conf,810,350) # expand details
        click(d,conf,990,390) # Sources pane
        click(d,conf,800,469) # recursive check in editor
        click(d,conf,920,601) # save
        eventually(first_checked,'editor checkbox saved')
        print('PASS Linux AppImage: per-row checkbox toggles on/off and editor checkbox saves')
    finally:
        if proc and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
        server.terminate();server.wait(timeout=3)
