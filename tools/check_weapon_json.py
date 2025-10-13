#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: check_weapon_json.py <file.json>')
    sys.exit(2)

p = Path(sys.argv[1])
if not p.exists():
    print('File not found:', p)
    sys.exit(2)

data = json.loads(p.read_text(encoding='utf-8'))

total = len(data)
empty = [obj for obj in data if not obj.get('weapon_form_id')]
nonempty = [obj for obj in data if obj.get('weapon_form_id')]
print('Total objects:', total)
print('Empty weapon_form_id:', len(empty))
print('Non-empty weapon_form_id:', len(nonempty))
print('\nSample empty entries (up to 20):')
for i,obj in enumerate(empty[:20]):
    print(i, obj.get('weapon_editor_id'), obj.get('weapon_name')[:80])

# Show possible mapping by editor_id from other file if present
other = Path(p.parent / 'weapon_ammo_map.json')
if other.exists():
    try:
        otherdata = json.loads(other.read_text(encoding='utf-8'))
        mapping = {o.get('editor_id'): o.get('ammo_form_id') for o in otherdata if 'editor_id' in o}
        print('\nFound weapon_ammo_map.json; sample mappings for some empty entries:')
        for obj in empty[:20]:
            eid = obj.get('weapon_editor_id')
            if eid in mapping:
                print(eid, '-> ammo_form_id:', mapping[eid])
    except Exception as e:
        print('Failed to read weapon_ammo_map.json:', e)
