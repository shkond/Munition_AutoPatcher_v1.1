from pathlib import Path
roots = [Path(r'E:/fo4mod/xedit'), Path(r'E:/Munition_AutoPatcher_v1.1')]
patterns = ['manual_debug_log.txt','omod_debug_log.txt','stage_filecount.txt','stage_before_fileloop.txt','stage_last_fileidx.txt']
found = False
for root in roots:
    if not root.exists():
        continue
    for pat in patterns:
        for p in root.rglob(pat):
            print(p)
            found = True

if not found:
    print('No stage/debug files found under roots')
