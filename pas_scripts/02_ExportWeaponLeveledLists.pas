unit ExportWeaponLeveledLists;

uses
  xEditAPI,
  Classes,
  SysUtils,
  StrUtils,
  Windows,
  'lib/AutoPatcherLib';

var
  jsonOutput: TStringList;

// 指定した EditorID の LVLI レコードを（可能なら高速に）解決する。
// 1) MainRecordByEditorID を試し（存在しない環境もあるため try/except）
// 2) 失敗時はすべてのファイルの LVLI グループを走査して一致する EditorID を探す。
function ResolveLvliByEditorID(const edid: string; out plugin, formid: string): boolean;
var
  rec, f, g, r: IInterface;
  i, j: integer;
begin
  Result := False;
  plugin := '';
  formid := '';

  // 1) MainRecordByEditorID（利用できない環境もある）
  try
    rec := MainRecordByEditorID(edid);
    if Assigned(rec) and (Signature(rec) = 'LVLI') then begin
      plugin := GetFileName(GetFile(rec));
      formid := IntToHex(GetLoadOrderFormID(rec), 8);
      Exit(True);
    end;
  except
    // 無視してフォールバックへ
  end;

  // 2) フォールバック: すべての読み込み済みプラグインの LVLI を総当たり
  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    g := GroupBySignature(f, 'LVLI'); // Leveled Item
    if not Assigned(g) then
      Continue;

    for j := 0 to Pred(ElementCount(g)) do begin
      r := ElementByIndex(g, j);
      if SameText(EditorID(r), edid) then begin
        plugin := GetFileName(GetFile(r));
        formid := IntToHex(GetLoadOrderFormID(r), 8);
        Exit(True);
      end;
    end;
  end;
end;

// EditorID から { "plugin": "...", "formid": "XXXXXXXX" } の JSON 行を返す（末尾カンマ制御付き）
function LeveledListJsonLine(const edid: string; const withComma: boolean): string;
var
  plug, fid, comma: string;
  ok: boolean;
begin
  ok := ResolveLvliByEditorID(edid, plug, fid);
  if not ok then
    LogWarning('LL EditorID not resolved: ' + edid);

  if withComma then comma := ',' else comma := '';

  // JSON を壊さないよう、空値は必ず "" を出力
  Result := Format('    "%s": { "plugin": "%s", "formid": "%s" }%s',
                   [edid, plug, fid, comma]);
end;

// 出力 JSON を構築して jsonOutput に格納
procedure BuildLeveledListsJson;
begin
  jsonOutput.Clear;
  jsonOutput.Add('{');
  jsonOutput.Add('  "LeveledLists": {');

  // 対象は固定の4つ（EditorID のみ使用）
  jsonOutput.Add(LeveledListJsonLine('LLI_Raider_Weapons', True));
  jsonOutput.Add(LeveledListJsonLine('LLI_Faction_Gunner_Weapons', True));
  jsonOutput.Add(LeveledListJsonLine('LLI_Faction_Institute_Weapons', True));
  // 最終行はカンマを付けない
  jsonOutput.Add(LeveledListJsonLine('LLI_Faction_SuperMutant_Weapons', False));

  jsonOutput.Add('  }');
  jsonOutput.Add('}');
end;

function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  Result := 0;
end;

function Process(e: IInterface): integer;
begin
  // このスクリプトはファイル単位の処理を行わないため何もしない
  Result := 0;
end;

function Finalize: integer;
var
  outputDir, jsonFilePath: string;
  ok: boolean;
begin
  Result := 0;
  try
    outputDir := GetOutputDirectory; // 'Edit Scripts\Output\' を返す（存在しなければ作成）
    jsonFilePath := outputDir + 'leveled_lists.json';

    LogInfo('Resolving leveled list EditorIDs to plugin|formid (4 targets).');

    BuildLeveledListsJson;

    // 重要: leveled_lists.json はクリーンアップ不要。空文字 "" が壊れるため autoCleanup=False にする。
    ok := SaveAndCleanJSONToFile(jsonOutput, jsonFilePath, 4, False);
    if ok then
      LogComplete('Leveled list export')  // Orchestrator 側の成功検出用メッセージ
    else
      LogWarning('Leveled list export saved with warnings');

  except
    on E: Exception do begin
      LogError('ExportWeaponLeveledLists: ' + E.Message);
      Result := 1;
    end;
  end;

  jsonOutput.Free;
end;

end.