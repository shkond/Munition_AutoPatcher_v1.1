import logging
from config_manager import ConfigManager
from Orchestrator import Orchestrator

# loggingをDEBUGレベルに設定
logging.basicConfig(level=logging.DEBUG)

# 1. ConfigManagerとOrchestratorを初期化
cm = ConfigManager('config.ini')
orch = Orchestrator(cm)

# 2. テストスクリプトの情報をconfig.iniに追加
script_name = 'mteFilesTests'
script_path = 'testmtelib\mteFilesTests.pas'
cm.config.set('Scripts', script_name, script_path)

# 3. Orchestratorを使ってスクリプトを実行
#    success_messageを意図的に見つからないものにし、代替ログを探索させる
print(f'Running {script_name} via Orchestrator...')
res = orch.run_xedit_script(script_name, '__NEVER_FIND_THIS__') 

# 4. 結果を表示
print('Result:', res)

# ログファイルはOrchestrator内のloggingによってコンソールに出力されるはず
print("Test finished. Check the console output for logs.")