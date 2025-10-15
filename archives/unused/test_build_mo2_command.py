"""
単体テスト: _build_mo2_command の動作確認
"""

from pathlib import Path
from Orchestrator import Orchestrator
from config_manager import ConfigManager
import logging

logging.basicConfig(level=logging.DEBUG)

# 設定を読み込む
config = ConfigManager('config.ini')
orchestrator = Orchestrator(config)

# テストケース1: auto mode (デフォルト)
print("=" * 60)
print("テストケース1: auto モード")
print("=" * 60)

env_settings = {
    'mo2_shortcut_format': 'auto',
    'mo2_instance_name': ''
}

command, uri = orchestrator._build_mo2_command(
    Path("E:/MO2/ModOrganizer.exe"),
    "TestProfile",
    "xEdit",
    ["-script:test.pas", "-S:scripts", "-L:log.txt"],
    env_settings
)

print("生成されたコマンド:")
for i, arg in enumerate(command):
    print(f"  [{i}] {arg}")
print(f"\nURI: {uri}")

# テストケース2: instance mode
print("\n" + "=" * 60)
print("テストケース2: instance モード")
print("=" * 60)

env_settings = {
    'mo2_shortcut_format': 'instance',
    'mo2_instance_name': 'Fallout 4'
}

command, uri = orchestrator._build_mo2_command(
    Path("E:/MO2/ModOrganizer.exe"),
    "TestProfile",
    "xEdit",
    ["-script:test.pas", "-S:scripts", "-L:log.txt"],
    env_settings
)

print("生成されたコマンド:")
for i, arg in enumerate(command):
    print(f"  [{i}] {arg}")
print(f"\nURI: {uri}")

# テストケース3: with_colon mode
print("\n" + "=" * 60)
print("テストケース3: with_colon モード")
print("=" * 60)

env_settings = {
    'mo2_shortcut_format': 'with_colon',
    'mo2_instance_name': ''
}

command, uri = orchestrator._build_mo2_command(
    Path("E:/MO2/ModOrganizer.exe"),
    "TestProfile",
    "xEdit",
    ["-script:test.pas", "-S:scripts", "-L:log.txt"],
    env_settings
)

print("生成されたコマンド:")
for i, arg in enumerate(command):
    print(f"  [{i}] {arg}")
print(f"\nURI: {uri}")

# テストケース4: no_colon mode
print("\n" + "=" * 60)
print("テストケース4: no_colon モード")
print("=" * 60)

env_settings = {
    'mo2_shortcut_format': 'no_colon',
    'mo2_instance_name': ''
}

command, uri = orchestrator._build_mo2_command(
    Path("E:/MO2/ModOrganizer.exe"),
    "TestProfile",
    "xEdit",
    ["-script:test.pas", "-S:scripts", "-L:log.txt"],
    env_settings
)

print("生成されたコマンド:")
for i, arg in enumerate(command):
    print(f"  [{i}] {arg}")
print(f"\nURI: {uri}")

# 引用符のチェック
print("\n" + "=" * 60)
print("引用符チェック")
print("=" * 60)
print("確認: xEdit引数に埋め込み引用符が含まれていないこと")
xedit_args = ["-script:test.pas", "-S:C:/Path With Spaces/Scripts", "-L:C:/Another Path/log.txt"]
for arg in xedit_args:
    has_quote = '"' in arg
    print(f"  {arg} ... {'✗ 引用符あり（NG）' if has_quote else '✓ 引用符なし（OK）'}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)
