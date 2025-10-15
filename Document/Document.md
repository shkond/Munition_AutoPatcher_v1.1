# Munition AutoPatcher v1.1 詳細処理フロー

更新日: 2025-10-14

このドキュメントは、Munition AutoPatcher フレームワークの内部的な処理の流れを詳細に解説します。GUIの操作から始まり、最終的なパッチファイルが生成されるまでの一連のステップを追跡します。

---

## 全体像

このフレームワークは、ユーザーが持つ様々な武器MODの弾薬設定を、標準化された弾薬フレームワーク「Munitions」のものに自動で置き換えるためのRobCo Patcher設定ファイルを生成することを目的としています。

処理は大きく分けて以下のフェーズで構成されます。

1.  **データ抽出フェーズ**: `xEdit` を利用して、ユーザーの現在のロードオーダーから武器や弾薬に関する情報を抽出します。
2.  **データ処理・マッピングフェーズ**: 抽出した情報を元に、どの弾薬をどのMunitions弾薬に置き換えるかの対応付け（マッピング）を行います。
3.  **最終生成フェーズ**: マッピング情報と定義済みの「戦略」に基づき、RobCo Patcherが解釈できる`.ini`ファイルを生成します。

以下に、GUIで「全自動処理を開始」ボタンが押されてからの詳細な処理フローを記述します。

---

## 詳細処理フロー

処理の司令塔となるのは `Orchestrator.py` です。GUI (`AutoPatcherGUI.py`) からの指示を受け、以下のステップを順番に実行します。

### ステップ 1: xEditによるデータ抽出

1.  **xEditの起動準備**:
    *   `Orchestrator.py` は `config.ini` の設定に基づき、`xEdit` の実行環境を準備します。
    *   `pas_scripts/` ディレクトリにある `00_RunAllExtractors.pas` スクリプトを、`xEdit` の `Edit Scripts/` フォルダに一時的な名前でコピーします。これにより、ユーザー環境の `xEdit` からスクリプトを実行できます。
    *   同時に、スクリプトが必要とするライブラリ (`pas_scripts/lib/*.pas`) も `Edit Scripts/lib/` にコピーされます。

2.  **xEditの実行**:
    *   `Orchestrator.py` は `subprocess` モジュールを使い、`xEdit` をコマンドラインから起動します。
    *   `config.ini` で `use_mo2 = True` が設定されている場合、`ModOrganizer.exe` 経由で `moshortcut` を利用し、指定されたプロファイルで `xEdit` を起動します。これにより、MO2の仮想ファイルシステム下で正確なロードオーダーを反映したデータ抽出が可能になります。
    *   起動された `xEdit` は、一時コピーされた `00_RunAllExtractors.pas` を実行します。このスクリプトは、さらに他の複数のPascalスクリプトを呼び出し、以下の情報を抽出・ファイルに出力します。

3.  **生成される主要なファイル**:
    *   `weapon_omod_map.json`: ゲーム内の武器レコード（WEAP）と、それに紐付く武器改造（OMOD）の情報をまとめたもの。武器の元の弾薬情報も含まれます。
    *   `unique_ammo_for_mapping.ini`: 抽出された武器が使用している弾薬のうち、Munitions管理外の「未知の弾薬」をリストアップしたもの。後のマッピング工程で使用されます。
    *   `munitions_ammo_ids.ini`: Munitions.eslに含まれる全弾薬のFormIDとEditorIDの対応リスト。
    *   `WeaponLeveledLists_Export.csv`: 武器が配布される可能性のあるLeveled List（敵のドロップリストなど）の情報をまとめたもの。
    *   `weapon_ammo_map.json`: 武器と弾薬の関連性を記録した補助的なファイル。

4.  **成果物の収集**:
    *   `xEdit` が出力した上記ファイル群は、通常、MO2の `Overwrite` フォルダ内か、`xEdit` の `Edit Scripts/Output/` フォルダに生成されます。
    *   `Orchestrator.py` はこれらの候補ディレクトリを自動で探索し、生成されたファイル群をプロジェクト内の `Output/` ディレクトリにコピー・集約します。これにより、後続の処理がファイルを見つけやすくなります。

### ステップ 2: 戦略ファイル (`strategy.json`) の動的更新

