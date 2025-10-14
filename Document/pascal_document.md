# Pascalスクリプト APIリファレンス

このドキュメントは、Munition_AutoPatcher_v1.1 プロジェクトで使用される主要なPascalスクリプトの構造と、各モジュールの役割を解説します。

---

### 処理の呼び出し階層

xEditからのスクリプト実行は、以下の階層で行われます。Pythonの`Orchestrator`からxEditが呼び出されると、まずエントリーポイントである`00_RunAllExtractors.pas`が実行されます。

1.  **`00_RunAllExtractors.pas`**: xEditから直接呼び出される唯一のスクリプト。各抽出処理を順番に呼び出す「司令塔」です。
2.  **`AutoPatcherCore.pas`**: 各抽出処理の本体（`AP_Run_...`）を定義するAPIレイヤー。一部のロジックはここに直接実装されていますが、主要なものは各`*Logic.pas`ファイルに委譲されます。
3.  **`*Logic.pas`** (`ExtractWeaponAmmoMappingLogic.pas` など): 特定のデータ抽出タスク（例: 武器と弾薬のマッピング）に関する具体的な実装が含まれます。
4.  **`lib/AutoPatcherLib.pas`**: ログ出力、ファイル保存、FormIDの解決など、全てのスクリプトから利用される汎用ヘルパー関数を提供します。

---

### 1. `00_RunAllExtractors.pas` (統合実行スクリプト)

このスクリプトは、xEditから実行される際の単一のエントリーポイントです。その唯一の役割は、`AutoPatcherCore.pas`で定義されている各種抽出関数 (`AP_Run_...`) を正しい順序で呼び出すことです。処理が成功または失敗したかに応じて、最終的なステータスをログに出力します。

| 関数名 | 役割 | 戻り値 |
| :--- | :--- | :--- |
| `Initialize` | スクリプトのエントリーポイント。`AP_Run_ExtractWeaponAmmoMapping`、`AP_Run_ExportWeaponAmmoDetails`などを順番に呼び出します。 | `Integer` (0: 全て成功, 1: いずれかが失敗) |

---

### 2. `AutoPatcherCore.pas` (コアAPI)

このユニットは、Pascalスクリプト群の主要なAPIを定義します。各抽出タスクは `AP_Run_...` という接頭辞を持つ関数として公開され、`00_RunAllExtractors.pas`から呼び出されます。一部の単純な抽出ロジックはこのファイル内に直接実装されていますが、複雑なものは外部の `*Logic.pas` ユニットに委譲されます。

| 関数名 | 役割 | 戻り値 |
| :--- | :--- | :--- |
| `AP_Run_ExtractWeaponAmmoMapping` | **(委譲)** 武器と弾薬のマッピング情報を抽出します。実際の処理は `ExtractWeaponAmmoMappingLogic.pas` に委譲されます。 | `Integer` (0: 成功, 1: 失敗) |
| `AP_Run_ExportWeaponLeveledLists` | **(委譲)** 武器関連のレベルドリストを抽出します。実際の処理は `ExportLeveledListsLogic.pas` に委譲されます。 | `Integer` (0: 成功, 1: 失敗) |
| `AP_Run_ExportWeaponAmmoDetails` | **(内部実装)** 全ての武器レコードを走査し、武器の基本情報（プラグイン、FormID、EditorID）と、それに紐付く弾薬、さらに武器に適用可能な全Object Modification (OMOD) の情報を抽出し、`weapon_omod_map.json` として出力します。このファイルは後続のPython処理で最も重要な入力の一つです。 | `Integer` (0: 成功, 1: 失敗) |
| `AP_Run_ExportMunitionsAmmoIDs` | **(内部実装)** `Munitions - An Ammo Expansion.esl` から全ての弾薬のFormIDとEditorIDを抽出し、`munitions_ammo_ids.ini` を生成します。 | `Integer` (0: 成功, 1: 失敗) |

---

### 3. `ExtractWeaponAmmoMappingLogic.pas` (武器・弾薬マッピング抽出ロジック)

このユニットは、MODが追加した武器（WEAP）がどの弾薬（AMMO）を使用しているかを検出し、その関連情報をファイルに出力する具体的なロジックを実装しています。

| 関数名 | 役割 | 戻り値 |
| :--- | :--- | :--- |
| `AP_Run_ExtractWeaponAmmoMapping` | 全てのプラグインを走査し、武器とその弾薬の関連情報を抽出します。以下の2つのファイルを生成します。<br>- `weapon_ammo_map.json`: 武器のEditorIDと弾薬のFormIDのマップ。<br>- `unique_ammo_for_mapping.ini`: 抽出されたユニークな弾薬の一覧。これはPythonの`mapper.py`でユーザーが手動マッピングを行う際の入力データとなります。 | `Integer` (0: 成功, 1: 失敗) |

