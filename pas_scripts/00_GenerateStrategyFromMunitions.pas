// ... 既存 uses のまま ...

// 文字列正規化（EditorID 用）
function NormalizeEditorId(const s: string): string;
var
  t: string;
begin
  t := LowerCase(s);
  // ノイズ語・接頭辞の除去
  t := StringReplace(t, 'munitions_', '', [rfReplaceAll]);
  t := StringReplace(t, 'ammo', '',       [rfReplaceAll]);
  t := StringReplace(t, '_',    '',       [rfReplaceAll]);
  t := StringReplace(t, '-',    '',       [rfReplaceAll]);
  t := StringReplace(t, 'caliber','',     [rfReplaceAll]);
  t := StringReplace(t, 'round', '',      [rfReplaceAll]);
  t := StringReplace(t, 'shell', '',      [rfReplaceAll]);
  t := StringReplace(t, 'ball',  '',      [rfReplaceAll]);
  // mm は残す（545mm, 57mm などの判定に使う）
  Result := t;
end;

// ... Finalize 内のループの前後を一部変更 ...
  for i := 0 to Pred(ElementCount(ammoGroup)) do begin
    ammoRec := ElementByIndex(ammoGroup, i);
    editorId := EditorID(ammoRec);
    formId := IntToHex(GetLoadOrderFormID(ammoRec), 8);

    // 追加: 正規化文字列で判定
    var normalizedId := NormalizeEditorId(editorId);

    classified := False;
    for j := 0 to Pred(classificationRules.Count) do begin
      rule := classificationRules.Items[j] as TJSONObject;
      if rule.FindValue('keywords', jsonValue) and (jsonValue is TJSONArray) then begin
        keywords := jsonValue as TJSONArray;
        for k := 0 to Pred(keywords.Count) do begin
          if Pos(LowerCase(keywords.Items[k].Value), normalizedId) > 0 then begin
            // 以下は既存処理のまま
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
      // 既存の WARNING ログをそのまま維持
      AddMessage('[AutoPatcher] WARNING: ' + editorId + ' は自動分類できませんでした。');
      // 既存の未分類処理（Uncategorized）もそのまま
      newAmmoNode := TJSONObject.Create;
      newAmmoNode.AddPair('Category', TJSONString.Create('Uncategorized'));
      newAmmoNode.AddPair('Power', TJSONNumber.Create(0));
      ammoClassificationNode.AddPair(formId, newAmmoNode);
    end;
  end;