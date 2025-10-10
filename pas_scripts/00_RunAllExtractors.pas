// e:\Munition_AutoPatcher_v1.1\pas_scripts\00_RunAllExtractors.pas

unit RunAllExtractors;

interface
uses
  xEditAPI, AutoPatcherCore;

implementation

function Initialize: integer;
var
  success: Boolean;
begin
  Result := 0; // 成功をデフォルトとする
  success := True;

  AddMessage('[AutoPatcher] All-in-one extraction process started.');

  // --- ステップ1: 武器と弾薬のマッピングを抽出 ---
  if success and (AP_Run_ExtractWeaponAmmoMapping() <> 0) then
  begin
    LogError('Weapon and ammo mapping extraction failed.');
    success := False;
  end;

  // --- ステップ2: レベルドリストをエクスポート ---
  if success and (AP_Run_ExportWeaponLeveledLists() <> 0) then
  begin
    LogError('Leveled list export failed.');
    success := False;
  end;

  // --- ステップ3: Munitionsの弾薬IDをエクスポート ---
  if success and (AP_Run_ExportMunitionsAmmoIDs() <> 0) then
  begin
    LogError('Munitions ammo ID export failed.');
    success := False;
  end;

  // ★★★ 確認・追加ポイント ★★★
  // --- ステップ4: 武器詳細情報のエクスポート ---
  if success and (AP_Run_ExportWeaponAmmoDetails() <> 0) then
  begin
    LogError('Weapon ammo details export failed.');
    success := False;
  end;

  // --- 最終結果 ---
  if success then
  begin
    LogComplete('All extractions'); // 成功メッセージ
    Result := 0;
  end
  else
  begin
    LogError('One or more extraction steps failed. Check log for details.');
    Result := 1; // 失敗
  end;
end;

end.
