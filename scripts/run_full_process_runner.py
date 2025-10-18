from config_manager import ConfigManager
from Orchestrator import Orchestrator
import traceback

if __name__ == '__main__':
    try:
        cfg = ConfigManager('config.ini')
        orch = Orchestrator(cfg)
        print('Running full process via Orchestrator.run_full_process()')
        ok = orch.run_full_process()
        print('Orchestrator.run_full_process returned:', ok)
    except Exception as e:
        print('Exception while running:', e)
        traceback.print_exc()

def run():
    try:
        cfg = ConfigManager('config.ini')
        orch = Orchestrator(cfg)
        print('Running full process via Orchestrator.run_full_process()')
        ok = orch.run_full_process()
        print('Orchestrator.run_full_process returned:', ok)
        return ok
    except Exception as e:
        print('Exception while running:', e)
        traceback.print_exc()
        return False
