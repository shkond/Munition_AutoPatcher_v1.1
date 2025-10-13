import re
from pathlib import Path
p = Path(r'E:/Munition_AutoPatcher_v1.1/Output')
patterns = [re.compile(x, re.I) for x in [r'Exception', r'Access Violation', r'EAccessViolation', r'\[EARLY_PROBE\]', r'\[AutoPatcher-Test\]']]
found = []
for f in p.rglob('*'):
    if not f.is_file():
        continue
    try:
        txt = f.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for i, line in enumerate(txt.splitlines(), start=1):
        for pat in patterns:
            if pat.search(line):
                found.append((f, i, line.strip()))
                break
print('Matches:', len(found))
for path, ln, line in found:
    print(f'{path} @ {ln}: {line}')
