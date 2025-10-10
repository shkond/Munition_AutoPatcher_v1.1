unit ExportWeaponLeveledListsSuggest;

interface
implementation
uses xEditAPI, Classes, SysUtils, StrUtils, Windows,
  AutoPatcherCore;

function Initialize: integer;
begin
  AP_Reset_ExportWeaponLeveledListsState;
  ScriptProcessElements := [etFile];
  Result := 0;
end;

function Process(e: IInterface): integer;
begin
  AP_OnFile_ExportWeaponLeveledLists(e);
  Result := 0;
end;

function Finalize: integer;
begin
  Result := AP_Finalize_ExportWeaponLeveledLists;
end;

end.