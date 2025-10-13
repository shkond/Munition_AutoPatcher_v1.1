第一部：要望どおり — 「これまでのデバッグの主な原因」と「再発防止／デバッグ手順」のドキュメント

短い要点（1段落）

主な原因は「実行環境（xEdit の PascalScript インタプリタ）が想定より制限が多い」「ワークスペースと実行時コピーの不一致」「文字エンコーディング（日本語／非ASCII）がパーサや出力で問題を起こす」「一部 API（ProgramPath、AssignFile、TStringList.Size 等）がランタイムで使えない／存在しない」。これらが組み合わさり、スクリプトが予期せず終了したりファイルが作成されなかったりしました。
チェックリスト／再発防止手順（正しい順で使えるコマンド/操作を含む）

変更前に必要な準備
変更する Pascal スクリプトは必ずワークスペースで編集する。編集→コミット→「runtime へ上書きコピー」を必ず1つの手順で行う（コピー忘れを防ぐ）。
xEdit 実行前に runtime の Edit Scripts フォルダが最新であることを確認（タイムスタンプ比較）。PowerShell 例:
Get-ChildItem 'E:\fo4mod\xedit\Edit Scripts\AutoPatcherCore.pas' | Select-Object Name,LastWriteTime
Get-ChildItem 'E:\Munition_AutoPatcher_v1.1\pas_scripts\AutoPatcherCore.pas' | Select-Object Name,LastWriteTime

パーサ／ランタイム互換の基本ルール（必ず守る）
PascalScript で未定義の組み込み識別子（ProgramPath, AssignFile, Rewrite, Append, TextFile など）を使わない。代替：AddMessage（ログ出力）でプローブする。
TStringList のプロパティは runtime 実装に依存する。一般的には .Count を使う（.Size は存在しない場合がある）。
unit の構造は正しく（単一の interface、implementation 各セクション）。uses の位置に注意（interface と implementation に分ける）。
文字列リテラル／コメントの非ASCII（日本語など）はビルド／解析で文字化けの原因になることがある。可能ならログ文は ASCII にするか、UTF-8 での保存と xEdit の読み取り挙動を考慮。
デバッグ手順（問題が出たら順に実行）
minimal_probe を用意する：AddMessage のみで早期に実行開始をログに出す。実行して xEdit のセッションログ（-Log）に AddMessage が出るか確認。
core に小さなプローブ（AddMessage）を入れてワークフローを細分化（例：ファイルループの先頭、各武器の処理開始、OMOD の処理開始/終了）。プローブはファイルIOではなく AddMessage で出す。
もしセッションログに EJvInterpreterError（例: Undeclared Identifier 'X'）が出たら、該当識別子を使っている行をコメントアウト／置換して再実行。該当行は必ず runtime の TEMP コピーを確認する（Orchestrator は TEMP 名を出力する場合がある）。
ファイル入出力が失敗する場合（パスが見つからない等）は、まず GetOutputDirectory の戻すパスが存在するか確認し、存在しないなら ForceDirectories で作成するか一時的にワークスペースの絶対パスを返すデバッグ stub を用意して実行。
出力物が生成されたら内容をサンプリングして、文字化けや値の欠落（例：FormID が空）を検査する。問題箇所があればその関数（例：GetFullFormID）だけを堅牢化する。
速攻で使える PowerShell のワンライナー（トラブル時）
Get-ChildItem 'E:\Munition_AutoPatcher_v1.1\Output\xEdit_session_*.log' -File |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
  ForEach-Object { Get-Content $_.FullName -Tail 200 }


xEdit ログの末尾確認:
runtime と workspace ファイル差分確認（タイムスタンプ）:
Compare-Object (Get-Content 'E:\Munition_AutoPatcher_v1.1\pas_scripts\AutoPatcherCore.pas') (Get-Content 'E:\fo4mod\xedit\Edit Scripts\AutoPatcherCore.pas')


長期的な再発防止（推奨）
CI スクリプト（ローカル）を用意して、pas_scripts の差分を runtime に自動でコピー・バックアップする。これにより手動ミスを減らせる。
スクリプトは AddMessage トレースを標準で入れる（デバッグフラグで詳細度を変える）。
主要なヘルパ（AutoPatcherLib）を xEdit 環境での最小互換実装にしておき、実行時に利用される API を中央でラップする（ProgramPath 等の扱いを一元化）。