"""
成果物収集機能の単体テスト
"""

from config_manager import ConfigManager
from Orchestrator import Orchestrator
import logging

logging.basicConfig(level=logging.DEBUG)

config = ConfigManager('config.ini')
orchestrator = Orchestrator(config)

# 直接テスト
result = orchestrator._move_results_from_overwrite([
    'weapon_ammo_map.json',
    'unique_ammo_for_mapping.ini'
])

print(f"\n結果: {'✓ 成功' if result else '✗ 失敗'}")

# Output ディレクトリを確認
from pathlib import Path
output_dir = Path('Output')
if output_dir.exists():
    print(f"\nOutput ディレクトリの内容:")
    for f in output_dir.glob('*'):
        if f.is_file():
            print(f"  - {f.name} ({f.stat().st_size} bytes)")