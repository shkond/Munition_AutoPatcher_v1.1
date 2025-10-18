unit AutoPatcherLib;

interface
uses
  xEditAPI, Classes, SysUtils;

function EnsureTrailingSlash(const s: string): string;
function GetOutputDirectory: string;
function GetEditorIdSafe(rec: IInterface): string;
function GetFullFormID(rec: IInterface): string;

function SaveAndCleanJSONToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;
function SaveINIToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;

procedure LogDebug(const msg: string);
procedure LogError(const msg: string);
procedure LogSuccess(const msg: string);
procedure LogComplete(const msg: string);

implementation

function EnsureTrailingSlash(const s: string): string;
begin
  if (s <> '') and (s[Length(s)] <> '\') then
    Result := s + '\'
  else
    Result := s;
end;

function GetOutputDirectory: string;
begin
  // Return a sane default. Adjust to your environment if needed.
  try
    if DirectoryExists('E:\fo4mod\xedit\Edit Scripts\Output') then
      Result := 'E:\fo4mod\xedit\Edit Scripts\Output\'
    else
      Result := 'E:\Munition_AutoPatcher_v1.1\Output\';
  except
    Result := 'E:\Munition_AutoPatcher_v1.1\Output\';
  end;
end;

function GetEditorIdSafe(rec: IInterface): string;
begin
  Result := '';
  if not Assigned(rec) then
    Exit;
  try
    Result := EditorID(rec);
  except
    try
      if ElementExists(rec, 'EDID') then
        Result := GetElementEditValues(rec, 'EDID');
      else
        Result := '';
    except
      Result := '';
    end;
  end;
end;

function GetFullFormID(rec: IInterface): string;
var
  f: IInterface;
  loadOrder: Integer;
  rawFormID: Cardinal;
begin
  Result := '';
  if not Assigned(rec) then
    Exit;

  f := GetFile(rec);

  if Assigned(f) then
    loadOrder := GetLoadOrder(f)
  else
    loadOrder := 0;

  rawFormID := GetElementNativeValues(rec, 'Record Header\FormID');

  if loadOrder < 0 then
    loadOrder := 0;

  loadOrder := loadOrder and $FF;
  rawFormID := rawFormID and $FFFFFF;

  Result := UpperCase(IntToHex(loadOrder, 2) + IntToHex(rawFormID, 6));
end;

function SaveAndCleanJSONToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;
begin
  Result := False;
  if not Assigned(sl) then
    Exit;
  try
    ForceDirectories(ExtractFilePath(path));
  except
    LogError('Failed to create directory for JSON file' + path);
  end;
  try
    sl.SaveToFile(path);
    LogSuccess('Saved JSON file' + path);
    Result := True;
  except
    LogError('Failed to save JSON file' + path);
    Result := False;
  end;
end;

function SaveINIToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;
begin
  Result := False; // It is good practice to initialize the result
  try
    ForceDirectories(ExtractFilePath(path));
  except
    LogError('Failed to create directory for INI file: ' + path);
    Exit; // Exit if we can't create the directory
  end;
  try
    sl.SaveToFile(path);
    LogSuccess('Saved INI file: ' + path);
    Result := True;
  except
    LogError('Failed to save INI file: ' + path);
    Result := False;
  end;
end;

procedure LogDebug(const msg: string);
begin
  try
    AddMessage('[DEBUG] ' + msg);
  except
    // ignore
  end;
end;

procedure LogError(const msg: string);
begin
  try
    AddMessage('[ERROR] ' + msg);
  except
    // ignore
  end;
end;

procedure LogSuccess(const msg: string);
begin
  try
    AddMessage('[SUCCESS] ' + msg);
  except
    // ignore
  end;
end;

procedure LogComplete(const msg: string);
begin
  try
    AddMessage('[COMPLETE] ' + msg);
  except
    // ignore
  end;
end;

end.