unit ExtractWeaponAmmoMapping;

uses
  'lib/mteBase',
  'lib/mteElements',
  'lib/mteFiles',
  'lib/mteRecords',
  'lib/mteAutoPatcher',  // ★★★ 追加 ★★★
  StrUtils;

var
  jsonOutput: TStringList;
  uniqueAmmoOutput: TStringList;
  masterFilesToExclude: TStringList;
  processedWeapons: TStringList;

function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  uniqueAmmoOutput := TStringList.Create;
  processedWeapons := TStringList.Create;
  
  // ★★★ 修正: ライブラリ関数を使用 ★★★
  masterFilesToExclude := CreateMasterExclusionList;
  
  ScriptProcessElements := [etFile];
  Result := 0;
end;

function Process(e: IInterface): integer;
var
  i: integer;
  weapGroup, rec, winningRec, ammoRec, ammoLinkElement: IInterface;
  pluginName, weapEditorID, weapFullName: string;
  ammoFormIDInt: Cardinal;
  ammoFormIDHex, ammoPlugin, ammoEditorID: string;
  jsonEntry: string;
begin
  pluginName := GetFileName(e);

  // ★★★ 修正: ライブラリ関数を使用 ★★★
  if IsMasterFileExcluded(pluginName, masterFilesToExclude) then Exit;
  if IsCreationClubContent(pluginName) then Exit;

  if not HasGroup(e, 'WEAP') then Exit;

  weapGroup := GroupBySignature(e, 'WEAP');
  for i := 0 to Pred(ElementCount(weapGroup)) do begin
    rec := ElementByIndex(weapGroup, i);
    winningRec := WinningOverride(rec);
    weapEditorID := EditorID(rec);
    
    if processedWeapons.IndexOf(weapEditorID) > -1 then Continue;
    processedWeapons.Add(weapEditorID);

    weapFullName := GetElementEditValues(winningRec, 'FULL');
    if weapFullName = '' then weapFullName := weapEditorID;

    ammoFormIDInt := GetElementNativeValues(winningRec, 'DNAM\AMMO');
    if ammoFormIDInt = 0 then Continue;
    
    // ★★★ 修正: ライブラリ関数を使用 ★★★
    ammoFormIDHex := FormIDToHex(ammoFormIDInt);
    ammoLinkElement := ElementByPath(winningRec, 'DNAM\AMMO');
    ammoRec := nil;
    if Assigned(ammoLinkElement) then ammoRec := LinksTo(ammoLinkElement);

    if Assigned(ammoRec) then begin
      ammoPlugin := GetFileName(GetFile(ammoRec));
      ammoEditorID := EditorID(ammoRec);

      if uniqueAmmoOutput.IndexOfName(ammoFormIDHex) = -1 then
        uniqueAmmoOutput.Add(Format('%s=%s|%s', [ammoFormIDHex, ammoPlugin, ammoEditorID]));

      jsonEntry := Format('    { "editor_id": "%s", "full_name": "%s", "ammo_form_id": "%s" }', [
        weapEditorID,
        weapFullName,
        ammoFormIDHex
      ]);
      jsonOutput.Add(jsonEntry);
    end;
  end;
  Result := 0;
end;

function Finalize: integer;
var
  outputDir, jsonFilePath, iniFilePath: string;
  i: integer;
  jsonFile: TStringList;
begin
  // ★★★ 修正: ライブラリ関数を使用 ★★★
  outputDir := GetOutputDirectory;

  // --- JSONファイルの保存 ---
  jsonFilePath := outputDir + 'weapon_ammo_map.json';
  jsonFile := TStringList.Create;
  try
    BeginJSONArray(jsonFile);  // ★★★ ライブラリ関数 ★★★
    
    if jsonOutput.Count > 0 then begin
      for i := 0 to jsonOutput.Count - 2 do
        AddJSONArrayItem(jsonFile, jsonOutput[i], False);  // ★★★ ライブラリ関数 ★★★
      AddJSONArrayItem(jsonFile, jsonOutput[jsonOutput.Count - 1], True);  // ★★★ ライブラリ関数 ★★★
    end;
    
    EndJSONArray(jsonFile);  // ★★★ ライブラリ関数 ★★★
    
    SaveJSONToFile(jsonFile, jsonFilePath, jsonOutput.Count);  // ★★★ ライブラリ関数 ★★★
  finally
    jsonFile.Free;
  end;

  // --- INIファイルの保存 ---
  iniFilePath := outputDir + 'unique_ammo_for_mapping.ini';
  uniqueAmmoOutput.Insert(0, '[UnmappedAmmo]');
  uniqueAmmoOutput.Sort;
  SaveINIToFile(uniqueAmmoOutput, iniFilePath, uniqueAmmoOutput.Count - 1);  // ★★★ ライブラリ関数 ★★★

  LogComplete('Weapon and ammo mapping extraction');  // ★★★ ライブラリ関数 ★★★

  jsonOutput.Free;
  uniqueAmmoOutput.Free;
  processedWeapons.Free;
  masterFilesToExclude.Free;
  Result := 0;
end;

end.