1.  **弾薬の分類**:
    *   `Orchestrator.py` の `run_strategy_generation` 関数が呼び出されます。
    *   この関数は、ステップ1で生成された `munitions_ammo_ids.ini`（Munitionsの全弾薬リスト）と、手動で定義された分類ルール `ammo_categories.json` を読み込みます。
    *   `ammo_categories.json` には、「EditorIDに `10mm` が含まれていたらカテゴリは `Pistol`」のようなルールが記述されています。
    *   このルールに基づき、全Munitions弾薬をカテゴリ（`Pistol`, `Rifle`など）と威力（`Low`, `Medium`, `High`など）に自動で分類します。

2.  **`strategy.json`への反映**:
    *   分類結果は、`strategy.json` ファイル内の `ammo_classification` セクションに書き込まれます。
    *   `strategy.json` は、最終的なパッチ生成の際に「どの武器をどの勢力（レイダー、ガンナーなど）のLeveled Listに追加するか」や、「どのカテゴリの武器を優先的に配布するか」といった大局的な方針を定義するファイルです。この動的更新により、Munitions.eslが更新された場合でも柔軟に対応できます。

### ステップ 3: 手動マッピング (`mapper.py`)

1.  **マッピングツールの起動**:
    *   `Orchestrator.py` は、Pythonで書かれたGUIツール `mapper.py` を別プロセスとして起動します。
    *   このツールは、ステップ1で生成された `unique_ammo_for_mapping.ini`（未知の弾薬リスト）と `munitions_ammo_ids.ini`（Munitions弾薬リスト）を読み込みます。

2.  **ユーザーによるマッピング作業**:
    *   `mapper.py` の画面には、左側に「未知の弾薬」、右側にMunitions弾薬のドロップダウンリストが表示されます。
    *   ユーザーは、各MOD弾薬に対して、どのMunitions弾薬に置き換えるべきかを選択します。例えば、「.308 Pistol Ammo」を「.308 Munitions Ammo」に紐付けます。

3.  **マッピング結果の保存**:
    *   ユーザーが保存ボタンを押すと、マッピング結果が `config.ini` で指定された `ammo_map_file`（通常は `ammo_map.ini` または `ammo_map.json`）に保存されます。
    *   このファイルには、`[元の弾薬FormID] = [置き換え先のMunitions弾薬FormID]` という形式で対応関係が記録されます。

### ステップ 4: RobCo Patcher INIファイルの最終生成

1.  **生成スクリプトの実行**:
    *   `Orchestrator.py` は、最終生成ロジックを担当する `robco_ini_generate.py` を呼び出します。

2.  **入力データの統合**:
    *   `robco_ini_generate.py` は、これまでのステップで生成・収集された以下の情報をすべて読み込みます。
        *   `weapon_omod_map.json`（武器とOMODの情報）
        *   `ammo_map.ini` / `.json`（手動マッピングの結果）
        *   `strategy.json`（配布戦略と弾薬分類）
        *   `WeaponLeveledLists_Export.csv`（Leveled Listの情報）

3.  **INIファイルの生成**:
    *   これらの情報を元に、RobCo Patcherの各機能に対応した`.ini`ファイルを `RobCo_Auto_Patcher/` ディレクトリ以下に生成します。
    *   **`weapon/Munitions_Weapon_SetAmmo.ini`**: 個別の武器の弾薬を `setNewAmmo` を使って置き換えます。
    *   **`omod/Munitions_OMOD_SetAmmo.ini`**: 武器MOD（OMOD）が持つ弾薬情報を `changeOModPropertiesForm` を使って置き換えます。
    *   **`formlist/Munitions_FormList_AddWeaponsToLL.ini`**: パッチが適用された武器を、`strategy.json` の定義に基づき、ガンナーやレイダーなどのLeveled Listに追加します。
    *   **`formlist/Munitions_FormList_RemoveCustomAmmo.ini`**: 元のMOD弾薬をLeveled Listから削除し、流通しないようにします。

### ステップ 5: 配布物の作成

1.  **ZIPアーカイブの生成**:
    *   `robco_ini_generate.py` は、最後に `RobCo_Auto_Patcher/` ディレクトリ全体を `RobCo_Auto_Patcher.zip` という名前のZIPファイルに圧縮します。
    *   このZIPファイルをMO2などのMOD管理ツールでインストールすることで、生成されたパッチがゲームに適用されます。

---

## 処理フロー図

