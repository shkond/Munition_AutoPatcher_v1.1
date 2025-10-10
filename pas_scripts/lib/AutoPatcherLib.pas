{
  AutoPatcherLib
  
  AutoPatcher専用の共通関数ライブラリ
  重複コードの削減とメンテナンス性向上を目的とする
  
  主な機能:
  - パス操作ヘルパー
  - JSON出力ヘルパー
  - INI出力ヘルパー
  - ログ出力統一
}

unit AutoPatcherLib;

uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows;

interface
  // 成功メッセージのプレフィックス
  AP_LOG_PREFIX = '[AutoPatcher]';
  AP_SUCCESS_PREFIX = '[AutoPatcher] SUCCESS:';
  AP_ERROR_PREFIX = '[AutoPatcher] ERROR:';
  AP_WARNING_PREFIX = '[AutoPatcher] WARNING:';
  AP_INFO_PREFIX = '[AutoPatcher] INFO:';
  
  // 出力ディレクトリ
  AP_OUTPUT_SUBDIR = 'Edit Scripts\Output\';
const

{****************************************************}
{ パス操作ヘルパー
  - EnsureTrailingSlash
  - GetOutputDirectory
}
{****************************************************}

{
  EnsureTrailingSlash:
  文字列の末尾にバックスラッシュを確実に付与します。
  既に存在する場合は追加しません。
  
  Example usage:
  path := EnsureTrailingSlash('C:\Program Files');
  AddMessage(path); // 'C:\Program Files\'
}
function EnsureTrailingSlash(const s: string): string;
var
  lastChar: string;
begin
  if s = '' then begin
    Result := '';
    Exit;
  end;
  lastChar := Copy(s, Length(s), 1);
  if lastChar <> '\' then
    Result := s + '\'
  else
    Result := s;
end;

{
  GetOutputDirectory:
  xEdit の標準出力ディレクトリを取得します。
  ディレクトリが存在しない場合は作成します。
  
  Returns:
    string: 'ProgramPath\Edit Scripts\Output\'
    
  Example usage:
  outputDir := GetOutputDirectory;
  SaveStringToFile('test.txt', outputDir + 'test.txt');
}
function GetOutputDirectory: string;
begin
  Result := EnsureTrailingSlash(ProgramPath) + AP_OUTPUT_SUBDIR;
  ForceDirectories(Result);
end;

{****************************************************}
{ JSON出力ヘルパー
  - BeginJSONArray
  - AddJSONArrayItem
  - EndJSONArray
  - SaveJSONToFile
}
{****************************************************}

{
  BeginJSONArray:
  JSON配列の開始を TStringList に追加します。
  
  Example usage:
  json := TStringList.Create;
  BeginJSONArray(json);
}
procedure BeginJSONArray(var sl: TStringList);
begin
  sl.Add('[');
end;


(*  AddJSONArrayItem:
  JSON配列に要素を追加します。
  最後の要素でない場合、自動的にカンマを付与します。
  
  Parameters:
    sl: 対象のTStringList
    item: 追加するJSON文字列
    isLast: 最後の要素の場合 True
    
  Example usage:
  AddJSONArrayItem(json, '  { "id": 1, "name": "test" }', False);
  AddJSONArrayItem(json, '  { "id": 2, "name": "test2" }', True);
*)

procedure AddJSONArrayItem(var sl: TStringList; const item: string; isLast: Boolean);
begin
  if isLast then
    sl.Add(item)
  else
    sl.Add(item + ',');
end;

{
  EndJSONArray:
  JSON配列の終了を TStringList に追加します。
  
  Example usage:
  EndJSONArray(json);
}
procedure EndJSONArray(var sl: TStringList);
begin
  sl.Add(']');
end;

{
  SaveJSONToFile:
  TStringList を JSON ファイルとして保存します。
  
  Parameters:
    sl: 保存する TStringList
    filename: ファイル名（フルパスまたは相対パス）
    recordCount: レコード数（ログ出力用、省略可）
    
  Returns:
    Boolean: 成功した場合 True
    
  Example usage:
  success := SaveJSONToFile(json, 'output.json', 100);
}
function SaveJSONToFile(var sl: TStringList; const filename: string; recordCount: Integer = -1): Boolean;
begin
  Result := False;
  try
    sl.SaveToFile(filename);
    
    if recordCount >= 0 then
      AddMessage(Format('%s %d records -> %s', [AP_SUCCESS_PREFIX, recordCount, filename]))
    else
      AddMessage(Format('%s File saved: %s', [AP_SUCCESS_PREFIX, filename]));
      
    Result := True;
  except
    on E: Exception do
      AddMessage(Format('%s Failed to save JSON: %s - %s', [AP_ERROR_PREFIX, filename, E.Message]));
  end;
