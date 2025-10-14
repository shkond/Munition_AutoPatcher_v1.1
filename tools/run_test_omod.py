from config_manager import ConfigManager
from Orchestrator import Orchestrator
import time
cm = ConfigManager('config.ini')
orch = Orchestrator(cm)
print('Running test_export_weapon_omod_only via Orchestrator...')
# Register the test script in the config (overwrites or adds the entry)
cm.config.set('Scripts', 'test_export_weapon_omod_only', 'test_export_weapon_omod_only.pas')

# Expected success marker and expected output file(s)
success_marker = '[AutoPatcher-Test] AP_Run_ExportWeaponAmmoDetails completed'
expected_outputs = ['weapon_omod_map.json']

res = orch.run_xedit_script('test_export_weapon_omod_only', success_marker, expected_outputs)
print('Result:', res)

# show Output dir listing
from pathlib import Path
out = cm.get_path('Paths', 'output_dir')
print('Output dir:', out)
for p in sorted(out.iterdir()):
    print(' -', p.name)
