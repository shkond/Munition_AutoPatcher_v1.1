from config_manager import ConfigManager
from Orchestrator import Orchestrator
import logging
logging.basicConfig(level=logging.DEBUG)
cm = ConfigManager('config.ini')
orch = Orchestrator(cm)
print('Calling run_xedit_script...')
res = orch.run_xedit_script('test_export_weapon_omod_only', 'AutoPatcher-Test', expected_outputs=['weapon_omod_map.json'])
print('Result:', res)
