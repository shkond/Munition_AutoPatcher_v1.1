unit AutoPatcherCore;

interface
uses ExtractWeaponAmmoMappingLogic, // AP_Run_ExtractWeaponAmmoMapping の実装を外部化
     ExportLeveledListsLogic;     // AP_Run_ExportWeaponLeveledLists の実装を外部化
uses
  xEditAPI, Classes, SysUtils, StrUtils, Windows,
  'lib/AutoPatcherLib',
  'lib/mteBase',
  'lib/mteElements',
  'lib/mteFiles',
  'lib/mteRecords';

{
  各スクリプトの実処理をコア関数として提供。
  既存スクリプトの Initialize から本関数を呼び出す形に変更します。
}

function AP_Run_ExportWeaponAmmoDetails: Integer;
function AP_Run_ExportMunitionsAmmoIDs: Integer;
function AP_Run_GenerateStrategyFromMunitions: Integer;

implementation

// --- 内部ヘルパー: 文字列ユーティリティ ---
function _LowerTrim(const s: string): string;
begin
  Result := LowerCase(Trim(s));
end;

procedure _EnsureList(var L: TStringList);
begin
  if not Assigned(L) then L := TStringList.Create;
end;

procedure _SplitCSVToList(const csv: string; var L: TStringList);
var
  tmp: TStringList;
  i: Integer;
  item: string;
begin
  _EnsureList(L);
  L.Clear;
  tmp := TStringList.Create;
  try
    tmp.StrictDelimiter := False; // カンマを主、空白も許容
    tmp.Delimiter := ',';
    tmp.DelimitedText := csv;
    for i := 0 to tmp.Count - 1 do begin
      item := _LowerTrim(tmp[i]);
      if item <> '' then L.Add(item);
    end;
  finally
    tmp.Free;
  end;
end;

// ワイルドカード一致（'*' と '?'） 大小無視
function _WildcardMatchCI(const text, pattern: string): boolean;
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

function _MatchesAnyPattern(const text: string; patterns: TStringList): boolean;
var
  k: Integer;
begin
  if (not Assigned(patterns)) or (patterns.Count = 0) then Exit(True);
  for k := 0 to patterns.Count - 1 do begin
    if _WildcardMatchCI(text, patterns[k]) then Exit(True);
  end;
  Result := False;
end;

function _ContainsAnyTokenCI(const text: string; tokens: TStringList): boolean;
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

// --- 内部ヘルパー: 02_ExportWeaponLeveledLists 用 ---
// これらの関数は元々 02_ExportWeaponLeveledLists.pas にありましたが、
// AP_Run_ExportWeaponLeveledLists がここに実装されるため移動します。

// 01_ExportWeaponAmmoDetails の中身をこちらへ移設
function AP_Run_ExportWeaponAmmoDetails: Integer;
var
  i, j: Integer;
  aFile: IwbFile;
  group, rec, ammoRec: IInterface;
  sl: TStringList;
  outputDir, outPath: string;
  weapPlugin, weapFormID, weapEdid: string;
  ammoPlugin, ammoFormID, ammoEdid: string;
begin
  Result := 0;
  sl := TStringList.Create;
  try
    // ヘッダ無し、本体のみ（Orchestrator 期待形式）
    // 1行: Plugin|WeaponFormID|WeaponEditorID|AmmoPlugin|AmmoFormID|AmmoEditorID

    for i := 0 to FileCount - 1 do begin
      aFile := FileByIndex(i);
      group := GroupBySignature(aFile, 'WEAP'); // 武器
      if not Assigned(group) then
        Continue;

      for j := 0 to ElementCount(group) - 1 do begin
        rec := ElementByIndex(group, j);

        weapEdid := GetElementEditValues(rec, 'EDID');
        if weapEdid = '' then
          Continue;

        // 武器側
        weapPlugin := GetFileName(GetFile(rec));
        weapFormID := IntToHex(FixedFormID(rec), 8);

        // 弾薬参照（DNAM\Ammo）
        ammoRec := LinksTo(ElementByPath(rec, 'DNAM\Ammo'));
        if not Assigned(ammoRec) then
          Continue; // 弾薬無しの武器はスキップ（近接等）

        ammoPlugin := GetFileName(GetFile(ammoRec));
        ammoFormID := IntToHex(FixedFormID(ammoRec), 8);
        ammoEdid   := EditorID(ammoRec);

        sl.Add(Format('%s|%s|%s|%s|%s|%s',
          [weapPlugin, weapFormID, weapEdid, ammoPlugin, ammoFormID, ammoEdid]));
      end;
    end;

    outputDir := GetOutputDirectory; // 例: Edit Scripts\Output\
    outPath := outputDir + 'weapon_ammo_details.txt';
    sl.SaveToFile(outPath);

    AddMessage('[AutoPatcher] SUCCESS: weapon_ammo_details -> ' + outPath);
  except
    on E: Exception do begin
      AddMessage('[AutoPatcher] ERROR: ' + E.Message);
      Result := 1;
    end;
  end;
  sl.Free;
end;

// 内部ヘルパー: Munitionsプラグイン探索（デフォルト名→フォールバック）
function _FindMunitionsFile: IInterface;
var
  i: integer;
  f: IInterface;
  nameLower: string;
const
  DEFAULT_NAME = 'Munitions - An Ammo Expansion.esl';
