unit ExportMunitionsAmmoIDs;

uses xEditAPI, Classes, SysUtils, StrUtils, Windows;

var
  iniLines: TStringList;

// ★★★ 修正箇所: 正しいヘルパー関数に置き換え ★★★
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

function Initialize: integer;
begin
  iniLines := TStringList.Create;
  Result := 0;
end;

function Finalize: integer;
var
  ammoGroup, rec: IInterface;
  i, j: integer;
  iniFilePath, editorID, fullFormID: string;
  targetModFileName: string;
  outputDir: string;
  munitionsPlugin: IInterface;
begin
  Result := 0;
  AddMessage('[AutoPatcher] Exporting ammo EditorID and FormID from Munitions mod...');
  
  targetModFileName := 'Munitions - An Ammo Expansion.esl';

  iniLines.Add('[MunitionsAmmo]');
  iniLines.Add('; FormID=EditorID');

  try
    outputDir := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\Output\';
    if not DirectoryExists(outputDir) then
      ForceDirectories(outputDir);

    munitionsPlugin := FileByName(targetModFileName);
    if not Assigned(munitionsPlugin) then begin
        AddMessage('[AutoPatcher] ERROR: ' + targetModFileName + ' is not loaded.');
        Exit;
    end;

    AddMessage('[AutoPatcher] Processing file: ' + targetModFileName);

    ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
    if not Assigned(ammoGroup) then begin
      AddMessage('[AutoPatcher]  - No AMMO group found in ' + targetModFileName);
      Exit;
    end;

    for j := 0 to ElementCount(ammoGroup) - 1 do begin
      rec := ElementByIndex(ammoGroup, j);
      if not IsMaster(rec) then Continue;
      
      rec := MasterOrSelf(rec);
      editorID := GetElementEditValues(rec, 'EDID');
      fullFormID := IntToHex(GetLoadOrderFormID(rec), 8);

      iniLines.Add(Format('%s=%s', [fullFormID, editorID]));
    end;

    iniFilePath := outputDir + 'munitions_ammo_ids.ini';
    iniLines.SaveToFile(iniFilePath, TEncoding.UTF8);
    
    AddMessage('[AutoPatcher] SUCCESS: Export Complete.');
    AddMessage('[AutoPatcher] File: ' + iniFilePath);
    AddMessage('[AutoPatcher] Records: ' + IntToStr(iniLines.Count - 2));

    AddMessage('[AutoPatcher] Munitions ammo ID export complete.');

  except
    on E: Exception do
    begin
      AddMessage('[AutoPatcher] ERROR: ' + E.Message);
      Result := 1;
    end;
  end;

  iniLines.Free;
end;

end.