```
[ユーザー]
    |
    v
[AutoPatcherGUI.py] --(処理開始)--> [Orchestrator.py]
    |                                      |
    |                                      v
    |                  (1. xEdit実行) ----> [xEdit.exe] + [*.pasスクリプト]
    |                                      |
    |                                      v
    |                  (成果物収集) <---- [Overwriteフォルダ]
    |                      |
    |                      v
    |                  (2. 戦略更新) ----> [strategy.json]
    |                      |
    |                      v
    |                  (3. マッパー起動) -> [mapper.py] --(ユーザー操作)--> [ammo_map.ini]
    |                      |
    |                      v
    |                  (4. INI生成) ----> [robco_ini_generate.py]
    |                                      |
    |                                      v
    |                  (5. ZIP圧縮) -----> [RobCo_Auto_Patcher.zip]
    |                                      |
    v                                      |
[ログ表示/完了通知] <--------------------------+

```
---

## `Orchestrator.py` 関数詳細

`Orchestrator` クラスは、自動化プロセス全体を管理する心臓部です。以下に、主要な関数の役割と処理の流れを詳述します。

### `__init__(self, config_manager)`
- **役割**: `Orchestrator` クラスのインスタンスを初期化します。
- **処理**:
    1. `config_manager` のインスタンスを内部に保持し、後続の処理で設定情報（`config.ini`の内容）にアクセスできるようにします。
    2. アプリケーションが管理者権限で実行されているかを確認し、されていない場合は警告ログを出力します。

### `run_full_process(self) -> bool`
- **役割**: 全自動処理のメインエントリーポイント。データ抽出から最終的なINI生成までの一連のプロセスを順番に実行します。
- **処理**:
    1. **ステップ1: データ抽出**: `run_xedit_script` を呼び出し、xEditによるデータ抽出プロセスを開始します。成功しなかった場合は、`False`を返して処理を中断します。
    2. **ステップ2: 戦略ファイル更新**: `run_strategy_generation` を呼び出し、`strategy.json` を最新の状態に更新します。
    3. **ステップ3: 弾薬マッピング**: `mapper.py` を外部プロセスとして起動します。ユーザーがマッピングを完了し、ツールを正常に終了するまで待機します。
    4. **ステップ4: 最終INI生成**: `_generate_robco_ini`（実体は `robco_ini_generate.run`）を呼び出し、最終的なRobCo Patcher用INIファイルの生成とZIP化を行います。
    5. 全てのステップが成功した場合、`True` を返します。

### `run_xedit_script(self, script_key: str, success_message: str, expected_outputs: list) -> bool`
- **役割**: 指定されたPascalスクリプトをxEdit経由で安全に実行し、成果物を収集する、本フレームワークで最も複雑かつ重要な関数です。
- **処理**:
    1. **事前準備**:
        - `config.ini` からxEditのパス、スクリプトのパス、MO2の設定などを読み込みます。
        - 実行対象のPascalスクリプト (`.pas`) を、xEditの `Edit Scripts` フォルダに一時的な名前（例: `TEMP_163... .pas`）でコピーします。
        - スクリプトが依存するライブラリ群 (`pas_scripts/lib/`) も同様に `Edit Scripts/lib/` へコピーします（既存のlibはバックアップ・リストアされます）。
    2. **コマンド構築**:
        - **MO2を使用する場合**: `_build_mo2_command` ヘルパー関数を使い、`moshortcut` URIスキームを利用したコマンドラインを構築します。これにより、MO2の仮想ファイルシステム（VFS）経由でxEditを起動できます。
        - **MO2を使用しない場合**: xEdit実行ファイルへのパスと、スクリプト実行に必要な引数（`-script:`など）を含む直接的なコマンドラインを構築します。
    3. **プロセス実行と監視**:
        - 構築したコマンドで `subprocess.Popen` または `subprocess.run` を使ってxEditを起動します。
        - MO2経由の場合は、`psutil` を使ってxEditのプロセスが実際に起動したことを検出し、そのプロセスが終了するまで待機します。タイムアウトも設定されています。
    4. **成功判定**:
        - xEditプロセスの終了コードが `0` であることを確認します。
        - xEditが生成するログファイル（`xEdit_session_... .log` または `xEdit_debug_... .txt`）をポーリングし、引数で指定された `success_message`（例: `All extractions complete.`）が含まれているかを確認します。
    5. **成果物収集**:
        - `expected_outputs` で指定されたファイルリスト（`weapon_omod_map.json`など）が、`_candidate_output_dirs` で特定された候補ディレクトリ（MO2のOverwriteフォルダなど）内に存在するかを確認します。
        - 1つ以上のファイルが見つかった場合、`_move_results_from_overwrite` を呼び出して、それらのファイルをプロジェクトの `Output/` ディレクトリに集約します。
    6. **クリーンアップ**:
        - 処理終了後、`Edit Scripts` フォルダにコピーした一時スクリプトを削除し、ライブラリのバックアップを元に戻します。

