unit ExportWeaponLeveledListsToCSV;

interface
implementation
uses xEditAPI, Classes, SysUtils, StrUtils, Windows;

// 対象ファイルかどうかをチェック（Fallout4、DLC、CCコンテンツのみ）
function IsTargetFile(fileName: string): boolean;
begin
  Result := 
    // Fallout4本体
    (fileName = 'Fallout4.esm') or
    // 主要DLC
    (fileName = 'DLCRobot.esm') or
    (fileName = 'DLCCoast.esm') or
    (fileName = 'DLCworkshop01.esm') or
    (fileName = 'DLCworkshop02.esm') or
    (fileName = 'DLCworkshop03.esm') or
    (fileName = 'DLCNukaWorld.esm') or
    // CCコンテンツ（パターンマッチ）
    (Pos('cc', LowerCase(fileName)) = 1) or
    (Pos('cc', LowerCase(fileName)) = 3) or // 例: "ccBGSFO4044-HellfirePowerArmor.esl"
    (Pos('creations', LowerCase(fileName)) = 1); // 新しいCCコンテンツ
end;

// 勢力タイプを判定
function GetFactionType(editorID: string): string;
begin
  if Pos('Gunner', editorID) > 0 then
    Result := 'Gunner'
  else if Pos('Institute', editorID) > 0 then
    Result := 'Institute'
  else if (Pos('Mutant', editorID) > 0) then
    Result := 'Mutant'
  else if Pos('Raider', editorID) > 0 then
    Result := 'Raider'
  else
    Result := 'Other';
end;

// レベルドリストが他のLVLIを含むかチェック
function ContainsLeveledList(rec: IInterface): boolean;
var
  entries, entry, lvlo: IInterface;
  i: integer;
  refSig: string;
begin
  Result := false;
  entries := ElementByName(rec, 'Leveled List Entries');
  if not Assigned(entries) then Exit;

  for i := 0 to ElementCount(entries) - 1 do
  begin
    entry := ElementByIndex(entries, i);
    lvlo := ElementByName(entry, 'LVLO - Base Data');

    if Assigned(lvlo) then
    begin
      refSig := Signature(LinksTo(ElementByName(lvlo, 'Reference')));
      if refSig = 'LVLI' then
      begin
        Result := true;
        Exit;
      end;
    end;
  end;
end;

// 武器関連リストかチェック（VRWorkshopShared除外）
function IsWeaponRelated(rec: IInterface): boolean;
var
  editorID: string;
begin
  Result := false;
  editorID := GetElementEditValues(rec, 'EDID');

  // 除外条件
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
  begin
    Exit;
  end;

  // 武器関連キーワード
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
  begin
    Result := true;
  end;
end;

function Initialize: integer;
var
  i, j: integer;
  aFile: IwbFile;
  Group, Rec: IInterface;
  EditorID, formIDStr, factionType, listType, fileName: string;
  csvLines: TStringList;
  csvFilePath: string;
  containsLL, isWeapon: boolean;
  processedCount: integer;
begin
  AddMessage('Fallout4本体、DLC、CCコンテンツの武器レベルドリストをCSV形式でエクスポート開始...');
  processedCount := 0;

  // CSVファイルパスを設定（FO4Editスクリプトフォルダに出力）
  csvFilePath := ScriptsPath + 'WeaponLeveledLists_Export.csv';
  csvLines := TStringList.Create;

  try
    // CSVヘッダーを追加
    csvLines.Add('EditorID,FormID,SourceFile');

    // 全てのプラグインファイルを処理
    for i := 0 to FileCount - 1 do
    begin
      aFile := FileByIndex(i);
      fileName := GetFileName(aFile);
      
      // 対象ファイルのみ処理（Fallout4、DLC、CCコンテンツ）
      if not IsTargetFile(fileName) then
      begin
        AddMessage('スキップ: ' + fileName);
        Continue;
      end;
      
      AddMessage('処理中: ' + fileName);
      processedCount := processedCount + 1;

      Group := GroupBySignature(aFile, 'LVLI');
      if not Assigned(Group) then Continue;

      // 各レベルドリストを処理
      for j := 0 to ElementCount(Group) - 1 do
      begin
        Rec := ElementByIndex(Group, j);
        EditorID := GetElementEditValues(Rec, 'EDID');

        if EditorID = '' then Continue;

        // VRWorkshopSharedを除外
        if (Pos('VRWorkshopShared', EditorID) > 0) then
          Continue;

        // 勢力関連かつ武器関連かチェック
        if ((Pos('Gunner', EditorID) > 0) or
           (Pos('Institute', EditorID) > 0) or
           (Pos('Mutant', EditorID) > 0) or
           (Pos('Raider', EditorID) > 0)) then
        begin
          isWeapon := IsWeaponRelated(Rec);
          containsLL := ContainsLeveledList(Rec);

          if isWeapon then
          begin
            formIDStr := IntToHex(FixedFormID(Rec), 8);
            factionType := GetFactionType(EditorID);

            // リストタイプを判定
            if containsLL then
              listType := 'MidLevel'
            else
              listType := 'BottomLevel';

            // CSV行を追加（ソースファイル情報も含める）
            csvLines.Add(Format('"%s","%s","%s"', [EditorID, formIDStr, fileName]));
          end;
        end;
      end;
    end;

    // CSVファイルを保存
    csvLines.SaveToFile(csvFilePath);
    AddMessage('');
    AddMessage('=== エクスポート完了 ===');
    AddMessage('CSVファイル: ' + csvFilePath);
    AddMessage('処理したファイル数: ' + IntToStr(processedCount));
    AddMessage('抽出されたレベルドリスト数: ' + IntToStr(csvLines.Count - 1));

  except
    on E: Exception do
    begin
      AddMessage('エラーが発生しました: ' + E.Message);
      Result := 1;
    end;
  end;

  // リソースの解放
  csvLines.Free;
  Result := 0;
end;

end.