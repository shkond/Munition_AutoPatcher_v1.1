# Leveled List Export and Robco INI Generation Enhancements

## Overview

This update adds support for exporting leveled list plugin|formid data from xEdit and consuming it in the Orchestrator to generate Robco Patcher INI files. The changes maintain backward compatibility while adding new features for improved diagnostics and flexibility.

## Changes Summary

### 1. Pascal Script: 02_ExportWeaponLeveledLists.pas

**Purpose**: Export specific leveled list records with their plugin and FormID information.

**Key Features**:
- Exports 4 specific leveled lists by EditorID:
  - `LLI_Raider_Weapons`
  - `LLI_Faction_Gunner_Weapons`
  - `LLI_Faction_Institute_Weapons`
  - `LLI_Faction_SuperMutant_Weapons`

- Uses `MainRecordByEditorID` for fast lookup with a fallback mechanism that walks LVLI groups if the function is not available

- Output format (`leveled_lists.json`):
```json
{
  "LeveledLists": {
    "LLI_Raider_Weapons": { "plugin": "Fallout4.esm", "formid": "00187D0E" },
    "LLI_Faction_Gunner_Weapons": { "plugin": "Fallout4.esm", "formid": "00187D12" },
    "LLI_Faction_Institute_Weapons": { "plugin": "Fallout4.esm", "formid": "00187D1A" },
    "LLI_Faction_SuperMutant_Weapons": { "plugin": "Fallout4.esm", "formid": "00187D16" }
  }
}
```

### 2. Python Orchestrator: New Helper Functions

#### `_load_leveled_lists_json(output_dir: Path) -> dict`
Loads the `leveled_lists.json` file and returns a dictionary mapping EditorID to plugin/formid info.

#### `_load_ammo_map(ammo_map_file: Path) -> dict`
Loads ammo mappings from either:
1. `ammo_map.json` (preferred, if exists)
2. `ammo_map.ini` (fallback)

Returns a dictionary mapping original FormID to target FormID (lowercase).

#### `_invert_robco_chance(weight: float) -> int`
Converts allocation matrix weights (0..1) to Robco Patcher exclusion percentages:
- Input: 0.7 (70% spawn chance)
- Output: 30 (30% exclusion chance)

#### `_category_to_ammo_group_for_robco(category: str) -> str`
Maps ammo categories to Robco Patcher ammo groups:
- **pistol**: Categories containing "low" or "handgun"
- **rifle**: All other categories (medium, advanced, military, shotgun, energy, explosive, primitive, exotic)

### 3. Updated Robco INI Generation

**New Output Format**: `robco_ammo_patch.ini` (configurable via config.ini)

**Key Features**:

1. **Diagnostics Logging**:
   - Weapon count from weapon_ammo_map.json
   - Ammo classification count
   - Ammo map size (JSON/INI)
   - Category breakdown
   - Leveled lists used from strategy.json

2. **Settings Section**:
```ini
[Settings]
filterByAmmos=Munitions - An Ammo Expansion.esl|
```

3. **Weapon Sections** (new format):
```ini
[Weapon.EditorID]
editorId = EditorID
name = Full Name
leveledLists = Fallout4.esm|00187D0E@pistol:30, Fallout4.esm|00187D12@rifle:20
```

Where:
- Section key is EditorID (or plugin|formid if available)
- `leveledLists` uses format: `plugin|formid@ammogroup:invertedchance`
- Inverted chances: allocation_matrix weight of 0.7 → 30% exclusion

## Backward Compatibility

✅ **Maintained**:
- Existing `ammo_map.ini` format still works (automatic fallback)
- Graceful handling when `leveled_lists.json` is missing
- Works with weapon_ammo_map.json without plugin/formid fields
- Strategy.json format unchanged

## Testing

Three test files included:

1. **test_robco_helpers.py**: Tests individual helper functions
2. **test_robco_generation.py**: Tests full INI generation with sample data
3. **test_comprehensive.py**: Comprehensive validation of all features

All tests pass successfully.

## Usage Example

### Running the Orchestrator
```python
from config_manager import ConfigManager
from Orchestrator import Orchestrator

config = ConfigManager('config.ini')
orchestrator = Orchestrator(config)

# Run full process (includes leveled list export and Robco INI generation)
success = orchestrator.run_full_process()
```

### Manual Testing
```bash
# Test helper functions
python test_robco_helpers.py

# Test INI generation
python test_robco_generation.py

# Run comprehensive tests
python test_comprehensive.py
```

## Configuration

In `config.ini`, you can customize:
```ini
[Parameters]
robco_output_filename = robco_ammo_patch.ini
```

## Files Modified

- `pas_scripts/02_ExportWeaponLeveledLists.pas` - Complete rewrite
- `Orchestrator.py` - Added 4 helper methods, updated `_generate_robco_ini()`
- `.gitignore` - Added `Robco Patcher/*.ini`

## Files Added

- `test_robco_helpers.py`
- `test_robco_generation.py`
- `test_comprehensive.py`

## Dependencies

No new dependencies required. Uses existing:
- Python 3.x
- json, configparser, pathlib (standard library)
- psutil (already required)
