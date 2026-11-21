import os, subprocess, tempfile, time, signal
from pathlib import Path
from Xlib import X,display as xdisplay,protocol,XK
APP='/mnt/data/File-Sorter-v1.3.9-x86_64.AppImage'
def eventually(fn, label,sec=8):
 limit=time.monotonic()+sec
 while time.monotonic()<limit:
  try:
   result=fn()
   if result:return result
  except Exception:pass
  time.sleep(.12)
 raise AssertionError('Timed out '+label)
def click(d,w,x,y):
 event=protocol.event.ButtonPress(time=X.CurrentTime,root=d.screen().root,window=w,child=X.NONE,same_screen=1,root_x=x,root_y=y,event_x=x,event_y=y,state=0,detail=1)
 w.send_event(event,event_mask=X.ButtonPressMask);d.flush();time.sleep(.18)
def key(d,w,k,state=0):
 code=d.keysym_to_keycode(XK.string_to_keysym(k))
 if not code:raise AssertionError('Unknown key '+k)
 e=protocol.event.KeyPress(time=X.CurrentTime,root=d.screen().root,window=w,child=X.NONE,same_screen=1,root_x=1,root_y=1,event_x=1,event_y=1,state=state,detail=code)
 w.send_event(e,event_mask=X.KeyPressMask);d.flush();time.sleep(.075)
with tempfile.TemporaryDirectory() as t:
 home=Path(t)/'home';home.mkdir();cfg=home/'.config/sorter-config';cfg.mkdir(parents=True)
 (home/'Downloads').mkdir();(home/'Documents').mkdir()
 (cfg/'auto-update.txt').write_text('off\n');(cfg/'directories.txt').write_text('~/Downloads\n')
 (cfg/'rules.tsv').write_text('watch\t*.zip\t~/Downloads/Archives\tarchive\nwatch\tfilename.zip\t~/Sorted/Special\tmove\n')
 xauth=Path(t)/'.Xauthority';xauth.touch();os.environ['XAUTHORITY']=str(xauth)
 env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'DISPLAY':':139'}
 server=subprocess.Popen(['Xvfb',':139','-screen','0','1600x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 proc=None
 try:
  time.sleep(.4);proc=subprocess.Popen([APP],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=os.setsid)
  d=xdisplay.Display(':139')
  main=eventually(lambda:next((w for w in d.screen().root.query_tree().children if w.get_wm_name()=='File Sorter v1.3.9'),None),'menu')
  click(d,main,125,357)
  conf=eventually(lambda:next((w for w in main.query_tree().children if 'Configuration Editor' in (w.get_wm_name() or '')),None),'config')
  click(d,conf,310,117)  # sorting rules
  click(d,conf,190,270)  # first rule
  click(d,conf,812,350)  # expand details
  click(d,conf,1000,388) # priority / sources
  # Move rule 1 down; it should become position 2/2, not a manual number.
  click(d,conf,468,598)  # MOVE DOWN
  def saved():
   text=(cfg/'rules.tsv').read_text()
   return text.startswith('# rule-order: position') and text.index('filename.zip')<text.index('*.zip')
  eventually(saved,'ordered rules saved')
  lines=[line for line in (cfg/'rules.tsv').read_text().splitlines() if line and not line.startswith('#')]
  assert lines[0].split('\t')[1]=='filename.zip',lines
  assert lines[0].split('\t')[4]=='2',lines
  assert lines[1].split('\t')[4]=='1',lines
  print('PASS Linux GUI reorders rank 1/2 and 2/2:',lines)
  # Screenshot shows the actual two-item ranked list and priority card.
  click(d,conf,812,350)  # expand details
  click(d,conf,1000,388) # Priority / Sources
  subprocess.run(['scrot','-z','-o','/mnt/data/File-Sorter-v1.3.9-Linux-Priority-Preview.png'],env=env,timeout=7)
 finally:
  if proc and proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.communicate(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
  server.terminate();server.wait(timeout=3)
