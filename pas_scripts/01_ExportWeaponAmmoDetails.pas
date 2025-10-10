unit ExportWeaponAmmoDetails;

interface
implementation

uses
  xEditAPI,
  Classes,
  SysUtils,
  StrUtils,
  Windows,
  'lib/AutoPatcherLib',
  AutoPatcherCore;

function Initialize: Integer;
begin
  Result := AP_Run_ExportWeaponAmmoDetails;
end;

end.