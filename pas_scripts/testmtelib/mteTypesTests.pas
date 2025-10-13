{
  mteTypes Tests
  Tests for functions in mteTypes
}

unit mteTypesTests;

uses '..\lib\mteBase', '..\lib\mteTypes', '..\lib\jvTest';

const
  mteTestVersion = '0.0.0.1';

{
  mteVersionTest:
  Raises an exception if the testing suite is not built to target the 
  version of mteFunctions the user is running.
}
procedure mteVersionTest;
begin
  if mteVersion <> mteTestVersion then
    raise Exception.Create('mteTypesTests - These tests are meant to be '+
      'run on mteFunctions v'+mteTestVersion+', you are running '+
      mteVersion+'.  Testing terminated.');
end;

{
  TestBooleanHelpers:
  Tests the boolean helper functions in mteTypes.
}
procedure TestBooleanHelpers;
begin
  (*** IfThenVar Tests ***)
  Describe('IfThenVar');
  try
    Describe('nil values');
    try
      ExpectEqual(IfThenVar(true, nil, nil), nil, 'ATrue: Should return properly');
      ExpectEqual(IfThenVar(false, nil, nil), nil, 'AFalse: Should return properly');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Integer values');
    try
      ExpectEqual(IfThenVar(true, 1, 0), 1, 'ATrue: Should return properly');
      ExpectEqual(IfThenVar(false, 1, 0), 0, 'AFalse: Should return properly');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Floating point values');
    try
      ExpectEqual(IfThenVar(true, 1.0, 0.5), 1.0, 'ATrue: Should return properly');
      ExpectEqual(IfThenVar(false, 1.0, 0.5), 0.5, 'AFalse: Should return properly');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('String values');
    try
      ExpectEqual(IfThenVar(true, 'True', 'False'), 'True', 'ATrue: Should return properly');
      ExpectEqual(IfThenVar(false, 'True', 'False'), 'False', 'AFalse: Should return properly');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** BoolToStr Tests ***)
  Describe('BoolToStr');
  try
    ExpectEqual(BoolToStr(true), 'True', 'True should return "True"');
    ExpectEqual(BoolToStr(false), 'False', 'false should return "False"');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{
  TestIntegerHelpers:
  Tests the integer helper functions in mteTypes.
}
procedure TestIntegerHelpers;
var
  bCaughtException: boolean;
begin
  (*** IntLog Tests ***)
  Describe('IntLog');
  try
    Describe('Base 0');
    try
      bCaughtException := false;
      try
        IntLog(2, 0);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'IntLog: Base cannot be less than or equal to 1',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Value 0');
    try
      ExpectEqual(IntLog(0, 2), 0, 'Should return 0');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Base 1');
    try
      bCaughtException := false;
      try
        IntLog(4, 1);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'IntLog: Base cannot be less than or equal to 1',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Negative Base');
    try
      bCaughtException := false;
      try
        IntLog(4, -2);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'IntLog: Base cannot be less than or equal to 1',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Positive Base');
    try
      ExpectEqual(IntLog(2, 2), 1, 'Should handle equality');
      ExpectEqual(IntLog(4, 2), 2, 'Should handle perfect logarithms correctly');
      ExpectEqual(IntLog(257, 2), 8, 'Should ignore small remainders correctly');
      ExpectEqual(IntLog(255, 2), 7, 'Should ignore large remainders correctly');
      ExpectEqual(IntLog(IntPower(1024, 3), 1024), 3, 'Should handle large values correctly');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  
  (*** FormatFileSize Tests ***)
  Describe('FormatFileSize');
  try
    Describe('Zero');
    try
      ExpectEqual(FormatFileSize(0), '0 bytes', 'Should return "0 bytes"');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Bytes');
    try
      ExpectEqual(FormatFileSize(-1), '-1 bytes', 'Lowest negative value should be -1 bytes');
      ExpectEqual(FormatFileSize(1), '1 bytes', 'Lowest positive value should be 1 bytes');
      ExpectEqual(FormatFileSize(1023), '1023 bytes', 'Upper limit should be 1023 bytes');
      ExpectEqual(FormatFileSize(-1023), '-1023 bytes', 'Lower limit should be -1023 bytes');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Kilobytes');
    try
      ExpectEqual(FormatFileSize(-1024), '-1.00 KB', '-1024 bytes should equal -1.00 KB');
      ExpectEqual(FormatFileSize(1024), '1.00 KB', '1024 bytes should equal 1.00 KB');
      ExpectEqual(FormatFileSize(1024 * 1024 - 1), '1024.00 KB', 'Upper limit should be 1024.00 KB');
      ExpectEqual(FormatFileSize(-1024 * 1024 + 1), '-1024.00 KB', 'Lower limit should be -1024.00 KB');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Megabytes');
    try
      ExpectEqual(FormatFileSize(-1048576), '-1.00 MB', '-1048576 bytes should equal -1.00 MB');
      ExpectEqual(FormatFileSize(1048576), '1.00 MB', '1048576 bytes should equal 1.00 MB');
      ExpectEqual(FormatFileSize(1024 * 1048576 - 1), '1024.00 MB', 'Upper limit should be 1024.00 MB');
      ExpectEqual(FormatFileSize(-1024 * 1048576 + 1), '-1024.00 MB', 'Lower limit should be -1024.00 MB');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Gigabytes');
    try
      ExpectEqual(FormatFileSize(-1073741824), '-1.00 GB', '-1073741824 bytes should equal -1.00 GB');
      ExpectEqual(FormatFileSize(1073741824), '1.00 GB', '1073741824 bytes should equal 1.00 GB');
      ExpectEqual(FormatFileSize(2147483647), '2.00 GB', 'Upper limit should be 2.00 GB');
      ExpectEqual(FormatFileSize(-2147483647), '-2.00 GB', 'Lower limit should be -2.00 GB');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{
  TestStringHelpers:
  Tests the string helper functions in mteTypes.
}
procedure TestStringHelpers;
var
  bCaughtException: boolean;
