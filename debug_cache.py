"""
xEdit キャッシュ機能の診断・テストスクリプト
キャッシュ関連の全機能を単体でテストします
"""

import sys
import time
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

def test_get_cache_path(orchestrator):
    """_get_cache_path() のテスト"""
    print_section("1. キャッシュパスの取得テスト")
    
    try:
        cache_path = orchestrator._get_cache_path()
        
        if cache_path:
            print(f"✓ キャッシュディレクトリ: {cache_path}")
            print(f"  存在: {cache_path.exists()}")
            
            if cache_path.exists():
                # ディレクトリ内容を表示
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
        else:
            print("✗ キャッシュディレクトリが見つかりません")
            print("\n[原因の可能性]")
            print("  1. xEdit 実行ファイルのパスが正しく設定されていない")
            print("  2. FO4Edit Cache フォルダが存在しない (初回実行)")
        
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