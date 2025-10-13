#!/usr/bin/env python3
"""
Fill empty weapon_form_id in weapon_omod_map by looking up editor_id in weapon_ammo_map.
Writes weapon_omod_map.filled.json
"""
import json
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print('Usage: fill_weapon_formid_from_map.py <weapon_omod_map.json> <weapon_ammo_map.json>')
    sys.exit(2)

omod = Path(sys.argv[1])
amap = Path(sys.argv[2])
if not omod.exists() or not amap.exists():
    print('File missing')
    sys.exit(2)

data = json.loads(omod.read_text(encoding='utf-8'))
mapdata = json.loads(amap.read_text(encoding='utf-8'))

mapping = {o.get('editor_id'): o.get('ammo_form_id') for o in mapdata if 'editor_id' in o}

filled = 0
for obj in data:
    if not obj.get('weapon_form_id'):
        editor = obj.get('weapon_editor_id')
        # try exact match
        if editor in mapping and mapping[editor]:
            obj['weapon_form_id'] = mapping[editor]
            filled += 1

out = omod.with_name(omod.stem + '.final.json')
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {out}. Filled {filled} entries out of {len(data)}')
