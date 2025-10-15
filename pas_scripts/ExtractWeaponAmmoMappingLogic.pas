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
// Minimal robust logger: write to a per-script log file if possible and always AddMessage
procedure LogMsg(const s: string);
  jsonOutput: TStringList;
  uniqueAmmoOutput: TStringList;
  processedWeapons: TStringList;
  masterFilesToExclude: TStringList;
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
begin
  Result := 0;
  // Log start for debugging
  try
    LogMsg('AP_Run_ExtractWeaponAmmoMapping start');
  except
    // ignore logging failures
  end;
  // Initialize local state
  jsonOutput := TStringList.Create;
  uniqueAmmoOutput := TStringList.Create;
  processedWeapons := TStringList.Create;
  masterFilesToExclude := CreateMasterExclusionList; // From AutoPatcherLib

  try
    // Process all files (equivalent to iterating through ScriptProcessElements = [etFile])
    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      pluginName := GetFileName(aFile);

      if IsMasterFileExcluded(pluginName, masterFilesToExclude) then Continue;
      if IsCreationClubContent(pluginName) then Continue;

      if not HasGroup(aFile, 'WEAP') then Continue;

      weapGroup := GroupBySignature(aFile, 'WEAP');
      for j := 0 to Pred(ElementCount(weapGroup)) do begin

        rec := ElementByIndex(weapGroup, j);
        winningRec := WinningOverride(rec);
        weapEditorID := EditorID(rec);

        if processedWeapons.IndexOf(weapEditorID) > -1 then Continue;
        processedWeapons.Add(weapEditorID);

        weapFullName := GetElementEditValues(winningRec, 'FULL');
        if weapFullName = '' then weapFullName := weapEditorID;

        ammoFormIDInt := GetElementNativeValues(winningRec, 'DNAM\AMMO');
        if ammoFormIDInt = 0 then Continue;

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
    end; // End of file loop

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
      SaveAndCleanJSONToFile(jsonFile, jsonFilePath, jsonOutput.Count, True);
    finally
      jsonFile.Free;
    end;

    // INI保存
    iniFilePath := outputDir + 'unique_ammo_for_mapping.ini';
    uniqueAmmoOutput.Insert(0, '[UnmappedAmmo]');
    uniqueAmmoOutput.Sort;
    SaveINIToFile(uniqueAmmoOutput, iniFilePath, uniqueAmmoOutput.Count - 1);

    LogComplete('Weapon and ammo mapping extraction');
  except
    on E: Exception do begin
      try
        LogMsg('ERROR: ' + E.ClassName + ': ' + E.Message);
      except
        // ignore logging failures
      end;
      Result := 1;
    end;
  finally
    // Free local state
    jsonOutput.Free;
    uniqueAmmoOutput.Free;
    processedWeapons.Free;
    masterFilesToExclude.Free;
  end;
end;

end.