"""
config.ini のパス設定を診断します
"""

import sys
from pathlib import Path
from config_manager import ConfigManager

def main():
    print("=" * 60)
    print("設定ファイル診断ツール")
    print("=" * 60)
    
    try:
        config = ConfigManager('config.ini')
        
        # 主要パスを検証
        paths_to_check = [
            ('Paths', 'overwrite_path'),
            ('Paths', 'game_data_path'),
            ('Paths', 'xedit_executable'),
            ('Paths', 'output_dir'),
            ('Paths', 'project_root'),
        ]
        
        print("\n[Paths] セクションの検証:")
        for section, option in paths_to_check:
            try:
                path = config.get_path(section, option)
                exists = path.exists()
                status = "✓" if exists else "✗"
                print(f"  {status} {option}: {path}")
                if not exists:
                    print(f"      [警告] パスが存在しません")
            except Exception as e:
                print(f"  ✗ {option}: 取得失敗 ({e})")
        
        # Environment 設定を検証
        print("\n[Environment] セクションの検証:")
        try:
            env = config.get_env_settings()
            print(f"  use_mo2: {env.get('use_mo2')}")
            
            if env.get('use_mo2'):
                print(f"  mo2_executable_path: {env.get('mo2_executable_path')}")
                print(f"  xedit_profile_name: {env.get('xedit_profile_name')}")
                
                mo2_ow = env.get('mo2_overwrite_dir')
                if mo2_ow:
                    mo2_ow_path = Path(mo2_ow)
                    exists = mo2_ow_path.exists()
                    status = "✓" if exists else "✗"
                    print(f"  {status} mo2_overwrite_dir: {mo2_ow_path}")
                    
                    # Edit Scripts/Output の確認
                    output_dir = mo2_ow_path / 'Edit Scripts' / 'Output'
                    output_exists = output_dir.exists()
                    status = "✓" if output_exists else "✗"
                    print(f"  {status}   └─ Edit Scripts/Output: {output_dir}")
        except Exception as e:
            print(f"  [エラー] Environment 取得失敗: {e}")
        
        # xEdit 実行フォルダの確認
        print("\n[xEdit 関連] の検証:")
        try:
            xedit_exe = config.get_path('Paths', 'xedit_executable')
            xedit_dir = xedit_exe.parent
            edit_scripts = xedit_dir / 'Edit Scripts'
            edit_output = edit_scripts / 'Output'
            
            print(f"  xEdit 実行ファイル: {xedit_exe}")
            print(f"    存在: {xedit_exe.exists()}")
            print(f"  Edit Scripts: {edit_scripts}")
            print(f"    存在: {edit_scripts.exists()}")
            print(f"  Edit Scripts/Output: {edit_output}")
            print(f"    存在: {edit_output.exists()}")
            
            if edit_output.exists():
                files = list(edit_output.glob('*'))
                print(f"    ファイル数: {len(files)}")
        except Exception as e:
            print(f"  [エラー] xEdit パス検証失敗: {e}")
        
        print("\n" + "=" * 60)
        print("[診断完了]")
        return True
        
    except Exception as e:
        print(f"\n[致命的エラー] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)