begin
  (*** TitleCase Tests ***)
  Describe('TitleCase');
  try
    Describe('Empty string');
    try
      ExpectEqual(TitleCase(''), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('One letter');
    try
      ExpectEqual(TitleCase('a'), 'A', 'If lowercase, should return the letter uppercase');
      ExpectEqual(TitleCase('B'), 'B', 'If uppercase, should not change');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Several words separated by spaces');
    try
      ExpectEqual(TitleCase('this is a title'), 'This Is A Title', 
        'Should capitalize the first letter of each word');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Other delimiters');
    try
      ExpectEqual(TitleCase('this.is [a title] {hi} (good) "please"'), 'This.Is [A Title] {Hi} (Good) "Please"', 
        'Should capitalize the first letter of each word');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** SentenceCase Tests ***)
  Describe('SentenceCase');
  try
    Describe('Empty string');
    try
      ExpectEqual(SentenceCase(''), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('One letter');
    try
      ExpectEqual(SentenceCase('a'), 'A', 'If lowercase, should return the letter uppercase');
      ExpectEqual(SentenceCase('B'), 'B', 'If uppercase, should not change');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('One sentence');
    try
      ExpectEqual(SentenceCase('this is an example sentence.'), 'This is an example sentence.', 
        'Should capitalize the first letter of the sentence');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Two sentences');
    try
      ExpectEqual(SentenceCase('wow!  that''s really cool.'), 'Wow!  That''s really cool.', 
        'Should capitalize the first letter of each sentence');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Mixed punctuation');
    try
      ExpectEqual(SentenceCase('what? are. you!  this,has.no!spaces?o'), 'What? Are. You!  This,has.No!Spaces?O',
        'Should capitalize the first letter of each word after .!?');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** ItPos ***)
  Describe('ItPos');
  try
    Describe('Target is less than 1');
    try
      ExpectEqual(ItPos('b', 'aba', 0), 0, 'Should return 0');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Search String is empty');
    try
      ExpectEqual(ItPos('a', '', 1), 0, 'Should return 0');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Substring is empty');
    try
      ExpectEqual(ItPos('', 'hi', 2), 0, 'Should return 0');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Equal, single character');
    try
      ExpectEqual(ItPos('a', 'a', 1), 1, 'Should return 1 if target iteration is 1');
      ExpectEqual(ItPos('a', 'a', 2), 0, 'Should return 0 if target iteration is greater than 1');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Equal, multiple characters');
    try
      ExpectEqual(ItPos('ababa', 'ababa', 1), 1, 'Should return 1 if target iteration is 1');
      ExpectEqual(ItPos('ababa', 'ababa', 2), 0, 'Should return 0 if target iteration is greater than 1');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Contains, single character');
    try
      ExpectEqual(ItPos('3', '123453', 1), 3, 'Should return first position if target iteration is 1');
      ExpectEqual(ItPos('3', '123453', 2), 6, 'Should return second position if target iteration is 2');
      ExpectEqual(ItPos('3', '123453', 3), 0, 
        'Should return 0 if target iteration exceeds the number of iterations present');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Contains, multiple characters');
    try
      ExpectEqual(ItPos('are', 'are you aware of the area, snare', 1), 1, 
        'Should return first position if target iteration is 1');
      ExpectEqual(ItPos('are', 'are you aware of the area, snare', 2), 11, 
        'Should return second position if target iteration is 2');
      ExpectEqual(ItPos('are', 'are you aware of the area, snare', 3), 22, 
        'Should return third position if target iteration is 3');
      ExpectEqual(ItPos('are', 'are you aware of the area, snare', 4), 30, 
        'Should return fourth position if target iteration is 4');
      ExpectEqual(ItPos('are', 'are you aware of the area, snare', 5), 0, 
        'Should return 0 if target iteration exceeds the number of iterations present');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** LastPos ***)
  Describe('LastPos');
  try
    Describe('Search String is empty');
    try
      ExpectEqual(LastPos('a', ''), 0, 'Should return 0');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Substring is empty');
    try
      ExpectEqual(LastPos('', 'hi'), 2, 'Should return Length(str)');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Equal');
    try
      ExpectEqual(LastPos('a', 'a'), 1, 'Single Character: Should return 1');
      ExpectEqual(LastPos('ababa', 'ababa'), 1, 'Multiple Characters: Should return 1');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Contains');
    try
      ExpectEqual(LastPos('sub', 'A sub, another sub.  Not a sud.'), 16, 'Should return the last position');
      ExpectEqual(LastPos('sub', 'A sub, another sub.  SUB.'), 16, 'Should be case sensitive');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
  
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  
  
  (*** CopyFromTo Tests ***)
  Describe('CopyFromTo');
  try
    Describe('Start index less than 1');
    try
      bCaughtException := false;
      try
        CopyFromTo('1234', -1, 2);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'CopyFromTo: Start index cannot be less than 1', 
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('End index < start index');
    try
      bCaughtException := false;
      try
        CopyFromTo('1234', 3, 1);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'CopyFromTo: End index cannot be less than the start index', 
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Start index = end index');
    try
      ExpectEqual(CopyFromTo('12345', 2, 2), '2', 'Should return the character at the index');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Start index > length of input string');
    try
      ExpectEqual(CopyFromTo('123', 4, 5), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('End index > length of input string');
    try
      ExpectEqual(CopyFromTo('12345', 3, 7), '345', 
        'Should return a substring from the start index to the last valid index');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Full length of string');
    try
      ExpectEqual(CopyFromTo('abcdefg', 1, 7), 'abcdefg', 'Should return the input string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** ReverseString Tests ***)
  Describe('ReverseString');
  try
    Describe('Empty string');
    try
      ExpectEqual(ReverseString(''), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Single character string');
    try
      ExpectEqual(ReverseString('a'), 'a', 'Should return the same string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Multiple character string');
    try
      ExpectEqual(ReverseString('backwards'), 'sdrawkcab', 'Should reverse the string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** GetTextIn Tests ***)
  Describe('GetTextIn');
  try
    Describe('Empty string');
    try
      ExpectEqual(GetTextIn('', '(', ')'), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('No delimiters present');
    try
      ExpectEqual(GetTextIn('Some string with no delims', '(', ')'), '',
        'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Open delimiter, but no close delimiter');
    try
      ExpectEqual(GetTextIn('<This is never closed', '<', '>'), '',
        'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Close delimiter, but no open delimiter');
    try
      ExpectEqual(GetTextIn('This> is never opened', '<', '>'), '',
        'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Entire string is delimited');
    try
      ExpectEqual(GetTextIn('(I''m in parenthesis!)', '(', ')'), 'I''m in parenthesis!',
        'Should return the string inside the delimiters');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Nested delimiters');
    try
      ExpectEqual(GetTextIn('[This [is a [triply] [nested] string]]', '[', ']'), 'triply', 
        'Should return the most inner delimited text');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Open and close delimiters the same');
    try
      ExpectEqual(GetTextIn('Here is,a comma,separated text', ',', ','), 'a comma',
        'Should return the text between two instances of the delimiter character');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
  
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** StrEndsWith Tests **)
  Describe('StrEndsWith');
  try
    Describe('Empty string');
    try
      Expect(StrEndsWith('', ''), 'Empty string ends with empty string');
      Expect(not StrEndsWith('', 'a'), 'Empty string doesn''t end with non-empty string');
      Expect(StrEndsWith('a', ''), 'String ends with empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Equality');
    try
      Expect(StrEndsWith('a', 'a'), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Inequality');
    try
      Expect(not StrEndsWith('a', 'b'), 'Should return false');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Second string longer than first');
    try
      Expect(not StrEndsWith('a', 'aa'), 'Should return false');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Valid');
    try
      Expect(StrEndsWith('This is a sample string.', 'string.'), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Invalid');
    try
      Expect(not StrEndsWith('This is a sample string.', 'b string.'), 
        'Should return false when beginning differs');
      Expect(not StrEndsWith('This is a sample string.', 'str1ng.'), 
        'Should return false when middle differs');
      Expect(not StrEndsWith('This is a sample string.', 'string. '), 
        'Should return false when ending differs');
      Expect(not StrEndsWith('This is a sample string.', 'STRING.'), 
        'Should be case sensitive');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** AppendIfMissing Tests **)
  Describe('AppendIfMissing');
  try
    ExpectEqual(AppendIfMissing('Sample', ' string'), 'Sample string', 
      'Should append when missing');
    ExpectEqual(AppendIfMissing('Sample string', ' string'), 'Sample string', 
      'Should not append when present');
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** RemoveFromEnd Tests **)
  Describe('RemoveFromEnd');
  try
    ExpectEqual(RemoveFromEnd('Sample string', 'string '), 'Sample string', 
      'Should not remove when missing');
    ExpectEqual(RemoveFromEnd('Sample string', ' string'), 'Sample', 
      'Should remove when present');
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** StrStartsWith Tests **)
  Describe('StrStartsWith');
  try
    Describe('Empty string');
    try
      Expect(StrStartsWith('', ''), 'Empty string starts with empty string');
      Expect(not StrStartsWith('', 'a'), 'Empty string doesn''t start with non-empty string');
      Expect(StrStartsWith('a', ''), 'String starts with empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Equality');
    try
      Expect(StrStartsWith('a', 'a'), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Inequality');
    try
      Expect(not StrStartsWith('a', 'b'), 'Should return false');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Second string longer than first');
    try
      Expect(not StrStartsWith('a', 'aa'), 'Should return false');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Valid');
    try
      Expect(StrStartsWith('This is a sample string.', 'This '), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Invalid');
    try
      Expect(not StrStartsWith('This is a sample string.', 'This b'), 
        'Should return false when end differs');
      Expect(not StrStartsWith('This is a sample string.', 'Th1s '), 
        'Should return false when middle differs');
      Expect(not StrStartsWith('This is a sample string.', ' This'), 
        'Should return false when start differs');
      Expect(not StrStartsWith('This is a sample string.', 'THIS '), 
        'Should be case sensitive');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** PrependIfMissing Tests **)
  Describe('PrependIfMissing');
  try
    ExpectEqual(PrependIfMissing('string', 'Sample '), 'Sample string', 
      'Should prepend when missing');
    ExpectEqual(PrependIfMissing('Sample string', 'Sample '), 'Sample string', 
      'Should not prepend when present');
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** RemoveFromStart Tests **)
  Describe('RemoveFromStart');
  try
    ExpectEqual(RemoveFromStart('Sample string', ' Sample'), 'Sample string', 
      'Should not remove when missing');
    ExpectEqual(RemoveFromStart('Sample string', 'Sample '), 'string', 
      'Should remove when present');
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** IsURL Tests **)
  Describe('IsURL');
  try
    Describe('http');
    try
      Expect(IsURL('http://www.google.com'), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('https');
    try
      Expect(IsURL('https://www.google.com'), 'Should return true');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Case sensitivty');
    try
      Expect(IsURL('Https://www.google.com'), 'Should be case insensitive');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Unsupported protocol');
    try
      Expect(not IsURL('ftp://www.google.com'), 'Should return false');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** Wordwrap Tests **)
  Describe('Wordwrap');
  try
    Describe('Empty string');
    try
      ExpectEqual(Wordwrap('', 1), '', 'Should return an empty string');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Words longer than character limit');
    try
      ExpectEqual(Wordwrap('This is a test', 3), 'This '#13#10'is '#13#10'a '#13#10'test', 
        'Should insert a newline after each word');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Never reach character limit');
    try
      ExpectEqual(Wordwrap('This is a test', 15), 'This is a test', 
        'Should not insert any newlines');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Multiple multi-word lines');
    try
      ExpectEqual(Wordwrap('This is a test of multiple lines being wrapped', 9), 
        'This is a '#13#10'test of '#13#10'multiple '#13#10'lines '#13#10'being '#13#10'wrapped', 
        'Should insert newlines in correct locations');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Lines that are already wrapped');
    try
      ExpectEqual(Wordwrap('This is a '#13#10'test of '#13#10'multiple '#13#10'lines '#13#10'being '#13#10'wrapped', 9), 
        'This is a '#13#10'test of '#13#10'multiple '#13#10'lines '#13#10'being '#13#10'wrapped', 
        'Should not insert more newlines');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{
  TestDateAndTimeHelpers:
  Tests the date and time helper functions in mteTypes.
}
procedure TestDateAndTimeHelpers;
begin
  (** DayOf Tests **)
  Describe('DayOf');
  try
    ExpectEqual(DayOf(0.0), 0, '0.0 should return 0');
    ExpectEqual(DayOf(1.0), 1, '1.0 should return 1');
    ExpectEqual(DayOf(1.999999), 1, '1.999999 should return 1');
    ExpectEqual(DayOf(123456.7890), 123456, '123456.7890 should return 123456');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** HourOf Tests **)
  Describe('HourOf');
  try
    ExpectEqual(HourOf(0.0), 0, '0.0 should return 0');
    ExpectEqual(HourOf(1.0 * aHour), 1, '1.0 hour should return 1');
    ExpectEqual(HourOf(1.99999 * aHour), 1, '1.99999 hours should return 1');
    ExpectEqual(HourOf(23.999 * aHour), 23, '23.999 hours should return 23');
    ExpectEqual(HourOf(24.0 * aHour), 0, '24.0 hours should return 0');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** MinuteOf Tests **)
  Describe('MinuteOf');
  try
    ExpectEqual(MinuteOf(0.0), 0, '0.0 should return 0');
    ExpectEqual(MinuteOf(1.0 * aMinute), 1, '1.0 minute should return 1');
    ExpectEqual(MinuteOf(1.9999 * aMinute), 1, '1.9999 minutes should return 1');
    ExpectEqual(MinuteOf(59.99 * aMinute), 59, '59.99 minutes should return 59');
    ExpectEqual(MinuteOf(60.0 * aMinute), 0, '60.0 minutes should return 0');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** RateStr Tests **)
  Describe('RateStr');
  try
    ExpectEqual(RateStr(0.0), 'Every 0.0 minutes', '0 should render as "Every 0.0 minutes"');
    ExpectEqual(RateStr(10.3 * aMinute), 'Every 10.3 minutes', 'Minutes should render');
    ExpectEqual(RateStr(6.7 * aHour), 'Every 6.7 hours', 'Hours should render');
    ExpectEqual(RateStr(3.6 * aDay), 'Every 3.6 days', 'Days should render');
    ExpectEqual(RateStr(1.0 * aHour), 'Every 60.0 minutes', '1 hour should render as 60.0 minutes');
    ExpectEqual(RateStr(1.0 * aDay), 'Every 24.0 hours', '1 day should render as 24.0 hours');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** DurationStr Tests **)
  Describe('DurationStr');
  try
    ExpectEqual(DurationStr(0.0, ' '), '0d 0h 0m', 'No time passed should render 0d 0h 0m');
    ExpectEqual(DurationStr(aMinute, ' '), '0d 0h 1m', 'Minutes should render');
    ExpectEqual(DurationStr(aHour, ' '), '0d 1h 0m', 'Hours should render');
    ExpectEqual(DurationStr(aDay, ' '), '1d 0h 0m', 'Days should render');
    ExpectEqual(DurationStr(aDay + aHour + aMinute, ':'), '1d:1h:1m', 
      'Custom separator should render');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{
  TestColorHelpers:
  Tests color helper functions in mteTypes.
}
procedure TestColorHelpers;
begin
  (*** GetRValue ***)
  Describe('GetRValue');
  try
    ExpectEqual(GetRValue(clBlack), $00, 'clBlack red value = $00');
    ExpectEqual(GetRValue(clWhite), $FF, 'clWhite red value = $FF');
    ExpectEqual(GetRValue(clGray), $80, 'clGray red value = $80');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** GetGValue ***)
  Describe('GetGValue');
  try
    ExpectEqual(GetGValue(clBlack), $00, 'clBlack green value = $00');
    ExpectEqual(GetGValue(clWhite), $FF, 'clWhite green value = $FF');
    ExpectEqual(GetGValue(clGray), $80, 'clGray green value = $80');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** GetBValue ***)
  Describe('GetBValue');
  try
    ExpectEqual(GetBValue(clBlack), $00, 'clBlack blue value = $00');
    ExpectEqual(GetBValue(clWhite), $FF, 'clWhite blue value = $FF');
    ExpectEqual(GetBValue(clGray), $80, 'clGray blue value = $80');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** RGB ***)
  Describe('RGB');
  try
    ExpectEqual(RGB(0, 0, 0), clBlack, '0, 0, 0 should be clBlack');
    ExpectEqual(RGB(255, 255, 255), clWhite, '255, 255, 255 should be clWhite');
    ExpectEqual(RGB(128, 128, 128), clGray, '80, 80, 80 should be clGray');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** ColorToHex ***)
  Describe('ColorToHex');
  try
    ExpectEqual(ColorToHex(clBlack), '000000', 'clBlack should be "000000"');
    ExpectEqual(ColorToHex(clWhite), 'FFFFFF', 'clWhite should be "FFFFFF"');
    ExpectEqual(ColorToHex(clGray), '808080', 'clGray should be "808080"');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (*** HexToColor ***)
  Describe('HexToColor');
  try
    ExpectEqual(HexToColor('000000'), clBlack, '"000000" should be clBlack');
    ExpectEqual(HexToColor('FFFFFF'), clWhite, '"FFFFFF" should be clWhite');
    ExpectEqual(HexToColor('808080'), clGray, '"808080" should be clGray');
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{
  TestClassHelpers:
  Tests class helper functions in mteTypes.
}
procedure TestClassHelpers;
var
  bCaughtException: boolean;
  sl, slNoInit: TStringList;
  s: String;
  lst: TList;
