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

const
  TARGET_EDITORIDS: array[0..3] of string = (
    'LLI_Raider_Weapons',
    'LLI_Faction_Gunner_Weapons',
    'LLI_Faction_Institute_Weapons',
    'LLI_Faction_SuperMutant_Weapons'
  );

function FindRecordByEditorID(editorID: string): IInterface;
var
  i, j: integer;
  aFile: IwbFile;
  Group, Rec: IInterface;
  recEditorID: string;
begin
  Result := nil;
  
  // Try MainRecordByEditorID first (if available in this xEdit version)
  try
    Result := MainRecordByEditorID(editorID);
    if Assigned(Result) then begin
      LogInfo(Format('Found via MainRecordByEditorID: %s', [editorID]));
      Exit;
    end;
  except
    // MainRecordByEditorID may not be available in all versions, continue with fallback
  end;
  
  // Fallback: walk through LVLI groups
  LogInfo(Format('Fallback search for: %s', [editorID]));
  for i := 0 to FileCount - 1 do begin
    aFile := FileByIndex(i);
    Group := GroupBySignature(aFile, 'LVLI');
    if not Assigned(Group) then Continue;
    
    for j := 0 to ElementCount(Group) - 1 do begin
      Rec := ElementByIndex(Group, j);
      recEditorID := GetElementEditValues(WinningOverride(Rec), 'EDID');
      if SameText(recEditorID, editorID) then begin
        Result := Rec;
        LogInfo(Format('Found via fallback: %s in %s', [editorID, GetFileName(aFile)]));
        Exit;
      end;
    end;
  end;
end;

function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  Result := 0;
end;

function Process(e: IInterface): integer;
begin
  Result := 0;
end;

function Finalize: integer;
var
  i: integer;
  rec: IInterface;
  editorID, pluginName, formIDStr: string;
  outputDir, jsonFilePath: string;
  SaveSuccess: Boolean;
  foundCount: integer;
begin
  Result := 0;
  foundCount := 0;
  
  try
    LogInfo('Starting weapon leveled list export');
    jsonOutput.Add('{');
    jsonOutput.Add('  "LeveledLists": {');

    for i := Low(TARGET_EDITORIDS) to High(TARGET_EDITORIDS) do begin
      editorID := TARGET_EDITORIDS[i];
      LogInfo(Format('Looking for: %s', [editorID]));
      
      rec := FindRecordByEditorID(editorID);
      if Assigned(rec) then begin
        pluginName := GetFileName(GetFile(rec));
        formIDStr := GetFullFormID(rec);
        
        if foundCount > 0 then
          jsonOutput.Strings[jsonOutput.Count - 1] := jsonOutput.Strings[jsonOutput.Count - 1] + ',';
        
        jsonOutput.Add(Format('    "%s": { "plugin": "%s", "formid": "%s" }', 
                             [editorID, pluginName, formIDStr]));
        LogInfo(Format('Exported: %s = %s|%s', [editorID, pluginName, formIDStr]));
        Inc(foundCount);
      end else begin
        LogWarning(Format('Not found: %s', [editorID]));
      end;
    end;

    jsonOutput.Add('  }');
    jsonOutput.Add('}');
    
    outputDir := GetOutputDirectory;
    jsonFilePath := outputDir + 'leveled_lists.json';
    
    LogInfo(Format('Saving to: %s', [jsonFilePath]));
    SaveSuccess := SaveAndCleanJSONToFile(jsonOutput, jsonFilePath, foundCount, False);
    
    if SaveSuccess then begin
      LogSuccess(Format('Exported %d leveled lists to leveled_lists.json', [foundCount]));
      LogComplete('Weapon leveled list export');
    end else begin
      LogError('Failed to save leveled_lists.json');
      Result := 1;
    end;
      
  finally
    jsonOutput.Free;
  end;
end;

end.

