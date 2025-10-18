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
  // Use AddMessage instead of ShowMessage to avoid modal UI and encoding issues
  AddMessage('[DEBUG] 00_RunAllExtractors.pas');
  Result := 0;
  success := True;
  debugLog := TStringList.Create;

  try
    // initial manual debug entry
    debugLog.Add('[Manual Log] Initialize function started.');
    try
      debugLog.SaveToFile(GetOutputDirectory + 'manual_debug_log.txt');
    except
    end;

    AddMessage('[AutoPatcher] All-in-one extraction process started.');

    // Step 1
    debugLog.Add('[Manual Log] Calling AP_Run_ExtractWeaponAmmoMapping...');
    try
      if AP_Run_ExtractWeaponAmmoMapping() <> 0 then
      begin
        LogError('Weapon and ammo mapping extraction failed.');
        success := False;
      end
      else
        debugLog.Add('[Manual Log] AP_Run_ExtractWeaponAmmoMapping finished.');
    except
      debugLog.Add('[EXCEPTION] AP_Run_ExtractWeaponAmmoMapping');
      success := False;
    end;

    // Step 2
    debugLog.Add('[Manual Log] Calling AP_Run_ExportWeaponAmmoDetails...');
    try
      if success and (AP_Run_ExportWeaponAmmoDetails() <> 0) then
      begin
        LogError('Weapon OMOD export failed.');
        success := False;
      end
      else
        debugLog.Add('[Manual Log] AP_Run_ExportWeaponAmmoDetails finished.');
    except
      debugLog.Add('[EXCEPTION] AP_Run_ExportWeaponAmmoDetails');
      success := False;
    end;

    // Step 3
    debugLog.Add('[Manual Log] Calling AP_Run_ExportWeaponLeveledLists...');
    try
      if success and (AP_Run_ExportWeaponLeveledLists() <> 0) then
      begin
        LogError('Leveled list export failed.');
        success := False;
      end
      else
        debugLog.Add('[Manual Log] AP_Run_ExportWeaponLeveledLists finished.');
    except
      debugLog.Add('[EXCEPTION] AP_Run_ExportWeaponLeveledLists');
      success := False;
    end;

    // Step 4
    debugLog.Add('[Manual Log] Calling AP_Run_ExportMunitionsAmmoIDs...');
    try
      if success and (AP_Run_ExportMunitionsAmmoIDs() <> 0) then
      begin
        LogError('Munitions ammo ID export failed.');
        success := False;
      end
      else
        debugLog.Add('[Manual Log] AP_Run_ExportMunitionsAmmoIDs finished.');
    except
      debugLog.Add('[EXCEPTION] AP_Run_ExportMunitionsAmmoIDs');
      success := False;
    end;

    // Final
    if success then
      LogComplete('All extractions')
    else
      LogError('One or more extraction steps failed. Check log for details.');

    try
      debugLog.SaveToFile(GetOutputDirectory + 'manual_debug_log.txt');
    except
    end;

  finally
    debugLog.Free;
  end;
end;

end.
