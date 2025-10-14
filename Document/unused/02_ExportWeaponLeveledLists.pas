unit ExportWeaponLeveledListsToCSV;

interface
implementation
uses xEditAPI, Classes, SysUtils, StrUtils, Windows,
  AutoPatcherCore;

// 対象ファイルか判定（Fallout4本体+DLC+CC）
function IsTargetFile(fileName: string): boolean;
begin
  Result :=
    (fileName = 'Fallout4.esm') or
    (fileName = 'DLCRobot.esm') or
    (fileName = 'DLCCoast.esm') or
    (fileName = 'DLCworkshop01.esm') or
    (fileName = 'DLCworkshop02.esm') or
    (fileName = 'DLCworkshop03.esm') or
    (fileName = 'DLCNukaWorld.esm') or
    (Pos('cc', LowerCase(fileName)) = 1) or
    (Pos('cc', LowerCase(fileName)) = 3) or
    (Pos('creations', LowerCase(fileName)) = 1);
end;

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