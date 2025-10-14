#!/usr/bin/env python3
"""
Fill weapon_omod_map.json ammo_form_id by matching ammo_editor_id to entries in weapon_ammo_map.fixed.json
Writes weapon_omod_map.ammofilled.json and prints stats.
"""
import json
from pathlib import Path

root = Path('e:/Munition_AutoPatcher_v1.1')
out = root / 'Output'
weapon_file = out / 'weapon_omod_map.json'
ammo_map_file = out / 'weapon_ammo_map.fixed.json'

if not weapon_file.exists():
    print('weapon_omod_map.json not found')
    raise SystemExit(1)
if not ammo_map_file.exists():
    print('weapon_ammo_map.fixed.json not found')
    raise SystemExit(1)

weapons = json.loads(weapon_file.read_text(encoding='utf-8'))
ammo_map = json.loads(ammo_map_file.read_text(encoding='utf-8'))
# ammo_map entries: list of {editor_id, full_name, ammo_form_id}
map_by_editor = { (entry.get('editor_id') or '').strip(): (entry.get('ammo_form_id') or '').strip().upper() for entry in ammo_map }

filled = 0
total = 0
for w in weapons:
    total += 1
    if not (w.get('ammo_form_id') or '').strip():
        ed = (w.get('ammo_editor_id') or '').strip()
        if ed and ed in map_by_editor and map_by_editor[ed]:
            w['ammo_form_id'] = map_by_editor[ed]
            filled += 1

out_file = out / 'weapon_omod_map.ammofilled.json'
out_file.write_text(json.dumps(weapons, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {out_file}. Filled ammo_form_id for {filled} of {total} entries')
# sample prints
samples = [w for w in weapons if w.get('ammo_form_id')]
print('Sample with ammo_form_id (first 10):')
for s in samples[:10]:
    print(s.get('weapon_editor_id'), s.get('ammo_editor_id'), s.get('ammo_form_id'))