### `_move_results_from_overwrite(self, expected_filenames: list) -> bool`
- **役割**: xEditの実行結果として生成されたファイルを、複数の可能性のある場所から探し出し、プロジェクトの `Output` ディレクトリに安全にコピーします。
- **処理**:
    1. `_candidate_output_dirs` を呼び出して、成果物が存在する可能性のあるディレクトリのリスト（優先順位付き）を取得します。
    2. `expected_filenames` で指定された各ファイルについて、候補ディレクトリを探索します。
    3. 同じファイルが複数見つかった場合は、ファイルの更新時刻が最も新しいものをソースとして選択します。
    4. ファイルをまず `.part` という拡張子で `Output` ディレクトリにコピーし、コピーが成功したことを確認してから、アトミックな `replace` 操作でリネームします。これにより、コピー中の不完全なファイルを後続処理が読み込むのを防ぎます。
    5. 期待されるファイルが1つでも見つからなかった場合、エラーログを出力して `False` を返します。

### `run_strategy_generation(self) -> bool`
- **役割**: `munitions_ammo_ids.ini` と `ammo_categories.json` を基に、`strategy.json` の `ammo_classification` セクションを自動生成・更新します。
- **処理**:
    1. 必要な入力ファイル（`munitions_ammo_ids.ini`, `ammo_categories.json`, `strategy.json`）の存在を確認します。
    2. `ammo_categories.json` から分類ルール（キーワード、カテゴリ、威力）を読み込みます。
    3. `munitions_ammo_ids.ini` を解析し、Munitionsの全弾薬リストを取得します。
    4. 各Munitions弾薬のEditorIDを分類ルールのキーワードと照合し、一致したルールのカテゴリと威力を割り当てます。
    5. 割り当て結果を `strategy.json` に書き込み、ファイルを更新します。

### `_generate_robco_ini(self) -> bool`
- **役割**: 最終的なRobCo Patcher用INIファイルの生成プロセスをキックします。
- **処理**:
    - この関数の実体は、`robco_ini_generate.py` ファイルからインポートされた `run` 関数です。
    - `config_manager` のインスタンスを `robco_ini_generate.run` 関数に渡して呼び出します。INI生成に関する複雑なロジックはすべて `robco_ini_generate.py` モジュール内にカプセル化されています。
---

## `robco_ini_generate.py` 関数詳細

このモジュールは、自動化プロセスの最終ステップとして、RobCo Patcherが解釈可能なINIファイル群と配布用のZIPアーカイブを生成します。`Orchestrator`から`run`関数が呼び出されることで処理が開始されます。

