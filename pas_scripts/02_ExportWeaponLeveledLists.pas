unit ExportWeaponLeveledListsToCSV;

interface
implementation
uses xEditAPI, Classes, SysUtils, StrUtils, Windows;

// 対象ファイルか判定（Fallout4本体+DLC+CC）
function IsTargetFile(fileName: string): boolean;
begin
  Result :=
    (fileName = 'Fallout4.esm') or
    (fileName = 'DLCRobot.esm') or
    (fileName = 'DLCCoast.esm') or
    (fileName = 'DLCworkshop01.esm') or
    (fileName = 'DLCworkshop02.esm') or
    (fileName = 'DLCworkshop03.esm') or
    (fileName = 'DLCNukaWorld.esm') or
    (Pos('cc', LowerCase(fileName)) = 1) or
    (Pos('cc', LowerCase(fileName)) = 3) or
    (Pos('creations', LowerCase(fileName)) = 1);
end;

function Initialize: integer;
var
  i, j: integer;
  aFile: IwbFile;
  Group, Rec: IInterface;
  EditorID, formIDStr, fileName: string;
  csvLines: TStringList;
  csvFilePath: string;
begin
  AddMessage('LVLI を CSV 出力: WeaponLeveledLists_Export.csv');
  csvFilePath := ScriptsPath + 'WeaponLeveledLists_Export.csv';
  csvLines := TStringList.Create;

  try
    csvLines.Add('EditorID,FormID,Faction,ListType,SourceFile');

    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      fileName := GetFileName(aFile);
      if not IsTargetFile(fileName) then Continue;

      Group := GroupBySignature(aFile, 'LVLI');
      if not Assigned(Group) then Continue;

      for j := 0 to ElementCount(Group) - 1 do begin
        Rec := ElementByIndex(Group, j);
        EditorID := GetElementEditValues(Rec, 'EDID');
        if EditorID = '' then Continue;

        formIDStr := IntToHex(FixedFormID(Rec), 8);
        // Faction/ListType は最低限空文字で出力（互換のためカラム維持）
        csvLines.Add(Format('"%s","%s","%s","%s","%s"',
          [EditorID, formIDStr, '', '', fileName]));
      end;
    end;

    csvLines.SaveToFile(csvFilePath);
    AddMessage('CSV: ' + csvFilePath);
  except
    on E: Exception do begin
      AddMessage('エラー: ' + E.Message);
      Result := 1;
    end;
  end;

  csvLines.Free;
  Result := 0;
end;

end.