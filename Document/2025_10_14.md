2025-10-14
===========

作業概要:
- xEdit 上の Pascal スクリプト実行で発生していた欠落データと文字化け問題を解析・対処しました。

主な変更点:
- `pas_scripts/AutoPatcherCore.pas`
	- 武器単位のプローブを追加（`[PROBE_WEAPON]`, `[PROBE_FORMID_RAW]`, `[PROBE_FORMID_HEX]`）して、各レコードの plugin/editorid/raw FormID をログ出力するようにしました。
- `pas_scripts/lib/AutoPatcherLib.pas`
	- `GetFullFormID` を堅牢化（Format での型エラーを避けるため IntToHex を利用）し、raw FormID の解釈を安定化しました。

ツール追加（workspace/tools）:
- `fix_weapon_json.py` — 出力 JSON のエンコーディング検出と正常化（UTF-8化）。
- `repair_weapon_names.py` — weapon_name の mojibake 修復候補を試行し最良候補を採用。
- `check_weapon_json.py` — JSON の簡易検査（empty FormID のカウント等）。
- `parse_and_fill_from_logs.py` — xEdit ログから `[PROBE_FORMID_*]` を抽出し editorID→FormID マップを生成、JSON に埋める。
- `fill_weapon_formid_from_map.py` — 別マップから editorID で FormID を埋める簡易ツール（補助）。
- `inspect_final_json.py` — before/after の比較と要約出力。
- `replace_name_with_editorid.py` — 文字化け/空の `weapon_name` を `weapon_editor_id` で上書きする処理。

生成された成果物（`Output/`）:
- `weapon_omod_map.fixed.json` — エンコーディング正規化済
- `weapon_omod_map.repaired.json` — 名前修復適用済
- `weapon_omod_map.repaired.final-logfilled.json` — ログから抽出した FormID を埋めた最終版
- `weapon_omod_map.namefixed.json` — weapon_name を editorID で上書きした版
- `weapon_name_changes.csv` — name を editorID で置換した変更ログ
- `weapon_ammo_map.fixed.json` — ammo マップのエンコーディング正規化版

実行した修正と結果の要点:
- xEdit の実行ログから raw FormID を抽出して 484 件すべてに `weapon_form_id` を付与しました。
- 文字化け（CJK/Shift_JIS 系）は多数残存しているため、最終的に `weapon_name` を `weapon_editor_id` に置換する保守的な処置を行いました（変更: 422 件）。

残タスク / 推奨事項:
- 将来的には `AutoPatcherLib` の本実装へ置き換え、エンコーディング周りを xEdit 側で安定させるのが望ましいです。
- 文字列修復をさらに改善する場合、別途外部の翻字/エンコーディング復元ライブラリを使うことを推奨します。

作業ブランチ: copilot/export-leveled-lists-json

備考:
- コミットメッセージは短くまとめてリポジトリに記録しました。ファイル名や細かい文言は後で差し替えてください。

