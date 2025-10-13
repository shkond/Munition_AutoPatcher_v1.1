import os
from pathlib import Path
import datetime

probe_strings = [
    '[EARLY_PROBE]',
    'EARLY_RAW',
    'early_stage_start',
    'manual_debug_log',
    'AP_Run_ExportWeaponAmmoDetails',
    '[AutoPatcher-Test]',
    'omod_debug_log',
]

roots = [
    Path(r"E:/Munition_AutoPatcher_v1.1/Output"),
    Path(r"E:/fo4mod/xedit/Edit Scripts/Output"),
]

results = []
errors = []

print('Probe run at', datetime.datetime.now().isoformat())

# Search files
for root in roots:
    print('\nScanning', root)
    if not root.exists():
        print('  -> not found')
        continue
    for p in sorted(root.glob('**/*'), key=lambda x: x.stat().st_mtime if x.exists() else 0):
        if p.is_file():
            try:
                # Only scan text files up to a reasonable size to avoid huge reads
                size = p.stat().st_size
                if size > 5 * 1024 * 1024:
                    # skip very large files
                    continue
                try:
                    text = p.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    text = p.read_text(encoding='cp932', errors='replace')
                for s in probe_strings:
                    if s in text:
                        # find first matching line
                        for ln, line in enumerate(text.splitlines(), 1):
                            if s in line:
                                results.append((str(p), s, ln, line.strip()[:400]))
                                break
            except Exception as e:
                errors.append((str(p), str(e)))

# Print results
if results:
    print('\nFound probe matches:')
    for f, s, ln, line in results:
        print(f' - {s} in {f} @ line {ln}: {line}')
else:
    print('\nNo probe matches found in scan roots.')

if errors:
    print('\nSome files could not be read:')
    for f, e in errors:
        print(f' - {f}: {e}')

# Write permission tests
print('\nWrite permission tests:')
write_targets = [
    Path(r"E:/Munition_AutoPatcher_v1.1/Output/test_write_probe_{ts}.txt"),
    Path(r"E:/fo4mod/xedit/Edit Scripts/Output/test_write_probe_{ts}.txt"),
]

ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
for t in write_targets:
    target = Path(str(t).format(ts=ts))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write('probe write at ' + ts + '\n')
        print(f' - WROTE: {target}')
    except Exception as e:
        print(f' - FAILED to write {target}: {e}')

# List TEMP_*.pas and AutoPatcherCore.pas in runtime Edit Scripts
print('\nRuntime script files:')
edit_scripts = Path(r"E:/fo4mod/xedit/Edit Scripts")
if edit_scripts.exists():
    for p in sorted(edit_scripts.glob('TEMP_*.pas'), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)[:10]:
        print(' -', p.name, p.stat().st_mtime)
    ap_core = edit_scripts / 'AutoPatcherCore.pas'
    if ap_core.exists():
        print(' - AutoPatcherCore.pas last modified', ap_core.stat().st_mtime)
else:
    print(' - Edit Scripts folder not found')

print('\nProbe run complete.')
