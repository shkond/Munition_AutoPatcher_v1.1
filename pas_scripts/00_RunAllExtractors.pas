// e:\Munition_AutoPatcher_v1.1\pas_scripts\00_RunAllExtractors.pas

unit RunAllExtractors;

interface
uses
  xEditAPI, AutoPatcherCore;

implementation

function Initialize: integer;
var
  success: Boolean;
  debugLog: TStringList;
begin
  Result := 0;
  success := True;
  debugLog := TStringList.Create;

  try
    debugLog.Add('[Manual Log] Initialize function started.');
    debugLog.SaveToFile('manual_debug_log.txt');

    AddMessage('[AutoPatcher] All-in-one extraction process started.');

    // --- ステップ1: 武器と弾薬のマッピングを抽出 ---
    debugLog.Add('[Manual Log] Calling AP_Run_ExtractWeaponAmmoMapping...');
    debugLog.SaveToFile('manual_debug_log.txt');
    if success and (AP_Run_ExtractWeaponAmmoMapping() <> 0) then
    begin
      LogError('Weapon and ammo mapping extraction failed.');
      success := False;
    end;
    debugLog.Add('[Manual Log] AP_Run_ExtractWeaponAmmoMapping finished.');
    debugLog.SaveToFile('manual_debug_log.txt');

    // --- ステップ2: 武器とOMOD情報をエクスポート ---
    debugLog.Add('[Manual Log] Calling AP_Run_ExportWeaponAmmoDetails...');
    debugLog.SaveToFile('manual_debug_log.txt');
    if success and (AP_Run_ExportWeaponAmmoDetails() <> 0) then
    begin
      LogError('Weapon OMOD export failed.');
      success := False;
    end;
    debugLog.Add('[Manual Log] AP_Run_ExportWeaponAmmoDetails finished.');
    debugLog.SaveToFile('manual_debug_log.txt');

    // --- ステップ2: レベルドリストをエクスポート ---
    debugLog.Add('[Manual Log] Calling AP_Run_ExportWeaponLeveledLists...');
    debugLog.SaveToFile('manual_debug_log.txt');
    if success and (AP_Run_ExportWeaponLeveledLists() <> 0) then
    begin
      LogError('Leveled list export failed.');
      success := False;
    end;
    debugLog.Add('[Manual Log] AP_Run_ExportWeaponLeveledLists finished.');
    debugLog.SaveToFile('manual_debug_log.txt');

    // --- ステップ3: Munitionsの弾薬IDをエクスポート ---
    debugLog.Add('[Manual Log] Calling AP_Run_ExportMunitionsAmmoIDs...');
    debugLog.SaveToFile('manual_debug_log.txt');
    if success and (AP_Run_ExportMunitionsAmmoIDs() <> 0) then
    begin
      LogError('Munitions ammo ID export failed.');
      success := False;
    end;
    debugLog.Add('[Manual Log] AP_Run_ExportMunitionsAmmoIDs finished.');
    debugLog.SaveToFile('manual_debug_log.txt');

    // --- 最終結果 ---
    if success then
    begin
      LogComplete('All extractions'); // 成功メッセージ
      Result := 0;
    end
    else
    begin
      LogError('One or more extraction steps failed. Check log for details.');
      Result := 1; // 失敗
    end;
    debugLog.Add('[Manual Log] Initialize function finished.');
    debugLog.SaveToFile('manual_debug_log.txt');

  finally
    debugLog.Free;
  end;
end;

end.
