"""
xEdit キャッシュ機能の診断・テストスクリプト
キャッシュ関連の全機能を単体でテストします
"""

import sys
import time
import subprocess
import psutil
from pathlib import Path
from config_manager import ConfigManager
from Orchestrator import Orchestrator
import logging

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_section(title):
    """セクション区切り線を表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

# ★★★ 追加: MO2起動確認関数 ★★★
def is_mo2_running(mo2_executable_path: str) -> bool:
    """
    MO2が起動しているか確認します
    
    Args:
        mo2_executable_path: MO2実行ファイルのパス
    
    Returns:
        bool: MO2が起動している場合 True
    """
    mo2_name = Path(mo2_executable_path).name.lower()
    
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() == mo2_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return False

# ★★★ 追加: MO2起動関数 ★★★
def launch_mo2_if_needed(orchestrator) -> bool:
    """
    MO2を使用する設定で、かつMO2が起動していない場合、起動を試みます
    
    Args:
        orchestrator: Orchestratorインスタンス
    
    Returns:
        bool: MO2が起動済み、または起動成功した場合 True
    """
    try:
        env = orchestrator.config.get_env_settings()
        use_mo2 = env.get('use_mo2', False)
        
        if not use_mo2:
            print("  MO2使用設定: 無効 → MO2起動不要")
            return True
        
        mo2_executable = env.get('mo2_executable_path')
        profile_name = env.get('xedit_profile_name')
        
        if not mo2_executable:
            print("  ⚠ MO2実行ファイルパスが設定されていません")
            return False
        
        if not profile_name:
            print("  ⚠ xEdit プロファイル名が設定されていません")
            return False
        
        # ★★★ 修正: FO4Edit/xEditが既に起動しているか確認 ★★★
        xedit_executable = orchestrator.config.get_path('Paths', 'xedit_executable')
        xedit_name = xedit_executable.name.lower()
        
        xedit_running = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == xedit_name:
                    xedit_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if xedit_running:
            print(f"  ✓ {xedit_executable.name} は既に起動しています")
            return True
        
        # 起動を試みる
        print(f"  {xedit_executable.name} が起動していません")
        response = input("  MO2経由でFO4Editを起動しますか? (yes/no): ")
        
        if response.lower() != 'yes':
            print("  ⚠ 起動せずに続行します（キャッシュ検出できない可能性があります）")
            return False
        
        # ★★★ 修正: moshortcut:// プロトコルを使用してFO4Editを起動 ★★★
        # MO2の「実行ファイルリスト」で設定された名前を取得
        # デフォルトは "FO4Edit" だが、設定で変更可能にする
        executable_name_in_mo2 = "FO4Edit"  # または xEdit
        
        # xEdit.exe の場合は "xEdit" を使用
        if xedit_name == "xedit.exe":
            executable_name_in_mo2 = "xEdit"
        
        command = [
            mo2_executable,
            "-p",
            profile_name,
            f"moshortcut://:{executable_name_in_mo2}"
        ]
        
        print(f"  [起動中] MO2経由で {executable_name_in_mo2} を起動")
        print(f"  コマンド: {' '.join(command)}")
        
        try:
            # ★★★ 重要: subprocess.Popen でバックグラウンド起動 ★★★
            # subprocess.run だと FO4Edit の終了を待ってしまうため、Popen を使用
            subprocess.Popen(command)
            
            # FO4Edit/xEdit プロセスの起動を待機（最大60秒）
            print(f"  {xedit_executable.name} プロセスの起動を待機中...", end="", flush=True)
            wait_start = time.time()
            while time.time() - wait_start < 60:
                for proc in psutil.process_iter(['name']):
                    try:
                        if proc.info['name'].lower() == xedit_name:
                            print(" ✓ 起動完了")
                            # キャッシュ生成の待機時間（プラグイン読み込み）
                            print("  プラグイン読み込み完了を待機中（10秒）...", end="", flush=True)
                            time.sleep(10)
                            print(" ✓")
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                time.sleep(1)
                print(".", end="", flush=True)
            
            print(" ✗ タイムアウト")
            print(f"  ⚠ {xedit_executable.name} の起動に失敗しました")
            print(f"\n  [トラブルシューティング]")
            print(f"    1. MO2の「実行ファイルリスト」で '{executable_name_in_mo2}' が登録されているか確認")
            print(f"    2. 登録名が異なる場合、debug_cache.py の executable_name_in_mo2 を修正")
            print(f"    3. 手動でMO2から {xedit_executable.name} を起動してキャッシュを生成してください")
            return False
            
        except FileNotFoundError:
            print(f"\n  ✗ エラー: ModOrganizer.exe が見つかりません: {mo2_executable}")
            return False
        except Exception as e:
            print(f"\n  ✗ 起動コマンド実行エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"  ✗ MO2起動確認中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_cache_path(orchestrator):
    """_get_cache_path() のテスト"""
    print_section("1. キャッシュパスの取得テスト")
    
    try:
        print("[候補パスの確認]")
        
        # MO2設定の確認
        try:
            env = orchestrator.config.get_env_settings()
            use_mo2 = env.get('use_mo2', False)
            print(f"  MO2使用: {use_mo2}")
            
            if use_mo2:
                # ★★★ 追加: プロファイル名を表示 ★★★
                profile_name = env.get('xedit_profile_name')
                print(f"  プロファイル名: {profile_name}")
                
                # ★★★ 追加: プロファイル内キャッシュ ★★★
                mo2_executable = env.get('mo2_executable_path')
                if mo2_executable and profile_name:
                    mo2_dir = Path(mo2_executable).parent
                    
                    # インスタンス版
                    profile_cache_instance = mo2_dir / 'profiles' / profile_name / 'FO4Edit Cache'
                    exists = profile_cache_instance.exists()
                    status = "✓" if exists else "✗"
                    print(f"  {status} MO2プロファイル(インスタンス版): {profile_cache_instance}")
                    if exists:
                        cache_count = len(list(profile_cache_instance.glob('*.cache')))
                        print(f"      キャッシュファイル数: {cache_count}")
                    
                    # ポータブル版
                    mo2_ow_dir = env.get('mo2_overwrite_dir')
                    if mo2_ow_dir:
                        mo2_base = Path(mo2_ow_dir).parent
                        profile_cache_portable = mo2_base / 'profiles' / profile_name / 'FO4Edit Cache'
                        exists = profile_cache_portable.exists()
                        status = "✓" if exists else "✗"
                        print(f"  {status} MO2プロファイル(ポータブル版): {profile_cache_portable}")
                        if exists:
                            cache_count = len(list(profile_cache_portable.glob('*.cache')))
                            print(f"      キャッシュファイル数: {cache_count}")
                
                # overwrite_path
                try:
                    overwrite_path = orchestrator.config.get_path('Paths', 'overwrite_path')
                    mo2_cache = overwrite_path / 'FO4Edit Cache'
                    exists = mo2_cache.exists()
                    status = "✓" if exists else "✗"
                    print(f"  {status} MO2 overwrite: {mo2_cache}")
                    if exists:
                        cache_count = len(list(mo2_cache.glob('*.cache')))
                        print(f"      キャッシュファイル数: {cache_count}")
                except Exception as e:
                    print(f"  ✗ overwrite_path 取得失敗: {e}")
                
                # mo2_overwrite_dir
                mo2_ow_dir = env.get('mo2_overwrite_dir')
                if mo2_ow_dir:
                    mo2_alt_cache = Path(mo2_ow_dir) / 'FO4Edit Cache'
                    exists = mo2_alt_cache.exists()
                    status = "✓" if exists else "✗"
                    print(f"  {status} MO2 環境設定: {mo2_alt_cache}")
                    if exists:
                        cache_count = len(list(mo2_alt_cache.glob('*.cache')))
                        print(f"      キャッシュファイル数: {cache_count}")
        except Exception as e:
            print(f"  [エラー] 環境設定取得失敗: {e}")
        
        # xEditフォルダ
        try:
            xedit_executable = orchestrator.config.get_path('Paths', 'xedit_executable')
            xedit_cache = xedit_executable.parent / 'FO4Edit Cache'
            exists = xedit_cache.exists()
            status = "✓" if exists else "✗"
            print(f"  {status} xEditフォルダ: {xedit_cache}")
            if exists:
                cache_count = len(list(xedit_cache.glob('*.cache')))
                print(f"      キャッシュファイル数: {cache_count}")
        except Exception as e:
            print(f"  ✗ xEdit実行ファイルパス取得失敗: {e}")
        
        # 実際の取得結果
        print("\n[実際の取得結果]")
        cache_path = orchestrator._get_cache_path()
        
        if cache_path:
            print(f"✓ キャッシュディレクトリ: {cache_path}")
            print(f"  存在: {cache_path.exists()}")
            
            if cache_path.exists():
                cache_files = list(cache_path.glob('*.cache'))
                print(f"  キャッシュファイル数: {len(cache_files)}")
                
                if cache_files:
                    print("\n  キャッシュファイル一覧:")
                    for idx, cf in enumerate(cache_files, 1):
                        size_mb = cf.stat().st_size / (1024 * 1024)
                        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cf.stat().st_mtime))
                        age_hours = (time.time() - cf.stat().st_mtime) / 3600
                        print(f"    {idx}. {cf.name}")
                        print(f"       サイズ: {size_mb:.2f} MB")
                        print(f"       最終更新: {mtime} ({age_hours:.1f}時間前)")
                else:
                    print("  ⚠ キャッシュファイルが見つかりません")
                    print("\n  [ヒント]")
                    print("    1. MO2経由で一度 FO4Edit を起動してください")
                    print("    2. プラグインを読み込んでキャッシュを生成します")
                    print("    3. 次回以降、自動的に高速化されます")
        else:
            print("✗ キャッシュディレクトリが見つかりません")
            print("\n[推奨アクション]")
            print("  1. config.ini の xedit_profile_name を確認")
            print("     現在: {}".format(orchestrator.config.get_string('Environment', 'xedit_profile_name')))
            print("  2. MO2で実際に使用しているプロファイル名と一致させてください")
        
        return cache_path
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_should_use_cache(orchestrator):
    """_should_use_cache() のテスト"""
    print_section("2. キャッシュ使用判定テスト")
    
    try:
        # config.ini の設定を表示
        print("[設定値の確認]")
        try:
            use_cache_config = orchestrator.config.get_boolean('Parameters', 'use_xedit_cache', True)
            max_age_config = orchestrator._get_numeric('Parameters', 'max_cache_age_hours', 168, int)
            print(f"  use_xedit_cache: {use_cache_config}")
            print(f"  max_cache_age_hours: {max_age_config}")
        except Exception as e:
            print(f"  ⚠ 設定読み込みエラー: {e}")
        
        print("\n[判定実行]")
        should_use = orchestrator._should_use_cache()
        
        if should_use:
            print("✓ 判定結果: キャッシュを使用する")
        else:
            print("✗ 判定結果: キャッシュを使用しない")
        
        print("\n[判定理由の詳細]")
        
        # 設定確認
        use_cache_config = orchestrator.config.get_boolean('Parameters', 'use_xedit_cache', True)
        if not use_cache_config:
            print("  ✗ config.ini で use_xedit_cache = False に設定されている")
            return should_use
        else:
            print("  ✓ config.ini で use_xedit_cache = True")
        
        # キャッシュディレクトリ確認
        cache_dir = orchestrator._get_cache_path()
        if not cache_dir:
            print("  ✗ キャッシュディレクトリが存在しない")
            return should_use
        else:
            print(f"  ✓ キャッシュディレクトリ存在: {cache_dir}")
        
        # キャッシュファイル確認
        cache_files = list(cache_dir.glob('*.cache'))
        if not cache_files:
            print("  ✗ キャッシュファイルが見つからない (初回実行)")
            return should_use
        else:
            print(f"  ✓ キャッシュファイル発見: {len(cache_files)}個")
        
        # キャッシュの新しさ確認
        newest_cache = max(cache_files, key=lambda p: p.stat().st_mtime)
        cache_age_hours = (time.time() - newest_cache.stat().st_mtime) / 3600
        max_cache_age = orchestrator._get_numeric('Parameters', 'max_cache_age_hours', 168, int)
        
        print(f"\n  最新キャッシュ: {newest_cache.name}")
        print(f"  経過時間: {cache_age_hours:.1f}時間")
        print(f"  有効期限: {max_cache_age}時間")
        
        if cache_age_hours > max_cache_age:
            print(f"  ✗ キャッシュが古すぎる ({cache_age_hours:.1f} > {max_cache_age})")
        else:
            print(f"  ✓ キャッシュは有効期限内 ({cache_age_hours:.1f} ≤ {max_cache_age})")
        
        return should_use
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_clear_cache(orchestrator):
    """_clear_cache() のテスト"""
    print_section("3. キャッシュクリアテスト")
    
    # 事前確認
    cache_dir = orchestrator._get_cache_path()
    if not cache_dir or not cache_dir.exists():
        print("⚠ キャッシュディレクトリが存在しないため、テストをスキップします")
        return True
    
    cache_files_before = list(cache_dir.glob('*.cache'))
    print(f"[実行前] キャッシュファイル数: {len(cache_files_before)}")
    
    if not cache_files_before:
        print("⚠ クリアするキャッシュが存在しません")
        return True
    
    # ユーザー確認
    print("\n⚠ 警告: キャッシュをクリアすると次回の xEdit 起動が遅くなります")
    response = input("本当にキャッシュをクリアしますか? (yes/no): ")
    
    if response.lower() != 'yes':
        print("✓ キャッシュクリアをキャンセルしました")
        return True
    
    try:
        print("\n[実行中] キャッシュをクリア中...")
        result = orchestrator._clear_cache()
        
        # 事後確認
        cache_files_after = list(cache_dir.glob('*.cache'))
        deleted_count = len(cache_files_before) - len(cache_files_after)
        
        if result:
            print(f"✓ キャッシュクリア成功")
            print(f"  削除されたファイル: {deleted_count}個")
            print(f"  残りのファイル: {len(cache_files_after)}個")
            
            if cache_files_after:
                print("\n  ⚠ 一部のファイルが削除できませんでした:")
                for cf in cache_files_after:
                    print(f"    - {cf.name}")
        else:
            print(f"✗ キャッシュクリア失敗")
        
        return result
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_command_line(orchestrator):
    """xEdit コマンドラインでの -cache オプションテスト"""
    print_section("4. xEdit コマンドライン -cache オプションテスト")
    
    print("[シミュレーション] run_xedit_script() での -cache パラメータ追加")
    
    # 設定情報を取得
    try:
        xedit_executable = orchestrator.config.get_path('Paths', 'xedit_executable')
        game_data_path = orchestrator.config.get_path('Paths', 'game_data_path')
        print(f"\nxEdit 実行ファイル: {xedit_executable}")
        print(f"ゲームDataパス: {game_data_path}")
    except Exception as e:
        print(f"✗ 設定取得エラー: {e}")
        return False
    
    # キャッシュ使用判定
    should_use = orchestrator._should_use_cache()
    
    # コマンドライン例を表示
    print("\n[生成されるコマンドライン例]")
    
    command_parts = [
        str(xedit_executable),
        "-FO4",
        "-IKnowWhatImDoing",
        "-AllowMasterFilesEdit",
        "-script:TEMP_example.pas",
        '-L:"E:/Munition_AutoPatcher_v1.1/Output/xEdit_session_example.log"'
    ]
    
    if should_use:
        command_parts.append("-cache")
        print("✓ -cache オプションが追加されます\n")
    else:
        print("✗ -cache オプションは追加されません\n")
    
    # コマンド全体を表示
    for idx, part in enumerate(command_parts, 1):
        print(f"  {idx}. {part}")
    
    print("\n[PowerShell 再現コマンド]")
    pwsh_line = " ".join(f'"{p}"' if " " in p else p for p in command_parts)
    print(f"  {pwsh_line}")
    
    return True

def test_cache_performance_estimate(orchestrator):
    """キャッシュによるパフォーマンス向上の推定"""
    print_section("5. キャッシュパフォーマンス推定")
    
    cache_dir = orchestrator._get_cache_path()
    if not cache_dir or not cache_dir.exists():
        print("⚠ キャッシュが存在しないため、推定をスキップします")
        return
    
    cache_files = list(cache_dir.glob('*.cache'))
    if not cache_files:
        print("⚠ キャッシュファイルが存在しないため、推定をスキップします")
        return
    
    # キャッシュサイズから推定
    total_size_mb = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)
    plugin_count_estimate = len(cache_files)  # 通常、プラグイン数とキャッシュファイル数は対応
    
    print(f"[推定情報]")
    print(f"  キャッシュファイル数: {len(cache_files)}")
    print(f"  総キャッシュサイズ: {total_size_mb:.2f} MB")
    print(f"  推定プラグイン数: {plugin_count_estimate}")
    
    print(f"\n[パフォーマンス推定]")
    
    # 経験則に基づく推定
    if plugin_count_estimate < 50:
        print("  プラグイン数: 少ない")
        print("  キャッシュなし起動時間: 約30秒~1分")
        print("  キャッシュあり起動時間: 約5~10秒")
        print("  短縮時間: 約20~50秒")
    elif plugin_count_estimate < 150:
        print("  プラグイン数: 中程度")
        print("  キャッシュなし起動時間: 約1~3分")
        print("  キャッシュあり起動時間: 約10~20秒")
        print("  短縮時間: 約1~3分")
    else:
        print("  プラグイン数: 多い")
        print("  キャッシュなし起動時間: 約3~10分")
        print("  キャッシュあり起動時間: 約20~60秒")
        print("  短縮時間: 約3~10分")
    
    print("\n  ✓ キャッシュ使用により、大幅な時間短縮が期待できます")

def main():
    print("=" * 60)
    print("  xEdit キャッシュ機能 診断・テストツール")
    print("=" * 60)
    
    try:
        # 設定とオーケストレータの初期化
        print("\n[初期化]")
        config = ConfigManager('config.ini')
        orchestrator = Orchestrator(config)
        print("✓ 設定読み込み完了")
        
        # ★★★ 追加: MO2起動確認 ★★★
        print_section("MO2起動確認")
        mo2_launched = launch_mo2_if_needed(orchestrator)
        
        if not mo2_launched:
            print("\n⚠ 警告: MO2が起動していない状態で続行します")
            print("  キャッシュファイルが検出できない可能性があります")
            response = input("\n続行しますか? (yes/no): ")
            if response.lower() != 'yes':
                print("✓ 診断を中止しました")
                return False
        
        # テスト1: キャッシュパスの取得
        cache_path = test_get_cache_path(orchestrator)
        
        # テスト2: キャッシュ使用判定
        should_use = test_should_use_cache(orchestrator)
        
        # テスト3: xEdit コマンドライン
        test_cache_command_line(orchestrator)
        
        # テスト4: パフォーマンス推定
        if cache_path and cache_path.exists():
            test_cache_performance_estimate(orchestrator)
        
        # テスト5: キャッシュクリア (オプション)
        print_section("オプション: キャッシュクリア")
        print("キャッシュクリア機能をテストしますか?")
        response = input("テストする場合は 'test' と入力: ")
        
        if response.lower() == 'test':
            test_clear_cache(orchestrator)
        else:
            print("✓ キャッシュクリアテストをスキップしました")
        
        # 最終サマリー
        print_section("診断サマリー")
        print(f"キャッシュディレクトリ: {'✓ 存在' if cache_path else '✗ 不在'}")
        print(f"キャッシュ使用判定: {'✓ 使用する' if should_use else '✗ 使用しない'}")
        
        if should_use:
            print("\n[推奨アクション]")
            print("  ✓ 現在の設定で xEdit 起動が高速化されます")
            print("  ✓ そのまま使用を継続してください")
        else:
            print("\n[推奨アクション]")
            if not cache_path:
                print("  1. xEdit を一度実行してキャッシュを生成してください")
                print("  2. 次回以降は自動的に高速化されます")
            else:
                print("  1. config.ini で use_xedit_cache = True に設定")
                print("  2. キャッシュが古い場合は xEdit を再実行")
        
        print("\n" + "=" * 60)
        print("  診断完了")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[致命的エラー] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)