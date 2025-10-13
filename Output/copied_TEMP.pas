
unit TEST_export_weapon_omod_only;

interface
uses xEditAPI, AutoPatcherCore;

implementation

function Initialize: integer;
begin
  Result := 0;
  // Early marker: ensure the test wrapper logs immediately when invoked
  AddMessage('[TEMP_WRAPPER_ENTER] test_export_weapon_omod_only Initialize start');
  AddMessage('[AutoPatcher-Test] Starting OMOD-only extraction');
  try
    if AP_Run_ExportWeaponAmmoDetails() <> 0 then
    begin
      LogError('AP_Run_ExportWeaponAmmoDetails returned non-zero');
      Result := 1;
    end
    else
    begin
      AddMessage('[AutoPatcher-Test] AP_Run_ExportWeaponAmmoDetails completed');
      LogComplete('AP_Run_ExportWeaponAmmoDetails (test)');
    end;
  except
    on E: Exception do
    begin
      LogError('Exception in test wrapper: ' + E.ClassName + ' ' + E.Message);
      Result := 1;
    end;
  end;
end;

end.
