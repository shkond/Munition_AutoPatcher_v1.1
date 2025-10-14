#!/usr/bin/env python3
import json
from pathlib import Path
import configparser

root = Path('e:/Munition_AutoPatcher_v1.1')
out = root / 'Output'
weapon_path = out / 'weapon_omod_map.json'
ammo_ini = root / 'ammo_map.ini'

def load_ammo_map_ini(p: Path):
    mapping = {}
    if not p.is_file():
        return mapping
    parser = configparser.ConfigParser()
    try:
        parser.read(p, encoding='utf-8')
    except Exception:
        parser.read(p, encoding='cp932', errors='replace')
    # UnmappedAmmo or general key=value
    if parser.has_section('UnmappedAmmo'):
        for k,v in parser.items('UnmappedAmmo'):
            mapping[k.strip().lower()] = v.strip().lower()
    else:
        # try top-level key=value
        for s in parser.sections():
            for k,v in parser.items(s):
                mapping[k.strip().lower()] = v.strip().lower()
    return mapping

W = json.loads(weapon_path.read_text(encoding='utf-8'))
map_ini = load_ammo_map_ini(ammo_ini)

total_weapons = len(W)
weapons_with_omods = sum(1 for w in W if w.get('omods'))
weapons_with_orig_ammo_in_map = 0
weapons_with_omods_and_orig_ammo_map = 0
sample_with_match = []
sample_with_omods = []

for w in W:
    orig_ammo = (w.get('ammo_form_id') or '').strip().lower()
    if orig_ammo in map_ini:
        weapons_with_orig_ammo_in_map += 1
    if w.get('omods') and len(w.get('omods'))>0:
        sample_with_omods.append((w.get('weapon_editor_id'), orig_ammo, w.get('omods')[:2]))
        if orig_ammo in map_ini:
            weapons_with_omods_and_orig_ammo_map += 1
            sample_with_match.append((w.get('weapon_editor_id'), orig_ammo, w.get('omods')[:2]))

print('Total weapons:', total_weapons)
print('Weapons with any OMODs:', weapons_with_omods)
print('Weapons whose original ammo formid appears in ammo_map.ini:', weapons_with_orig_ammo_in_map)
print('Weapons with OMODs AND orig_ammo in ammo_map.ini:', weapons_with_omods_and_orig_ammo_map)
print('\nSample weapons with OMODs (first 10):')
for i, s in enumerate(sample_with_omods[:10]):
    print(i+1, s[0], 'orig_ammo=', s[1], 'sample_omods=', s[2])
print('\nSample weapons with OMODs AND mapping (first 10):')
for i, s in enumerate(sample_with_match[:10]):
    print(i+1, s[0], 'orig_ammo=', s[1], 'sample_omods=', s[2])

print('\nAmmo map keys count:', len(map_ini))
print('Some ammo_map.ini keys sample:', list(map_ini.keys())[:20])
