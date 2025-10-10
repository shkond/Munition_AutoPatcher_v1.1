"""
MO2 moshortcut URI 診断スクリプト

このスクリプトは、異なるmoshortcut URI形式をテストし、
どれが動作するかを確認します。

使用方法:
    python debug_mo2_shortcut.py

前提条件:
    - config.ini に MO2 と xEdit の設定が済んでいること
    - MO2 が閉じていること（スクリプトが自動で終了させます）
"""

import sys
import time
import subprocess
import logging
from pathlib import Path
from config_manager import ConfigManager
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def terminate_mo2():
    """実行中のMO2プロセスを終了"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'ModOrganizer.exe' in proc.info['name']:
            try:
                logging.info(f"MO2プロセス終了中 (PID={proc.pid})")
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                logging.warning(f"MO2終了エラー: {e}")

def test_moshortcut_uri(
    mo2_exe: Path,
    profile: str,
    uri: str,
    xedit_exe_name: str,
    timeout: int = 15
) -> bool:
    """
    特定のmoshortcut URIをテストする
    
    Returns:
        True: xEditが起動に成功
        False: タイムアウトまたはエラー
    """
    logging.info(f"\n{'='*60}")
    logging.info(f"テスト URI: {uri}")
    logging.info(f"{'='*60}")
    
    # MO2を起動
    command = [str(mo2_exe), "-p", profile, uri]
    logging.info(f"コマンド: {' '.join(command)}")
    
    try:
        launch_ts = time.time()
        proc = subprocess.Popen(command)
        logging.info(f"MO2起動 (PID={proc.pid})")
        
        # xEdit プロセスの検出を待機
        detect_start = time.time()
        xedit_found = False
        
        while time.time() - detect_start < timeout:
            for p in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if p.info['name'] and p.info['name'].lower() == xedit_exe_name.lower():
                        if p.info['create_time'] >= (launch_ts - 1.0):
                            logging.info(f"✓ xEdit検出成功 (PID={p.info['pid']})")
                            xedit_found = True
                            # xEditを即座に終了
                            xedit_proc = psutil.Process(p.info['pid'])
                            xedit_proc.terminate()
                            xedit_proc.wait(timeout=5)
                            logging.info("  xEditを終了しました")
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if xedit_found:
                break
            time.sleep(0.5)
        
        if not xedit_found:
            logging.error(f"✗ タイムアウト: {timeout}秒以内にxEditが起動しませんでした")
        
        # MO2を終了
        terminate_mo2()
        time.sleep(1)
        
        return xedit_found
        
    except Exception as e:
        logging.error(f"✗ エラー発生: {e}")
        terminate_mo2()
        return False

def main():
    print("=" * 60)
    print("MO2 moshortcut URI 診断ツール")
    print("=" * 60)
    
    try:
        # 設定読み込み
        config = ConfigManager('config.ini')
        env = config.get_env_settings()
        
        mo2_exe = Path(env.get('mo2_executable_path', ''))
        if not mo2_exe.exists():
            logging.error(f"MO2実行ファイルが見つかりません: {mo2_exe}")
            logging.error("config.ini の [Environment] mo2_executable_path を確認してください")
            return False
        
        profile = env.get('xedit_profile_name', '')
        if not profile:
            logging.error("プロファイル名が設定されていません")
            logging.error("config.ini の [Environment] xedit_profile_name を設定してください")
            return False
        
        entry_name = env.get('mo2_xedit_entry_name', 'xEdit')
        instance_name = env.get('mo2_instance_name', '')
        
        xedit_exe = config.get_path('Paths', 'xedit_executable')
        xedit_exe_name = xedit_exe.name
        
        logging.info("\n[設定情報]")
        logging.info(f"  MO2実行ファイル: {mo2_exe}")
        logging.info(f"  プロファイル: {profile}")
        logging.info(f"  エントリ名: {entry_name}")
        logging.info(f"  インスタンス名: {instance_name or '(未設定)'}")
        logging.info(f"  xEdit実行ファイル: {xedit_exe_name}")
        
        # 既存のMO2を終了
        logging.info("\n[準備] 既存のMO2プロセスを終了中...")
        terminate_mo2()
        time.sleep(2)
        
        # テストするURI形式のリスト
        test_cases = [
            ("コロンなし形式", f"moshortcut://{entry_name}"),
            ("コロンあり形式", f"moshortcut://:{entry_name}"),
        ]
        
        if instance_name:
            test_cases.insert(0, ("インスタンス修飾形式", f"moshortcut://{instance_name}/{entry_name}"))
        
        # 各URIをテスト
        results = {}
        for label, uri in test_cases:
            result = test_moshortcut_uri(mo2_exe, profile, uri, xedit_exe_name)
            results[label] = result
            time.sleep(2)  # 次のテストの前に少し待機
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("[テスト結果サマリー]")
        print("=" * 60)
        
        success_count = 0
        for label, uri in test_cases:
            status = "✓ 成功" if results[label] else "✗ 失敗"
            print(f"  {status}: {label}")
            print(f"    URI: {uri}")
            if results[label]:
                success_count += 1
        
        print("\n" + "=" * 60)
        if success_count > 0:
            print(f"[結論] {success_count}/{len(test_cases)} 形式が動作しました")
            print("\n推奨設定:")
            for label, uri in test_cases:
                if results[label]:
                    format_value = "no_colon" if "コロンなし" in label else \
                                   "with_colon" if "コロンあり" in label else "instance"
                    print(f"  config.ini に以下を設定:")
                    print(f"    mo2_shortcut_format = {format_value}")
                    if format_value == "instance":
                        print(f"    mo2_instance_name = {instance_name}")
                    break
        else:
            print("[警告] すべての形式が失敗しました")
            print("\nトラブルシューティング:")
            print("  1. MO2の『実行』メニューに '{entry_name}' が登録されているか確認")
            print("  2. MO2のショートカット設定を確認")
            print("  3. MO2を手動起動してプロファイルが正しく読み込まれるか確認")
        print("=" * 60)
        
        return success_count > 0
        
    except Exception as e:
        logging.error(f"致命的エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # クリーンアップ
        terminate_mo2()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
