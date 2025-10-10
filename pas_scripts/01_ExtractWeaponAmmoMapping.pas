unit ExtractWeaponAmmoMapping;

uses
  'lib/mteBase',
  'lib/mteElements',
  'lib/mteFiles',
  'lib/mteRecords',
  'lib/AutoPatcherLib',
  AutoPatcherCore,
  StrUtils;

function Initialize: integer;
begin
  AP_Reset_ExtractWeaponAmmoMappingState;
  ScriptProcessElements := [etFile];
  Result := 0;
end;

function Process(e: IInterface): integer;
begin
  AP_OnFile_ExtractWeaponAmmoMapping(e);
  Result := 0;
end;

function Finalize: integer;
begin
  Result := AP_Finalize_ExtractWeaponAmmoMapping;
end;

end.
