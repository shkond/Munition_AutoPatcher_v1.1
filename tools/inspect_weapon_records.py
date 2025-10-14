from config_manager import ConfigManager
from robco_ini_generate import _read_weapon_records
cm = ConfigManager('config.ini')
output_dir = cm.get_path('Paths','output_dir')
xedit_output_dir = cm.get_path('Paths','xedit_output_dir') if hasattr(cm, 'get_path') else None
print('output_dir:', output_dir)
print('xedit_output_dir:', xedit_output_dir)
recs = _read_weapon_records(output_dir, xedit_output_dir)
print('weapon_records found:', len(recs))
for r in recs[:5]:
    print(r)
