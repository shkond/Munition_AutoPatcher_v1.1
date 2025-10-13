from pathlib import Path
root = Path('E:/fo4mod/xedit')
bkdirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith('disabled_lib_backups_move_')], key=lambda d: d.stat().st_mtime, reverse=True)
if not bkdirs:
    print('No backup dirs')
    raise SystemExit(0)
bk = bkdirs[0]
print('Using backup dir:', bk)
cand = None
for p in bk.iterdir():
    if 'Edit Scripts_lib_AutoPatcherLib.pas' in p.name:
        cand = p
        break
if not cand:
    print('No candidate found matching pattern in backup dir')
    raise SystemExit(0)
dest = Path('E:/fo4mod/xedit/Edit Scripts/lib/AutoPatcherLib.pas')
dest.parent.mkdir(parents=True, exist_ok=True)
print('Restoring', cand, '->', dest)
cand.rename(dest)
print('Restored')
