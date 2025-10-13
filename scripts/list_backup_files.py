from pathlib import Path
root = Path(r'E:/fo4mod/xedit')
bkdirs = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith('disabled_lib_backups_move_')], key=lambda d: d.stat().st_mtime, reverse=True)
if not bkdirs:
    print('No backup dirs')
    raise SystemExit(0)
bk = bkdirs[0]
print('Using backup dir:', bk)
for p in sorted(bk.iterdir()):
    try:
        st = p.stat()
        print(p.name, st.st_size)
    except Exception as e:
        print(p.name, 'ERR', e)
