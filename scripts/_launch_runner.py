import sys, os
sys.path.insert(0, os.getcwd())
from scripts.run_minimal_probe_runner import run
print('launcher start')
run()
print('launcher finished')
