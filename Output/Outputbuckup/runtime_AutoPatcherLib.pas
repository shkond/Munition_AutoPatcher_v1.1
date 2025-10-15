{
  Minimal AutoPatcherLib
  This is a lightweight stub implementing a small subset of helper
  functions used by AutoPatcherCore so the scripts can run for
  inspection and iterative debugging. It's intentionally conservative
  (returns safe defaults) — replace with the canonical implementation
  when available.
}

unit AutoPatcherLib;

interface
uses xEditAPI, Classes, SysUtils;

function EnsureTrailingSlash(const s: string): string;
function GetOutputDirectory: string;
function GetEditorIdSafe(rec: IInterface): string;
function GetFullFormID(rec: IInterface): string;

function SaveAndCleanJSONToFile(sl: TStringList; const path: string; recordCount: Integer; pretty: Boolean): Boolean;
function SaveINIToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;

procedure LogDebug(const msg: string);
procedure LogError(const msg: string);
procedure LogSuccess(const msg: string);
procedure LogComplete(const msg: string);

implementation

function EnsureTrailingSlash(const s: string): string;
begin
  if (s <> '') and (s[Length(s)] <> '\\') then
    Result := s + '\\'
  else
    Result := s;
end;

// Returns the output directory used by scripts: <ProgramPath>\Edit Scripts\Output\
function GetOutputDirectory: string;
begin
  try
    Result := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\\Output\\';
  except
    // Fallback to a relative Output folder near ProgramPath
    Result := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\\Output\\';
  end;
end;

function GetEditorIdSafe(rec: IInterface): string;
begin
  Result := '';
  if not Assigned(rec) then Exit;
  try
    Result := EditorID(rec);
  except
    try
      if ElementExists(rec, 'EDID') then
        Result := GetElementEditValues(rec, 'EDID')
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
  if not Assigned(rec) then Exit;
  try
    // Attempt a robust FormID composition: LO (2 hex) + FormID (6 hex)
    f := GetFile(rec);
    if Assigned(f) then
      loadOrder := GetLoadOrder(f)
    else
      loadOrder := 0;
    // Try to read native FormID value from record header if available
    try
      rawFormID := GetElementNativeValues(rec, 'Record Header\FormID');
    except
      // Fallback: use integer part of FormID(rec) if available
      try
        rawFormID := Integer(FormID(rec));
      except
        rawFormID := 0;
      end;
    end;
    Result := UpperCase(Format('%2.2x%6.6x', [loadOrder, rawFormID]));
  except
    Result := '';
  end;
end;

function SaveAndCleanJSONToFile(sl: TStringList; const path: string; recordCount: Integer; pretty: Boolean): Boolean;
begin
  Result := False;
  try
    if not Assigned(sl) then begin
      LogError('SaveAndCleanJSONToFile: missing TStringList');
      Exit;
    end;
    // Ensure target dir exists
    try
      ForceDirectories(ExtractFilePath(path));
    except
    end;
    sl.SaveToFile(path);
    LogSuccess('Saved JSON: ' + path);
    Result := True;
  except
    on E: Exception do begin
      LogError('SaveAndCleanJSONToFile exception: ' + E.Message);
      Result := False;
    end;
  end;
end;

function SaveINIToFile(sl: TStringList; const path: string; recordCount: Integer): Boolean;
begin
  Result := False;
  try
    if not Assigned(sl) then begin
      LogError('SaveINIToFile: missing TStringList');
      Exit;
    end;
    try
      ForceDirectories(ExtractFilePath(path));
    except
    end;
    sl.SaveToFile(path);
    LogSuccess('Saved INI: ' + path);
    Result := True;
  except
    on E: Exception do begin
      LogError('SaveINIToFile exception: ' + E.Message);
      Result := False;
    end;
  end;
end;

procedure LogDebug(const msg: string);
begin
  try
    AddMessage('[DEBUG] ' + msg);
  except
  end;
end;

procedure LogError(const msg: string);
begin
  try
    AddMessage('[ERROR] ' + msg);
  except
  end;
end;

procedure LogSuccess(const msg: string);
begin
  try
    AddMessage('[SUCCESS] ' + msg);
  except
  end;
end;

procedure LogComplete(const msg: string);
begin
  try
    AddMessage('[COMPLETE] ' + msg);
  except
  end;
end;

end.
