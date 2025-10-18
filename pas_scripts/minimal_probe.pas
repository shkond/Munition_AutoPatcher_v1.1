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
      _early: TStringList;
      markerF: TextFile;
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

        // Write a marker file into the project's Output/intermediate directory so
        // the Orchestrator can detect success even if MO2/xEdit console output
        // isn't available to the runner. Use a relative path under the script's
        // working directory (xEdit's current dir will allow writing to the host
        // filesystem in most setups).
        try
          // Write a simple marker file to C:\temp so Orchestrator can detect success.
          outp := 'C:\\temp\\probe_done_' + IntToStr(Trunc(Now)) + '.txt';
          try
            AssignFile(markerF, outp);
            {$I-}
            Rewrite(markerF);
            WriteLn(markerF, '[MINIMAL_PROBE_MARKER] OK');
            CloseFile(markerF);
            {$I+}
          except
            // ignore file write errors
          end;
        except
          // ignore any outer errors
        end;