end;

(*
  CleanupDoubleQuotes:
  JSON文字列内の二重エスケープされた引用符を修正します。
  ""aaa"" → "aaa"
  
  Parameters:
    s: 処理対象の文字列
    
  Returns:
    string: クリーンアップされた文字列
    
  Example usage:
  cleaned := CleanupDoubleQuotes('{ "name": ""John""Doe"" }');
  // Result: '{ "name": "John"Doe" }'
*)
function CleanupDoubleQuotes(const s: string): string;
begin
  // 二重引用符のペアを単一引用符に置換
  Result := StringReplace(s, '""', '"', [rfReplaceAll]);
end;

{
  FixJSONFile:
  既存のJSONファイルを読み込み、二重エスケープされた引用符を修正して上書き保存します。
  
  Parameters:
    filename: 修正対象のJSONファイルパス
    
  Returns:
    Boolean: 成功した場合 True
    
  Example usage:
  if FixJSONFile(outputDir + 'weapon_ammo_map.json') then
    LogSuccess('JSON file cleaned up');
}

function FixJSONFile(const filename: string): Boolean;
var
  jsonContent: TStringList;
  i: Integer;
  originalLine, cleanedLine: string;
  changesCount: Integer;
begin
  Result := False;
  changesCount := 0;
  
  if not FileExists(filename) then begin
    LogError(Format('File not found: %s', [filename]));
    Exit;
  end;
  
  jsonContent := TStringList.Create;
  try
    // ファイルを読み込む
    try
      jsonContent.LoadFromFile(filename);
    except
      on E: Exception do begin
        LogError(Format('Failed to load JSON file: %s - %s', [filename, E.Message]));
        Exit;
      end;
    end;
    
    // 各行をクリーンアップ
    for i := 0 to jsonContent.Count - 1 do begin
      originalLine := jsonContent[i];
      cleanedLine := CleanupDoubleQuotes(originalLine);
      
      if originalLine <> cleanedLine then begin
        jsonContent[i] := cleanedLine;
        Inc(changesCount);
      end;
    end;
    
    // 変更があった場合のみ保存
    if changesCount > 0 then begin
      try
        jsonContent.SaveToFile(filename);
        LogInfo(Format('JSON cleaned: %d lines fixed in %s', [changesCount, ExtractFileName(filename)]));
        Result := True;
      except
        on E: Exception do begin
          LogError(Format('Failed to save cleaned JSON: %s - %s', [filename, E.Message]));
          Exit;
        end;
      end;
    end else begin
      LogInfo(Format('JSON already clean: %s', [ExtractFileName(filename)]));
      Result := True;
    end;
    
  finally
    jsonContent.Free;
  end;
end;

{****************************************************}
{ INI出力ヘルパー
  - BeginINISection
  - AddINIComment
  - AddINIKeyValue
  - SaveINIToFile
}
{****************************************************}

{
  BeginINISection:
  INIファイルのセクションを開始します。
  
  Example usage:
  ini := TStringList.Create;
  BeginINISection(ini, 'Settings');
}
procedure BeginINISection(var sl: TStringList; const sectionName: string);
begin
  sl.Add(Format('[%s]', [sectionName]));
end;

{
  AddINIComment:
  INIファイルにコメント行を追加します。
  
  Example usage:
  AddINIComment(ini, 'This is a comment');
}
procedure AddINIComment(var sl: TStringList; const comment: string);
begin
  sl.Add('; ' + comment);
end;

{
  AddINIKeyValue:
  INIファイルにキー=値の行を追加します。
  
  Example usage:
  AddINIKeyValue(ini, 'Key', 'Value');
}
procedure AddINIKeyValue(var sl: TStringList; const key, value: string);
begin
  sl.Add(Format('%s=%s', [key, value]));
end;

