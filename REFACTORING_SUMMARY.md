# リファクタリング概要 - run_xedit_script メソッド

## 変更内容

### 1. 引数構築の再構成（関数の最初へ移動）

**変更前:**
- 引数は関数の中盤で構築されていた
- 設定値の取得とコマンド構築が分散していた

**変更後:**
- 全ての設定値とパスを関数の最初で取得
- xEdit 引数を関数の最初で構築
- MO2 引数も関数の最初で構築

### 2. config_manager.py の活用

**設定値の取得を標準化:**
```python
# MO2 関連のパラメータ
mo2_executable_path = env_settings.get('mo2_executable_path', '')
xedit_profile_name = env_settings.get('xedit_profile_name', 'Default')

# xEdit 関連のパラメータ
xedit_executable_path = self.config.get_path('Paths', 'xedit_executable')
game_data_path = self.config.get_path('Paths', 'game_data_path')

# オプションパラメータ
force_data_param = self.config.get_boolean('Parameters', 'force_data_param', False)
use_cache = self._should_use_cache()
```

### 3. xEdit 引数の明確な構造化

**推奨されるフラグを使用:**
- `-FO4` - ゲームモードを Fallout 4 に設定
- `-script:<script>` - 実行するスクリプトを指定
- `-S:"<path>"` - スクリプトディレクトリを指定
- `-IKnowWhatImDoing` - 警告ダイアログを抑制
- `-AllowMasterFilesEdit` - マスターファイルの編集を許可
- `-L:"<path>"` - ログファイルの出力先を指定
- `-cache` - キャッシュを使用（オプション）
- `-D:"<path>"` - Data ディレクトリを指定（条件付き）

### 4. コマンドライン構築

**MO2 経由の場合:**
```python
command_list = [
    str(mo2_executable_path),
    '-p',
    str(xedit_profile_name),
    f'moshortcut://:{executable_name_in_mo2}'
]
```

**直接起動の場合:**
```python
command_list = [str(xedit_executable_path)] + xedit_args
```

## subprocess の使用について

### 現在の実装
- **直接起動**: `subprocess.run` を使用（同期実行）
- **MO2 経由**: `subprocess.Popen` を使用（非同期実行 + プロセス検出）

### subprocess.Popen を使う理由（MO2 経由）
MO2 経由で xEdit を起動する場合、以下の処理が必要:
1. MO2 プロセスを起動
2. MO2 が xEdit プロセスを起動するのを待機
3. xEdit プロセスの PID を検出
4. xEdit プロセスの終了を待機

`subprocess.run` は起動したプロセス（MO2）の終了を待つため、xEdit プロセスを直接監視できません。そのため `subprocess.Popen` を使用し、psutil でプロセスを検出する実装になっています。

## テスト結果

### test_arguments.py
引数構築ロジックをテストするスクリプトを作成しました。

**実行結果:**
```
✓ -script:TEMP_example.pas
✓ -S:".../Edit Scripts\"
✓ -IKnowWhatImDoing
✓ -AllowMasterFilesEdit
✓ -L:"Output/xEdit_session_example.log"
✗ -D (MO2使用時は省略)

[完全なコマンドライン（MO2経由の場合）]
E:/MO2/ModOrganizer.exe -p new1 moshortcut://:xEdit
```

### debug_config_paths.py
設定ファイルの読み込みが正常に動作することを確認しました。

## 利点

1. **可読性の向上**: 引数構築が関数の最初にまとまっているため、理解しやすい
2. **保守性の向上**: 引数を変更する際、関数の最初だけを見れば良い
3. **デバッグの容易化**: コマンドラインの内容が明確に構造化されている
4. **config.ini との統合**: 全てのパスとパラメータが config_manager 経由で取得される

## 今後の改善案

1. subprocess.run の完全な採用を検討（MO2 経由の処理方法を見直す必要がある）
2. xEdit 引数のさらなるカスタマイズオプション追加
3. エラーハンドリングの強化
