unit UserScript;

uses 'lib/mteBase', 'lib/mteElements', 'lib/mteFiles', 'lib/mteRecords';

var
  jsonOutput: TStringList;
  keywordMap: TStringList;
  outputDir: string;

// ★★★ 修正箇所: 正しいヘルパー関数に置き換え ★★★
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

//============================================================================
function Initialize: integer;
begin
  jsonOutput := TStringList.Create;
  keywordMap := TStringList.Create;

  outputDir := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\Output\';

  keywordMap.Add('Grenade=Explosive|3');
  keywordMap.Add('Rocket=Explosive|4');
  keywordMap.Add('Arrow=Primitive|1');
  keywordMap.Add('9mm=StandardBallistic_Low|1');
  
  Result := 0;
end;

//============================================================================
function Process(e: IInterface): integer;
begin
  Result := 0;
end;

//============================================================================
function Finalize: integer;
var
  i, j: integer;
  munitionsPlugin, ammoGroup, ammoRec: IInterface;
  editorId, formId, category, power: string;
  classified: boolean;
  firstEntry: boolean;
  categoryData: TStringList;
  outputFilePath: string;
begin
  Result := 0;
  
  munitionsPlugin := FileByName('Munitions - An Ammo Expansion.esl');
  if not Assigned(munitionsPlugin) then begin
    AddMessage('[AutoPatcher] ERROR: "Munitions - An Ammo Expansion.esl" がロードされていません。');
    Exit;
  end;

  jsonOutput.Add('{');
  jsonOutput.Add('  "ammo_classification": {');
  ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
  firstEntry := True;
  
  for i := 0 to Pred(ElementCount(ammoGroup)) do begin
    ammoRec := ElementByIndex(ammoGroup, i);
    editorId := EditorID(ammoRec);
    formId := IntToHex(GetLoadOrderFormID(ammoRec), 8);
    
    classified := False;
    for j := 0 to Pred(keywordMap.Count) do begin
      if Pos(keywordMap.Names[j], editorId) > 0 then begin
        categoryData := TStringList.Create;
        categoryData.Delimiter := '|';
        categoryData.DelimitedText := keywordMap.ValueFromIndex[j];
        category := categoryData[0];
        power := categoryData[1];
        categoryData.Free;
        
        if not firstEntry then 
          jsonOutput.Strings[jsonOutput.Count - 1] := jsonOutput.Strings[jsonOutput.Count - 1] + ',';
        jsonOutput.Add(Format('    "%s": "%s"', [formId, category]));
        
        classified := True;
        firstEntry := False;
        Break;
      end;
    end;
    
    if not classified then begin
       if not firstEntry then 
          jsonOutput.Strings[jsonOutput.Count - 1] := jsonOutput.Strings[jsonOutput.Count - 1] + ',';
      jsonOutput.Add(Format('    "%s": "Uncategorized"', [formId]));
      firstEntry := False;
      AddMessage('[AutoPatcher] WARNING: ' + editorId + ' は自動分類できませんでした。');
    end;
  end;
  jsonOutput.Add('  },');
  jsonOutput.Add('');

  jsonOutput.Add('  "allocation_matrix": {');
  jsonOutput.Add('    "Raiders": { "Primitive": 30, "StandardBallistic_Low": 40, "Shotgun_Standard": 20, "StandardBallistic_Medium": 10, "AdvancedBallistic": 0, "Explosive": 0 },');
  jsonOutput.Add('    "SuperMutants": { "Primitive": 20, "StandardBallistic_Low": 25, "StandardBallistic_Medium": 20, "AdvancedBallistic": 15, "MilitaryGrade": 10, "Shotgun_Heavy": 5, "Explosive": 5 }');
  jsonOutput.Add('  },');
  jsonOutput.Add('');

  jsonOutput.Add('  "faction_leveled_lists": {');
  jsonOutput.Add('    "Raiders": "LLI_Raider_Weapons",');
  jsonOutput.Add('    "Gunners": "LLI_Faction_Gunner_Weapons",');
  jsonOutput.Add('    "Institute": "LLI_Faction_Institute_Weapons",');
  jsonOutput.Add('    "BrotherhoodOfSteel": "LLI_Faction_BoS_Weapons",');
  jsonOutput.Add('    "SuperMutants": "LLI_Faction_SuperMutant_Weapons"');
  jsonOutput.Add('  }');
  jsonOutput.Add('');

  jsonOutput.Add('}');

  if not DirectoryExists(outputDir) then
    ForceDirectories(outputDir);
  outputFilePath := outputDir + 'strategy.json';
  jsonOutput.SaveToFile(outputFilePath);
  AddMessage('[AutoPatcher] SUCCESS: "' + outputFilePath + '" が正常に生成されました。');
  
  AddMessage('[AutoPatcher] Strategy JSON generation complete.');

  jsonOutput.Free;
  keywordMap.Free;
end;

end.

