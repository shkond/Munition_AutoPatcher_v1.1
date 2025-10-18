from config_manager import ConfigManager
from Orchestrator import Orchestrator
import traceback

if __name__ == '__main__':
    try:
        cfg = ConfigManager('config.direct.ini')
        orch = Orchestrator(cfg)
        print('Running minimal_probe via Orchestrator.run_xedit_script() with direct xEdit (no MO2)')
        ok = orch.run_xedit_script('minimal_probe', '[COMPLETE] Minimal probe')
        print('Orchestrator.run_xedit_script returned:', ok)
    except Exception as e:
        print('Exception while running:', e)
        traceback.print_exc()

def run():
    try:
        cfg = ConfigManager('config.direct.ini')
        orch = Orchestrator(cfg)
        print('Running minimal_probe via Orchestrator.run_xedit_script() with direct xEdit (no MO2)')
        ok = orch.run_xedit_script('minimal_probe', '[COMPLETE] Minimal probe')
        print('Orchestrator.run_xedit_script returned:', ok)
        return ok
    except Exception as e:
        print('Exception while running:', e)
        traceback.print_exc()
        return False
