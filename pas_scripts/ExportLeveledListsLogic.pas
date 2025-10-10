unit ExportLeveledListsLogic;

interface

uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows,
  'lib/AutoPatcherLib';

function AP_Run_ExportWeaponLeveledLists: Integer;

implementation

// 対象ファイルかどうか（Fallout4、DLC、CC）
function _IsTargetFile(const fileName: string): boolean;
var
  lower: string;
begin
  lower := LowerCase(fileName);
  Result :=
    (fileName = 'Fallout4.esm') or
    (fileName = 'DLCRobot.esm') or
    (fileName = 'DLCCoast.esm') or
    (fileName = 'DLCworkshop01.esm') or
    (fileName = 'DLCworkshop02.esm') or
    (fileName = 'DLCworkshop03.esm') or
    (fileName = 'DLCNukaWorld.esm') or
    (Pos('cc', lower) = 1) or
    (Pos('cc', lower) = 3) or
    (Pos('creations', lower) = 1);
end;

// 武器関連レベルドリストの判定（除外条件含む）
function _IsWeaponRelated(rec: IInterface): boolean;
var
  editorID: string;
begin
  Result := false;
  editorID := GetElementEditValues(rec, 'EDID');

  if (Pos('VRWorkshopShared', editorID) > 0) or
     (Pos('Grenade', editorID) > 0) or
     (Pos('Mine', editorID) > 0) or
     (Pos('Ammo', editorID) > 0) or
     (Pos('Armor', editorID) > 0) or
     (Pos('Clothes', editorID) > 0) or
     (Pos('Outfit', editorID) > 0) or
     (Pos('Stimpack', editorID) > 0) or
     (Pos('Chem', editorID) > 0) or
     (Pos('Container', editorID) > 0) or
     (Pos('Loot', editorID) > 0) or
     (Pos('Dog', editorID) > 0) or
     (Pos('Misc', editorID) > 0) or
     (Pos('Underarmor', editorID) > 0) or
     (Pos('Vendor', editorID) > 0) then Exit;

  if (Pos('Weapon', editorID) > 0) or
     (Pos('Gun', editorID) > 0) or
     (Pos('Pistol', editorID) > 0) or
     (Pos('Rifle', editorID) > 0) or
     (Pos('Shotgun', editorID) > 0) or
     (Pos('Sniper', editorID) > 0) or
     (Pos('Auto', editorID) > 0) or
     (Pos('SemiAuto', editorID) > 0) or
     (Pos('Melee', editorID) > 0) or
     (Pos('Laser', editorID) > 0) or
     (Pos('Plasma', editorID) > 0) or
     (Copy(editorID, 1, 4) = 'LLI_') then
    Result := true;
end;

// ========== AP_Run_ExportWeaponLeveledLists 実装 ==========
function AP_Run_ExportWeaponLeveledLists: Integer;
var
  // Local state variables
  csvLines: TStringList;
  processedCount: Integer;
  // Loop variables
  i, j: Integer;
  aFile: IwbFile;
  Group, Rec: IInterface;
  EditorID, formIDStr, fileName, csvFilePath: string;
begin
  Result := 0;
  csvLines := TStringList.Create;
  try
    // Initialize local state
    csvLines.Add('EditorID,FormID,SourceFile');
    processedCount := 0;

    // Process all files (equivalent to iterating through ScriptProcessElements = [etFile])
    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      fileName := GetFileName(aFile);

      if not _IsTargetFile(fileName) then Continue;

      if not HasGroup(aFile, 'LVLI') then Continue;
      Group := GroupBySignature(aFile, 'LVLI');
      for j := 0 to ElementCount(Group) - 1 do begin
        Rec := ElementByIndex(Group, j);
        EditorID := GetElementEditValues(Rec, 'EDID');
        if EditorID = '' then Continue;
        if (Pos('VRWorkshopShared', EditorID) > 0) then Continue;

        // Base check
        if _IsWeaponRelated(Rec) then begin
          // No external filters for simplicity in this consolidated function.
          // If filtering is needed, it should be passed as parameters.
          formIDStr := IntToHex(FixedFormID(Rec), 8);
          csvLines.Add(Format('"%s","%s","%s"', [EditorID, formIDStr, fileName]));
        end;
      end;
      Inc(processedCount);
    end; // End of file loop

    // Finalize (save file)
    csvFilePath := ScriptsPath + 'WeaponLeveledLists_Export.csv';
    csvLines.SaveToFile(csvFilePath);
    LogSuccess(Format('CSV exported: %s (files processed: %d, rows: %d)', [
      csvFilePath, processedCount, csvLines.Count - 1]));
    LogComplete('Leveled list export');
  except
    on E: Exception do begin
      LogError('Failed to save WeaponLeveledLists_Export.csv: ' + E.Message);
      Result := 1;
    end;
  finally
    // Free local state
    csvLines.Free;
  end;
end;

end.