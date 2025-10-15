"""
候補ディレクトリの診断スクリプト
_candidate_output_dirs() の動作を単体でテストします
"""

import sys
from pathlib import Path
from config_manager import ConfigManager
from Orchestrator import Orchestrator

def main():
    print("=" * 60)
    print("候補ディレクトリ診断ツール")
    print("=" * 60)
    
    try:
        # 設定読み込み
        config = ConfigManager('config.ini')
        orchestrator = Orchestrator(config)
        
        # 候補ディレクトリを取得
        print("\n[診断] _candidate_output_dirs() を呼び出し中...")
        candidates = orchestrator._candidate_output_dirs()
        
        print(f"\n[結果] 候補ディレクトリ数: {len(candidates)}")
        
        if not candidates:
            print("[警告] 候補ディレクトリが1つも見つかりません！")
            print("\n[対策] 以下を確認してください:")
            print("  1. config.ini の [Paths] overwrite_path が正しいか")
            print("  2. config.ini の [Environment] mo2_overwrite_dir が設定されているか")
            print("  3. config.ini の [Paths] xedit_executable のパスが正しいか")
            return False
        
        # 各候補の詳細情報を表示
        print("\n" + "=" * 60)
        for idx, candidate_dir in enumerate(candidates, 1):
            print(f"\n候補 {idx}: {candidate_dir}")
            print(f"  存在: {candidate_dir.exists()}")
            
            if candidate_dir.exists():
                try:
                    # ディレクトリ内のファイルを列挙
                    files = list(candidate_dir.glob('*'))
                    print(f"  ファイル数: {len(files)}")
                    
                    # 期待される成果物を検索
                    expected_files = [
                        'weapon_ammo_map.json',
                        'unique_ammo_for_mapping.ini',
                        'leveled_lists.json',
                        'munitions_ammo_ids.ini'
                    ]
                    
                    found_expected = []
                    for expected in expected_files:
                        if (candidate_dir / expected).is_file():
                            found_expected.append(expected)
                    
                    if found_expected:
                        print(f"  期待ファイル発見: {found_expected}")
                    else:
                        print(f"  期待ファイル: なし")
                    
                    # 全ファイルリスト（先頭10件）
                    print(f"  全ファイル (先頭10件):")
                    for f in files[:10]:
                        file_size = f.stat().st_size if f.is_file() else 0
                        print(f"    - {f.name} ({file_size} bytes)")
                    
                except Exception as e:
                    print(f"  [エラー] ファイル列挙失敗: {e}")
            else:
                print("  [警告] ディレクトリが存在しません")
        
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