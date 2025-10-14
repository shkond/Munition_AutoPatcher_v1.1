from pathlib import Path
root = Path(r"e:\Munition_AutoPatcher_v1.1")
pas = root / 'pas_scripts' / 'test_export_weapon_omod_only.pas'
out = root / 'Output' / 'copied_source_debug.pas'
print('reading', pas)
if pas.exists():
    txt = pas.read_text(encoding='utf-8', errors='replace')
    out.write_text(txt, encoding='utf-8')
    print('wrote', out)
    # print head
    print('--- head of file ---')
    for i,l in enumerate(txt.splitlines()[:80],1):
        print(f'{i:03}: {l}')
else:
    print('source not found:', pas)
