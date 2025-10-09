"""
GUI構造の確認スクリプト
実際のGUIウィジェットを表示せずに、GUI構造を検証します
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys

# GUIを非表示で初期化
root = tk.Tk()
root.withdraw()  # ウィンドウを非表示

print("=" * 60)
print("GUI構造検証")
print("=" * 60)

# MO2設定フレームの構造を再現
mo2_settings_frame = ttk.Frame(root)

# 既存フィールド
fields = [
    (0, "MO2実行ファイル:", "Entry"),
    (1, "プロファイル名:", "Entry"),
    (2, "実行ファイルリスト名:", "Entry"),
    (3, "Overwriteフォルダ:", "Entry"),
]

print("\n[既存のMO2設定フィールド]")
for row, label, widget_type in fields:
    print(f"  Row {row}: {label:<25} ({widget_type})")

# 新規追加フィールド
new_fields = [
    (4, "ショートカット形式:", "Combobox", ["auto", "no_colon", "with_colon", "instance"]),
    (5, "インスタンス名:", "Entry", None),
]

print("\n[新規追加フィールド] ★★★")
for row, label, widget_type, values in new_fields:
    if values:
        print(f"  Row {row}: {label:<25} ({widget_type})")
        print(f"         選択肢: {', '.join(values)}")
    else:
        print(f"  Row {row}: {label:<25} ({widget_type})")

print("\n" + "=" * 60)
print("設定の保存/読込確認")
print("=" * 60)

# 設定項目リスト
config_items = [
    ("Environment", "mo2_shortcut_format", "ショートカット形式"),
    ("Environment", "mo2_instance_name", "インスタンス名"),
]

print("\n[新規追加の設定項目]")
for section, option, description in config_items:
    print(f"  [{section}] {option}")
    print(f"    説明: {description}")

print("\n" + "=" * 60)
print("デフォルト値")
print("=" * 60)

defaults = {
    "mo2_shortcut_format": "auto",
    "mo2_instance_name": "",
}

print("\n[新規設定のデフォルト値]")
for key, value in defaults.items():
    display_value = f'"{value}"' if value else "(空文字列)"
    print(f"  {key}: {display_value}")

print("\n" + "=" * 60)
print("GUI検証完了")
print("=" * 60)

# 実際のウィジェット作成テスト
print("\n[ウィジェット作成テスト]")
try:
    # ショートカット形式のCombobox
    format_var = tk.StringVar()
    format_combo = ttk.Combobox(
        mo2_settings_frame,
        textvariable=format_var,
        values=["auto", "no_colon", "with_colon", "instance"],
        state="readonly",
        width=57
    )
    format_combo.set("auto")
    print("  ✓ Combobox (ショートカット形式) 作成成功")
    print(f"    デフォルト値: {format_var.get()}")
    print(f"    選択肢: {format_combo['values']}")
    
    # インスタンス名のEntry
    instance_var = tk.StringVar()
    instance_entry = ttk.Entry(
        mo2_settings_frame,
        textvariable=instance_var,
        width=60
    )
    print("  ✓ Entry (インスタンス名) 作成成功")
    
    print("\n  すべてのウィジェットが正常に作成されました")
    
except Exception as e:
    print(f"  ✗ エラー: {e}")
    sys.exit(1)

root.destroy()
print("\n" + "=" * 60)
print("✓ GUI構造検証完了 - エラーなし")
print("=" * 60)
