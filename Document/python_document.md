# Python スクリプト入出力仕様

このドキュメントは、Munition_AutoPatcher_v1.1 の主要な Python スクリプト群が想定する入力ファイルと生成する出力ファイルを整理したものです。

追記日: 2025-10-14

## 想定入力ファイル（Python 側が読み込む）
- `config.ini` (ルート)
  - プロジェクトルートや `output_dir`、`robco_patcher_dir`、`strategy_file`、`ammo_map_file`、`xedit_output_dir` 等のパスを提供します。
- `setting/strategy.json` (または `strategy.json`)
  - RobCo 生成に必要な `ammo_classification`, `allocation_matrix`, `faction_leveled_lists` 等の戦略データ。
- `setting/ammo_categories.json` (または `ammo_categories.json`)
  - 弾薬のカテゴリ分類情報。
- `ammo_map.json` または `ammo_map.ini` (指定された `ammo_map_file`)
  - 元弾薬 FormID -> Munitions 側 FormID のマッピング。`ammo_map.json` を優先して読み込み、無ければ `ammo_map.ini` の `[UnmappedAmmo]` セクションを使用します。
- `Output/weapon_omod_map.json`（または `xedit_edit_scripts_output/weapon_omod_map.json`）
  - xEdit(Pascal) が出力する武器レコード。OMOD 情報や武器/弾薬の FormID を含む。
- `Output/weapon_ammo_map.json`（補助的）
  - 武器 EditorID と弾薬の相関マップ。いくつかのツールで参考にされます。
- `Output/unique_ammo_for_mapping.ini`
  - xEdit 抽出から得た未マップ弾薬の候補リスト（ユーザーが `ammo_map` を作るための入力）。
- `Output/munitions_ammo_ids.ini`
  - Munitions ESL に定義された弾薬 FormID -> EditorID の一覧。RobCo 生成時に Munitions の EditorID を注釈として利用。
- `Output/WeaponLeveledLists_Export.csv` または `Output/leveled_lists.json`
  - 武器を追加すべき leveled lists の情報。CSV が優先され、JSON がフォールバックとなります。
- `Output/weapon_ammo_details.txt`
  - 武器の完全識別子（プラグイン名|FormID|EditorID 等）。RobCo 生成で leveled list 追加やコメント付与に使用。
- （任意）`Output/munitions_npc_lists.ini`
  - Munitions 弾薬ごとに NPC 用フォームリストを指定するマップ。`MunitionsAmmoFormID=FormListFormID`。

## 想定出力ファイル（Python が生成する）
- `RobCo_Auto_Patcher/F4SE/Plugins/RobCo_Patcher/formlist/Munitions_FormList_RemoveCustomAmmo.ini`
  - カスタム弾薬をフォームリストから除去する指示（formsToRemove 等）。
- `RobCo_Auto_Patcher/F4SE/Plugins/RobCo_Patcher/formlist/Munitions_FormList_AddWeaponsToLL.ini`
  - 武器を特定の leveled lists に追加する指示（formsToAdd）および `setNewAmmoList`（NPC 用フォームリスト指示）。
- `RobCo_Auto_Patcher/F4SE/Plugins/RobCo_Patcher/weapon/Munitions_Weapon_SetAmmo.ini`
  - 個別武器の `setNewAmmo` 指示（filterByWeapons=...:setNewAmmo=...）。
- `RobCo_Auto_Patcher/F4SE/Plugins/RobCo_Patcher/omod/Munitions_OMOD_SetAmmo.ini`
  - OMOD の Ammo プロパティを差し替える指示（filterByOMod=...:changeOModPropertiesForm=Ammo=...）。
- `RobCo_Auto_Patcher.zip` (プロジェクトルート直下)
  - 上記 `RobCo_Auto_Patcher` ディレクトリをアーカイブした ZIP（配布用）。
- ログ・診断出力（標準出力や `patcher.log` に出力されるメッセージ）
  - `robco_ini_generate.py` は診断ログ（読み込んだマッピング数、未解決 LL 警告、OMOD 競合等）を出力します。

## 運用上の注意
- `ammo_map.json` が存在すると `ammo_map.ini` は使用されません。JSON のスキーマ（`mappings[].source.formid` -> `mappings[].target.formid`）に従う必要があります。
- leveled lists は CSV を優先して読み込みます。CSV の列ヘッダは `EditorID,FormID,SourceFile` を想定しています。
- Python 側は `config.ini` のパス定義（特に `output_dir` と `xedit_output_dir`）から入力ファイルを探索します。xEdit の実行先が `xedit_edit_scripts_output/` になる環境では `xedit_output_dir` の指定が必要になる場合があります。

