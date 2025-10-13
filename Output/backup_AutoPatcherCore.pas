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
  Result := False;
  while i <= Length(s) do begin
    if (j <= Length(p)) and ((p[j] = '?') or (p[j] = s[i])) then begin
      Inc(i); Inc(j);
    end else if (j <= Length(p)) and (p[j] = '*') then begin
      star := j; mark := i; Inc(j);
    end else if (star <> 0) then begin
      j := star + 1; Inc(mark); i := mark;
    end else begin
      Exit;
    end;
  end;
  while (j <= Length(p)) and (p[j] = '*') do Inc(j);
  Result := j > Length(p);
end;

function _MatchesAnyPattern(const text: string; patterns: TStringList): boolean;
var
  k: Integer;
begin
  if (not Assigned(patterns)) or (patterns.Count = 0) then begin
    Result := True;
    Exit;
  end;

  for k := 0 to patterns.Count - 1 do begin
    if _WildcardMatchCI(text, patterns[k]) then begin
      Result := True;
      Exit;
    end;
  end;

  Result := False;
end;

function _ContainsAnyTokenCI(const text: string; tokens: TStringList): boolean;
var
  t: string;
  k: Integer;
  lowerText: string;
begin
  if (not Assigned(tokens)) or (tokens.Count = 0) then begin
    Result := True;
    Exit;
  end;

  lowerText := LowerCase(text);
  for k := 0 to tokens.Count - 1 do begin
    t := tokens[k];
    if (t <> '') and (Pos(t, lowerText) > 0) then begin
      Result := True;
      Exit;
    end;
  end;
  Result := False;
end;

// --- 内部ヘルパー: 02_ExportWeaponLeveledLists 用 ---
// これらの関数は元々 02_ExportWeaponLeveledLists.pas にありましたが、
// AP_Run_ExportWeaponLeveledLists がここに実装されるため移動します。

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

