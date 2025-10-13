unit minimal_probe;

interface
uses xEditAPI, Classes, SysUtils;

implementation

function Initialize: integer;
var
  outp: string;
  _early: TStringList;
begin
  Result := 0;
  try
    AddMessage('[MINIMAL_PROBE] Initialize start');

    // TStringList probe (from AutoPatcherCore)
    try
      _early := TStringList.Create;
      try
        _early.Add('[EarlyProbe] Probe from minimal_probe');
        _early.Add(Format('Time=%s', [DateTimeToStr(Now)]));
        AddMessage(Format('[MINIMAL_EARLY] %s', [DateTimeToStr(Now)]));
      finally
        _early.Free;
      end;
      AddMessage('[MINIMAL_PROBE] TStringList probe succeeded');
    except
      on E: Exception do begin
        AddMessage('[MINIMAL_PROBE] TStringList probe failed: ' + E.Message);
        raise; // re-raise so outer handler records Result=1 and message
      end;
    end;

    // Original raw file write probe
    outp := '\early_minimal_probe_' + IntToStr(Trunc(Now)) + '.txt';
    AddMessage('[MINIMAL_PROBE] about to emit main probe message');
    try
      AddMessage(Format('[MINIMAL_PROBE_MAIN] %s outp=%s', [DateTimeToStr(Now), outp]));
    except
      AddMessage('[MINIMAL_PROBE] failed to AddMessage main');
      raise;
    end;

    // Indicate success explicitly
    AddMessage('[COMPLETE] Minimal probe (about to return 0)');
    AddMessage('[RETURN] 0');
  except
    on E: Exception do
    begin
        try
          AddMessage('[ERROR] Minimal probe exception: ' + E.ClassName + ' ' + E.Message);
        except
        end;
      Result := 1;
    end;
  end;
end;

end.