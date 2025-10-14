from pathlib import Path
from mapper import AmmoMapperApp
import tkinter as tk

root = tk.Tk(); root.withdraw()
base = Path('Output'); base.mkdir(exist_ok=True)
mun = base / 'munitions_ammo_ids.ini'; mun.write_text('[MunitionsAmmo]\n00112233=Mun_Ammo_Example\n', encoding='utf-8')
ammo = base / 'unique_ammo_for_mapping.ini'; ammo.write_text('[UnmappedAmmo]\n0001AAAA=MyMod.esp|CustomAmmoID\n', encoding='utf-8')
wom = base / 'weapon_omod_map.ammofilled.details.json'
wom.write_text('[{"weapon_plugin":"MyMod.esp","weapon_form_id":"01000ABC","weapon_editor_id":"MyWeap","weapon_name":"MyWeap","ammo_plugin":"MyMod.esp","ammo_form_id":"0001AAAA","ammo_editor_id":"CustomAmmoID","omods":[{"omod_plugin":"MyMod.esp","omod_form_id":"02000BBB","omod_editor_id":"MyOmod"}]}]', encoding='utf-8')
npc = base / 'munitions_npc_lists.ini'; npc.write_text('[AmmoNPCList]\n00112233=FORMLIST001\n', encoding='utf-8')
app = AmmoMapperApp(root, ammo_file_path=str(ammo), munitions_file_path=str(mun), output_file_path=str(base / 'ammo_map.ini'))
import json
print('ammo_to_map:')
print(json.dumps(app.ammo_to_map, ensure_ascii=False, indent=2, default=str))
for i, row in enumerate(app.ammo_to_map):
    print('row', i, 'keys=', list(row.keys()))

if app.ammo_to_map:
    row = app.ammo_to_map[0]
    print('row widgets before:', row.get('widgets'))
    # only set widgets if present
    if 'widgets' in row and row['widgets'].get('chk_var') is not None:
        row['widgets']['chk_var'].set(True)
        for v in app.munitions_ammo_list:
            if '00112233' in v:
                row['widgets']['combo'].set(v)
                break
    else:
        print('widgets not ready; setting selected_target for headless save')
        # set selected_target so save_ini_file can operate in headless mode
        row['selected_target'] = app.munitions_ammo_list[0] if app.munitions_ammo_list else ''
app.save_ini_file()
print('done')