function _EscapeJSON(const s: string): string;
begin
  Result := StringReplace(s, '\', '\\', [rfReplaceAll]);
  Result := StringReplace(Result, '"', '\"', [rfReplaceAll]);
  Result := StringReplace(Result, #13#10, '\n', [rfReplaceAll]);
  Result := StringReplace(Result, #13, '\n', [rfReplaceAll]);
  Result := StringReplace(Result, #10, '\n', [rfReplaceAll]);
end;

function AP_Run_ExportWeaponAmmoDetails: Integer;
var
  i, j, k: Integer;
  aFile: IwbFile;
  weapGroup, weaponRec, ammoRec, omodList, omodEntry, omodRec: IInterface;
  jsonLines, uniqueAmmoLines: TStringList;
  outputDir, jsonPath, uniqueAmmoPath: string;
  weaponPlugin, weaponFormID, weaponEditorID, weaponName: string;
  ammoPlugin, ammoFormID, ammoEditorID: string;
  weaponCount, omodCount: Integer;
  line: string;
  dbgF: TextFile; // per-weapon debug append file
begin
  Result := 0;
  jsonLines := TStringList.Create;
  uniqueAmmoLines := TStringList.Create;
  try
    LogDebug('AP_Run_ExportWeaponAmmoDetails: 開始');

    // Early instrumentation: write a short manual debug log so we can detect the script started
    // even if xEdit crashes before the main save occurs.
    try
      try
        ForceDirectories(EnsureTrailingSlash(GetOutputDirectory));
      except
      end;
      try
        var _dbg := TStringList.Create;
        try
          _dbg.Add('[ManualProbe] AP_Run_ExportWeaponAmmoDetails start');
          _dbg.Add(Format('ProgramPath=%s', [ProgramPath]));
          _dbg.Add(Format('Time=%s', [DateTimeToStr(Now)]));
          _dbg.SaveToFile(EnsureTrailingSlash(GetOutputDirectory) + 'manual_debug_log.txt');
        finally
          _dbg.Free;
        end;
      except
        // ignore
      end;

    except
    end;

    uniqueAmmoLines.Sorted := True;
    uniqueAmmoLines.Duplicates := dupIgnore;
    uniqueAmmoLines.NameValueSeparator := '=';

    outputDir := EnsureTrailingSlash(GetOutputDirectory);
    ForceDirectories(outputDir);
    jsonPath := outputDir + 'weapon_omod_map.json';
    uniqueAmmoPath := outputDir + 'unique_ammo_for_mapping.ini';
    LogDebug(Format('出力先JSON: %s', [jsonPath]));

    jsonLines.Add('[');
    // Create a minimal placeholder file early so we can detect partial runs/crashes.
    try
      var _placeholder := TStringList.Create;
      try
        _placeholder.Add('[]');
        SaveAndCleanJSONToFile(_placeholder, jsonPath, 0, True);
      finally
        _placeholder.Free;
      end;
    except
      // ignore placeholder failures
    end;
    weaponCount := 0;

    for i := 0 to Pred(FileCount) do begin
      aFile := FileByIndex(i);
      if not Assigned(aFile) then
        Continue;
      weapGroup := GroupBySignature(aFile, 'WEAP');
      if not Assigned(weapGroup) then
        Continue;
      if ElementCount(weapGroup) = 0 then
        Continue;

      for j := 0 to Pred(ElementCount(weapGroup)) do begin
        weaponRec := ElementByIndex(weapGroup, j);
        if not Assigned(weaponRec) then
          Continue;

        weaponPlugin := GetFileName(MasterOrSelf(weaponRec));
        weaponFormID := GetFullFormID(weaponRec); // ★★★ 修正: ESL対応のFormID取得関数に変更
        weaponEditorID := EditorID(weaponRec);
        weaponName := GetElementEditValues(weaponRec, 'FULL - Name');

        // Per-weapon append to debug file (best-effort) so we can see progress
        try
          try
            AssignFile(dbgF, outputDir + 'omod_debug_log.txt');
            if FileExists(outputDir + 'omod_debug_log.txt') then
              Append(dbgF)
            else
              Rewrite(dbgF);
            try
              Writeln(dbgF, Format('%d,%s,%s', [weaponCount, weaponEditorID, weaponFormID]));
            finally
              CloseFile(dbgF);
            end;
          except
            // ignore write failures
          end;
        except
        end;

        ammoRec := LinksTo(ElementByPath(weaponRec, 'DNAM\Ammo'));
        ammoPlugin := '';
        ammoFormID := '';
        ammoEditorID := '';
        if Assigned(ammoRec) then begin
          ammoPlugin := GetFileName(MasterOrSelf(ammoRec)); // マスターのファイル名を取得
          ammoFormID := GetFullFormID(ammoRec); // ★★★ 修正: ESL対応のFormID取得関数に変更
          ammoEditorID := EditorID(ammoRec);
          if (ammoFormID <> '') and (uniqueAmmoLines.IndexOfName(ammoFormID) = -1) then
            uniqueAmmoLines.Add(Format('%s=%s|%s', [ammoFormID, ammoPlugin, ammoEditorID]));
        end;

        if weaponCount > 0 then begin
          jsonLines[jsonLines.Count - 1] := jsonLines[jsonLines.Count - 1] + ',';
          jsonLines.Add('');
        end;

        jsonLines.Add('  {');
        jsonLines.Add(Format('    "weapon_plugin": "%s",', [_EscapeJSON(weaponPlugin)]));
        jsonLines.Add(Format('    "weapon_form_id": "%s",', [weaponFormID]));
        jsonLines.Add(Format('    "weapon_editor_id": "%s",', [_EscapeJSON(weaponEditorID)]));
        jsonLines.Add(Format('    "weapon_name": "%s",', [_EscapeJSON(weaponName)]));
        jsonLines.Add(Format('    "ammo_plugin": "%s",', [_EscapeJSON(ammoPlugin)]));
        jsonLines.Add(Format('    "ammo_form_id": "%s",', [ammoFormID]));
        jsonLines.Add(Format('    "ammo_editor_id": "%s",', [_EscapeJSON(ammoEditorID)]));
        jsonLines.Add('    "omods": [');

        LogDebug(Format('[OMOD] 武器: %s (%s) のOMOD処理を開始', [weaponEditorID, weaponFormID]));
        omodList := ElementByPath(weaponRec, 'OMOD - Object Mods');
        omodCount := 0;
        if Assigned(omodList) then begin
          omodCount := ElementCount(omodList);
          LogDebug(Format('[OMOD]   リスト発見。件数: %d', [omodCount]));
        end else begin
          LogDebug('[OMOD]   リストなし');
        end;

        for k := 0 to Pred(omodCount) do begin
          omodEntry := ElementByIndex(omodList, k);
          omodRec := LinksTo(omodEntry);
          if not Assigned(omodRec) then begin
            LogWarning(Format('[OMOD]     - OMOD[%d]: リンク先のレコードが見つかりません。スキップします。', [k]));
            Continue;
          end;

          LogDebug(Format('[OMOD]     - OMOD[%d]: %s (%s) を処理中', [k, EditorID(omodRec), GetFullFormID(omodRec)]));
          line := Format(
            '      { "omod_plugin": "%s", "omod_form_id": "%s", "omod_editor_id": "%s" }',
            [_EscapeJSON(GetFileName(MasterOrSelf(omodRec))),
             GetFullFormID(omodRec), // ★★★ 修正: ESL対応のFormID取得関数に変更
             _EscapeJSON(EditorID(omodRec))]
          );
          if k < omodCount - 1 then
            line := line + ',';
          jsonLines.Add(line);
        end;

        jsonLines.Add('    ]');
        jsonLines.Add('  }');
        Inc(weaponCount);
      end;
    end;

    jsonLines.Add(']');
    LogDebug(Format('[WeaponOMOD] 抽出武器件数: %d', [weaponCount]));

    // この2行は重複しているため、1行削除します
    // jsonLines.Add(']');
    // LogInfo(Format('[WeaponOMOD] 抽出件数: %d', [weaponCount]));

    LogDebug(Format('weapon_omod_map.json の保存を開始します... (TStringList.Size: %d)', [jsonLines.Size]));
    // Use the library helper which logs success/failure and optionally fixes JSON quoting issues.
    if not SaveAndCleanJSONToFile(jsonLines, jsonPath, weaponCount, True) then
    begin
      LogError(Format('weapon_omod_map.json の保存に失敗 (SaveAndCleanJSONToFile): %s', [jsonPath]));
      Result := 1;
      Exit;
    end
    else
    begin
      // The helper already emits an AddMessage on success; also emit an INFO-style message for clarity.
      LogInfo(Format('[WeaponOMOD] weapon_omod_map.json を保存しました: %s', [jsonPath]));
    end;

    if uniqueAmmoLines.IndexOf('[UnmappedAmmo]') = -1 then
      uniqueAmmoLines.Insert(0, '[UnmappedAmmo]');
    if not SaveINIToFile(uniqueAmmoLines, uniqueAmmoPath, uniqueAmmoLines.Count - 1) then begin
      LogWarning('unique_ammo_for_mapping.ini の保存に失敗しました');
      Result := 1;
    end else
      LogComplete('Weapon OMOD export');
    LogDebug('AP_Run_ExportWeaponAmmoDetails: 正常終了');
  finally
    uniqueAmmoLines.Free;
    jsonLines.Free;
  end;
end;

end.