### `run(config) -> bool`
- **役割**: モジュールのメインエントリーポイント。すべての入力ファイルを読み込み、複数のINIファイルを生成し、最後にZIPアーカイブを作成します。
- **処理**:
    1.  **設定と入力ファイルの読み込み**:
        -   `config_manager`から必要なパス（`strategy_file`, `output_dir`, `ammo_map_file`など）を取得します。
        -   `_read_weapon_records`: `weapon_omod_map.json`を読み込み、処理対象となるすべての武器レコードを取得します。
        -   `_load_ammo_map`: `ammo_map.json`（または`ammo_map.ini`）から、ユーザーが`mapper.py`で設定した弾薬の対応関係を読み込みます。
        -   `_load_ll_from_csv`: `WeaponLeveledLists_Export.csv`から、武器を追加すべきLeveled Listの情報を読み込みます。
        -   `strategy.json`から、弾薬の分類情報（`ammo_classification`）や、どの勢力にどの武器を配布するかの重み付け（`allocation_matrix`）を読み込みます。
    2.  **INI生成ロジック**:
        -   全武器レコードをループ処理します。
        -   各武器の弾薬が`_load_ammo_map`で読み込んだマップに存在する場合、その武器はパッチ対象となります。
        -   以下の4種類のINIファイルに対応するルールをメモリ上で生成します。
            -   **武器の弾薬置換**: `filterByWeapons=...:setNewAmmo=...`形式のルールを作成します。
            -   **OMODの弾薬置換**: 武器に紐付くOMODも同様に、`filterByOMod=...:changeOModPropertiesForm=Ammo=...`形式のルールを作成します。同じOMODが複数の武器で使われている場合の競合も考慮されます。
            -   **Leveled Listへの追加**: `strategy.json`の定義に基づき、パッチ適用済みの武器をどの勢力（Gunners, Raidersなど）のLeveled Listに追加するかを決定し、`formsToAdd=...`形式のルールを作成します。
            -   **NPC用弾薬リスト**: 必要に応じて、NPCが使用する弾薬リストを`setNewAmmoList=...`で設定するルールも生成します。
    3.  **ファイル書き出し**:
        -   `RobCo_Auto_Patcher/`以下の各サブディレクトリ（`weapon`, `omod`, `formlist`）に、生成したルールをそれぞれの`.ini`ファイルに書き出します。
        -   また、マッピングされた元のカスタム弾薬をゲーム内から削除するため、`Munitions_FormList_RemoveCustomAmmo.ini`も生成します。
    4.  **ZIPアーカイブ作成**:
        -   `shutil.make_archive`を使い、完成した`RobCo_Auto_Patcher`ディレクトリ全体を、プロジェクトルートに`RobCo_Auto_Patcher.zip`として圧縮します。
- **戻り値**: 処理がすべて成功すれば`True`、途中でエラーが発生した場合は`False`を返します。

---

## `AutoPatcherGUI.py` クラス・関数詳細

このスクリプトは、ユーザーが操作するGUIアプリケーションの本体です。`tkinter`を使用して構築されています。

### `Application(tk.Frame)` クラス
- **役割**: アプリケーションのメインウィンドウと、その中のすべてのUI要素（ウィジェット）を管理します。

#### `__init__(self, master, config_manager, orchestrator, log_queue)`
- **役割**: `Application`クラスのインスタンスを初期化します。
- **処理**:
    1.  メインウィンドウ(`master`)、`config_manager`、`orchestrator`のインスタンスを受け取り、内部に保持します。
    2.  `create_widgets`を呼び出してUIを構築し、`load_settings`で`config.ini`から設定を読み込みます。
    3.  `poll_log_queue`をスケジュールし、別スレッドからのログメッセージを定期的にGUIに表示できるようにします。

#### `create_widgets(self)`
- **役割**: ボタン、入力フィールド、チェックボックス、ログ表示エリアなど、GUIのすべてのUI要素を作成し、ウィンドウ内に配置します。
- **処理**:
    -   MO2連携設定、xEdit実行ファイルパス設定などのフレームを作成します。
    -   「戦略ファイルを生成・更新」「全自動処理を開始」の2つの主要な実行ボタンを配置します。
    -   `Orchestrator`からのログメッセージを表示するためのテキストボックスとスクロールバーを配置します。

#### `load_settings(self)` / `save_settings(self)`
- **役割**: `config.ini`とGUIの間のデータ連携を担当します。
- **処理**:
    -   `load_settings`: `config_manager`を介して`config.ini`から設定値を読み込み、GUIの各入力フィールドに反映させます。
    -   `save_settings`: GUIでユーザーが変更した設定値を`config_manager`を介して`config.ini`に保存します。処理開始前に必ず呼び出されます。

#### `start_full_process(self)` / `start_strategy_generation(self)`
- **役割**: メインの実行ボタンが押されたときのアクションを定義します。
- **処理**:
    -   `start_process`ヘルパー関数を呼び出します。
    -   `start_process`は、`run_full_process_in_thread`や`run_strategy_generation_in_thread`をターゲットとして新しいスレッド(`threading.Thread`)を生成・開始します。これにより、時間のかかる処理がバックグラウンドで実行され、GUIがフリーズするのを防ぎます。

