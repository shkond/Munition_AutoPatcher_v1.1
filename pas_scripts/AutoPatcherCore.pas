unit AutoPatcherCore;

interface

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

// 段階的リファクタ（既存の Process を内部委譲する予定）
procedure AP_Reset_ExtractWeaponAmmoMappingState;
procedure AP_OnFile_ExtractWeaponAmmoMapping(e: IInterface);
function AP_Finalize_ExtractWeaponAmmoMapping: Integer;

procedure AP_Reset_ExportWeaponLeveledListsState;
procedure AP_OnFile_ExportWeaponLeveledLists(e: IInterface);
function AP_Finalize_ExportWeaponLeveledLists: Integer;

// 02系用のフィルタ設定（任意）
// - 勢力名の限定（EditorID内にトークンが含まれるかで判定）
// - EditorIDのワイルドカードパターン（'*' と '?' をサポート、大小無視）
procedure AP_LL_ClearFilters;
procedure AP_LL_SetFactionFilterCSV(const csv: string); // 例: 'Gunner,Institute,Mutant,Raider'
procedure AP_LL_AddFactionToken(const token: string);
procedure AP_LL_SetEditorIDPatternsCSV(const csv: string); // 例: 'LLI_*,*Weapon*,*Rifle*'
procedure AP_LL_AddEditorIDPattern(const pattern: string);

implementation

var
  // 01_ExtractWeaponAmmoMapping 用の状態
  ap_jsonOutput: TStringList = nil;
  ap_uniqueAmmoOutput: TStringList = nil;
  ap_processedWeapons: TStringList = nil;
  ap_masterFilesToExclude: TStringList = nil;

  // 02_ExportWeaponLeveledLists 用の状態
  ap_csvLines: TStringList = nil;
  ap_processedCount: Integer = 0;
  ap_ll_factionFilter: TStringList = nil;      // lower-case tokens
  ap_ll_editorIdPatterns: TStringList = nil;   // as-given patterns (lowercased when matching)

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

// 内部ヘルパー: EditorID 安全取得
function _GetEditorIdSafe(e: IInterface): string;
begin
  Result := EditorID(e);
  if Result <> '' then Exit;
  Result := GetElementEditValues(e, 'EDID');
  if Result <> '' then Exit;
  Result := GetElementEditValues(e, 'EDID - Editor ID');
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
      edid := _GetEditorIdSafe(rec);
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

// ========== 01_ExtractWeaponAmmoMapping 実装 ==========

procedure AP_Reset_ExtractWeaponAmmoMappingState;
begin
  // 解放（多重呼び出し安全）
  if Assigned(ap_jsonOutput) then begin ap_jsonOutput.Free; ap_jsonOutput := nil; end;
  if Assigned(ap_uniqueAmmoOutput) then begin ap_uniqueAmmoOutput.Free; ap_uniqueAmmoOutput := nil; end;
  if Assigned(ap_processedWeapons) then begin ap_processedWeapons.Free; ap_processedWeapons := nil; end;
  if Assigned(ap_masterFilesToExclude) then begin ap_masterFilesToExclude.Free; ap_masterFilesToExclude := nil; end;

  // 再作成
  ap_jsonOutput := TStringList.Create;
  ap_uniqueAmmoOutput := TStringList.Create;
  ap_processedWeapons := TStringList.Create;
  ap_masterFilesToExclude := CreateMasterExclusionList;
end;

procedure AP_OnFile_ExtractWeaponAmmoMapping(e: IInterface);
var
  i: integer;
  weapGroup, rec, winningRec, ammoRec, ammoLinkElement: IInterface;
  pluginName, weapEditorID, weapFullName: string;
  ammoFormIDInt: Cardinal;
  ammoFormIDHex, ammoPlugin, ammoEditorID: string;
  jsonEntry: string;
begin
  if not Assigned(e) then Exit;

  pluginName := GetFileName(e);
  if IsMasterFileExcluded(pluginName, ap_masterFilesToExclude) then Exit;
  if IsCreationClubContent(pluginName) then Exit;

  if not HasGroup(e, 'WEAP') then Exit;

  weapGroup := GroupBySignature(e, 'WEAP');
  for i := 0 to Pred(ElementCount(weapGroup)) do begin
    rec := ElementByIndex(weapGroup, i);
    winningRec := WinningOverride(rec);
    weapEditorID := EditorID(rec);

    if ap_processedWeapons.IndexOf(weapEditorID) > -1 then Continue;
    ap_processedWeapons.Add(weapEditorID);

    weapFullName := GetElementEditValues(winningRec, 'FULL');
    if weapFullName = '' then weapFullName := weapEditorID;

    ammoFormIDInt := GetElementNativeValues(winningRec, 'DNAM\AMMO');
    if ammoFormIDInt = 0 then Continue;

    ammoFormIDHex := FormIDToHex(ammoFormIDInt);
    ammoLinkElement := ElementByPath(winningRec, 'DNAM\AMMO');
    ammoRec := nil;
    if Assigned(ammoLinkElement) then ammoRec := LinksTo(ammoLinkElement);

    if Assigned(ammoRec) then begin
      ammoPlugin := GetFileName(GetFile(ammoRec));
      ammoEditorID := EditorID(ammoRec);

      if ap_uniqueAmmoOutput.IndexOfName(ammoFormIDHex) = -1 then
        ap_uniqueAmmoOutput.Add(Format('%s=%s|%s', [ammoFormIDHex, ammoPlugin, ammoEditorID]));

      jsonEntry := Format('    { "editor_id": "%s", "full_name": "%s", "ammo_form_id": "%s" }', [
        weapEditorID,
        weapFullName,
        ammoFormIDHex
      ]);
      ap_jsonOutput.Add(jsonEntry);
    end;
  end;
