#!/usr/bin/env python3
"""
Simple runner for robco_ini_generate.run(config) using workspace paths.
Adjust paths below if needed.
"""
import sys
from pathlib import Path
import logging
import json

# import the module
import sys
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))
import robco_ini_generate as rig

class SimpleConfig:
    def __init__(self, paths):
        self._paths = paths
    def get_path(self, section, key):
        # ignore section/key, return from provided dict
        return self._paths[key]
    def get_boolean(self, section, key, fallback=False):
        return fallback
    def get_string(self, section, key, fallback=''):
        return fallback
    def get(self, key, fallback=None):
        return self._paths.get(key, fallback)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    root = Path('e:/Munition_AutoPatcher_v1.1').resolve()
    output_dir = root / 'Output'
    # set robust defaults
    paths = {
        'strategy_file': root / 'Output' / 'strategy.json',
        'output_dir': output_dir,
        'ammo_map_file': root / 'ammo_map.ini',
        'leveled_lists_csv': output_dir / 'WeaponLeveledLists_Export.csv',
        'robco_patcher_dir': root / 'RobCo_Auto_Patcher',
        'xedit_output_dir': root / 'Output',
        'munitions_npc_list_map': root / 'munitions_ammo_lists.ini'
    }
    cfg = SimpleConfig(paths)
    ok = rig.run(cfg)
    print('robco run ok=', ok)