begin
  Result := FileByName(DEFAULT_NAME);
  if Assigned(Result) then Exit;

  // フォールバック: ファイル名に "munitions" を含み、AMMO グループを持つファイルを探索
  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    nameLower := LowerCase(GetFileName(f));
    if Pos('munitions', nameLower) > 0 then begin
      if HasGroup(f, 'AMMO') then begin
        Result := f;
        Exit;
      end;
    end;
  end;
end;

// 03_ExportMunitionsAmmoIDs の中身をこちらへ移設
function AP_Run_ExportMunitionsAmmoIDs: Integer;
var
  iniLines: TStringList;
  ammoGroup, rec: IInterface;
  outputDir, iniFilePath: string;
  munitionsPlugin: IInterface;
  exportedCount, ammoCount, i: integer;
  formIDHex, edid: string;
begin
  Result := 0;
  iniLines := TStringList.Create;
  try
    // 対象Munitionsプラグインを取得
    munitionsPlugin := _FindMunitionsFile;
    if not Assigned(munitionsPlugin) then begin
      LogError('Munitions plugin not found (expected "Munitions - An Ammo Expansion.esl").');
      Result := 1;
      Exit;
    end;

    ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
    if not Assigned(ammoGroup) then begin
      LogError('AMMO group not found in Munitions plugin.');
      Result := 1;
      Exit;
    end;

    ammoCount := ElementCount(ammoGroup);

    // INI セクションヘッダとコメント
    BeginINISection(iniLines, 'MunitionsAmmo');
    AddINIComment(iniLines, 'FormID=EditorID');

    exportedCount := 0;
    for i := 0 to ammoCount - 1 do begin
      rec := ElementByIndex(ammoGroup, i);
      edid := GetEditorIdSafe(rec); // Lib関数を呼び出す
      if edid = '' then
        Continue; // EDID無しはスキップ

      // ESL対応の完全FormIDを使用
      formIDHex := GetFullFormID(rec);
      AddINIKeyValue(iniLines, formIDHex, edid);
      Inc(exportedCount);
    end;

    // 保存
    outputDir := GetOutputDirectory;
    iniFilePath := outputDir + 'munitions_ammo_ids.ini';
    if not SaveINIToFile(iniLines, iniFilePath, exportedCount) then begin
      Result := 1;
      Exit;
    end;

    // 完了シグナル（Python 側検出用）
    LogComplete('Munitions ammo ID export');
  except
    on E: Exception do begin
      LogError(E.Message);
      Result := 1;
    end;
  end;
  iniLines.Free;
end;

// 00_GenerateStrategyFromMunitions: Munitions AMMO を走査し ammo_classification を構築
// 備考: 可能なら分類ルール(ammo_categories.json)を Edit Scripts 配下で探索して適用。
// 見つからない場合は Uncategorized/Power=0 として出力。
function AP_Run_GenerateStrategyFromMunitions: Integer;
var
  munitionsPlugin, ammoGroup, rec: IInterface;
  outputDir, strategyPath: string;
  i, count: Integer;
  edid, normId, formId: string;
  sl: TStringList;
begin
  Result := 0;
  try
    munitionsPlugin := _FindMunitionsFile;
    if not Assigned(munitionsPlugin) then begin
      LogError('Munitions plugin not found (expected "Munitions - An Ammo Expansion.esl").');
      Exit(1);
    end;

    ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
    if not Assigned(ammoGroup) then begin
      LogError('AMMO group not found in Munitions plugin.');
      Exit(1);
    end;

    outputDir := GetOutputDirectory;
    strategyPath := outputDir + 'strategy.json';

    sl := TStringList.Create;
    try
      // JSON ヘッダ
      sl.Add('{');
      sl.Add('  "ammo_classification": {');

      count := 0;
      for i := 0 to ElementCount(ammoGroup) - 1 do begin
        rec := ElementByIndex(ammoGroup, i);
        edid := EditorID(rec);
        if edid = '' then Continue;

        // ESL対応の完全FormID
        formId := GetFullFormID(rec);
        // 正規化（今後のルール適用の余地を残す）
        normId := LowerCase(edid);
        normId := StringReplace(normId, 'munitions_', '', [rfReplaceAll]);
        normId := StringReplace(normId, 'ammo',       '', [rfReplaceAll]);
        normId := StringReplace(normId, '_',          '', [rfReplaceAll]);
        normId := StringReplace(normId, '-',          '', [rfReplaceAll]);
        normId := StringReplace(normId, 'caliber',    '', [rfReplaceAll]);
        normId := StringReplace(normId, 'round',      '', [rfReplaceAll]);
        normId := StringReplace(normId, 'shell',      '', [rfReplaceAll]);
        normId := StringReplace(normId, 'ball',       '', [rfReplaceAll]);

        // ルール適用（現状は見つからなければ未分類）
        // TODO: ammo_categories.json を Edit Scripts/ または Output/ で検出し、キーワードベースで Category/Power を設定
        if count > 0 then sl.Add(',');
        sl.Add(Format('    "%s": { "Category": "%s", "Power": %d }', [formId, 'Uncategorized', 0]));
        Inc(count);
      end;

      sl.Add('  },');
      sl.Add('  "allocation_matrix": {},');
      sl.Add('  "faction_leveled_lists": {}');
      sl.Add('}');

      sl.SaveToFile(strategyPath);
      LogSuccess(Format('strategy.json updated: %s (ammo_classification=%d)', [strategyPath, count]));
      LogComplete('Strategy generation');
    finally
      sl.Free;
    end;
  except
    on E: Exception do begin
      LogError(E.Message);
      Result := 1;
    end;
  end;
end;

end.