end;

function AP_Finalize_ExtractWeaponAmmoMapping: Integer;
var
  outputDir, jsonFilePath, iniFilePath: string;
  i: integer;
  jsonFile: TStringList;
begin
  Result := 0;
  try
    outputDir := GetOutputDirectory;

    // JSON保存
    jsonFilePath := outputDir + 'weapon_ammo_map.json';
    jsonFile := TStringList.Create;
    try
      BeginJSONArray(jsonFile);
      if ap_jsonOutput.Count > 0 then begin
        for i := 0 to ap_jsonOutput.Count - 2 do
          AddJSONArrayItem(jsonFile, ap_jsonOutput[i], False);
        AddJSONArrayItem(jsonFile, ap_jsonOutput[ap_jsonOutput.Count - 1], True);
      end;
      EndJSONArray(jsonFile);
      SaveAndCleanJSONToFile(jsonFile, jsonFilePath, ap_jsonOutput.Count, True);
    finally
      jsonFile.Free;
    end;

    // INI保存
    iniFilePath := outputDir + 'unique_ammo_for_mapping.ini';
    ap_uniqueAmmoOutput.Insert(0, '[UnmappedAmmo]');
    ap_uniqueAmmoOutput.Sort;
    SaveINIToFile(ap_uniqueAmmoOutput, iniFilePath, ap_uniqueAmmoOutput.Count - 1);

    LogComplete('Weapon and ammo mapping extraction');
  except
    on E: Exception do begin
      LogError(E.Message);
      Result := 1;
    end;
  end;

  // 解放
  if Assigned(ap_jsonOutput) then begin ap_jsonOutput.Free; ap_jsonOutput := nil; end;
  if Assigned(ap_uniqueAmmoOutput) then begin ap_uniqueAmmoOutput.Free; ap_uniqueAmmoOutput := nil; end;
  if Assigned(ap_processedWeapons) then begin ap_processedWeapons.Free; ap_processedWeapons := nil; end;
  if Assigned(ap_masterFilesToExclude) then begin ap_masterFilesToExclude.Free; ap_masterFilesToExclude := nil; end;
end;

// ========== 02_ExportWeaponLeveledLists 実装 ==========

// 対象ファイルかどうか（Fallout4、DLC、CC）
function _IsTargetFile(const fileName: string): boolean;
var
  lower: string;
begin
  lower := LowerCase(fileName);
  Result :=
    (fileName = 'Fallout4.esm') or
    (fileName = 'DLCRobot.esm') or
    (fileName = 'DLCCoast.esm') or
    (fileName = 'DLCworkshop01.esm') or
    (fileName = 'DLCworkshop02.esm') or
    (fileName = 'DLCworkshop03.esm') or
    (fileName = 'DLCNukaWorld.esm') or
    (Pos('cc', lower) = 1) or
    (Pos('cc', lower) = 3) or
    (Pos('creations', lower) = 1);
end;

// レベルドリストが他のLVLIを含むか（現状CSVには未使用だが参考として保持）
function _ContainsLeveledList(rec: IInterface): boolean;
var
  entries, entry, lvlo: IInterface;
  i: integer;
  refSig: string;
begin
  Result := false;
  entries := ElementByName(rec, 'Leveled List Entries');
  if not Assigned(entries) then Exit;

  for i := 0 to ElementCount(entries) - 1 do begin
    entry := ElementByIndex(entries, i);
    lvlo := ElementByName(entry, 'LVLO - Base Data');
    if Assigned(lvlo) then begin
      refSig := Signature(LinksTo(ElementByName(lvlo, 'Reference')));
      if refSig = 'LVLI' then begin
        Result := true;
        Exit;
      end;
    end;
  end;
end;

// 武器関連レベルドリストの判定（除外条件含む）
function _IsWeaponRelated(rec: IInterface): boolean;
var
  editorID: string;
