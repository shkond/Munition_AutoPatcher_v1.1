unit ExtractWeaponAmmoMapping;

uses
  'lib/mteBase',
  'lib/mteElements',
  'lib/mteFiles',
  'lib/mteRecords',
  StrUtils;

var
  jsonOutput: TStringList;
  uniqueAmmoOutput: TStringList;
  masterFilesToExclude: TStringList;
  processedWeapons: TStringList;

// ★★★ 修正箇所: 正しいヘルパー関数に置き換え ★★★
// xEditの古いバージョンでも動作するヘルパー関数
function EnsureTrailingSlash(const s: string): string;
begin
  // ★★★ 修正点: s[Length(s)] を使わない、より互換性の高い方法に変更 ★★★
  if s = '' then
    Result := ''
  else if Copy(s, Length(s), 1) <> '\' then
    Result := s + '\'
  else
    Result := s;
end;

function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  uniqueAmmoOutput := TStringList.Create;
  masterFilesToExclude := TStringList.Create;
  processedWeapons := TStringList.Create;

  masterFilesToExclude.Add('Fallout4.esm');
  masterFilesToExclude.Add('DLCRobot.esm');
  masterFilesToExclude.Add('DLCworkshop01.esm');
  masterFilesToExclude.Add('DLCCoast.esm');
  masterFilesToExclude.Add('DLCworkshop02.esm');
  masterFilesToExclude.Add('DLCworkshop03.esm');
  masterFilesToExclude.Add('DLCNukaWorld.esm');
  masterFilesToExclude.Add('Munitions - An Ammo Expansion.esl');
  
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

  if masterFilesToExclude.IndexOf(pluginName) > -1 then Exit;
  // CCコンテンツ（Creation Club）をスキップ
  if LeftStr(LowerCase(pluginName), 2) = 'cc' then Exit;

  if not HasGroup(e, 'WEAP') then Exit;

  weapGroup := GroupBySignature(e, 'WEAP');
  for i := 0 to Pred(ElementCount(weapGroup)) do begin
    rec := ElementByIndex(weapGroup, i);
    winningRec := WinningOverride(rec);
    weapEditorID := EditorID(rec);
    
    // 処理済みの武器はスキップして効率化
    if processedWeapons.IndexOf(weapEditorID) > -1 then Continue;
    processedWeapons.Add(weapEditorID);

    weapFullName := GetElementEditValues(winningRec, 'FULL');
    if weapFullName = '' then weapFullName := weapEditorID;

    ammoFormIDInt := GetElementNativeValues(winningRec, 'DNAM\AMMO');
    if ammoFormIDInt = 0 then Continue;
    
    ammoFormIDHex := IntToHex(ammoFormIDInt, 8);
    ammoLinkElement := ElementByPath(winningRec, 'DNAM\AMMO');
    ammoRec := nil;
    if Assigned(ammoLinkElement) then ammoRec := LinksTo(ammoLinkElement);

    if Assigned(ammoRec) then begin
      ammoPlugin := GetFileName(GetFile(ammoRec));
      ammoEditorID := EditorID(ammoRec);

      // INI形式で出力するためのデータを準備 (FormID=Plugin|EditorID)
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
  outputDir, jsonFilePath, iniFilePath, temp: string;
  i: integer;
begin
  outputDir := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\Output\';
  ForceDirectories(outputDir);

  // --- JSONファイルの保存 (weapon_ammo_map.json) ---
  jsonFilePath := outputDir + 'weapon_ammo_map.json';
  temp := '[\n';
  if jsonOutput.Count > 0 then begin
    for i := 0 to jsonOutput.Count - 2 do
      temp := temp + jsonOutput[i] + ',\n';
    temp := temp + jsonOutput[jsonOutput.Count - 1];
  end;
  temp := temp + '\n]';
  jsonOutput.Text := temp;
  // ★★★ 修正点: WriteBOM を使わず、互換性の高い CP_UTF8 を使用して保存 ★★★
  jsonOutput.SaveToFile(jsonFilePath);
  AddMessage('[AutoPatcher] SUCCESS: Weapon data exported: ' + IntToStr(jsonOutput.Count) + ' records -> ' + jsonFilePath);

  // --- INIファイルの保存 (unique_ammo_for_mapping.ini) ---
  iniFilePath := outputDir + 'unique_ammo_for_mapping.ini';
  uniqueAmmoOutput.Insert(0, '[UnmappedAmmo]');
  uniqueAmmoOutput.Sort;
  // ★★★ 修正点: WriteBOM を使わず、互換性の高い CP_UTF8 を使用して保存 ★★★
  uniqueAmmoOutput.SaveToFile(iniFilePath);
  AddMessage('[AutoPatcher] SUCCESS: Unique ammo for mapping exported: ' + IntToStr(uniqueAmmoOutput.Count - 1) + ' records -> ' + iniFilePath);

  AddMessage('[AutoPatcher] Weapon and ammo mapping extraction complete.');

  jsonOutput.Free;
  uniqueAmmoOutput.Free;
  processedWeapons.Free;
  masterFilesToExclude.Free;
  Result := 0;
end;

end.