begin
  (** IntegerListSum Tests **)
  Describe('IntegerListSum');
  try
    Describe('Input list not assigned');
    try
      bCaughtException := false;
      try
        IntegerListSum(sl, 2);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'IntegerListSum: Input stringlist is not assigned',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('Input maxIndex is out of bounds');
    try
      bCaughtException := false;
      sl := TStringList.Create;
      sl.Add('2');
      try
        IntegerListSum(sl, 1);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'IntegerListSum: Input maxIndex is out of bounds for the input stringlist',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    Describe('Item in list is not an integer');
    try
      bCaughtException := false;
      sl := TStringList.Create;
      sl.Add('a');
      sl.Add('-3');
      try
        IntegerListSum(sl, 1);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, '''''a'''' is not a valid integer value',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    Describe('Input index is negative');
    try
      sl := TStringList.Create;
      sl.Add('2');
      ExpectEqual(IntegerListSum(sl, -1), 0, 'Should return 0');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    Describe('One item in the list');
    try
      sl := TStringList.Create;
      sl.Add('2');
      ExpectEqual(IntegerListSum(sl, 0), 2, 'Should return the value of the item');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    Describe('Multiple items in the list');
    try
      sl := TStringList.Create;
      sl.Add('2');
      sl.Add('-3');
      sl.Add('9');
      sl.Add('173674');
      sl.Add('3');
      ExpectEqual(IntegerListSum(sl, 4), 173685, 
        'Should return complete sum when maxIndex = Count - 1');
      ExpectEqual(IntegerListSum(sl, 2), 8, 
        'Should return partial sum when maxIndex < Count - 1');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** SaveStringToFile Tests **)
  Describe('SaveStringToFile');
  try
    s := 'This is an example string';
    SaveStringToFile(s, 'MTE-TestFile.txt');
    sl := TStringList.Create;
    sl.LoadFromFile('MTE-TestFile.txt');
    Expect(FileExists('MTE-TestFile.txt'), 'The file should exist');
    ExpectEqual(sl.Text, 'This is an example string'#13#10, 
      'The file contents should match the input string');
    DeleteFile('MTE-TestFile.txt');
    FreeAndNil(sl);
    Pass;
  except
    on x: Exception do begin
      if Assigned(sl) then FreeAndNil(sl);
      Fail(x);
    end;
  end;
  
  (** LoadStringFromFile Tests **)
  Describe('LoadStringFromFile');
  try
    sl := TStringList.Create;
    sl.Add('This is an example string');
    sl.SavetoFile('MTE-TestFile.txt');
    FreeAndNil(sl);
    s := '';
    s := LoadStringFromFile('MTE-TestFile.txt');
    ExpectEqual(s, 'This is an example string'#13#10, 
      'The loaded string should match the file contents');
    Pass;
  except
    on x: Exception do begin
      if Assigned(sl) then FreeAndNil(sl);
      Fail(x);
    end;
  end;
  
  (** ApplyTemplate Tests **)
  Describe('ApplyTemplate');
  try
    Describe('Input list not assigned');
    try
      bCaughtException := false;
      try
        ApplyTemplate('Hi {{Person}}', slNoInit);
      except
        on x: Exception do begin
          bCaughtException := true;
          ExpectEqual(x.Message, 'ApplyTemplate: Input map stringlist is not assigned',
            'Should raise the correct exception');
        end;
      end;
      Expect(bCaughtException, 'Should have raised an exception');
      Pass;
    except
      on x: Exception do Fail(x);
    end;
    
    Describe('No matches in template');
    try
      sl := TStringList.Create;
      sl.Add('Person=George');
      ExpectEqual(ApplyTemplate('This is {{NotAMatch}}', sl), 'This is {{NotAMatch}}',
        'Should return the template unchanged');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    Describe('Multiple matches');
    try
      sl := TStringList.Create;
      sl.Add('Person=George');
      sl.Add('Day=Friday');
      ExpectEqual(ApplyTemplate('Hope your {{Day}} is going well, {{Person}}', sl), 
        'Hope your Friday is going well, George', 'Should substitute the mapped values');
      FreeAndNil(sl);
      Pass;
    except
      on x: Exception do begin
        if Assigned(sl) then FreeAndNil(sl);
        Fail(x);
      end;
    end;
    
    // all tests passed?
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  (** TryToFree Tests **)
  Describe('TryToFree');
  try
    TryToFree(slNoInit);
    Expect(not Assigned(slNoInit), 'Uninitialized object should be ignored');
    sl := TStringList.Create;
    TryToFree(sl);
    Expect(not Assigned(sl), 'Initialized object should be freed');
    TryToFree(sl);
    Expect(not Assigned(sl), 'Freed object should be ignored');
    Pass;
  except
    on x: Exception do begin
      if Assigned(sl) then FreeAndNil(sl);
      Fail(x);
    end;
  end;
end;

{ 
  TestMteTypes:
  Tests the functions in mteTypes using the jvTest framework.
}
procedure TestMteTypes;
begin
  Describe('Boolean Helpers');
  try
    TestBooleanHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  Describe('Integer Helpers');
  try
    TestIntegerHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  Describe('String Helpers');
  try
    TestStringHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  Describe('Date and Time Helpers');
  try
    TestDateAndTimeHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  Describe('Color Helpers');
  try
    TestColorHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
  
  Describe('Class Helpers');
  try
    TestClassHelpers;
    Pass;
  except
    on x: Exception do Fail(x);
  end;
end;

{******************************************************************************}
{ ENTRY POINTS
  Entry points for when the script is run in xEdit.
    - Initialize
}
{******************************************************************************}

function Initialize: Integer;
begin
  // don't perform tests if on wrong version
  mteVersionTest;
  
  jvtInitialize;
  // perform tests
  TestMteTypes;
  
  // finalize jvt
  jvtPrintReport;
  jvtFinalize;
end;

end.