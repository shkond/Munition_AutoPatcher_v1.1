# GUI Layout Visualization

## Before Changes

```
┌─ 環境設定 ────────────────────────────────────────────────────┐
│                                                                 │
│ ☑ Mod Organizer 2 を使用してxEditを起動する                      │
│                                                                 │
│ ┌─ MO2設定 ───────────────────────────────────────────┐       │
│ │                                                       │       │
│ │ MO2実行ファイル:      [___________________________] [参照...]│
│ │ プロファイル名:        [___________________________]         │
│ │ 実行ファイルリスト名:   [___________________________]         │
│ │ Overwriteフォルダ:    [___________________________] [参照...]│
│ │                                                       │       │
│ └───────────────────────────────────────────────────┘       │
│                                                                 │
│ xEdit実行ファイル:      [_______________________________] [参照...]
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

## After Changes (NEW FIELDS ADDED ★★★)

```
┌─ 環境設定 ────────────────────────────────────────────────────┐
│                                                                 │
│ ☑ Mod Organizer 2 を使用してxEditを起動する                      │
│                                                                 │
│ ┌─ MO2設定 ───────────────────────────────────────────┐       │
│ │                                                       │       │
│ │ MO2実行ファイル:      [___________________________] [参照...]│
│ │ プロファイル名:        [___________________________]         │
│ │ 実行ファイルリスト名:   [___________________________]         │
│ │ Overwriteフォルダ:    [___________________________] [参照...]│
│ │ ★ ショートカット形式:  [auto ▼__________________]   ★★★    │
│ │ ★ インスタンス名:      [___________________________]   ★★★  │
│ │                                                       │       │
│ └───────────────────────────────────────────────────┘       │
│                                                                 │
│ xEdit実行ファイル:      [_______________________________] [参照...]
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

## New Field Details

### ショートカット形式 (Combobox - Dropdown)
- **Type**: Read-only dropdown (Combobox)
- **Location**: Row 4 in MO2 settings frame
- **Options**:
  - `auto` (Default) - 自動検出 - Tries multiple formats
  - `no_colon` - moshortcut://xEdit
  - `with_colon` - moshortcut://:xEdit  
  - `instance` - moshortcut://Fallout 4/xEdit
- **Purpose**: Allows user to select or auto-detect the correct moshortcut URI format

### インスタンス名 (Text Entry)
- **Type**: Text input field (Entry)
- **Location**: Row 5 in MO2 settings frame
- **Default**: Empty string
- **Purpose**: Specifies the MO2 instance name for multi-instance setups
- **Example**: "Fallout 4", "Skyrim Special Edition"

## Config.ini Mapping

```ini
[Environment]
...existing settings...
mo2_shortcut_format = auto      # ← NEW
mo2_instance_name =             # ← NEW (empty by default)
```

## User Workflow

1. User opens GUI
2. Enables "Mod Organizer 2 を使用してxEditを起動する" checkbox
3. MO2 settings section becomes enabled
4. **NEW**: User can now:
   - Select moshortcut format from dropdown (or leave as "auto")
   - Enter instance name if using multi-instance MO2
5. Settings are saved to config.ini when user clicks save
6. When running xEdit, the tool automatically uses the correct URI format
