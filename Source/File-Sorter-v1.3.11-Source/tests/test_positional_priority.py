"""v1.3.9 positional precedence, legacy migration and per-rule sources."""
from pathlib import Path
from dataclasses import replace
import os, subprocess, sys, tempfile, time

ROOT=Path(__file__).resolve().parents[1]
for platform,base in [('Windows',ROOT/'windows/src'),('macOS',ROOT/'macos/File Sorter.app/Contents/Resources/src')]:
    sys.path.insert(0,str(base))
    import sorter_core as c
    assert c.VERSION=='1.3.11', (platform,c.VERSION)
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp);cfg=t/'config';cfg.mkdir();src=t/'input';src.mkdir()
        general=t/'general';specific=t/'specific'
        legacy=(f'watch\tfilename.zip\t{specific}\tmove\t5\t-\n'
                f'watch\t*.zip\t{general}\tmove\t20\t-\n')
        (cfg/'rules.tsv').write_text('# v1.3.8 numeric priorities\n'+legacy)
        rules=c.load_rules(cfg/'rules.tsv')
        assert [r.pattern for r in rules]==['*.zip','filename.zip'], rules
        assert [r.priority for r in rules]==[2,1]
        c.save_rules(cfg/'rules.tsv',rules)
        text=(cfg/'rules.tsv').read_text()
        assert '# rule-order: position' in text
        assert 'move\t2\t-' in text
        assert [r.pattern for r in c.load_rules(cfg/'rules.tsv')]==['*.zip','filename.zip']
        # In new format, list order wins even if numeric rank is manually changed.
        reverse=[rules[1],rules[0]]
        c.save_rules(cfg/'rules.tsv',reverse)
        lines=(cfg/'rules.tsv').read_text().splitlines()
        assert '\t2\t-' in lines[2] and '\t1\t-' in lines[3]
        assert [r.pattern for r in c.load_rules(cfg/'rules.tsv')]==['filename.zip','*.zip']
        c.save_directories(cfg/'directories.txt',[str(src)])
        (src/'filename.zip').write_text('original')
        c.SortEngine(config=cfg).scan_once()
        assert (specific/'filename.zip').read_text()=='original',platform
        # Reorder; glob at position 1 wins even though the name-specific rule matches too.
        c.save_rules(cfg/'rules.tsv',rules)
        (src/'filename.zip').write_text('second')
        c.SortEngine(config=cfg).scan_once()
        assert (general/'filename.zip').read_text()=='second',platform
        # 4-col legacy keeps its file order; sources default to all watched folders.
        (cfg/'rules.tsv').write_text(f'watch\tfilename.zip\t{specific}\tmove\nwatch\t*.zip\t{general}\tmove\n')
        four=c.load_rules(cfg/'rules.tsv')
        assert [r.pattern for r in four]==['filename.zip','*.zip']
        assert all(r.sources=='-' for r in four)
    sys.path.pop(0);sys.modules.pop('sorter_core',None)
    print(platform, 'positional rules and migration PASS')

script=ROOT/'linux/src/Sorter_Embedded.sh'
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);home=t/'home';home.mkdir();conf=t/'conf';conf.mkdir();src=t/'input';src.mkdir()
    general=t/'general';specific=t/'specific'
    (conf/'directories.txt').write_text(str(src)+'\n')
    (conf/'scan-interval.txt').write_text('0.1\n')
    env={**os.environ,'HOME':str(home),'SORTER_DIRS_FILE':str(conf/'directories.txt'),
         'SORTER_RULES_FILE':str(conf/'rules.tsv'),'SORTER_SCAN_INTERVAL_FILE':str(conf/'scan-interval.txt'),
         'SORTER_OVERWRITE_FILE':str(conf/'overwrite-files.txt'),
         'SORTER_DESTINATION_MODE_FILE':str(conf/'destination-mode.txt')}
    def check(config,desired):
        (conf/'rules.tsv').write_text(config)
        (src/'filename.zip').write_text('ok')
        p=subprocess.Popen(['bash',str(script)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            for _ in range(60):
                if desired.exists():break
                if p.poll() is not None:break
                time.sleep(.1)
        finally:
            p.terminate();out,err=p.communicate(timeout=4)
        assert desired.is_file(), (out[-1000:],err[-1000:])
        desired.unlink()
    # Old numeric priorities still win on initial upgrade.
    check(f'watch\tfilename.zip\t{specific}\tmove\t5\t-\nwatch\t*.zip\t{general}\tmove\t20\t-\n', general/'filename.zip')
    # New header means first line wins regardless of stored numeric value.
    check(f'# rule-order: position; first listed rule wins (1/N is highest)\nwatch\tfilename.zip\t{specific}\tmove\t1\t-\nwatch\t*.zip\t{general}\tmove\t99\t-\n', specific/'filename.zip')
    print('Linux positional rules and legacy migration PASS')
print('ALL positional tests PASS')
