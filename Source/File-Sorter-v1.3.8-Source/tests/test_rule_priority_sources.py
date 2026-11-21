from pathlib import Path
import importlib.util,tempfile,subprocess,os,time,shutil,sys
root=Path('/mnt/data/fs_v138_work')
for platform in ('windows','macos'):
    base=(root/'windows'/'src') if platform=='windows' else (root/'macos'/'File Sorter.app'/'Contents'/'Resources'/'src')
    sys.path.insert(0,str(base))
    import sorter_core as c
    assert c.VERSION=='1.3.8'
    with tempfile.TemporaryDirectory() as t:
        tmp=Path(t);globaldir=tmp/'global';custom=tmp/'only-this';dest1=tmp/'general';dest2=tmp/'special';dest3=tmp/'archive'
        globaldir.mkdir();custom.mkdir();conf=tmp/'config';conf.mkdir()
        c.save_directories(conf/'directories.txt',[str(globaldir)])
        r=[c.Rule('watch','*.zip',str(dest1),'move',20,'-'),c.Rule('watch','filename.zip',str(dest2),'move',5,'-'),c.Rule('watch','*.cbz',str(dest3),'move',30,str(custom))]
        c.save_rules(conf/'rules.tsv',r)
        assert [x.priority for x in c.load_rules(conf/'rules.tsv')]==[20,5,30]
        assert c.load_rules(conf/'rules.tsv')[2].sources==str(custom)
        (globaldir/'filename.zip').write_text('global')
        (custom/'comic.cbz').write_text('custom')
        (globaldir/'not_here.cbz').write_text('never move me')
        c.SortEngine(config=conf).scan_once()
        assert (dest1/'filename.zip').read_text()=='global'
        assert (dest3/'comic.cbz').read_text()=='custom'
        assert (globaldir/'not_here.cbz').is_file()
        (custom/'hello.zip').write_text('not global')
        c.SortEngine(config=conf).scan_once()
        assert (custom/'hello.zip').exists(), 'global rule must not monitor custom-only directory'
        # Rule-specific source works without globally watched folders.
        c.save_directories(conf/'directories.txt',[])
        (custom/'new.cbz').write_text('yes')
        c.SortEngine(config=conf).scan_once()
        assert (dest3/'new.cbz').is_file()
        # Old 4-column rules remain accepted; stable equal priority.
        (conf/'rules.tsv').write_text('watch\t*.zip\t'+str(dest1)+'\tmove\nwatch\tfilename.zip\t'+str(dest2)+'\tmove\n')
        x=c.load_rules(conf/'rules.tsv')
        assert len(x)==2 and x[0].sources=='-' and x[0].priority==0
    del sys.modules['sorter_core']
    sys.path.pop(0)
    print(platform,'PASS')

script=root/'linux'/'src'/'Sorter_Embedded.sh'
with tempfile.TemporaryDirectory() as t:
    tmp=Path(t);h=tmp/'home';h.mkdir();conf=tmp/'conf';conf.mkdir();g=tmp/'global';g.mkdir();custom=tmp/'custom';custom.mkdir()
    d1=tmp/'general';d2=tmp/'specific';d3=tmp/'cbz'
    (conf/'rules.tsv').write_text(f'watch\t*.zip\t{d1}\tmove\t30\t-\nwatch\tfilename.zip\t{d2}\tmove\t5\t-\nwatch\t*.cbz\t{d3}\tmove\t15\t{custom}\n')
    (conf/'directories.txt').write_text(str(g)+'\n')
    (conf/'scan-interval.txt').write_text('0.1\n')
    (g/'filename.zip').write_text('global')
    (g/'wrong.cbz').write_text('should stay')
    (custom/'correct.cbz').write_text('custom')
    env={**os.environ,'HOME':str(h),'SORTER_DIRS_FILE':str(conf/'directories.txt'),'SORTER_RULES_FILE':str(conf/'rules.tsv'),'SORTER_SCAN_INTERVAL_FILE':str(conf/'scan-interval.txt'),'SORTER_OVERWRITE_FILE':str(conf/'overwrite-files.txt'),'SORTER_DESTINATION_MODE_FILE':str(conf/'destination-mode.txt')}
    proc=subprocess.Popen(['bash',str(script)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    for _ in range(35):
        if (d1/'filename.zip').exists() and (d3/'correct.cbz').exists(): break
        if proc.poll() is not None:break
        time.sleep(.1)
    proc.terminate();out,err=proc.communicate(timeout=3)
    print('bash code',proc.returncode,'output',out[-1100:],'err',err[-1100:])
    assert (d1/'filename.zip').exists(), 'priority glob should win'
    assert (d3/'correct.cbz').exists(), 'explicit source should scan'
    assert (g/'wrong.cbz').exists(), 'explicit-only source must not scan main watch'
    print('Linux PASS')
print('ALL CROSS-PLATFORM TESTS PASS')
