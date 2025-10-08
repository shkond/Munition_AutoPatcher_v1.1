"""
引数構築のテスト
Arguments construction test
"""
from config_manager import ConfigManager
from Orchestrator import Orchestrator
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_argument_construction():
    """xEdit引数の構築をテストします"""
    print("=" * 60)
    print("引数構築テスト開始")
    print("=" * 60)
    
    try:
        config = ConfigManager('config.ini')
        orchestrator = Orchestrator(config)
        
        # 設定値を表示
        env_settings = config.get_env_settings()
        print("\n[設定値]")
        print(f"  use_mo2: {env_settings.get('use_mo2')}")
        if env_settings.get('use_mo2'):
            print(f"  mo2_executable_path: {env_settings.get('mo2_executable_path')}")
            print(f"  xedit_profile_name: {env_settings.get('xedit_profile_name')}")
        
        xedit_path = config.get_path('Paths', 'xedit_executable')
        print(f"  xedit_executable: {xedit_path}")
        
        game_data_path = config.get_path('Paths', 'game_data_path')
        print(f"  game_data_path: {game_data_path}")
        
        # xEdit 引数の例を表示（実際の実行はしない）
        print("\n[構築される xEdit 引数の例]")
        xedit_args = []
        
        # ゲーム指定
        use_mo2 = env_settings.get('use_mo2', False)
        if not use_mo2 and xedit_path.name.lower() == "xedit.exe":
            xedit_args.append("-FO4")
            print("  ✓ -FO4 (ゲーム指定)")
        
        # スクリプト指定
        xedit_args.append("-script:TEMP_example.pas")
        print("  ✓ -script:TEMP_example.pas")
        
        # スクリプトディレクトリ指定
        edit_scripts_dir = xedit_path.parent / "Edit Scripts"
        xedit_args.append(f'-S:"{edit_scripts_dir}\\"')
        print(f'  ✓ -S:"{edit_scripts_dir}\\"')
        
        # 警告抑制とマスターファイル編集許可
        xedit_args.extend([
            "-IKnowWhatImDoing",
            "-AllowMasterFilesEdit"
        ])
        print("  ✓ -IKnowWhatImDoing")
        print("  ✓ -AllowMasterFilesEdit")
        
        # ログファイル指定
        xedit_args.append('-L:"Output/xEdit_session_example.log"')
        print('  ✓ -L:"Output/xEdit_session_example.log"')
        
        # キャッシュオプション
        use_cache = orchestrator._should_use_cache()
        if use_cache:
            xedit_args.append("-cache")
            print("  ✓ -cache")
        
        # Data パス指定
        force_data_param = config.get_boolean('Parameters', 'force_data_param', False)
        if use_mo2 and not force_data_param:
            print("  ✗ -D (MO2使用時は省略)")
        else:
            xedit_args.append(f'-D:"{game_data_path}"')
            print(f'  ✓ -D:"{game_data_path}"')
        
        # 完全なコマンドライン
        print("\n[完全なコマンドライン（MO2経由の場合）]")
        if use_mo2:
            xedit_name = xedit_path.name.lower()
            if xedit_name == "fo4edit.exe":
                executable_name_in_mo2 = "FO4Edit"
            elif xedit_name == "xedit.exe":
                executable_name_in_mo2 = "xEdit"
            else:
                executable_name_in_mo2 = xedit_path.stem
            
            command_list = [
                str(env_settings.get('mo2_executable_path')),
                '-p',
                str(env_settings.get('xedit_profile_name')),
                f'moshortcut://:{executable_name_in_mo2}'
            ]
            print("  " + " ".join(f'"{arg}"' if " " in arg else arg for arg in command_list))
        else:
            print("\n[完全なコマンドライン（直接起動の場合）]")
            command_list = [str(xedit_path)] + xedit_args
            print("  " + " ".join(f'"{arg}"' if " " in arg else arg for arg in command_list))
        
        print("\n" + "=" * 60)
        print("✓ テスト成功")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_argument_construction()
    exit(0 if success else 1)
