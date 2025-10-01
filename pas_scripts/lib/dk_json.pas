unit dk_json;

interface

uses
  SysUtils, Classes;

type
  TJSONException = class(Exception);

  TJSONType = (jtObject, jtArray, jtString, jtNumber, jtBoolean, jtNull);

  TJSON = class
  private
    FType: TJSONType;
    FValue: string;
    FItems: TList;
    function GetItem(Index: Integer): TJSON;
    function GetItem(const Name: string): TJSON;
    function GetCount: Integer;
    function GetAsString: string;
    function GetAsInt: Integer;
    function GetAsFloat: Double;
    function GetAsBoolean: Boolean;
  public
    constructor Create(AType: TJSONType);
    destructor Destroy; override;
    class function Parse(const AJSON: string): TJSON;
    procedure Add(const AName: string; AItem: TJSON); overload;
    procedure Add(AItem: TJSON); overload;
    function IndexOf(const AName: string): Integer;
    function GetName(AIndex: Integer): string;
    property `Type`: TJSONType read FType;
    property Items[Index: Integer]: TJSON read GetItem; default;
    property Items[const Name: string]: TJSON read GetItem;
    property Count: Integer read GetCount;
    property AsString: string read GetAsString;
    property AsInt: Integer read GetAsInt;
    property AsFloat: Double read GetAsFloat;
    property AsBoolean: Boolean read GetAsBoolean;
  end;

implementation

type
  TJSONParser = class
  private
    FText: string;
    FPos: Integer;
    function ParseValue: TJSON;
    function ParseObject: TJSON;
    function ParseArray: TJSON;
    function ParseString: TJSON;
    function ParseNumber: TJSON;
    function ParseBoolean: TJSON;
    function ParseNull: TJSON;
    procedure SkipWhitespace;
    function ReadString: string;
  public
    constructor Create(const AText: string);
    function Parse: TJSON;
  end;

{ TJSON }

constructor TJSON.Create(AType: TJSONType);
begin
  inherited Create;
  FType := AType;
  if (AType = jtObject) or (AType = jtArray) then
    FItems := TList.Create;
end;

destructor TJSON.Destroy;
var
  I: Integer;
begin
  if FItems <> nil then
  begin
    for I := 0 to FItems.Count - 1 do
      TJSON(FItems[I]).Free;
    FItems.Free;
  end;
  inherited Destroy;
end;

class function TJSON.Parse(const AJSON: string): TJSON;
var
  Parser: TJSONParser;
begin
  Parser := TJSONParser.Create(AJSON);
  try
    Result := Parser.Parse;
  finally
    Parser.Free;
  end;
end;

procedure TJSON.Add(const AName: string; AItem: TJSON);
begin
  if FType <> jtObject then
    raise TJSONException.Create('Not an object');
  AItem.FValue := AName;
  FItems.Add(AItem);
end;

procedure TJSON.Add(AItem: TJSON);
begin
  if FType <> jtArray then
    raise TJSONException.Create('Not an array');
  FItems.Add(AItem);
end;

function TJSON.IndexOf(const AName: string): Integer;
var
  I: Integer;
begin
  Result := -1;
  if FType = jtObject then
    for I := 0 to FItems.Count - 1 do
      if AnsiSameText(TJSON(FItems[I]).FValue, AName) then
      begin
        Result := I;
        Break;
      end;
end;

function TJSON.GetName(AIndex: Integer): string;
begin
  if (FType = jtObject) and (AIndex >= 0) and (AIndex < FItems.Count) then
    Result := TJSON(FItems[AIndex]).FValue
  else
    Result := '';
end;

function TJSON.GetItem(Index: Integer): TJSON;
begin
  Result := TJSON(FItems[Index]);
end;

function TJSON.GetItem(const Name: string): TJSON;
var
  Index: Integer;
begin
  Index := IndexOf(Name);
  if Index = -1 then
    raise TJSONException.Create('Item not found: ' + Name);
  Result := TJSON(FItems[Index]);
end;

function TJSON.GetCount: Integer;
begin
  if FItems <> nil then
    Result := FItems.Count
  else
    Result := 0;
end;

function TJSON.GetAsString: string;
begin
  Result := FValue;
end;

function TJSON.GetAsInt: Integer;
begin
  Result := StrToIntDef(FValue, 0);
