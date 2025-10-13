from config_manager import ConfigManager
from Orchestrator import Orchestrator
import time
cm = ConfigManager('config.ini')
orch = Orchestrator(cm)
print('Running full extraction (00_RunAllExtractors) via Orchestrator...')
# Ensure script is registered
cm.config.set('Scripts', 'all_extractors', '00_RunAllExtractors.pas')
# Success marker from the RunAllExtractors flow
success_marker = '[AutoPatcher] All-in-one extraction process started.'
# Expected outputs (we'll look for weapon_omod_map.json among them)
expected_outputs = ['weapon_omod_map.json', 'weapon_ammo_map.json', 'munitions_ammo_ids.ini']
res = orch.run_xedit_script('all_extractors', success_marker, expected_outputs)
print('Result:', res)
out = cm.get_path('Paths','output_dir')
print('Output dir:', out)
for p in sorted(out.iterdir()):
    print(' -', p.name)
