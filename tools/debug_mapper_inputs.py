#!/usr/bin/env python3
import configparser
import json
from pathlib import Path

root = Path('e:/Munition_AutoPatcher_v1.1')
out = root / 'Output'

ammo_file = out / 'unique_ammo_for_mapping.ini'
munitions_file = out / 'munitions_ammo_ids.ini'
weapon_candidates = [out / 'weapon_omod_map.ammofilled.details.json', out / 'weapon_omod_map.json', Path.cwd() / 'Output' / 'weapon_omod_map.json']

print('Ammo file:', ammo_file, 'exists=', ammo_file.exists())
print('Munitions file:', munitions_file, 'exists=', munitions_file.exists())

# parse munitions
munitions_list = []
if munitions_file.exists():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(munitions_file, encoding='utf-8')
    except Exception:
        cfg.read(munitions_file, encoding='cp932', errors='replace')
    if cfg.has_section('MunitionsAmmo'):
        for k, v in cfg.items('MunitionsAmmo'):
            munitions_list.append((k.strip().upper(), v.strip()))
print('Munitions entries:', len(munitions_list))
print('Sample munitions:', munitions_list[:5])

# parse unmapped ammo
unmapped = []
if ammo_file.exists():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(ammo_file, encoding='utf-8')
    except Exception:
        cfg.read(ammo_file, encoding='cp932', errors='replace')
    if cfg.has_section('UnmappedAmmo'):
        for k, v in cfg.items('UnmappedAmmo'):
            unmapped.append((k.strip().upper(), v.strip()))
print('Unmapped ammo count:', len(unmapped))
print('Sample unmapped:', unmapped[:10])

# show filtering logic and which entries would be skipped (esp blacklist)
blacklist = ['Fallout4.esm', 'Munitions - An Ammo Expansion.esl', 'DLCRobot.esm', 'DLCCoast.esm', 'DLCNukaWorld.esm']
skipped = []
kept = []
for fid, details in unmapped:
    parts = details.split('|')
    esp = parts[0].strip() if parts else ''
    eid = parts[1].strip() if len(parts) > 1 else ''
    if any(x in esp for x in blacklist):
        skipped.append((fid, esp, eid))
    else:
        kept.append((fid, esp, eid))
print('Kept entries:', len(kept), 'Skipped entries:', len(skipped))
print('Kept sample:', kept[:10])
print('Skipped sample:', skipped[:10])

# build omod records from weapon json candidates
omod_records = {}
for p in weapon_candidates:
    if not p.exists():
        continue
    try:
        txt = p.read_text(encoding='utf-8')
        data = json.loads(txt)
    except Exception as e:
        print('Failed to load', p, e)
        continue
    count = 0
    for entry in data:
        count += 1
        key_a = (entry.get('ammo_form_id') or '').strip().upper()
        key_b = (entry.get('ammo_editor_id') or '').strip()
        omods = entry.get('omods') or []
        if key_a:
            omod_records.setdefault(key_a, []).extend(omods)
        if key_b:
            omod_records.setdefault(key_b, []).extend(omods)
    print('Loaded weapon json from', p, 'entries=', count)

# Attach and show per-kept unmapped entry whether omods found
for fid, esp, eid in kept:
    attached = omod_records.get(fid, []) + omod_records.get(eid, [])
    # dedupe
    seen = set(); uniq = []
    for o in attached:
        if not isinstance(o, dict):
            continue
        key = (o.get('omod_plugin') or '') + '|' + (o.get('omod_form_id') or '')
        if key and key not in seen:
            seen.add(key); uniq.append(o)
    print(f'Ammo {fid} ({esp}|{eid}) -> attached omods:', len(uniq), [ (o.get('omod_plugin'), o.get('omod_form_id')) for o in uniq ])

print('\nDiagnostics complete')
