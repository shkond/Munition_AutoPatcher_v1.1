from config_manager import ConfigManager
from robco_ini_generate import run

cm = ConfigManager('config.ini')
class CfgStub:
    def __init__(self, cm):
        self.cm = cm
    def get_path(self, section, key):
        return self.cm.get_path(section, key)
    def get_boolean(self, section, key, fallback=None):
        try:
            return self.cm.get_boolean(section, key, fallback)
        except Exception:
            return fallback
    def get_string(self, section, key, fallback=''):
        return self.cm.get_string(section, key, fallback)

cfg = CfgStub(cm)
print('Running robco_ini_generate.run(cfg) dry-run...')
ok = run(cfg)
print('run() returned ->', ok)
