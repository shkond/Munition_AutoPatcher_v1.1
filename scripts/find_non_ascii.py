from pathlib import Path
p = Path(r'e:\Munition_AutoPatcher_v1.1\pas_scripts\AutoPatcherCore.pas')
for i,l in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
    for ch in l:
        if ord(ch) > 127:
            print(i, repr(ch), hex(ord(ch)), l)
            break
