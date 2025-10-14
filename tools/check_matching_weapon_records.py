from config_manager import ConfigManager
from robco_ini_generate import _load_ammo_map, _read_weapon_records
cm = ConfigManager('config.ini')
output_dir = cm.get_path('Paths','output_dir')
xedit_output_dir = cm.get_path('Paths','xedit_output_dir')
print('output_dir:', output_dir)
ammo_map = _load_ammo_map(cm.get_path('Paths','ammo_map_file'))
print('ammo_map entries:', len(ammo_map))
recs = _read_weapon_records(output_dir, xedit_output_dir)
print('total weapon_records:', len(recs))
matches = []
for r in recs:
    orig = (r.get('ammo_formid') or '').strip().upper()
    if not orig:
        continue
    if orig.lower() in ammo_map:
        matches.append((r, ammo_map[orig.lower()]))
print('matched records:', len(matches))
for m in matches[:10]:
    print(m)