## 補助ツール（tools/ 以下）
- `tools/merge_ammofilled_into_weapon_map.py` — ammofilled の詳細を `weapon_omod_map.json` に安全に統合します（バックアップ作成、検証済み）。
- `tools/diagnose_robco_inputs.py` — weapon/OMOD/ ammo_map のカバレッジを診断し、未マップの件数やサンプルを出力します。
- `tools/check_matching_weapon_records.py` などの検査スクリプト — mapping のマッチング状況を簡易チェックします。

---

(追記: 2025-10-14)

# Pythonスクリプト APIリファレンス

このドキュメントは、Munition_AutoPatcher_v1.1 プロジェクトで使用される主要なPythonスクリプトの構造と、各モジュールの役割を解説します。

---

### 処理の呼び出し階層

ユーザーによるGUI操作は、以下の階層で処理されます。

1.  **`AutoPatcherGUI.py`**: ユーザーが操作するメインウィンドウ。ここから全ての処理が開始されます。
2.  **`Orchestrator.py`**: `AutoPatcherGUI`からの指示を受け、xEditの実行、ファイル収集、`mapper.py`の呼び出し、最終的なINI生成など、一連の処理フローを管理する「司令塔」です。
3.  **`mapper.py`**: `Orchestrator`から呼び出されるGUIツール。ユーザーが手動でMOD弾薬とMunitions弾薬を紐付けます。
4.  **`robco_ini_generate.py`**: `Orchestrator`から呼び出され、`strategy.json`と`mapper.py`で作成された`ammo_map.ini`を元に、RobCo Patcher用の最終的なINIファイルを生成します。

---

### 1. `AutoPatcherGUI.py` (メインGUI)

このスクリプトは、フレームワーク全体の操作を提供するメインアプリケーションです。ユーザーはここから設定を行い、自動処理を開始します。

| クラス/メソッド名 | 役割 |
| :--- | :--- |
| `Application` (クラス) | アプリケーションのメインウィンドウを構築・管理するTkinterフレームです。 |
| `__init__` | GUIを初期化し、`config_manager`と`orchestrator`のインスタンスを受け取ります。 |
| `create_widgets` | ボタン、入力フィールド、ログ表示エリアなど、全てのUIコンポーネントを配置します。 |
| `load_settings` / `save_settings` | `config.ini`から設定を読み込み、UIに反映させます。また、UIでの変更を`config.ini`に保存します。 |
| `start_full_process` | 「全自動処理を開始」ボタンが押されたときに呼び出され、`Orchestrator`のメイン処理を別スレッドで実行します。 |
| `start_strategy_generation` | 「戦略ファイルを生成」ボタンに対応し、`Orchestrator`の戦略ファイル更新処理を呼び出します。 |
| `run_process_wrapper` | バックグラウンド処理（`Orchestrator`のメソッド）を安全に実行し、UIの無効化/有効化、ログの更新、完了メッセージの表示などを行います。 |

---

### 2. `Orchestrator.py` (処理統括)

GUIからの指示に基づき、データ抽出から最終的なパッチ生成までの一連の複雑なタスクを調整・実行するバックエンドのコアコンポーネントです。

| クラス/メソッド名 | 役割 | 戻り値 |
| :--- | :--- | :--- |
| `Orchestrator` (クラス) | 全ての自動化処理を管理するメインクラスです。 | - |
| `run_full_process` | 全自動処理のメインエントリーポイント。xEdit実行、戦略更新、マッパー起動、INI生成を順番に呼び出します。 | `bool` (True: 成功, False: 失敗) |
| `run_xedit_script` | xEditスクリプトを実行します。MO2連携、一時スクリプトの管理、ログからの成功判定、タイムアウト処理など、複雑な実行ロジックを内包しています。 | `bool` (True: 成功, False: 失敗) |
| `_move_results_from_overwrite` | xEditの実行結果（`weapon_omod_map.json`など）を、MO2のOverwriteフォルダなど複数の候補から探索し、プロジェクトの`Output`ディレクトリに収集します。 | `bool` (True: 成功, False: 失敗) |
| `run_strategy_generation` | `munitions_ammo_ids.ini`と`ammo_categories.json`を元に、`strategy.json`内の`ammo_classification`（弾薬分類）を自動更新します。 | `bool` (True: 成功, False: 失敗) |
| `_generate_robco_ini` | `robco_ini_generate.py`の`run`関数を呼び出し、最終的なRobCo Patcher用INIファイルの生成をトリガーします。 | `bool` (True: 成功, False: 失敗) |

---

### 3. `mapper.py` (弾薬マッピングツール)

MODによって追加されたカスタム弾薬を、どのMunitions弾薬に置き換えるかをユーザーが視覚的に設定するためのGUIツールです。

