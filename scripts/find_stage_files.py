from pathlib import Path

paths = [Path(r'E:/fo4mod/xedit/Edit Scripts/Output'), Path(r'E:/Munition_AutoPatcher_v1.1/Output')]
patterns = ['stage_filecount.txt','stage_before_fileloop.txt','stage_last_fileidx.txt','manual_debug_log.txt','omod_debug_log.txt']

for p in paths:
    print('\nSearching in:', p)
    if not p.exists():
        print('  (not found)')
        continue
    found_any = False
    for pat in patterns:
        for f in p.rglob(pat):
            print('  Found:', f, f.stat().st_size)
            found_any = True
    if not found_any:
        print('  No stage/debug files found here.')
