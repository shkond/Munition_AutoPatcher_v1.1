unit ExportMunitionsAmmoIDs;

uses
  xEditAPI,
  Classes,
  SysUtils,
  StrUtils,
  Windows,
  'lib/AutoPatcherLib',
  AutoPatcherCore;

function Initialize: integer;
begin
  Result := 0; // xEditの契約上0で開始
end;

function Finalize: integer;
begin
  // 実処理をコアに委譲（中で LogComplete を出す）
  Result := AP_Run_ExportMunitionsAmmoIDs;
end;

end.