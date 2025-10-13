#!/usr/bin/env python3
import json
import sys
from pathlib import Path

fixed = Path('e:/Munition_AutoPatcher_v1.1/Output/weapon_omod_map.repaired.json')
final = Path('e:/Munition_AutoPatcher_v1.1/Output/weapon_omod_map.repaired.final-logfilled.json')
if not fixed.exists() or not final.exists():
    print('Required files missing:')
    print('  fixed:', fixed.exists(), ' final:', final.exists())
    sys.exit(2)

A = json.loads(fixed.read_text(encoding='utf-8'))
B = json.loads(final.read_text(encoding='utf-8'))

print('Counts:')
print('  before (repaired):', len(A))
print('  after  (final)  :', len(B))

# count non-empty weapon_form_id
before_nonempty = sum(1 for o in A if o.get('weapon_form_id'))
after_nonempty = sum(1 for o in B if o.get('weapon_form_id'))
print('Non-empty weapon_form_id: before=', before_nonempty, ' after=', after_nonempty)

# list sample where before empty and after filled
filled_samples = []
for a,b in zip(A,B):
    if not a.get('weapon_form_id') and b.get('weapon_form_id'):
        filled_samples.append((b.get('weapon_editor_id'), b.get('weapon_name'), b.get('weapon_form_id')))

print('\nSamples where weapon_form_id was filled from logs (up to 30):')
for i,s in enumerate(filled_samples[:30]):
    print(f' {i+1:3d}. editor_id={s[0]:30s} form_id={s[2]:10s} name="{s[1]:.40s}"')

# simple check for CJK in names
def cjk_count(s):
    cnt = 0
    for ch in s:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF) or (0x3040 <= cp <= 0x30FF) or (0xFF00 <= cp <= 0xFFEF):
            cnt += 1
    return cnt

names_with_cjk = [(o.get('weapon_editor_id'), o.get('weapon_name')) for o in B if cjk_count(o.get('weapon_name',''))>0]
print('\nEntries with CJK characters in weapon_name:', len(names_with_cjk))
if names_with_cjk:
    print('Sample CJK names (up to 10):')
    for i,(eid,name) in enumerate(names_with_cjk[:10]):
        print(f' {i+1:2d}. {eid:30s} "{name}"')

# print head of final file
print('\n--- Head of final JSON (first 120 lines) ---')
text = final.read_text(encoding='utf-8')
for ln in text.splitlines()[:120]:
    print(ln)

print('\nDone')