| クラス/メソッド名 | 役割 |
| :--- | :--- |
| `AmmoMapperApp` (クラス) | 弾薬マッピングを行うためのTkinterアプリケーションです。 |
| `load_data` | 以下のファイルを読み込み、マッピングの準備をします。<br>- `unique_ammo_for_mapping.ini`: 変換元となるカスタム弾薬のリスト。<br>- `munitions_ammo_ids.ini`: 変換先候補となるMunitions弾薬のリスト。<br>- `weapon_omod_map.json`: 武器に紐付くOMOD情報を取得し、UIに表示するために使用。 |
| `build_ui_rows` | `load_data`で読み込んだ情報に基づき、各カスタム弾薬に対してチェックボックスとMunitions弾薬を選択するドロップダウンリストを動的に生成します。 |
| `save_ini_file` | ユーザーが設定したマッピング情報を元に、RobCo Patcherが解釈可能なINIファイル (`robco_ammo_patch.ini`) を生成します。このファイルには、武器の弾薬を直接置き換える `filterByWeapons` ルールと、武器MOD（OMOD）の弾薬を変更する `filterByOMod` ルールの両方が含まれます。 |

---

### 4. `robco_ini_generate.py` (RobCo INI 生成)

`Orchestrator`から呼び出され、`strategy.json`、`ammo_map.ini`、およびxEditが出力した各種中間ファイル（`weapon_omod_map.json`など）を元に、RobCo Patcher用の配布可能なパッチファイルを一括生成します。

| 関数名 | 役割 |
| :--- | :--- |
| `run(config)` | モジュールのメイン関数。設定を読み込み、複数のINIファイルの生成とZIPアーカイブ化を実行します。 |
| `_read_weapon_records` | `weapon_omod_map.json`を読み込み、処理対象となる全ての武器のレコード（プラグイン名、FormID、OMOD情報など）を取得します。 |
| `_load_ammo_map` | `mapper.py`によって生成された`ammo_map.ini`（または`ammo_map.json`）から、弾薬の変換ルールを読み込みます。 |
| `_load_ll_from_csv` / `_load_ll_from_json` | `WeaponLeveledLists_Export.csv`や`leveled_lists.json`から、どのLeveled Listに武器を追加すべきかの情報を読み込みます。 |

#### 生成されるファイル

このスクリプトは、最終的に以下のファイルを`RobCo_Auto_Patcher`ディレクトリ内に生成し、それをZIP圧縮します。

| ファイルパス | 内容 |
| :--- | :--- |
| `formlist/Munitions_FormList_RemoveCustomAmmo.ini` | `mapper.py`でマッピングされた元のカスタム弾薬を、ゲーム内の全てのLeveled Listから削除するための指示を記述します。 |
| `weapon/Munitions_Weapon_SetAmmo.ini` | 各武器レコードに対し、使用弾薬を対応するMunitions弾薬に置き換える (`setNewAmmo`) 指示を記述します。 |
| `omod/Munitions_OMOD_SetAmmo.ini` | 武器MOD（OMOD）が独自の弾薬設定を持っている場合に、それをMunitions弾薬に変更するための指示を記述します。 |
| `formlist/Munitions_FormList_AddWeaponsToLL.ini` | パッチが適用された武器を、`strategy.json`で定義された勢力（Gunners, Raidersなど）のLeveled Listに追加するための指示を記述します。 |
| `RobCo_Auto_Patcher.zip` | 上記のファイル群を含む`RobCo_Auto_Patcher`ディレクトリ全体を圧縮した、配布用のZIPアーカイブです。 |
---

### 5. `config_manager.py` (設定管理)

このモジュールは、`config.ini` ファイルの読み込み、解析、アクセスを中央集権的に管理するクラスを提供します。パスの解決、型変換、デフォルト値の提供といった機能を通じて、アプリケーション全体で設定情報へ安全かつ一貫した方法でアクセスできるようにします。

| クラス/メソッド名 | 役割 |
| :--- | :--- |
| `ConfigManager` (クラス) | `config.ini` ファイルを操作するためのメインクラスです。 |
| `__init__(config_path)` | コンストラクタ。指定された `config.ini` のパスを読み込み、内部の `configparser` オブジェクトを初期化します。プロジェクトのルートディレクトリもこの段階で解決されます。 |
| `get_path(section, key)` | 設定ファイルからパスを取得し、絶対パスの `Path` オブジェクトとして返します。`project_root` を基準に相対パスを解決します。 |
| `get_string(section, key, fallback)` | 設定ファイルから文字列を安全に取得します。値が存在しない場合は指定された `fallback` 値を返します。 |
| `get_boolean(section, key, fallback)` | 設定ファイルから真偽値 (`True`/`False`) を取得します。 |
| `get_script_filename(key)` | `[Scripts]` セクションから特定のスクリプトファイル名を取得します。 |
| `get_env_settings()` | `[Environment]` セクション（MO2連携など）の設定を辞書としてまとめて取得します。 |
| `get_parameter(key)` | `[Parameters]` セクションから汎用的なパラメータを取得します。 |
| `save_setting(section, key, value)` | GUIなどから受け取った設定値を `config.ini` ファイルに書き込み、永続化します。 |
