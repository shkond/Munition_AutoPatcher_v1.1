unit ExportMunitionsAmmoIDs;

uses
  xEditAPI,
  Classes,
  SysUtils,
  StrUtils,
  Windows,
  'lib/AutoPatcherLib';

var
  iniLines: TStringList;

function Initialize: integer;
begin
  iniLines := TStringList.Create;
  Result := 0;
end;

function FindMunitionsFileFallback(defaultName: string): IInterface;
var
  i: integer;
  f: IInterface;
  nameLower: string;
begin
  Result := FileByName(defaultName);
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

function GetEditorIdSafe(e: IInterface): string;
begin
  // まず通常の EditorID()
  Result := EditorID(e);
  if Result <> '' then Exit;

  // フォールバック: EDID フィールドを直接参照（環境差対策）
  Result := GetElementEditValues(e, 'EDID');
  if Result <> '' then Exit;

  // さらに互換的なパス名（xEdit バージョン差対策）
  Result := GetElementEditValues(e, 'EDID - Editor ID');
end;

function Finalize: integer;
var
  ammoGroup, rec, winning: IInterface;
  i: integer;
  iniFilePath, editorID, fullFormID: string;
  targetModFileName: string;
  outputDir: string;
  munitionsPlugin: IInterface;
  exportedCount, ammoCount, warnCount: integer;
begin
  Result := 0;
  LogInfo('Exporting ammo EditorID and FormID from Munitions mod...');

  targetModFileName := 'Munitions - An Ammo Expansion.esl';

  BeginINISection(iniLines, 'MunitionsAmmo');
  AddINIComment(iniLines, 'FormID=EditorID');

  try
    outputDir := GetOutputDirectory;

    // 既定名 → フォールバック順で取得
    munitionsPlugin := FindMunitionsFileFallback(targetModFileName);
    if not Assigned(munitionsPlugin) then begin
      LogError(targetModFileName + ' is not loaded, and fallback search also failed.');
      Exit;
    end;

    LogInfo('Processing file: ' + GetFileName(munitionsPlugin));

    ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
    if not Assigned(ammoGroup) then begin
      LogInfo(' - No AMMO group found in ' + GetFileName(munitionsPlugin));
      Exit;
    end;

    ammoCount := ElementCount(ammoGroup);
    exportedCount := 0;
    warnCount := 0;

    for i := 0 to ammoCount - 1 do begin
      rec := ElementByIndex(ammoGroup, i);
      // WinningOverride を使用（環境差で EditorID が空になるのを避ける）
      winning := WinningOverride(rec);

      editorID := GetEditorIdSafe(winning);
      fullFormID := GetFullFormID(winning);

      if editorID = '' then begin
        Inc(warnCount);
        if warnCount <= 10 then
          LogWarning(Format('Empty EditorID for %s (first 10 shown)', [fullFormID]));
        // それでも空ならスキップせず空のまま書き出し（従来互換）
      end;

      AddINIKeyValue(iniLines, fullFormID, editorID);
      Inc(exportedCount);
    end;

    LogInfo(Format('AMMO records found: %d, exported: %d, empty EditorID: %d', [ammoCount, exportedCount, warnCount]));

    iniFilePath := outputDir + 'munitions_ammo_ids.ini';
    SaveINIToFile(iniLines, iniFilePath, exportedCount);

    LogComplete('Munitions ammo ID export');

  except
    on E: Exception do begin
      LogError(E.Message);
      Result := 1;
    end;
  end;

  iniLines.Free;
end;

end.