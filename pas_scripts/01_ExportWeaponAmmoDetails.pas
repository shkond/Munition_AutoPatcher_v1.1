unit ExportWeaponAmmoDetails;

interface
implementation

uses
  xEditAPI,
  Classes,
  SysUtils,
  StrUtils,
  Windows,
  'lib/AutoPatcherLib';

function Initialize: Integer;
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

end.