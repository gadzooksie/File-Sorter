#!/usr/bin/env python3
"""Xdnd to the unified parent X11 window must still reach embedded Config."""
import os,signal,subprocess,tempfile,time,shutil
from pathlib import Path
from urllib.parse import quote
from Xlib import X,Xatom,display as xd,protocol
ROOT=Path(__file__).resolve().parent
APP=Path(os.environ.get('FILE_SORTER_BINARY', str(ROOT/'File-Sorter-v1.3.7-x86_64.AppImage')))

def click(d,w,x,y):
    e=protocol.event.ButtonPress(time=X.CurrentTime,root=d.screen().root,window=w,child=X.NONE,
      same_screen=1,root_x=x,root_y=y,event_x=x,event_y=y,state=0,detail=1)
    w.send_event(e,event_mask=X.ButtonPressMask);d.flush()
def wait(f,description):
    for _ in range(100):
        try:
            r=f()
            if r:return r
        except Exception: pass
        time.sleep(.1)
    raise AssertionError('Timeout: '+description)

def send_dnd(d,host,owner,uri,trace):
    xdnd_sel=d.intern_atom('XdndSelection')
    uri_atom=d.intern_atom('text/uri-list')
    owner.set_selection_owner(xdnd_sel,X.CurrentTime)
    assert d.get_selection_owner(xdnd_sel).id==owner.id
    def msg(kind,values):
        ev=protocol.event.ClientMessage(window=host,client_type=d.intern_atom(kind),data=(32,values))
        host.send_event(ev,event_mask=X.NoEventMask)
        d.flush()
    msg('XdndEnter',[owner.id,5<<24,uri_atom,0,0])
    msg('XdndPosition',[owner.id,0,0,0,d.intern_atom('XdndActionCopy')])
    msg('XdndDrop',[owner.id,0,X.CurrentTime,0,0])
    deadline=time.monotonic()+6
    finished=False;requested=False;accepted=False
    while time.monotonic()<deadline and not finished:
        if not d.pending_events():
            time.sleep(.07);continue
        e=d.next_event()
        if e.type==X.SelectionRequest:
            requested=True
            assert e.selection==xdnd_sel
            target=e.requestor
            prop=e.property or uri_atom
            target.change_property(prop,uri_atom,8,('file://'+quote(str(uri))+'\r\n').encode())
            e2=protocol.event.SelectionNotify(time=e.time,requestor=target,
                selection=e.selection,target=e.target,property=prop)
            target.send_event(e2,event_mask=X.NoEventMask)
            d.flush()
            trace.append('SelectionRequest handled')
        elif e.type==X.ClientMessage and e.client_type==d.intern_atom('XdndStatus'):
            trace.append('XdndStatus')
        elif e.type==X.ClientMessage and e.client_type==d.intern_atom('XdndFinished'):
            trace.append('XdndFinished')
            accepted=bool(e.data[1][1]&1) if hasattr(e,'data') else True
            finished=True
    return requested,finished,accepted

with tempfile.TemporaryDirectory(prefix='fs-dnd-') as tmp:
    root=Path(tmp);home=root/'home';home.mkdir()
    (home/'Downloads').mkdir();(home/'Documents').mkdir()
    cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
    (cfg/'auto-update.txt').write_text('off\n')
    (cfg/'directories.txt').write_text(f'{home}/Downloads\n{home}/Documents\n')
    shutil.copy(ROOT/'defaults/sorter-config/rules.tsv',cfg/'rules.tsv')
    xauth=root/'.Xauthority';xauth.touch();os.environ['XAUTHORITY']=str(xauth)
    env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'DISPLAY':':139'}
    xvfb=subprocess.Popen(['Xvfb',':139','-screen','0','1600x1000x24','-nolisten','tcp'],stderr=subprocess.DEVNULL)
    app=None
    try:
        time.sleep(.5)
        app=subprocess.Popen([str(APP)],env=env,preexec_fn=os.setsid,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        d=xd.Display(':139')
        host=wait(lambda: next((w for w in d.screen().root.query_tree().children if (w.get_wm_name() or '').startswith('File Sorter v1.3.7')),None),'launcher')
        click(d,host,126,354)
        editor=wait(lambda:next((w for w in host.query_tree().children if (w.get_wm_name() or '')=='File Sorter - Configuration Editor'),None),'Config embedded')
        wait(lambda:editor.get_attributes().map_state==X.IsViewable,'Config visible')
        source=d.screen().root.create_window(0,0,1,1,0,0,window_class=X.InputOutput,
                                             event_mask=X.PropertyChangeMask)
        file=home/'Downloads/sample.part.tar.xz'
        file.write_text('sample')
        trace=[]
        # The file drop should detect the compound *.tar.xz extension.
        print('Sending file drop to top-level shell')
        print('file',send_dnd(d,host,source,file,trace),trace)
        assert 'SelectionRequest handled' in trace,trace
        assert 'XdndFinished' in trace,trace
        assert '*.tar.xz' not in (cfg/'rules.tsv').read_text(), 'Must not auto-save rule on drop'
        dest=home/'Other Folder';dest.mkdir()
        trace=[]
        print('Sending destination folder drop to top-level shell')
        print('folder',send_dnd(d,host,source,dest,trace),trace)
        assert 'XdndFinished' in trace,trace
        # Save the selected rule after sample and destination drops.
        click(d,editor,918,590)
        wait(lambda:'*.tar.xz' in (cfg/'rules.tsv').read_text(),'rule saved after drag and drop')
        assert '~/Other Folder' in (cfg/'rules.tsv').read_text()
        assert file.is_file(), 'Config must not move sample files'
        assert len([w for w in d.screen().root.query_tree().children if 'File Sorter' in (w.get_wm_name() or '')])==1
        print('PASS: embedded Config accepts file and folder drops through the single main window')
    finally:
        if app and app.poll() is None:
            os.killpg(app.pid,signal.SIGTERM)
            try:app.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(app.pid,signal.SIGKILL);app.communicate(timeout=3)
        xvfb.terminate();xvfb.wait(timeout=3)