{
  SaveINIToFile:
  TStringList を INI ファイルとして保存します。
  
  Parameters:
    sl: 保存する TStringList
    filename: ファイル名（フルパスまたは相対パス）
    recordCount: レコード数（ログ出力用、省略可）
    
  Returns:
    Boolean: 成功した場合 True
}
function SaveINIToFile(var sl: TStringList; const filename: string; recordCount: Integer = -1): Boolean;
begin
  Result := False;
  try
    sl.SaveToFile(filename);
    
    if recordCount >= 0 then
      AddMessage(Format('%s %d records -> %s', [AP_SUCCESS_PREFIX, recordCount, filename]))
    else
      AddMessage(Format('%s File saved: %s', [AP_SUCCESS_PREFIX, filename]));
      
    Result := True;
  except
    on E: Exception do
      AddMessage(Format('%s Failed to save INI: %s - %s', [AP_ERROR_PREFIX, filename, E.Message]));
  end;
end;

{****************************************************}
{ ログ出力ヘルパー
  - LogSuccess
  - LogError
  - LogWarning
  - LogInfo
  - LogComplete
}
{****************************************************}

{
  LogSuccess:
  成功メッセージをログに出力します。
}
procedure LogSuccess(const message: string);
begin
  AddMessage(AP_SUCCESS_PREFIX + ' ' + message);
end;

{
  LogError:
  エラーメッセージをログに出力します。
}
procedure LogError(const message: string);
begin
  AddMessage(AP_ERROR_PREFIX + ' ' + message);
end;

{
  LogWarning:
  警告メッセージをログに出力します。
}
procedure LogWarning(const message: string);
begin
  AddMessage(AP_WARNING_PREFIX + ' ' + message);
end;

{
  LogInfo:
  情報メッセージをログに出力します。
}
procedure LogInfo(const message: string);
begin
  AddMessage(AP_INFO_PREFIX + ' ' + message);
end;

{
  LogComplete:
  処理完了メッセージをログに出力します。
  Pythonスクリプトがこのメッセージを検出して成功判定を行います。
}
procedure LogComplete(const taskName: string);
begin
  AddMessage(Format('%s %s complete.', [AP_LOG_PREFIX, taskName]));
end;

{****************************************************}
{ フィルター除外ヘルパー
  - IsMasterFileExcluded
  - IsCreationClubContent
  - CreateMasterExclusionList
}
{****************************************************}

{
  IsMasterFileExcluded:
  指定されたファイル名が除外対象のマスターファイルかどうかを判定します。
  
  Parameters:
    filename: ファイル名
    exclusionList: 除外リスト（TStringList）
    
  Returns:
    Boolean: 除外対象の場合 True
}
function IsMasterFileExcluded(const filename: string; var exclusionList: TStringList): Boolean;
begin
  Result := exclusionList.IndexOf(filename) > -1;
end;

{
  IsCreationClubContent:
  ファイル名がCreation Clubコンテンツかどうかを判定します。
  （'cc' で始まるファイル）
}
function IsCreationClubContent(const filename: string): Boolean;
begin
  Result := (Length(filename) >= 2) and (LowerCase(Copy(filename, 1, 2)) = 'cc');
end;

{
  CreateMasterExclusionList:
  標準的なマスターファイル除外リストを作成します。
  
  Returns:
    TStringList: 除外リスト（呼び出し側で Free する必要があります）
    
  Example usage:
  exclusions := CreateMasterExclusionList;
  try
    if IsMasterFileExcluded(pluginName, exclusions) then Exit;
  finally
    exclusions.Free;
  end;
}
function CreateMasterExclusionList: TStringList;
begin
  Result := TStringList.Create;
  Result.Add('Fallout4.esm');
  Result.Add('DLCRobot.esm');
  Result.Add('DLCworkshop01.esm');
  Result.Add('DLCCoast.esm');
  Result.Add('DLCworkshop02.esm');
  Result.Add('DLCworkshop03.esm');
  Result.Add('DLCNukaWorld.esm');
  Result.Add('Munitions - An Ammo Expansion.esl');
end;

{****************************************************}
{ FormID操作ヘルパー
  - FormIDToHex
  - GetFullFormID
}
{****************************************************}

{
  FormIDToHex:
  Cardinal型のFormIDを8桁の16進数文字列に変換します。
  
  Example usage:
  formIDHex := FormIDToHex(12345678);
  AddMessage(formIDHex); // '00BC614E'
}
function FormIDToHex(formID: Cardinal): string;
begin
  Result := IntToHex(formID, 8);
end;

{
  GetFullFormID:
  レコードの完全なFormID（ロードオーダー込み）を取得します。
  
  Example usage:
  rec := RecordByIndex(group, 0);
  fullID := GetFullFormID(rec);
}
function GetFullFormID(rec: IInterface): string;
begin
  Result := FormIDToHex(GetLoadOrderFormID(rec));
