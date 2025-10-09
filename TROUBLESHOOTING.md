# MO2/xEdit トラブルシューティングガイド

## 目次
1. [moshortcut URI 形式について](#moshortcut-uri-形式について)
2. [環境別の設定推奨値](#環境別の設定推奨値)
3. [よくある問題と対処法](#よくある問題と対処法)
4. [診断ツールの使用方法](#診断ツールの使用方法)

---

## moshortcut URI 形式について

Mod Organizer 2 (MO2) を介してxEditを起動する際、環境によって有効なmoshortcut URI形式が異なることが確認されています。

### 対応する形式

1. **コロンなし形式** (`moshortcut://xEdit`)
   - 多くの環境で動作する基本形式
   
2. **コロンあり形式** (`moshortcut://:xEdit`)
   - 一部の環境で必要とされる形式
   
3. **インスタンス修飾形式** (`moshortcut://Fallout 4/xEdit`)
   - 複数のゲームインスタンスを管理している場合に必要

### 自動検出機能

本ツールは `mo2_shortcut_format = auto` に設定することで、上記の形式を優先順に自動試行します。
初回使用時は `auto` のまま実行し、問題が発生した場合のみ手動設定を検討してください。

---

## 環境別の設定推奨値

### 標準的な環境（ポータブル版MO2）

```ini
[Environment]
use_mo2 = True
mo2_executable_path = C:/Games/MO2/ModOrganizer.exe
xedit_profile_name = Default
mo2_xedit_entry_name = xEdit
mo2_shortcut_format = auto
mo2_instance_name = 
```

### 複数ゲームインスタンス環境

```ini
[Environment]
use_mo2 = True
mo2_executable_path = C:/Modding/ModOrganizer.exe
xedit_profile_name = MyProfile
mo2_xedit_entry_name = xEdit
mo2_shortcut_format = instance
mo2_instance_name = Fallout 4
```

### コロンあり形式が必要な環境

```ini
[Environment]
use_mo2 = True
mo2_executable_path = E:/MO2/ModOrganizer.exe
xedit_profile_name = Main
mo2_xedit_entry_name = xEdit
mo2_shortcut_format = with_colon
mo2_instance_name = 
```

---

## よくある問題と対処法

### 問題1: "Cannot start -n" エラー

**症状:**
MO2起動時に「Cannot start -n」というエラーが表示される

**原因:**
xEditに `-n` オプション（またはその他の不明なオプション）が誤って渡されている

**対処法:**
1. config.ini の設定を確認
2. 不要な引数が追加されていないか確認
3. 本ツールを最新版に更新（引用符問題が修正されています）

### 問題2: xEditが起動しない（タイムアウト）

**症状:**
「xEdit起動検出タイムアウト」エラーが発生

**原因:**
- moshortcut URI形式が環境に合っていない
- MO2の実行ファイルリストに登録されていない
- プロファイル名が間違っている

**対処法:**
1. 診断スクリプトを実行: `python debug_mo2_shortcut.py`
2. MO2を手動で起動し、「実行」メニューを確認
3. `mo2_xedit_entry_name` の値が実行ファイルリストと一致するか確認

### 問題3: RivaTuner / RTSS 干渉

**症状:**
- MO2またはxEditの起動が不安定
- オーバーレイ表示時にクラッシュ

**原因:**
RivaTuner Statistics Server (RTSS) やその他のオーバーレイソフトウェアが干渉

**対処法:**
1. RTSSを一時的に無効化
   - RTSSのシステムトレイアイコンを右クリック
   - 「Show On-Screen Display」のチェックを外す
   
2. RTSSの除外リストに追加
   - RTSS設定画面を開く
   - 「Profiles」タブで `ModOrganizer.exe` と `xEdit.exe` を追加
   - Application detection level を「None」に設定

3. 他のオーバーレイソフトの無効化
   - Discord オーバーレイ
   - GeForce Experience オーバーレイ
   - Steam オーバーレイ（ゲーム外ツールの場合は通常問題なし）

### 問題4: 引用符のエスケープ問題

**症状:**
xEditのログに `\"-S:...\"` のような形式で引数が記録されている

**原因:**
旧バージョンでは引数に不要な引用符が含まれていた

**対処法:**
本ツールを最新版に更新してください。修正済みです。

### 問題5: 成果物が見つからない

**症状:**
「必須ファイル欠落」エラーが発生

**原因:**
- MO2のOverwriteフォルダ設定が間違っている
- xEditスクリプトが正常に完了していない
- 管理者権限の不足

**対処法:**
1. `mo2_overwrite_dir` が正しく設定されているか確認
2. xEditのログファイルを確認（Output フォルダ内）
3. アプリケーションを管理者権限で実行

---

## 診断ツールの使用方法

### debug_mo2_shortcut.py

このスクリプトは、環境に最適なmoshortcut URI形式を自動検出します。

#### 使用方法

1. **前提条件**
   - config.ini の基本設定（MO2パス、プロファイル名など）が完了していること
   - MO2が閉じていること

2. **実行**
   ```powershell
   python debug_mo2_shortcut.py
   ```

3. **結果の確認**
   - スクリプトは各URI形式を順次テストします
   - xEditが正常に起動する形式を検出すると「✓ 成功」と表示されます
   - 推奨設定が自動的に表示されます

4. **設定の適用**
   - スクリプトが推奨する `mo2_shortcut_format` 値を config.ini に追加
   - または GUI の「ショートカット形式」ドロップダウンから選択

#### 出力例

```
[テスト結果サマリー]
============================================================
  ✓ 成功: コロンなし形式
    URI: moshortcut://xEdit
  ✗ 失敗: コロンあり形式
    URI: moshortcut://:xEdit

============================================================
[結論] 1/2 形式が動作しました

推奨設定:
  config.ini に以下を設定:
    mo2_shortcut_format = no_colon
============================================================
```

### debug_config_paths.py

パス設定の妥当性を確認します。

```powershell
python debug_config_paths.py
```

### debug_candidate_dirs.py

成果物の探索ディレクトリを診断します。

```powershell
python debug_candidate_dirs.py
```

---

## GUI設定項目の説明

### ショートカット形式

| 値 | 説明 | 使用するURI形式 |
|---|---|---|
| auto | 自動検出（推奨） | 複数の形式を優先順に試行 |
| no_colon | コロンなし | `moshortcut://xEdit` |
| with_colon | コロンあり | `moshortcut://:xEdit` |
| instance | インスタンス修飾 | `moshortcut://Fallout 4/xEdit` |

### インスタンス名

複数のゲームインスタンスを管理している場合に設定します。
例: `Fallout 4`, `Skyrim Special Edition`

通常は空欄のままで問題ありません。

---

## 追加のトラブルシューティング手順

### 手動でのmoshortcut テスト（PowerShell）

1. PowerShellを管理者権限で起動

2. 以下のコマンドを実行してテスト:

```powershell
# コロンなし形式
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "new2", "moshortcut://xEdit"

# コロンあり形式
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "new2", "moshortcut://:xEdit"

# インスタンス修飾形式
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "new2", "moshortcut://Fallout 4/xEdit"
```

※ パスとプロファイル名は環境に合わせて変更してください

3. 各コマンド実行後、xEditが正常に起動するか確認

### ログの確認方法

1. **xEditセッションログ**
   - 場所: `Output/xEdit_session_<timestamp>.log`
   - 確認内容: エラーメッセージ、スクリプト実行状況

2. **アプリケーションログ**
   - 場所: `patcher.log`
   - 確認内容: MO2起動コマンド、プロセス検出状況

3. **MO2ログ**
   - 場所: MO2インストールフォルダ内の `mo2.log`
   - 確認内容: MO2側のエラー情報

---

## サポート情報

問題が解決しない場合は、以下の情報を含めて報告してください：

1. config.ini の [Environment] セクション内容
2. patcher.log の関連部分（エラー前後の50行程度）
3. debug_mo2_shortcut.py の実行結果
4. 使用している MO2 のバージョン
5. 使用している xEdit のバージョン

---

**更新日:** 2025-01-09  
**バージョン:** v2.6
