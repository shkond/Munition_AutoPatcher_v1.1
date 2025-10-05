{
  mteAutoPatcher
  
  AutoPatcher専用の共通関数ライブラリ
  重複コードの削減とメンテナンス性向上を目的とする
  
  主な機能:
  - パス操作ヘルパー
  - JSON出力ヘルパー
  - INI出力ヘルパー
  - ログ出力統一
}

unit mteAutoPatcher;

uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows;

const
  // 成功メッセージのプレフィックス
  AP_LOG_PREFIX = '[AutoPatcher]';
  AP_SUCCESS_PREFIX = '[AutoPatcher] SUCCESS:';
  AP_ERROR_PREFIX = '[AutoPatcher] ERROR:';
  AP_WARNING_PREFIX = '[AutoPatcher] WARNING:';
  AP_INFO_PREFIX = '[AutoPatcher] INFO:';
  
  // 出力ディレクトリ
  AP_OUTPUT_SUBDIR = 'Edit Scripts\Output\';

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

end.