#### `run_process_wrapper(self, target_func, process_name)`
- **役割**: バックグラウンドで実行される処理（`Orchestrator`のメソッド）を安全にラップし、UIの更新を管理します。
- **処理**:
    1.  処理開始時に、実行ボタンを無効化し、ログエリアをクリアします。
    2.  引数で渡された`target_func`（`orchestrator.run_full_process`など）を実行します。
    3.  `try...finally`ブロックを使い、処理が成功しても失敗しても、必ず最後にボタンを有効化し、完了メッセージをログに出力します。
    4.  処理結果に応じて、成功または失敗のメッセージボックスをユーザーに表示します。

---

## `mapper.py` クラス・関数詳細

このスクリプトは、`Orchestrator`から独立したプロセスとして起動されるGUIツールです。xEditが抽出した「未知の弾薬」と「Munitionsの弾薬」をユーザーが手動で紐付ける（マッピングする）機能を提供します。

### `AmmoMapperApp` クラス
- **役割**: 弾薬マッピングツールのUIとロジック全体を管理します。

#### `__init__(self, root_window, ammo_file_path, munitions_file_path, output_file_path)`
- **役割**: `AmmoMapperApp`のインスタンスを初期化します。
- **処理**:
    -   `Orchestrator`から渡されたコマンドライン引数（変換元ファイルパス、Munitions弾薬ファイルパス、出力先ファイルパス）を受け取り、内部に保持します。
    -   `setup_ui`を呼び出してUIの骨格を作り、`reload_data_and_build_ui`でデータの読み込みとUIの動的な構築を行います。

#### `load_data(self)`
- **役割**: マッピングに必要な2つの主要なINIファイルを読み込みます。
- **処理**:
    1.  **Munitions弾薬の読み込み**: `munitions_file_path`（`munitions_ammo_ids.ini`）を読み込み、`[MunitionsAmmo]`セクションからFormIDとEditorIDのリストを取得し、UIのドロップダウンリストの選択肢として準備します。
    2.  **未知の弾薬の読み込み**: `ammo_file_path`（`unique_ammo_for_mapping.ini`）を読み込み、`[UnmappedAmmo]`セクションからマッピング対象となる弾薬のリストを取得します。
    3.  **OMOD情報の付与（エンリッチ）**: `weapon_omod_map.json`が存在すればそれを読み込み、各「未知の弾薬」に関連付けられている武器改造（OMOD）の情報を見つけ出し、UIに表示するために弾薬データに付与します。

#### `build_ui_rows(self)`
- **役割**: `load_data`で読み込んだ「未知の弾薬」リストに基づき、UIの各行を動的に生成します。
- **処理**:
    -   `ammo_to_map`リストの各弾薬に対して、以下のUI要素を含む一行を作成し、画面に配置します。
        -   変換対象に含めるかを選択する**チェックボックス**。
        -   弾薬の元となる**ESP名**と**EditorID**を表示するラベル。
        -   関連付けられた**OMOD**情報（存在する場合）。
        -   変換先を選択するための**ドロップダウンリスト**（`munitions_ammo_list`が選択肢となる）。

#### `save_ini_file(self)`
- **役割**: ユーザーがUIで行ったマッピング設定をファイルに保存します。
- **処理と問題点**:
    -   **現在の挙動**: この関数は、チェックボックスがオンにされ、かつドロップダウンで変換先が選択されている行の情報を収集します。そして、`Orchestrator`から指定された`output_file_path`（例: `ammo_map.ini`）を**無視**し、その親ディレクトリに`robco_ammo_patch.ini`という固定名のファイルを生成します。このファイルには、RobCo Patcherが直接解釈できる`filterByWeapons`や`filterByOMod`形式のルールが書き込まれます。
    -   **処理フロー上の矛盾**: `Orchestrator`のメインフローは、この`mapper.py`が`ammo_map.ini`（または`.json`）を生成・更新することを期待しています。しかし、現在の`save_ini_file`の実装はそうなっておらず、後続の`robco_ini_generate.py`が必要とする形式の入力ファイルが生成されません。結果として、**`mapper.py`でのユーザーの選択が最終的なパッチに反映されない**という問題が発生しています。これは、開発の過程で`mapper.py`の役割が変更されたものの、`Orchestrator`側の連携が更新されなかったために生じたレガシーな挙動と考えられます。

---

## Pascalスクリプト詳細

このセクションでは、`pas_scripts/`ディレクトリにあるPascalスクリプトの詳細を説明します。

### コアスクリプト

