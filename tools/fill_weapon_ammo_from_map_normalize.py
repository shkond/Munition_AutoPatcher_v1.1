#!/usr/bin/env python3
"""
Try to match ammo_editor_id to weapon_ammo_map.fixed.json with normalization heuristics.
"""
import json
from pathlib import Path
import re

root = Path('e:/Munition_AutoPatcher_v1.1')
out = root / 'Output'
weapon_file = out / 'weapon_omod_map.json'
ammo_map_file = out / 'weapon_ammo_map.fixed.json'

weapons = json.loads(weapon_file.read_text(encoding='utf-8'))
ammo_map = json.loads(ammo_map_file.read_text(encoding='utf-8'))
map_by_editor = { (entry.get('editor_id') or '').strip(): (entry.get('ammo_form_id') or '').strip().upper() for entry in ammo_map }

# normalization helpers
def norm(s):
    if not s: return ''
    s = s.strip()
    s = s.replace('\u00A0',' ')
    s = s.lower()
    s = re.sub(r'[_\- ]+','',s)
    s = re.sub(r'ammo','',s)
    s = re.sub(r'caliber','',s)
    return s

map_norm = {}
for k,v in map_by_editor.items():
    map_norm[norm(k)] = v

filled = 0
for w in weapons:
    if not (w.get('ammo_form_id') or '').strip():
        ed = (w.get('ammo_editor_id') or '').strip()
        if not ed: continue
        n = norm(ed)
        if n in map_norm:
            w['ammo_form_id'] = map_norm[n]
            filled += 1

out_file = out / 'weapon_omod_map.ammofilled.norm.json'
out_file.write_text(json.dumps(weapons, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {out_file}. Filled ammo_form_id for {filled} of {len(weapons)} entries')
if filled>0:
    for w in weapons[:20]:
        if w.get('ammo_form_id'):
            print(w.get('weapon_editor_id'), w.get('ammo_editor_id'), w.get('ammo_form_id'))
