"""
GUI構造の確認（モック版）
tkinterなしでGUI構造を検証します
"""

print("=" * 60)
print("GUI構造検証（モック版）")
print("=" * 60)

# 既存フィールド
fields = [
    (0, "MO2実行ファイル:", "Entry", "mo2_executable_var"),
    (1, "プロファイル名:", "Entry", "xedit_profile_var"),
    (2, "実行ファイルリスト名:", "Entry", "mo2_entry_name_var"),
    (3, "Overwriteフォルダ:", "Entry", "mo2_overwrite_dir_var"),
]

print("\n[既存のMO2設定フィールド]")
for row, label, widget_type, var_name in fields:
    print(f"  Row {row}: {label:<30} ({widget_type:<10}) -> {var_name}")

# 新規追加フィールド
new_fields = [
    (4, "ショートカット形式:", "Combobox", "mo2_shortcut_format_var", 
     ["auto", "no_colon", "with_colon", "instance"], "auto"),
    (5, "インスタンス名:", "Entry", "mo2_instance_name_var", None, ""),
]

print("\n[新規追加フィールド] ★★★")
for row, label, widget_type, var_name, values, default in new_fields:
    print(f"  Row {row}: {label:<30} ({widget_type:<10}) -> {var_name}")
    if values:
        print(f"         選択肢: {', '.join(values)}")
    print(f"         デフォルト: '{default}'")

print("\n" + "=" * 60)
print("設定ファイル (config.ini) の項目")
print("=" * 60)

# 既存の設定項目
existing_config = [
    ("Environment", "use_mo2", "MO2使用フラグ"),
    ("Environment", "mo2_executable_path", "MO2実行ファイル"),
    ("Environment", "xedit_profile_name", "プロファイル名"),
    ("Environment", "mo2_xedit_entry_name", "実行ファイルリスト名"),
    ("Environment", "mo2_overwrite_dir", "Overwriteフォルダ"),
]

print("\n[既存の設定]")
for section, option, description in existing_config:
    print(f"  [{section}] {option}")
    print(f"    -> {description}")

# 新規追加の設定項目
new_config = [
    ("Environment", "mo2_shortcut_format", "ショートカット形式", "auto"),
    ("Environment", "mo2_instance_name", "インスタンス名", ""),
]

print("\n[新規追加の設定] ★★★")
for section, option, description, default in new_config:
    print(f"  [{section}] {option}")
    print(f"    -> {description}")
    print(f"    デフォルト: '{default}'")

print("\n" + "=" * 60)
print("load_settings() と save_settings() の変更")
print("=" * 60)

print("\n[load_settings() に追加されたコード]")
print("""
    # 新規追加: moshortcut関連設定の読み込み
    shortcut_format = self.config_manager.get_string('Environment', 'mo2_shortcut_format') or 'auto'
    self.mo2_shortcut_format_var.set(shortcut_format)
    
    instance_name = self.config_manager.get_string('Environment', 'mo2_instance_name') or ''
    self.mo2_instance_name_var.set(instance_name)
""")

print("\n[save_settings() に追加されたコード]")
print("""
    # 新規追加: moshortcut関連設定の保存
    self.config_manager.save_setting('Environment', 'mo2_shortcut_format', self.mo2_shortcut_format_var.get())
    self.config_manager.save_setting('Environment', 'mo2_instance_name', self.mo2_instance_name_var.get())
""")

print("\n" + "=" * 60)
print("ショートカット形式の説明")
print("=" * 60)

formats = [
    ("auto", "自動検出（推奨）", "複数の形式を優先順に試行"),
    ("no_colon", "コロンなし", "moshortcut://xEdit"),
    ("with_colon", "コロンあり", "moshortcut://:xEdit"),
    ("instance", "インスタンス修飾", "moshortcut://Fallout 4/xEdit"),
]

print("\n[選択可能な形式]")
for value, label, uri_example in formats:
    print(f"  {value:<15} - {label:<20} - 例: {uri_example}")

print("\n" + "=" * 60)
print("変更点サマリー")
print("=" * 60)

changes = [
    "✓ AutoPatcherGUI.py に2つの新規フィールドを追加",
    "  - ショートカット形式選択 (Combobox)",
    "  - インスタンス名入力 (Entry)",
    "",
    "✓ load_settings() と save_settings() を更新",
    "  - 新規設定の読み込み/保存処理を追加",
    "",
    "✓ config.ini にデフォルト値を追加",
    "  - mo2_shortcut_format = auto",
    "  - mo2_instance_name = (空)",
]

for change in changes:
    print(f"  {change}")

print("\n" + "=" * 60)
print("✓ GUI構造検証完了")
print("=" * 60)