end;

{
  SaveAndCleanJSONToFile:
  TStringList を JSON ファイルとして保存し、二重エスケープを自動修正します。
  
  Parameters:
    sl: 保存する TStringList
    filename: ファイル名（フルパスまたは相対パス）
    recordCount: レコード数（ログ出力用、省略可）
    autoCleanup: 自動クリーンアップを有効にする（デフォルト: True）
    
  Returns:
    Boolean: 成功した場合 True
    
  Example usage:
  success := SaveAndCleanJSONToFile(json, 'output.json', 100);
}
function SaveAndCleanJSONToFile(var sl: TStringList; const filename: string; 
                                recordCount: Integer; autoCleanup: Boolean): Boolean;
begin
  Result := SaveJSONToFile(sl, filename, recordCount);
  
  if Result and autoCleanup then begin
    Result := FixJSONFile(filename);
  end;
end;


{
  ★★★ 汎用文字列/リストユーティリティ 実装 ★★★
}

function LowerTrim(const s: string): string;
begin
  Result := LowerCase(Trim(s));
end;

procedure EnsureList(var L: TStringList);
begin
  if not Assigned(L) then L := TStringList.Create;
end;

procedure SplitCSVToList(const csv: string; var L: TStringList);
var
  tmp: TStringList;
  i: Integer;
  item: string;
begin
  EnsureList(L);
  L.Clear;
  tmp := TStringList.Create;
  try
    tmp.StrictDelimiter := False; // カンマを主、空白も許容
    tmp.Delimiter := ',';
    tmp.DelimitedText := csv;
    for i := 0 to tmp.Count - 1 do begin
      item := LowerTrim(tmp[i]);
      if item <> '' then L.Add(item);
    end;
  finally
    tmp.Free;
  end;
end;

function WildcardMatchCI(const text, pattern: string): boolean;
var
  s, p: string;
  i, j, star, mark: Integer;
begin
  s := LowerCase(text);
  p := LowerCase(pattern);
  i := 1; j := 1; star := 0; mark := 0;
  while i <= Length(s) do begin
    if (j <= Length(p)) and ((p[j] = '?') or (p[j] = s[i])) then begin
      Inc(i); Inc(j);
    end else if (j <= Length(p)) and (p[j] = '*') then begin
      star := j; mark := i; Inc(j);
    end else if (star <> 0) then begin
      j := star + 1; Inc(mark); i := mark;
    end else begin
      Exit(False);
    end;
  end;
  while (j <= Length(p)) and (p[j] = '*') do Inc(j);
  Result := j > Length(p);
end;

function MatchesAnyPattern(const text: string; patterns: TStringList): boolean;
var
  k: Integer;
begin
  if (not Assigned(patterns)) or (patterns.Count = 0) then Exit(True);
  for k := 0 to patterns.Count - 1 do begin
    if WildcardMatchCI(text, patterns[k]) then Exit(True);
  end;
  Result := False;
end;

function ContainsAnyTokenCI(const text: string; tokens: TStringList): boolean;
var
  t: string;
  k: Integer;
  lowerText: string;
begin
  if (not Assigned(tokens)) or (tokens.Count = 0) then Exit(True);
  lowerText := LowerCase(text);
  for k := 0 to tokens.Count - 1 do begin
    t := tokens[k];
    if (t <> '') and (Pos(t, lowerText) > 0) then Exit(True);
  end;
  Result := False;
end;

function GetEditorIdSafe(e: IInterface): string;
begin
  Result := EditorID(e);
  if Result <> '' then Exit;
  Result := GetElementEditValues(e, 'EDID');
  if Result <> '' then Exit;
  Result := GetElementEditValues(e, 'EDID - Editor ID');
end;

end.

{
  * GetLoadOrderFormID → IntToHex の簡易ラッパー
}
function GetFullFormID(rec: IInterface): string;

{
  ★★★ 汎用文字列/リストユーティリティ ★★★
  AutoPatcherCore.pas から移動した、特定の処理に依存しないヘルパー関数群。
}
function LowerTrim(const s: string): string;
procedure EnsureList(var L: TStringList);
procedure SplitCSVToList(const csv: string; var L: TStringList);
function WildcardMatchCI(const text, pattern: string): boolean;
function MatchesAnyPattern(const text: string; patterns: TStringList): boolean;
function ContainsAnyTokenCI(const text: string; tokens: TStringList): boolean;
function GetEditorIdSafe(e: IInterface): string;



implementation
