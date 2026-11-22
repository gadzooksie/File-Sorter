"""Exercise real Linux AppImage per-rule overwrite row and editor controls."""
import os,subprocess,tempfile,time,signal
from pathlib import Path
from Xlib import X,display as xdisplay,protocol

APP=os.environ.get('FILE_SORTER_BINARY','/mnt/data/File-Sorter-v1.3.12-x86_64.AppImage')
def eventually(fn,label,timeout=9):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            result=fn()
            if result:return result
        except Exception:pass
        time.sleep(.12)
    raise AssertionError('Timeout: '+label)
def click(d,w,x,y):
    ev=protocol.event.ButtonPress(time=X.CurrentTime,root=d.screen().root,window=w,
        child=X.NONE,same_screen=1,root_x=x,root_y=y,event_x=x,event_y=y,state=0,detail=1)
    w.send_event(ev,event_mask=X.ButtonPressMask,propagate=False);d.flush();time.sleep(.15)
with tempfile.TemporaryDirectory(prefix='linux-overwrite-ui-') as temp:
    home=Path(temp)/'home';home.mkdir();(home/'Downloads').mkdir()
    cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
    (cfg/'auto-update.txt').write_text('off\n')
    (cfg/'overwrite-files.txt').write_text('off\n')
    (cfg/'directories.txt').write_text('~/Downloads\n')
    (cfg/'rules.tsv').write_text('watch\t*.zip\t~/Sorted/Zips\tmove\nwatch\t*.txt\t~/Sorted/Text\tmove\n')
    auth=Path(temp)/'.Xauthority';auth.touch()
    env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'DISPLAY':':149','XAUTHORITY':str(auth)}
    os.environ['XAUTHORITY']=str(auth)
    server=subprocess.Popen(['Xvfb',':149','-screen','0','1600x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    proc=None
    try:
        time.sleep(.45)
        proc=subprocess.Popen([APP],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,preexec_fn=os.setsid)
        d=xdisplay.Display(':149')
        main=eventually(lambda:next((w for w in d.screen().root.query_tree().children if w.get_wm_name()=='File Sorter v1.3.12'),None),'launcher')
        click(d,main,125,357)
        conf=eventually(lambda:next((w for w in main.query_tree().children if 'Configuration Editor' in (w.get_wm_name() or '')),None),'Config')
        click(d,conf,310,116) # Sorting rules
        def lines():return [line.split('\t') for line in (cfg/'rules.tsv').read_text().splitlines() if line and not line.startswith('#')]
        click(d,conf,81,265) # Enable first row overwrite: requires confirmation
        assert len(lines()[0])==4,'First click should not enable overwriting without confirmation'
        click(d,conf,81,265)
        eventually(lambda:len(lines()[0])==8 and lines()[0][7]=='1' and lines()[1][7]=='0','overwrite flag saved only for first rule')
        click(d,conf,81,265) # Off takes one click
        eventually(lambda:lines()[0][7]=='0','turn off without confirmation')
        click(d,conf,146,265) # choose first row
        click(d,conf,805,350) # details
        click(d,conf,985,388) # priority / sources
        click(d,conf,804,495) # overwrite checkbox on editor
        click(d,conf,920,601) # save rule
        eventually(lambda:lines()[0][7]=='1','editor overwrite enabled')
        # Bulk: mixed -> confirm twice -> all ON -> off once.
        click(d,conf,907,165)
        assert lines()[1][7]=='0','Bulk enable must require confirmation'
        click(d,conf,907,165)
        eventually(lambda:all(line[7]=='1' for line in lines()),'bulk overwrite all enabled')
        click(d,conf,907,165)
        eventually(lambda:all(line[7]=='0' for line in lines()),'bulk overwrite all disabled')
        print('PASS actual AppImage: R/O per-rule list, editor, bulk toggle and confirmation')
    finally:
        if proc and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
        server.terminate();server.wait(timeout=3)