---

### 4. `ExportLeveledListsLogic.pas` (レベルドリスト抽出ロジック)

このユニットは、武器が敵やコンテナに配布される際に使用されるレベルドリスト（LVLI）を特定し、その情報をCSVファイルとして出力するロジックを実装しています。

| 関数名 | 役割 | 戻り値 |
| :--- | :--- | :--- |
| `AP_Run_ExportWeaponLeveledLists` | `Fallout4.esm`や主要DLCに含まれるLVLIレコードを走査し、EditorIDに`Weapon`, `Gun`などのキーワードを含むものを抽出します。結果は `WeaponLeveledLists_Export.csv` に保存され、Pythonの`robco_ini_generate.py`がどのリストに武器を追加すべきかを判断するために使用します。 | `Integer` (0: 成功, 1: 失敗) |

---

### 5. `lib/AutoPatcherLib.pas` (汎用ライブラリ)

複数のスクリプトから共通して利用される、汎用的なヘルパー関数群を提供します。これにより、コードの重複を避け、一貫した処理（特にファイル出力とログ記録）を保証します。

| 関数名 | 役割 |
| :--- | :--- |
| `GetOutputDirectory` | スクリプトが出力ファイルを保存すべきディレクトリのパス（通常は `...\[Edit Scripts]\Output\`）を返します。 |
| `LogSuccess`, `LogError`, `LogComplete` | `[SUCCESS]`, `[ERROR]` といった接頭辞を付けてログメッセージをxEditのログウィンドウに出力します。Pythonの`Orchestrator`はこれらのメッセージを監視して、スクリプトの実行成否を判断します。 |
| `SaveAndCleanJSONToFile`, `SaveINIToFile` | `TStringList`の内容を、指定されたパスにテキストファイルとして保存します。ファイル保存の成功・失敗ログも自動で出力します。 |
| `GetFullFormID` | レコードがESLプラグインに属している場合でも、正しいロードオーダーを考慮した完全なFormID（例: `FE001800`）を文字列として取得します。これはPython側でレコードを一意に識別するために不可欠です。 |
| `GetEditorIdSafe` | `EditorID()`が例外を発生させる場合でも、`GetElementEditValues` を使って安全にEditorIDを取得するフォールバック機能を提供します。 |

---

### 6. 生成されるファイルと役割

xEditスクリプトは、後続のPython処理で利用される以下の中間ファイルを `Output` ディレクトリ（またはxEditの環境設定に依存する場所）に生成します。

| ファイル名 | 生成元スクリプト | 内容 | 利用先 (Python) |
| :--- | :--- | :--- | :--- |
| `weapon_omod_map.json` | `AutoPatcherCore.pas` | 武器のレコード、使用弾薬、および関連する全てのOMODの情報を含む最も重要なJSONファイル。 | `robco_ini_generate.py`: どの武器にどの弾薬を適用し、どのOMODをパッチするかの基本情報源。<br>`mapper.py`: OMOD情報を表示し、ユーザーのマッピングを補助するために使用。 |
| `munitions_ammo_ids.ini` | `AutoPatcherCore.pas` | `Munitions - An Ammo Expansion.esl` に含まれる全ての弾薬のFormIDとEditorIDを `[MunitionsAmmo]` セクションに記録したもの。 | `Orchestrator.py`: `strategy.json`を生成する際の入力。<br>`mapper.py`: ユーザーが弾薬をマッピングする際の、変換先候補リストとして使用。 |
| `unique_ammo_for_mapping.ini` | `ExtractWeaponAmmoMappingLogic.pas` | MODが追加したユニークな弾薬のリスト。`[UnmappedAmmo]`セクションに `FormID=ESP名|EditorID` の形式で記録される。 | `mapper.py`: このリストを元に、ユーザーが手動でMunitions弾薬への変換（マッピング）を行うための入力データとして使用。 |
| `WeaponLeveledLists_Export.csv` | `ExportLeveledListsLogic.pas` | 武器が配布される可能性のあるレベルドリスト（LVLI）の情報をCSV形式で出力したもの。`EditorID`, `FormID`, `SourceFile`などの列を含む。 | `robco_ini_generate.py`: `LLI_Hostile_Gunner_Any` などの特定のレベルドリストのFormIDを解決するために使用。これにより、Robco Patcherがどのレベルドリストに武器を追加すべきかを判断できる。 |
| `weapon_ammo_map.json` | `ExtractWeaponAmmoMappingLogic.pas` | (補助ファイル) 武器のEditorIDと弾薬のFormIDを関連付けたシンプルなJSON配列。 | `robco_ini_generate.py`: 補助的な情報として参照されることがある。 |