begin
  Result := false;
  editorID := GetElementEditValues(rec, 'EDID');

  if (Pos('VRWorkshopShared', editorID) > 0) or
     (Pos('Grenade', editorID) > 0) or
     (Pos('Mine', editorID) > 0) or
     (Pos('Ammo', editorID) > 0) or
     (Pos('Armor', editorID) > 0) or
     (Pos('Clothes', editorID) > 0) or
     (Pos('Outfit', editorID) > 0) or
     (Pos('Stimpack', editorID) > 0) or
     (Pos('Chem', editorID) > 0) or
     (Pos('Container', editorID) > 0) or
     (Pos('Loot', editorID) > 0) or
     (Pos('Dog', editorID) > 0) or
     (Pos('Misc', editorID) > 0) or
     (Pos('Underarmor', editorID) > 0) or
     (Pos('Vendor', editorID) > 0) then Exit;

  if (Pos('Weapon', editorID) > 0) or
     (Pos('Gun', editorID) > 0) or
     (Pos('Pistol', editorID) > 0) or
     (Pos('Rifle', editorID) > 0) or
     (Pos('Shotgun', editorID) > 0) or
     (Pos('Sniper', editorID) > 0) or
     (Pos('Auto', editorID) > 0) or
     (Pos('SemiAuto', editorID) > 0) or
     (Pos('Melee', editorID) > 0) or
     (Pos('Laser', editorID) > 0) or
     (Pos('Plasma', editorID) > 0) or
     (Copy(editorID, 1, 4) = 'LLI_') then
    Result := true;
end;

procedure AP_Reset_ExportWeaponLeveledListsState;
begin
  if Assigned(ap_csvLines) then begin ap_csvLines.Free; ap_csvLines := nil; end;
  ap_csvLines := TStringList.Create;
  ap_csvLines.Add('EditorID,FormID,SourceFile');
  ap_processedCount := 0;
end;

procedure AP_OnFile_ExportWeaponLeveledLists(e: IInterface);
var
  j: integer;
  Group, Rec: IInterface;
  EditorID, formIDStr, fileName: string;
begin
  if not Assigned(e) then Exit;

  fileName := GetFileName(e);
  if not _IsTargetFile(fileName) then Exit;

  if not HasGroup(e, 'LVLI') then Exit;
  Group := GroupBySignature(e, 'LVLI');
  for j := 0 to ElementCount(Group) - 1 do begin
    Rec := ElementByIndex(Group, j);
    EditorID := GetElementEditValues(Rec, 'EDID');
    if EditorID = '' then Continue;
    if (Pos('VRWorkshopShared', EditorID) > 0) then Continue;

    // ベース判定
    if _IsWeaponRelated(Rec) then begin
      // 追加フィルタ: 勢力トークン、EditorIDパターン
      if not _ContainsAnyTokenCI(EditorID, ap_ll_factionFilter) then Continue;
      if not _MatchesAnyPattern(EditorID, ap_ll_editorIdPatterns) then Continue;
      formIDStr := IntToHex(FixedFormID(Rec), 8);
      ap_csvLines.Add(Format('"%s","%s","%s"', [EditorID, formIDStr, fileName]));
    end;
  end;
  Inc(ap_processedCount);
end;

function AP_Finalize_ExportWeaponLeveledLists: Integer;
var
  csvFilePath: string;
begin
  Result := 0;
  try
    // FO4Edit Scripts直下に保存（Orchestratorは親フォルダも探索）
    csvFilePath := ScriptsPath + 'WeaponLeveledLists_Export.csv';
    ap_csvLines.SaveToFile(csvFilePath);
    LogSuccess(Format('CSV exported: %s (files processed: %d, rows: %d)', [
      csvFilePath, ap_processedCount, ap_csvLines.Count - 1]));
    LogComplete('Leveled list export');
  except
    on E: Exception do begin
      LogError('Failed to save WeaponLeveledLists_Export.csv: ' + E.Message);
      Result := 1;
    end;
  end;
  if Assigned(ap_csvLines) then begin ap_csvLines.Free; ap_csvLines := nil; end;
end;

// --- 公開フィルタAPI ---
procedure AP_LL_ClearFilters;
begin
  if Assigned(ap_ll_factionFilter) then ap_ll_factionFilter.Clear;
  if Assigned(ap_ll_editorIdPatterns) then ap_ll_editorIdPatterns.Clear;
end;

procedure AP_LL_SetFactionFilterCSV(const csv: string);
begin
  _SplitCSVToList(csv, ap_ll_factionFilter);
end;

procedure AP_LL_AddFactionToken(const token: string);
var
  t: string;
begin
  _EnsureList(ap_ll_factionFilter);
  t := _LowerTrim(token);
  if (t <> '') and (ap_ll_factionFilter.IndexOf(t) = -1) then
    ap_ll_factionFilter.Add(t);
end;

procedure AP_LL_SetEditorIDPatternsCSV(const csv: string);
begin
  _SplitCSVToList(csv, ap_ll_editorIdPatterns);
end;

procedure AP_LL_AddEditorIDPattern(const pattern: string);
var
  p: string;
begin
  _EnsureList(ap_ll_editorIdPatterns);
  p := Trim(pattern);
  if (p <> '') and (ap_ll_editorIdPatterns.IndexOf(p) = -1) then
    ap_ll_editorIdPatterns.Add(p);
end;

end.