unit ExportWeaponLeveledLists;

uses xEditAPI, Classes, SysUtils, StrUtils, Windows;

var
  jsonOutput: TStringList;
  processedLists: TStringList;

// ššš C³‰ÓŠ: ³‚µ‚¢ƒwƒ‹ƒp[ŠÖ”‚É’u‚«Š·‚¦ ššš
function EnsureTrailingSlash(const s: string): string;
var
  lastChar: string;
begin
  if s = '' then begin
    Result := '';
    Exit;
  end;
  lastChar := Copy(s, Length(s), 1);
  if lastChar <> '\' then
    Result := s + '\'
  else
    Result := s;
end;

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
begin
  jsonOutput.Add('{');
  
  for i := 0 to FileCount - 1 do begin
    aFile := FileByIndex(i);
    fileName := GetFileName(aFile);
    if not IsTargetFile(fileName) then Continue;

    Group := GroupBySignature(aFile, 'LVLI');
    if not Assigned(Group) then Continue;

    for j := 0 to ElementCount(Group) - 1 do begin
      Rec := ElementByIndex(Group, j);
      winningRec := WinningOverride(Rec);
      EditorID := GetElementEditValues(winningRec, 'EDID');

      if (EditorID = '') or (processedLists.IndexOf(EditorID) > -1) then Continue;
      
      factionType := GetFactionType(EditorID);
      if factionType = 'Unknown' then Continue;

      processedLists.Add(EditorID);
      formIDStr := IntToHex(FixedFormID(Rec), 8);

      if jsonOutput.Count > 1 then jsonOutput.Strings[jsonOutput.Count - 1] := jsonOutput.Strings[jsonOutput.Count - 1] + ',';
      jsonOutput.Add(Format('  "%s": "%s"', [factionType, EditorID]));
    end;
  end;

  jsonOutput.Add('}');
  
  outputDir := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\Output\';
  ForceDirectories(outputDir);
  jsonFilePath := outputDir + 'leveled_lists.json';
  
  jsonOutput.SaveToFile(jsonFilePath, TEncoding.UTF8);
  AddMessage('[AutoPatcher] SUCCESS: Leveled list export finished: ' + IntToStr(processedLists.Count) + ' records -> ' + jsonFilePath);
  
  AddMessage('[AutoPatcher] Leveled list export complete.');

  jsonOutput.Free;
  processedLists.Free;
  Result := 0;
end;

end.

