"""
test_json_cleanup.py
SaveAndCleanJSONToFile の動作を確認するスクリプト
"""

import json
from pathlib import Path

def test_json_files():
    """生成されたJSONファイルの妥当性をチェック"""
    
    output_dir = Path('Output')
    json_files = [
        'weapon_ammo_map.json',
        'leveled_lists.json',
        'strategy.json'
    ]
    
    print("=" * 60)
    print("  JSON ファイルのクリーンアップ検証")
    print("=" * 60)
    
    for filename in json_files:
        file_path = output_dir / filename
        
        print(f"\n[検証] {filename}")
        print(f"  パス: {file_path}")
        
        if not file_path.exists():
            print("  ✗ ファイルが存在しません")
            continue
        
        # ファイルサイズ
        size_kb = file_path.stat().st_size / 1024
        print(f"  サイズ: {size_kb:.2f} KB")
        
        # UTF-8エンコーディングで読み込み
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 二重エスケープのチェック
            double_escaped = content.count('""')
            if double_escaped > 0:
                print(f"  ⚠ 二重エスケープ検出: {double_escaped}箇所")
            else:
                print("  ✓ 二重エスケープなし")
            
            # JSON構文のチェック
            try:
                data = json.loads(content)
                print(f"  ✓ JSON構文: 正常")
                
                # データ構造の簡易チェック
                if isinstance(data, list):
                    print(f"  データ型: 配列 (要素数: {len(data)})")
                elif isinstance(data, dict):
                    print(f"  データ型: オブジェクト (キー数: {len(data)})")
                
                # weapon_ammo_map.json の特別チェック
                if filename == 'weapon_ammo_map.json' and isinstance(data, list):
                    if len(data) > 0:
                        sample = data[0]
                        full_name = sample.get('full_name', '')
                        print(f"  サンプル full_name: {full_name}")
                        
                        # 日本語が含まれているかチェック
                        has_japanese = any(ord(c) > 0x3000 for c in full_name)
                        if has_japanese:
                            print("  ✓ 日本語文字列を検出（エンコーディング正常）")
                        else:
                            print("  ✓ ASCII文字列")
                
            except json.JSONDecodeError as e:
                print(f"  ✗ JSON構文エラー: {e}")
                print(f"    行: {e.lineno}, 列: {e.colno}")
                
        except Exception as e:
            print(f"  ✗ ファイル読み込みエラー: {e}")
    
    print("\n" + "=" * 60)
    print("  検証完了")
    print("=" * 60)

if __name__ == "__main__":
    test_json_files()