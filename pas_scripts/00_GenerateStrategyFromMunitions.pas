unit GenerateStrategyFromMunitions;

interface
implementation
uses xEditAPI, Classes, SysUtils, StrUtils, Windows,
  AutoPatcherCore;

function Initialize: integer;
begin
  Result := AP_Run_GenerateStrategyFromMunitions;
end;

end.