*   **`00_RunAllExtractors.pas`**: データ抽出フェーズのメインエントリーポイントとなるスクリプトです。`AutoPatcherCore.pas`から他の関数を特定の順序で呼び出し、ユーザーのロードオーダーから必要なすべてのデータを抽出します。
*   **`AutoPatcherCore.pas`**: パッチロジックの中心となるライブラリです。武器の詳細、弾薬情報、レベルドリスト、Munitionsの弾薬IDを抽出するためのコア機能が含まれています。また、JSON操作やロギングのためのヘルパー関数も含まれています。
*   **`ExtractWeaponAmmoMappingLogic.pas`**: `AP_Run_ExtractWeaponAmmoMapping`のロジックを含むスクリプトです。すべての武器レコードを反復処理し、弾薬情報を抽出して、`weapon_ammo_map.json`と`unique_ammo_for_mapping.ini`の2つのファイルを生成します。
*   **`ExportLeveledListsLogic.pas`**: `AP_Run_ExportWeaponLeveledLists`のロジックを含むスクリプトです。武器に関連するレベルドリストをスキャンし、それらのEditorID、FormID、およびソースファイルを`WeaponLeveledLists_Export.csv`にエクスポートします。

### ライブラリスクリプト (`lib/`)

*   **`AutoPatcherLib.pas`**: 他のPascalスクリプトに不可欠なヘルパー関数を提供する軽量のスタブライブラリです。出力ディレクトリの取得、安全なEditorIDとFormIDの取得、JSONおよびINIファイルの保存、ロギングなどの機能が含まれています。
*   **`dk_json.pas`**: シンプルなJSONパーサーとオブジェクトモデルです。JSONデータを表現するための`TJSON`クラスと、JSON文字列を解析するための`TJSONParser`クラスを提供します。
*   **`mteBase.pas`**: `mteFunctions`ライブラリの一部です。主にバージョン比較（`VersionCompare`、`VersionCheck`）のためのベースレベルのヘルパー関数を提供します。
*   **`mteElements.pas`**: `mteFunctions`ライブラリの一部です。比較、トラバーサル（`ElementByIP`）、値の取得/設定、フラグ操作など、xEdit要素（`IInterface`）を操作するための包括的な関数セットを提供します。
*   **`mteFiles.pas`**: `mteFunctions`ライブラリの一部です。ファイルヘッダーの取得、マスターファイルの管理、オーバーライドレコードの取得など、プラグインファイル（`.esp`/`.esm`）を操作するための関数を提供します。
*   **`mteGUI.pas`**: `mteFunctions`ライブラリの一部です。このユニットはGUI関連機能のプレースホルダーのようですが、現在は空です。
*   **`mteRecords.pas`**: `mteFunctions`ライブラリの一部です。プラグインファイル内でレコードを作成および操作するためのヘルパー関数を提供します。
*   **`mteSystem.pas`**: `mteFunctions`ライブラリの一部です。ファイルパス操作などのシステムレベルのヘルパー関数を提供します。
*   **`mteTypes.pas`**: `mteFunctions`ライブラリの一部です。ブール値、整数、文字列、日時、色などの基本型を処理するための幅広い汎用ヘルパー関数を提供します。また、`TStringList`などの一般的なクラスのヘルパーも含まれています。

### テストスクリプト (`testmtelib/`)

*   **`mteBaseTests.pas`**: `mteBase`ユニットのテストです。
*   **`mteElementsTests.pas`**: `mteElements`ユニットのテストです。
*   **`mteFilesTests.pas`**: `mteFiles`ユニットのテストです。
*   **`mteRecordsTests.pas`**: `mteRecords`ユニットのテストです。
*   **`mteTypesTests.pas`**: `mteTypes`ユニットのテストです。

### その他のスクリプト

*   **`compile_check.pas`**: すべての`mteFunctions`ライブラリユニットをインクルードして、それらが正しく一緒にコンパイルされることを確認するシンプルなスクリプトです。
*   **`minimal_probe.pas`**: デバッグに使用される診断用スクリプトです。xEditスクリプトの実行が正常に開始されたことを示す小さなログファイルを書き込みます。
*   **`test_export_weapon_omod_only.pas`**: `AutoPatcherCore.pas`から`AP_Run_ExportWeaponAmmoDetails`関数を具体的に実行して、武器とOMODの抽出ロジックを単独でテストするテストスクリプトです。