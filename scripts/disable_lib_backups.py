import os
import shutil
from pathlib import Path

ess = Path(r"E:\fo4mod\xedit\Edit Scripts")
dest = ess / 'disabled_lib_backups'

if not ess.exists():
    print(f'Edit Scripts folder not found: {ess}')
    raise SystemExit(1)

backups = [p for p in ess.iterdir() if p.is_dir() and p.name.startswith('_lib_backup')]
if not backups:
    print('No _lib_backup* dirs found')
else:
    dest.mkdir(parents=True, exist_ok=True)
    for b in backups:
        target = dest / b.name
        print(f'Moving: {b} -> {target}')
        if target.exists():
            # if target exists, remove it first to allow move
            if target.is_dir():
                shutil.rmtree(target)
        shutil.move(str(b), str(target))
    print('Moved backups to', dest)

# list remaining AutoPatcherLib.pas
print('\n--- Remaining AutoPatcherLib.pas files ---')
for p in ess.rglob('AutoPatcherLib.pas'):
    st = p.stat()
    print(p, st.st_size, st.st_mtime)

# search for AP_LOG_PREFIX occurrences in pas files
print('\n--- AP_LOG_PREFIX occurrences ---')
for p in ess.rglob('*.pas'):
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    if 'AP_LOG_PREFIX' in txt:
        for i, line in enumerate(txt.splitlines(), start=1):
            if 'AP_LOG_PREFIX' in line:
                print(f'{p}:{i}: {line.strip()}')

print('\nDone. If xEdit is running, restart it before retrying the script.')
