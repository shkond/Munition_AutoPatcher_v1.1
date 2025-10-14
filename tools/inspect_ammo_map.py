from config_manager import ConfigManager
from robco_ini_generate import _load_ammo_map
cm = ConfigManager('config.ini')
ammo_map_file = cm.get_path('Paths','ammo_map_file')
print('ammo_map_file:', ammo_map_file)
mapping = _load_ammo_map(ammo_map_file)
print('mapping count:', len(mapping))
for k,v in mapping.items():
    print(k,'->',v)
