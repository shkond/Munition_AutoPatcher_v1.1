unit UserScript;

uses 'lib/mteBase', 'lib/mteElements', 'lib/mteFiles', 'lib/mteRecords', 'SysUtils', 'Classes', 'System.JSON';

var
  outputDir: string;
  jsonRoot: TJSONObject;          // JSONファイル全体のルート
  classificationRules: TJSONArray; // JSONから読み込んだ分類ルールを保持
  strategyJson: TJSONObject;      // 既存のstrategy.jsonを保持

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
  Result := 0;
  jsonRoot := nil;
  classificationRules := nil;
  strategyJson := nil;

  // --- 変数定義 ---
  var sl: TStringList;
  var categoriesPath, strategyPath: string;
  var jsonValue: TJSONValue;

  outputDir := EnsureTrailingSlash(ProgramPath) + 'Edit Scripts\Output\';
  sl := TStringList.Create;

  // --- ammo_categories.json を読み込む ---
  try
    categoriesPath := EnsureTrailingSlash(ProgramPath) + '..' + PathDelim + 'ammo_categories.json';
    sl.LoadFromFile(categoriesPath);
    jsonValue := TJSONObject.ParseJSONValue(sl.Text);
    if not Assigned(jsonValue) or not (jsonValue is TJSONObject) then
      raise Exception.Create('JSONのルートがオブジェクトではありません。');
    jsonRoot := jsonValue as TJSONObject;

    if jsonRoot.FindValue('classification_rules', jsonValue) and (jsonValue is TJSONArray) then
      classificationRules := jsonValue as TJSONArray
    else
      raise Exception.Create('キー "classification_rules" が見つからないか、配列ではありません。');
      
  except
    on E: Exception do begin
      AddMessage('[AutoPatcher] FATAL: 分類ルールファイル (' + categoriesPath + ') の読み込みに失敗しました。Error: ' + E.Message);
      Result := 1;
      sl.Free;
      Exit;
    end;
  end;

  // ★★★ 修正点: 既存の strategy.json を読み込む ★★★
  strategyPath := EnsureTrailingSlash(ProgramPath) + '..' + PathDelim + 'strategy.json';
  if FileExists(strategyPath) then begin
    try
      jsonValue := nil;
      sl.LoadFromFile(strategyPath);
      jsonValue := TJSONObject.ParseJSONValue(sl.Text);
      if Assigned(jsonValue) and (jsonValue is TJSONObject) then
        strategyJson := jsonValue as TJSONObject
      else if Assigned(jsonValue) then begin
        jsonValue.Free; // オブジェクトでない場合は破棄
      end;
    except
      on E: Exception do
        AddMessage('[AutoPatcher] WARNING: 既存の strategy.json の解析に失敗しました。新しいファイルを作成します。Error: ' + E.Message);
    end;
  end else begin
    AddMessage('[AutoPatcher] INFO: 既存の strategy.json が見つかりません。新しいファイルを作成します。');
  end;

  if not Assigned(strategyJson) then
    strategyJson := TJSONObject.Create;

  sl.Free;

end;

//============================================================================
function Process(e: IInterface): integer;
begin
  Result := 0;
end;

//============================================================================
function Finalize: integer;
var
  i, j, k, powerInt: integer;
  munitionsPlugin, ammoGroup, ammoRec, jsonValue: IInterface;
  editorId, formId, category: string;
  classified: boolean;
  rule: TJSONObject;
  keywords: TJSONArray;
  newAmmoNode, ammoClassificationNode: TJSONObject;
  outputFilePath: string;
begin
  Result := 0;
  
  munitionsPlugin := FileByName('Munitions - An Ammo Expansion.esl');
  if not Assigned(munitionsPlugin) then begin
    AddMessage('[AutoPatcher] ERROR: "Munitions - An Ammo Expansion.esl" がロードされていません。');
    Exit;
  end;

  if not Assigned(classificationRules) then begin
    AddMessage('[AutoPatcher] ERROR: 分類ルールが読み込まれていません。');
    Result := 1;
    Exit;
  end;

  // ammo_classification ノードを取得または新規作成
  if strategyJson.FindValue('ammo_classification', jsonValue) and (jsonValue is TJSONObject) then begin
    ammoClassificationNode := jsonValue as TJSONObject;
    ammoClassificationNode.Clear; // 既存のノードをクリアして再生成
  end else begin
    // AddPairは第二引数の所有権を持つため、Createしたものを直接渡す
    ammoClassificationNode := TJSONObject.Create;
    strategyJson.AddPair('ammo_classification', ammoClassificationNode);
  end;

  ammoGroup := GroupBySignature(munitionsPlugin, 'AMMO');
  
  for i := 0 to Pred(ElementCount(ammoGroup)) do begin
    ammoRec := ElementByIndex(ammoGroup, i);
    editorId := EditorID(ammoRec);
    formId := IntToHex(GetLoadOrderFormID(ammoRec), 8);

    classified := False;
    for j := 0 to Pred(classificationRules.Count) do begin
      rule := classificationRules.Items[j] as TJSONObject;
      if rule.FindValue('keywords', jsonValue) and (jsonValue is TJSONArray) then begin
        keywords := jsonValue as TJSONArray;
        for k := 0 to Pred(keywords.Count) do begin
          if Pos(LowerCase(keywords.Items[k].Value), LowerCase(editorId)) > 0 then begin
            category := rule.GetValue<string>('Category');
            powerInt := rule.GetValue<integer>('Power');
            
            newAmmoNode := TJSONObject.Create;
            newAmmoNode.AddPair('Category', TJSONString.Create(category));
            newAmmoNode.AddPair('Power', TJSONNumber.Create(powerInt));
            ammoClassificationNode.AddPair(formId, newAmmoNode);
            
            classified := True;
            Break;
          end;
        end;
      end;
      if classified then Break;
    end;
    
    if not classified then begin
      newAmmoNode := TJSONObject.Create;
      newAmmoNode.AddPair('Category', TJSONString.Create('Uncategorized'));
      newAmmoNode.AddPair('Power', TJSONNumber.Create(0));
      ammoClassificationNode.AddPair(formId, newAmmoNode);
      AddMessage('[AutoPatcher] WARNING: ' + editorId + ' は自動分類できませんでした。');
    end;
  end;

  if not DirectoryExists(outputDir) then
    ForceDirectories(outputDir);
  outputFilePath := outputDir + 'strategy.json';
  TFile.WriteAllText(outputFilePath, strategyJson.ToJSON(true)); // trueはpretty-print
  AddMessage('[AutoPatcher] SUCCESS: "' + outputFilePath + '" が正常に生成されました。');
  
  AddMessage('[AutoPatcher] Strategy JSON generation complete.');

  if Assigned(strategyJson) then strategyJson.Free;

end;

end.
