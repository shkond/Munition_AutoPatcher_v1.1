unit compile_check;

uses
  'lib/mteBase',
  'lib/mteTypes',
  'lib/mteElements',
  'lib/mteFiles',
  'lib/mteRecords',
  'lib/mteSystem',
  'lib/mteGUI';

function Initialize: integer;
begin
  AddMessage('[COMPILE_CHECK] Success');
  Result := 0;
end;

end.