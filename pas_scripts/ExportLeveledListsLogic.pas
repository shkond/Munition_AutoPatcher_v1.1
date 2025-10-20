unit ExportLeveledListsLogic;

interface

uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows,
  'AutoPatcherLib';

function AP_Run_ExportWeaponLeveledLists: Integer;

implementation

// 対象ファイルかどうか（Fallout4、DLC、CC）
// JvInterpreter 安定化のため const を使わず、長い or 連結は避ける
function IsTargetFileLL(fileName: string): boolean;
var
  lower: string;
begin
  lower := LowerCase(fileName);
  // 本体
  if lower = 'fallout4.esm' then
  begin
    Result := True;
    Exit;
  end;

  // DLC 系（"dlc" で始まるものをまとめて許可）
  if Pos('dlc', lower) = 1 then
  begin
    Result := True;
    Exit;
  end;

  // Creation Club
  if (Pos('cc', lower) = 1) or (Pos('creations', lower) = 1) then
  begin
    Result := True;
    Exit;
  end;

  Result := False;
end;

// 武器関連レベルドリストの判定（除外条件含む）
function IsWeaponRelatedLL(rec: IInterface): boolean;
var
  editorID: string;
begin
  Result := False;

  // EDID は Lib の安全関数で取得
  editorID := GetEditorIdSafe(rec);
  if editorID = '' then Exit;

  // 除外キーワード
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
     (Pos('Vendor', editorID) > 0) then
    Exit;

  // 武器関連キーワード（見つかったら True）
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
    Result := True;
end;

// ========== AP_Run_ExportWeaponLeveledLists 実装 ==========
function AP_Run_ExportWeaponLeveledLists: Integer;
var
  csvLines: TStringList;
  processedCount: Integer;
  i, j: Integer;
  aFile: IwbFile;
  Group, Rec: IInterface;
  EditorID, formIDStr, fileName, csvFilePath: string;
begin
  Result := 0;
  csvLines := TStringList.Create;
  try
    csvLines.Add('EditorID,FormID,SourceFile');
    processedCount := 0;

    for i := 0 to FileCount - 1 do
    begin
      aFile := FileByIndex(i);
      fileName := GetFileName(aFile);

      if not IsTargetFileLL(fileName) then
        Continue;

      if not HasGroup(aFile, 'LVLI') then
        Continue;

      Group := GroupBySignature(aFile, 'LVLI');
      for j := 0 to ElementCount(Group) - 1 do
      begin
        Rec := ElementByIndex(Group, j);
        EditorID := GetEditorIdSafe(Rec);
        if EditorID = '' then
          Continue;

        if IsWeaponRelatedLL(Rec) then
        begin
          formIDStr := IntToHex(FixedFormID(Rec), 8);
          csvLines.Add(Format('"%s","%s","%s"', [EditorID, formIDStr, fileName]));
        end;
      end;

      Inc(processedCount);
    end;

    csvFilePath := ScriptsPath + 'WeaponLeveledLists_Export.csv';
    csvLines.SaveToFile(csvFilePath);
    LogSuccess(Format('CSV exported: %s (files processed: %d, rows: %d)', [
      csvFilePath, processedCount, csvLines.Count - 1]));
    LogComplete('Leveled list export');
  except
    on E: Exception do
    begin
      LogError('Failed to save WeaponLeveledLists_Export.csv: ' + E.Message);
      Result := 1;
    end;
  end;

  csvLines.Free;
end;

end.