unit AutoPatcherLib;

interface
uses
  xEditAPI, Classes, SysUtils;

function EnsureTrailingSlash(s: string): string;
function GetOutputDirectory: string;
function GetEditorIdSafe(rec: IInterface): string;
function GetFullFormID(rec: IInterface): string;

function SaveAndCleanJSONToFile(sl: TStringList; path: string; recordCount: Integer): Boolean;
function SaveINIToFile(sl: TStringList; path: string; recordCount: Integer): Boolean;

// 新・内部実装（予約語衝突しにくい短い名前）
procedure LogDbg(msg: string);
procedure LogErrMsg(msg: string);
procedure LogOk(msg: string);
procedure LogDone(msg: string);

// 旧・互換API（他ファイルで使用中の名前）
procedure LogDebug(msg: string);
procedure LogError(msg: string);
procedure LogSuccess(msg: string);
procedure LogComplete(msg: string);
procedure LogWarning(msg: string);
procedure LogInfo(msg: string);

implementation

function EnsureTrailingSlash(s: string): string;
begin
  if (s <> '') and (s[Length(s)] <> '\') then
  begin
    Result := s + '\';
  end
  else
  begin
    Result := s;
  end;
end;

function SafeForceDirectories(Dir: string): Boolean;
var
  i: Integer;
  sub: string;
begin
  Result := True;
  if Dir = '' then Exit;

  Dir := EnsureTrailingSlash(Dir);

  sub := '';
  for i := 1 to Length(Dir) do
  begin
    if Dir[i] = '\' then
    begin
      if (sub <> '') and not DirectoryExists(sub) then
      begin
        if not CreateDir(sub) then
        begin
          Result := False;
          Exit;
        end;
      end;
    end;
    sub := sub + Dir[i];
  end;

  if (sub <> '') and not DirectoryExists(sub) then
  begin
    Result := CreateDir(sub);
  end;
end;

function GetOutputDirectory: string;
var
  a, b: string;
begin
  a := 'E:\fo4mod\xedit\Edit Scripts\Output\';
  b := 'E:\Munition_AutoPatcher_v1.1\Output\';

  if DirectoryExists(a) then
    Result := EnsureTrailingSlash(a)
  else
    Result := EnsureTrailingSlash(b);

  if (Result <> '') and not DirectoryExists(Result) then
  begin
    if not SafeForceDirectories(Result) then
      LogErrMsg('Failed to ensure output directory exists: ' + Result);
  end;
end;

function GetEditorIdSafe(rec: IInterface): string;
var
  ed: IInterface;
begin
  Result := '';
  if not Assigned(rec) then Exit;

  ed := ElementByPath(rec, 'EDID - Editor ID');
  if Assigned(ed) then
    Result := GetEditValue(ed)
  else
    Result := '';
end;

function GetFullFormID(rec: IInterface): string;
var
  f: IInterface;
  loadOrder: Integer;
  rawFormID: Integer;
begin
  Result := '';
  if not Assigned(rec) then Exit;

  f := GetFile(rec);
  if Assigned(f) then
    loadOrder := GetLoadOrder(f)
  else
    loadOrder := 0;

  if ElementExists(rec, 'Record Header\FormID') then
    rawFormID := GetElementNativeValues(rec, 'Record Header\FormID')
  else
    rawFormID := 0;

  if loadOrder < 0 then
    loadOrder := 0;

  // JvInterpreter 回避: ビット演算の代わりに mod でマスク
  loadOrder := loadOrder mod 256;         // $FF
  rawFormID := rawFormID mod 16777216;    // $00FFFFFF

  Result := IntToHex(loadOrder, 2) + IntToHex(rawFormID, 6);
end;

function SaveAndCleanJSONToFile(sl: TStringList; path: string; recordCount: Integer): Boolean;
var
  dir: string;
begin
  Result := False;
  if not Assigned(sl) then Exit;

  dir := ExtractFilePath(path);
  if (dir <> '') and not DirectoryExists(dir) then
    if not SafeForceDirectories(dir) then
      LogErrMsg('Failed to create directory for JSON file: ' + dir);

  sl.SaveToFile(path);
  LogOk('Saved JSON file: ' + path);
  Result := True;
end;

function SaveINIToFile(sl: TStringList; path: string; recordCount: Integer): Boolean;
var
  dir: string;
begin
  Result := False;
  if not Assigned(sl) then Exit;

  dir := ExtractFilePath(path);
  if (dir <> '') and not DirectoryExists(dir) then
  begin
    if not SafeForceDirectories(dir) then
    begin
      LogErrMsg('Failed to create directory for INI file: ' + dir);
      Exit;
    end;
  end;

  sl.SaveToFile(path);
  LogOk('Saved INI file: ' + path);
  Result := True;
end;

// ---- Logging (internal safe names) ----
procedure LogDbg(msg: string);
begin
  AddMessage('[DEBUG] ' + msg);
end;

procedure LogErrMsg(msg: string);
begin
  AddMessage('[ERROR] ' + msg);
end;

procedure LogOk(msg: string);
begin
  AddMessage('[SUCCESS] ' + msg);
end;

procedure LogDone(msg: string);
begin
  AddMessage('[COMPLETE] ' + msg);
end;

// ---- Backward-compatible wrappers ----
procedure LogDebug(msg: string); begin LogDbg(msg); end;
procedure LogError(msg: string); begin LogErrMsg(msg); end;
procedure LogSuccess(msg: string); begin LogOk(msg); end;
procedure LogComplete(msg: string); begin LogDone(msg); end;

procedure LogWarning(msg: string);
begin
  AddMessage('[WARN] ' + msg);
end;

procedure LogInfo(msg: string);
begin
  AddMessage('[INFO] ' + msg);
end;

end.