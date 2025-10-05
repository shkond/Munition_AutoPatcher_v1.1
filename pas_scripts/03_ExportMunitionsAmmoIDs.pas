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

function Finalize: integer;
var
  ammoGroup, rec: IInterface;
  i, j: integer;
  iniFilePath, editorID, fullFormID: string;
  targetModFileName: string;
  outputDir: string;
  munitionsPlugin: IInterface;
begin
  Result := 0;
  LogInfo('Exporting ammo EditorID and FormID from Munitions mod...');  // ★★★ ライブラリ関数 ★★★
  
  targetModFileName := 'Munitions - An Ammo Expansion.esl';

  // ★★★ 修正: ライブラリ関数を使用 ★★★
  BeginINISection(iniLines, 'MunitionsAmmo');
  AddINIComment(iniLines, 'FormID=EditorID');

  try
    outputDir := GetOutputDirectory;  // ★★★ ライブラリ関数 ★★★

    munitionsPlugin := FileByName(targetModFileName);
    if not Assigned(munitionsPlugin) then begin
      LogError(targetModFileName + ' is not loaded.');  // ★★★ ライブラリ関数 ★★★
      Exit;
    end;

    LogInfo('Processing file: ' + targetModFileName);  // ★★★ ライブラリ関数 ★★★

    ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
    if not Assigned(ammoGroup) then begin
      LogInfo(' - No AMMO group found in ' + targetModFileName);  // ★★★ ライブラリ関数 ★★★
      Exit;
    end;

    for i := 0 to ElementCount(ammoGroup) - 1 do begin
      rec := ElementByIndex(ammoGroup, i);
      editorID := EditorID(rec);
      // ★★★ 修正: ライブラリ関数を使用 ★★★
      fullFormID := GetFullFormID(rec);

      AddINIKeyValue(iniLines, fullFormID, editorID);  // ★★★ ライブラリ関数 ★★★
    end;

    iniFilePath := outputDir + 'munitions_ammo_ids.ini';
    SaveINIToFile(iniLines, iniFilePath, ElementCount(ammoGroup));  // ★★★ ライブラリ関数 ★★★
    
    LogComplete('Munitions ammo ID export');  // ★★★ ライブラリ関数 ★★★
    
  except
    on E: Exception do begin
      LogError(E.Message);  // ★★★ ライブラリ関数 ★★★
      Result := 1;
    end;
  end;

  iniLines.Free;
end;

end.