end;

function TJSON.GetAsFloat: Double;
begin
  Result := StrToFloat(FValue);
end;

function TJSON.GetAsBoolean: Boolean;
begin
  Result := AnsiSameText(FValue, 'true');
end;

{ TJSONParser }

constructor TJSONParser.Create(const AText: string);
begin
  inherited Create;
  FText := AText;
  FPos := 1;
end;

function TJSONParser.Parse: TJSON;
begin
  SkipWhitespace;
  Result := ParseValue;
end;

procedure TJSONParser.SkipWhitespace;
begin
  while (FPos <= Length(FText)) and (FText[FPos] <= ' ') do
    Inc(FPos);
end;

function TJSONParser.ParseValue: TJSON;
begin
  SkipWhitespace;
  case FText[FPos] of
    '{': Result := ParseObject;
    '[': Result := ParseArray;
    '"': Result := ParseString;
    '-', '0'..'9': Result := ParseNumber;
    't', 'f': Result := ParseBoolean;
    'n': Result := ParseNull;
  else
    raise TJSONException.Create('Invalid character at pos ' + IntToStr(FPos));
  end;
end;

function TJSONParser.ParseObject: TJSON;
var
  Name: string;
begin
  Result := TJSON.Create(jtObject);
  Inc(FPos); // Skip '{'
  SkipWhitespace;
  while FText[FPos] <> '}' do
  begin
    Name := ReadString;
    SkipWhitespace;
    if FText[FPos] <> ':' then
      raise TJSONException.Create('":" expected at pos ' + IntToStr(FPos));
    Inc(FPos);
    Result.Add(Name, ParseValue);
    SkipWhitespace;
    if FText[FPos] = ',' then
    begin
      Inc(FPos);
      SkipWhitespace;
    end
    else if FText[FPos] <> '}' then
      raise TJSONException.Create('"}" or "," expected at pos ' + IntToStr(FPos));
  end;
  Inc(FPos); // Skip '}'
end;

function TJSONParser.ParseArray: TJSON;
begin
  Result := TJSON.Create(jtArray);
  Inc(FPos); // Skip '['
  SkipWhitespace;
  while FText[FPos] <> ']' do
  begin
    Result.Add(ParseValue);
    SkipWhitespace;
    if FText[FPos] = ',' then
    begin
      Inc(FPos);
      SkipWhitespace;
    end
    else if FText[FPos] <> ']' then
      raise TJSONException.Create('"]" or "," expected at pos ' + IntToStr(FPos));
  end;
  Inc(FPos); // Skip ']'
end;

function TJSONParser.ParseString: TJSON;
begin
  Result := TJSON.Create(jtString);
  Result.FValue := ReadString;
end;

function TJSONParser.ReadString: string;
var
  Start: Integer;
begin
  if FText[FPos] <> '"' then
    raise TJSONException.Create('""" expected at pos ' + IntToStr(FPos));
  Inc(FPos);
  Start := FPos;
  while FText[FPos] <> '"' do
    Inc(FPos);
  Result := Copy(FText, Start, FPos - Start);
  Inc(FPos);
end;

function TJSONParser.ParseNumber: TJSON;
var
  Start: Integer;
begin
  Result := TJSON.Create(jtNumber);
  Start := FPos;
  while (FPos <= Length(FText)) and (FText[FPos] in ['0'..'9', '.', '-', 'e', 'E', '+']) do
    Inc(FPos);
  Result.FValue := Copy(FText, Start, FPos - Start);
end;

function TJSONParser.ParseBoolean: TJSON;
begin
  Result := TJSON.Create(jtBoolean);
  if Copy(FText, FPos, 4) = 'true' then
  begin
    Result.FValue := 'true';
    Inc(FPos, 4);
  end
  else if Copy(FText, FPos, 5) = 'false' then
  begin
    Result.FValue := 'false';
    Inc(FPos, 5);
  end
  else
    raise TJSONException.Create('Invalid boolean at pos ' + IntToStr(FPos));
end;

function TJSONParser.ParseNull: TJSON;
begin
  Result := TJSON.Create(jtNull);
  if Copy(FText, FPos, 4) = 'null' then
    Inc(FPos, 4)
  else
    raise TJSONException.Create('Invalid null at pos ' + IntToStr(FPos));
end;

end.