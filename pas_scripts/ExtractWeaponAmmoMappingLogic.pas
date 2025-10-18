unit ExtractWeaponAmmoMappingLogic;

interface

uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows,
  AutoPatcherLib;

function AP_Run_ExtractWeaponAmmoMapping: Integer;

implementation

// ========== AP_Run_ExtractWeaponAmmoMapping 実装 ==========
function AP_Run_ExtractWeaponAmmoMapping: Integer;
var
  // Local state variables
  jsonOutput: TStringList;
  uniqueAmmoOutput: TStringList;
  processedWeapons: TStringList;
  masterFilesToExclude: TStringList;
  debugLog: TStringList;
  // Loop variables
  i, j: Integer;
  aFile: IwbFile;
  weapGroup, rec, winningRec, ammoRec, ammoLinkElement: IInterface;
  pluginName, weapEditorID, weapFullName: string;
  ammoFormIDInt: Cardinal;
  ammoFormIDHex, ammoPlugin, ammoEditorID: string;
  jsonEntry: string;
  // Output variables
  outputDir, jsonFilePath, iniFilePath: string;
  jsonFile: TStringList;
  debugFilePath: string;
  debugLogPath: string;
begin
  Result := 0;
  // Initialize local state
  jsonOutput := TStringList.Create;
  uniqueAmmoOutput := TStringList.Create;
  processedWeapons := TStringList.Create;
  masterFilesToExclude := CreateMasterExclusionList; // From AutoPatcherLib
  debugLog := TStringList.Create;
  // Also use a file in the working dir that Orchestrator already collects
  // (manual_debug_log.txt) so we can trace progress when MO2 redirects logs.
  try
    debugLog.Add('[EXTRACT] Starting AP_Run_ExtractWeaponAmmoMapping');
    try AddMessage('[DEBUG] AP_Run_ExtractWeaponAmmoMapping: entry'); except end;
    // prefer writing to the project's Output directory so Orchestrator can collect reliably
    try
      debugLog.SaveToFile(GetOutputDirectory + 'manual_debug_log.txt');
    except
      // fallback to current dir if GetOutputDirectory isn't available yet
      try
        debugLog.SaveToFile('manual_debug_log.txt');
      except
      end;
    end;
  except
  end;

  try
    // Early debug: record entry to file so we can detect early crashes
    try
      debugLog.Add('Entered AP_Run_ExtractWeaponAmmoMapping at ' + DateTimeToStr(Now));
      try
        GetOutputDirectory; // ensure function available
        debugLog.SaveToFile(GetOutputDirectory + 'ap_extract_entry.txt');
      except
      end;
    except
    end;
    // Process all files (equivalent to iterating through ScriptProcessElements = [etFile])
    debugLog.Add('Starting file loop, FileCount=' + IntToStr(FileCount));
    try AddMessage('[DEBUG] AP_Run_ExtractWeaponAmmoMapping: Starting file loop, FileCount=' + IntToStr(FileCount)); except end;
    // ensure we have a stable path to write per-iteration debug info
    debugLogPath := GetOutputDirectory + 'manual_debug_log.txt';
    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      pluginName := GetFileName(aFile);

      debugLog.Add('Processing plugin: ' + pluginName);
      try
        try AddMessage('[DEBUG] Processing plugin: ' + pluginName); except end;
        debugLog.SaveToFile(debugLogPath);
      except
        try debugLog.SaveToFile('manual_debug_log.txt'); except end;
      end;

      if IsMasterFileExcluded(pluginName, masterFilesToExclude) then begin
        debugLog.Add('Skipping excluded master: ' + pluginName);
        try debugLog.SaveToFile('manual_debug_log.txt'); except end;
        Continue;
      end;
      if IsCreationClubContent(pluginName) then begin
        debugLog.Add('Skipping creation club content: ' + pluginName);
        try debugLog.SaveToFile('manual_debug_log.txt'); except end;
        Continue;
      end;

      if not HasGroup(aFile, 'WEAP') then Continue;

      weapGroup := GroupBySignature(aFile, 'WEAP');
      for j := 0 to Pred(ElementCount(weapGroup)) do begin

        rec := ElementByIndex(weapGroup, j);
        winningRec := WinningOverride(rec);
        weapEditorID := EditorID(rec);
        try
          debugLog.Add('Found weapon: ' + weapEditorID);
          try AddMessage('[DEBUG] Found weapon: ' + weapEditorID + ' (plugin=' + pluginName + ')'); except end;
          debugLog.SaveToFile(debugLogPath);
        except
        end;

        if processedWeapons.IndexOf(weapEditorID) > -1 then Continue;
        processedWeapons.Add(weapEditorID);

        weapFullName := GetElementEditValues(winningRec, 'FULL');
        if weapFullName = '' then weapFullName := weapEditorID;

        ammoFormIDInt := GetElementNativeValues(winningRec, 'DNAM\AMMO');
        if ammoFormIDInt = 0 then begin
          try
            debugLog.Add('Weapon ' + weapEditorID + ' has no ammo (native=0)');
            try AddMessage('[DEBUG] Weapon ' + weapEditorID + ' has no ammo (native=0)'); except end;
            debugLog.SaveToFile(debugLogPath);
          except
          end;
          Continue;
        end;

        debugLog.Add(Format('Weapon %s -> ammo native=%d', [weapEditorID, ammoFormIDInt]));
        try AddMessage('[DEBUG] Weapon ' + weapEditorID + ' -> ammo native=' + IntToStr(ammoFormIDInt)); except end;

        ammoFormIDHex := FormIDToHex(ammoFormIDInt);
        ammoLinkElement := ElementByPath(winningRec, 'DNAM\AMMO');
        ammoRec := nil;
        if Assigned(ammoLinkElement) then ammoRec := LinksTo(ammoLinkElement);

        if Assigned(ammoRec) then begin
          ammoPlugin := GetFileName(GetFile(ammoRec));
          ammoEditorID := EditorID(ammoRec);

          try
            debugLog.Add(Format('Weapon %s -> Ammo %s in %s', [weapEditorID, ammoEditorID, ammoPlugin]));
            try AddMessage('[DEBUG] Weapon ' + weapEditorID + ' -> Ammo ' + ammoEditorID + ' in ' + ammoPlugin); except end;
            debugLog.SaveToFile(debugLogPath);
          except
            try debugLog.SaveToFile('manual_debug_log.txt'); except end;
          end;

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
    end; // End of file loop

    // Write debug log to output dir
    try
      outputDir := GetOutputDirectory;
      debugFilePath := outputDir + 'extract_debug_' + IntToStr(Trunc(Now)) + '.txt';
      debugLog.SaveToFile(debugFilePath);
      try AddMessage('[DEBUG] Saved debug log to ' + debugFilePath); except end;
    except
      // ignore
    end;

    // Finalize (save files)
    outputDir := GetOutputDirectory;

    // JSON保存
    jsonFilePath := outputDir + 'weapon_ammo_map.json';
    jsonFile := TStringList.Create;
    try
      BeginJSONArray(jsonFile);
      if jsonOutput.Count > 0 then begin
        for i := 0 to jsonOutput.Count - 2 do
          AddJSONArrayItem(jsonFile, jsonOutput[i], False);
        AddJSONArrayItem(jsonFile, jsonOutput[jsonOutput.Count - 1], True);
      end;
      EndJSONArray(jsonFile);
  SaveAndCleanJSONToFile(jsonFile, jsonFilePath, jsonOutput.Count);
      try AddMessage('[DEBUG] Saved JSON to ' + jsonFilePath); except end;
    finally
      jsonFile.Free;
    end;

    // INI保存
    iniFilePath := outputDir + 'unique_ammo_for_mapping.ini';
    uniqueAmmoOutput.Insert(0, '[UnmappedAmmo]');
    uniqueAmmoOutput.Sort;
    SaveINIToFile(uniqueAmmoOutput, iniFilePath, uniqueAmmoOutput.Count - 1);
  try AddMessage('[DEBUG] Saved INI to ' + iniFilePath); except end;

    LogComplete('Weapon and ammo mapping extraction');
  except
    on E: Exception do begin
      // Log and write exception to a debug file for offline inspection
      LogError(E.Message);
      try
        debugLog.Add('Exception: ' + E.ClassName + ' ' + E.Message);
        debugLog.SaveToFile(GetOutputDirectory + 'ap_extract_exception.txt');
      except
      end;
      Result := 1;
    end;
  finally
    // Free local state
    if Assigned(debugLog) then debugLog.Free;
    jsonOutput.Free;
    uniqueAmmoOutput.Free;
    processedWeapons.Free;
    masterFilesToExclude.Free;
  end;
end;

end.