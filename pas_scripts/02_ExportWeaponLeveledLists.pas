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
  processedLists: TStringList;

function IsTargetFile(fileName: string): boolean;
begin
  Result := (LowerCase(fileName) = 'fallout4.esm') or (Pos('dlc', LowerCase(fileName)) = 1);
end;

function GetFactionType(editorID: string): string;
begin
  if Pos('Raider', editorID) > 0 then Result := 'Raiders'
  else if Pos('Gunner', editorID) > 0 then Result := 'Gunners'
  else if Pos('Institute', editorID) > 0 then Result := 'Institute'
  else if Pos('BoS', editorID) > 0 then Result := 'BrotherhoodOfSteel'
  else if Pos('Mutant', editorID) > 0 then Result := 'SuperMutants'
  else Result := 'Unknown';
end;

function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  processedLists := TStringList.Create;
  Result := 0;
end;

function Process(e: IInterface): integer;
begin
  Result := 0;
end;

function Finalize: integer;
var
  i, j: integer;
  aFile: IwbFile;
  Group, Rec, winningRec: IInterface;
  EditorID, formIDStr, factionType, fileName: string;
  outputDir, jsonFilePath: string;
  SaveSuccess: Boolean;
begin
  Result := 0;
  try
    LogInfo('Finalize: レベルドリスト処理開始');
    jsonOutput.Add('{');

    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      fileName := GetFileName(aFile);
      LogInfo(Format('ファイル検査: %s', [fileName]));
      
      if not IsTargetFile(fileName) then Continue;
      LogInfo(Format('対象ファイル: %s', [fileName]));

      Group := GroupBySignature(aFile, 'LVLI');
      if not Assigned(Group) then begin
        LogWarning(Format('%s にLVLIグループが見つかりません', [fileName]));
        Continue;
      end;
      
      LogInfo(Format('%s のLVLI数: %d', [fileName, ElementCount(Group)]));

      for j := 0 to ElementCount(Group) - 1 do begin
        Rec := ElementByIndex(Group, j);
        winningRec := WinningOverride(Rec);
        EditorID := GetElementEditValues(winningRec, 'EDID');

        if (EditorID = '') or (processedLists.IndexOf(EditorID) > -1) then Continue;
        
        factionType := GetFactionType(EditorID);
        if factionType = 'Unknown' then Continue;

        processedLists.Add(EditorID);
        formIDStr := GetFullFormID(Rec);

        if jsonOutput.Count > 1 then
          jsonOutput.Strings[jsonOutput.Count - 1] := jsonOutput.Strings[jsonOutput.Count - 1] + ',';

        jsonOutput.Add(Format('  "%s": "%s"', [factionType, EditorID]));
        LogInfo(Format('追加: %s -> %s', [factionType, EditorID]));
      end;
    end;

    jsonOutput.Add('}');
    
    LogInfo(Format('処理されたリスト数: %d', [processedLists.Count]));
    
    outputDir := GetOutputDirectory;
    jsonFilePath := outputDir + 'leveled_lists.json';
    
    LogInfo(Format('出力先: %s', [jsonFilePath]));
    
  // ★★★ 修正: SaveAndCleanJSONToFile を使用して自動クリーンアップ ★★★
  // 第4引数(True)はJSON出力から重複エントリを削除するかどうかを制御します
  SaveSuccess := SaveAndCleanJSONToFile(jsonOutput, jsonFilePath, processedLists.Count, True);
    
    if saveSuccess then begin
      LogSuccess(Format('leveled_lists.json を保存しました (%d リスト)', [processedLists.Count]));
      LogComplete('Leveled list export');
    end else begin
      LogError('leveled_lists.json の保存に失敗しました');
      Result := 1;
    end;
  finally
    jsonOutput.Free;
    processedLists.Free;
  end;
end;

end.

