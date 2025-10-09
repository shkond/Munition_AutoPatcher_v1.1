# User Guide: MO2 moshortcut Configuration

## Quick Start

### For Most Users (Recommended)

1. **Open the GUI** (`AutoPatcherGUI.py`)

2. **Enable MO2 integration**:
   - ☑ Check "Mod Organizer 2 を使用してxEditを起動する"

3. **Configure basic MO2 settings**:
   - **MO2実行ファイル**: Browse to `ModOrganizer.exe`
   - **プロファイル名**: Enter your MO2 profile name (e.g., "Default", "new2")
   - **実行ファイルリスト名**: Enter "xEdit" (or the name you used in MO2's executable list)
   - **Overwriteフォルダ**: Should auto-detect; if not, browse to MO2's overwrite folder

4. **Leave new settings as default** ⭐:
   - **ショートカット形式**: Leave as `auto`
   - **インスタンス名**: Leave empty

5. **Save settings** and run your process

The tool will automatically detect the correct moshortcut format!

---

## When Auto-Detection Fails

If xEdit doesn't start or you see timeout errors:

### Step 1: Run Diagnostics

```bash
python debug_mo2_shortcut.py
```

This will:
- Test all moshortcut URI formats
- Show which one works
- Provide recommended settings

### Step 2: Apply Recommended Settings

If the diagnostic shows, for example:
```
推奨設定:
  config.ini に以下を設定:
    mo2_shortcut_format = no_colon
```

Then in the GUI:
1. Set **ショートカット形式** to `no_colon`
2. Save settings
3. Try again

---

## Advanced: Multi-Instance MO2 Setup

If you manage multiple games with one MO2 installation:

1. **Find your instance name**:
   - Open MO2
   - Look at the window title or settings
   - Common examples: "Fallout 4", "Skyrim Special Edition"

2. **Configure in GUI**:
   - **ショートカット形式**: Select `instance`
   - **インスタンス名**: Enter your instance name (e.g., "Fallout 4")

3. **Save and test**

---

## Understanding the Settings

### ショートカット形式 (Shortcut Format)

| Setting | When to Use | URI Format |
|---------|-------------|------------|
| **auto** | Default - try this first | Tries all formats automatically |
| **no_colon** | If diagnostic recommends it | `moshortcut://xEdit` |
| **with_colon** | If diagnostic recommends it | `moshortcut://:xEdit` |
| **instance** | Multi-instance MO2 setup | `moshortcut://Fallout 4/xEdit` |

### インスタンス名 (Instance Name)

- **When needed**: Only for `instance` mode
- **What to enter**: The exact name MO2 uses for your game instance
- **Example**: "Fallout 4" (with space, exact capitalization)

---

## Troubleshooting Common Issues

### Issue: "xEdit起動検出タイムアウト"

**Meaning**: The tool couldn't detect xEdit starting up

**Solutions**:
1. Run `python debug_mo2_shortcut.py` to find working format
2. Check that MO2's executable list has "xEdit" entry
3. Verify profile name matches exactly
4. Try running xEdit manually from MO2 first

### Issue: "Cannot start -n" Error

**Meaning**: Invalid arguments being passed to xEdit

**Solution**: 
✅ This is **fixed** in the new version! Update your code.

The problem was embedded quotes in arguments. The new version removes them.

### Issue: xEdit Starts Then Immediately Closes

**Possible causes**:
1. **RivaTuner/RTSS interference**:
   - Disable RTSS temporarily
   - Or add MO2/xEdit to RTSS exclusion list

2. **Wrong profile/settings**:
   - Verify profile name is correct
   - Check MO2 logs for errors

3. **Mod conflicts**:
   - Try with a minimal mod list first

### Issue: GUI Fields Not Saving

**Check**:
1. Settings are saved when you click the save button
2. config.ini file is not read-only
3. You have write permissions in the application folder

---

## Manual Testing (PowerShell)

If you want to test moshortcut URIs manually:

```powershell
# Test 1: No colon format
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "YourProfile", "moshortcut://xEdit"

# Test 2: With colon format
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "YourProfile", "moshortcut://:xEdit"

# Test 3: Instance format
Start-Process "E:/MO2/ModOrganizer.exe" -ArgumentList "-p", "YourProfile", "moshortcut://Fallout 4/xEdit"
```

Replace:
- `E:/MO2/ModOrganizer.exe` with your MO2 path
- `YourProfile` with your profile name
- `Fallout 4` with your instance name (if applicable)

---

## FAQ

**Q: Do I need to set these every time?**  
A: No. Once configured and saved, settings persist in config.ini.

**Q: What if I don't use MO2?**  
A: Uncheck "Mod Organizer 2 を使用してxEditを起動する". The new fields won't affect you.

**Q: Can I switch between formats?**  
A: Yes. Change the dropdown and save. The tool will use the new setting immediately.

**Q: What's the difference between the formats?**  
A: Technical differences in how MO2 parses the URI. Most environments work with `no_colon`, but some need the alternatives. That's why `auto` tries them all.

**Q: Will this break my existing setup?**  
A: No. The default `auto` mode preserves existing behavior while adding fallback options.

**Q: How do I know which format is being used?**  
A: Check the log file (`patcher.log`). It will show:
```
[xEdit] moshortcut URI 自動検出モード - 試行: moshortcut://xEdit
```

---

## Getting Help

If you're still having issues:

1. **Collect information**:
   - Run `python debug_mo2_shortcut.py` and save output
   - Check `patcher.log` for error messages
   - Note your MO2 version and setup type

2. **Check documentation**:
   - See `TROUBLESHOOTING.md` for detailed solutions
   - See `IMPLEMENTATION_SUMMARY.md` for technical details

3. **Report issue** with:
   - Your config.ini [Environment] section
   - Diagnostic script output
   - Log excerpts showing the error
   - MO2 and xEdit versions

---

## Configuration File Reference

Your `config.ini` should look like this:

```ini
[Environment]
use_mo2 = True
mo2_executable_path = E:/MO2/ModOrganizer.exe
xedit_profile_name = Default
mo2_xedit_entry_name = xEdit
mo2_overwrite_dir = E:/mo2data/overwrite
mo2_shortcut_format = auto          # ← NEW: auto, no_colon, with_colon, or instance
mo2_instance_name =                 # ← NEW: Empty unless using instance mode

[Paths]
xedit_executable = E:/fo4mod/xedit/xEdit.exe
...
```

---

## What Changed?

### Previous Behavior
- Hardcoded to one URI format: `moshortcut://xEdit`
- No way to change it without editing code
- Embedded quotes caused argument parsing issues

### New Behavior
- ✅ Auto-detects best format
- ✅ User can override via GUI
- ✅ Supports multiple formats including instance-qualified
- ✅ Fixed quote handling
- ✅ Diagnostic tool to test formats

---

**Version**: 2.6  
**Last Updated**: 2025-01-09
