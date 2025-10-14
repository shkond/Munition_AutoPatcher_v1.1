#!/usr/bin/env python3
"""
Fill weapon ammo_form_id in Output/weapon_omod_map.json using
xedit_edit_scripts_output/weapon_ammo_details.txt which contains lines like:
Fallout4.esm|0000463F|AssaultRifle|Fallout4.esm|0001F278|Ammo556

This script writes Output/weapon_omod_map.ammofilled.details.json
"""
from pathlib import Path
import json

root = Path('e:/Munition_AutoPatcher_v1.1')
out = root / 'Output'
weapon_file = out / 'weapon_omod_map.json'
details = root / 'xedit_edit_scripts_output' / 'weapon_ammo_details.txt'

if not weapon_file.exists():
    raise SystemExit(f'Missing {weapon_file}')
if not details.exists():
    raise SystemExit(f'Missing {details}')

# build mapping ammo_editor -> ammo_form
map_ = {}
for line in details.read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    parts = line.split('|')
    if len(parts) < 6:
        continue
    ammo_editor = parts[5].strip()
    ammo_form = parts[4].strip().upper()
    if ammo_editor:
        map_[ammo_editor] = ammo_form

weapons = json.loads(weapon_file.read_text(encoding='utf-8'))
filled = 0
for w in weapons:
    if (w.get('ammo_form_id') or '').strip():
        continue
    ae = (w.get('ammo_editor_id') or '').strip()
    if not ae:
        continue
    if ae in map_:
        w['ammo_form_id'] = map_[ae]
        filled += 1

out_file = out / 'weapon_omod_map.ammofilled.details.json'
out_file.write_text(json.dumps(weapons, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {out_file}. Filled ammo_form_id for {filled} of {len(weapons)} entries')
# print sample mappings used
if filled>0:
    used = [w for w in weapons if w.get('ammo_form_id')]
    for w in used[:30]:
        print(w.get('weapon_editor_id'), '=>', w.get('ammo_editor_id'), '->', w.get('ammo_form_id'))
