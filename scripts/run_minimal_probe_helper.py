import sys
sys.path.insert(0, r'E:\Munition_AutoPatcher_v1.1')
from config_manager import ConfigManager
from Orchestrator import Orchestrator
cm=ConfigManager('config.ini')
orch=Orchestrator(cm)
print('Running minimal_probe via Orchestrator...')
res=orch.run_xedit_script('minimal_probe', 'Minimal probe', expected_outputs=None)
print('Result:', res)
