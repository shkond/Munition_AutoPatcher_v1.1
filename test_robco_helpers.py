"""
Test the new Robco INI helper functions
"""
import json
from pathlib import Path
from config_manager import ConfigManager
from Orchestrator import Orchestrator
import logging

logging.basicConfig(level=logging.INFO)

config = ConfigManager('config.ini')
orchestrator = Orchestrator(config)

print("=" * 60)
print("  Testing Robco Helper Functions")
print("=" * 60)

# Test 1: _invert_robco_chance
print("\n[Test 1] _invert_robco_chance")
test_cases = [
    (0.7, 30),   # 70% spawn -> 30% exclude
    (0.5, 50),   # 50% spawn -> 50% exclude
    (1.0, 0),    # 100% spawn -> 0% exclude
    (0.0, 100),  # 0% spawn -> 100% exclude
]
for weight, expected in test_cases:
    result = orchestrator._invert_robco_chance(weight)
    status = "✓" if result == expected else "✗"
    print(f"  {status} weight={weight} -> {result} (expected {expected})")

# Test 2: _category_to_ammo_group_for_robco
print("\n[Test 2] _category_to_ammo_group_for_robco")
test_categories = [
    ("StandardBallistic_Low", "pistol"),
    ("handgun", "pistol"),
    ("StandardBallistic_Medium", "rifle"),
    ("AdvancedBallistic", "rifle"),
    ("MilitaryGrade", "rifle"),
    ("Shotgun_Standard", "rifle"),
    ("Energy_Advanced", "rifle"),
    ("Explosive", "rifle"),
    ("Primitive", "rifle"),
    ("Exotic", "rifle"),
]
for category, expected in test_categories:
    result = orchestrator._category_to_ammo_group_for_robco(category)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {category} -> {result} (expected {expected})")

# Test 3: _load_leveled_lists_json (if file exists)
print("\n[Test 3] _load_leveled_lists_json")
output_dir = Path('Output')
if output_dir.exists():
    # Create a test file
    test_ll_file = output_dir / 'leveled_lists.json'
    test_data = {
        "LeveledLists": {
            "LLI_Raider_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D0E"},
            "LLI_Faction_Gunner_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D12"}
        }
    }
    test_ll_file.write_text(json.dumps(test_data, indent=2), encoding='utf-8')
    
    result = orchestrator._load_leveled_lists_json(output_dir)
    print(f"  Loaded {len(result)} leveled lists")
    for ll_name, ll_info in result.items():
        print(f"    - {ll_name}: {ll_info['plugin']}|{ll_info['formid']}")
    
    # Clean up test file
    test_ll_file.unlink()
else:
    print("  ⚠ Output directory not found, skipping test")

# Test 4: _load_ammo_map (JSON preferred, INI fallback)
print("\n[Test 4] _load_ammo_map")
ammo_map_file = Path('ammo_map.ini')
if ammo_map_file.exists():
    result = orchestrator._load_ammo_map(ammo_map_file)
    print(f"  Loaded {len(result)} ammo mappings from INI")
    for orig, target in list(result.items())[:3]:
        print(f"    - {orig} -> {target}")
else:
    print("  ⚠ ammo_map.ini not found, skipping test")

# Test JSON version
test_json = Path('ammo_map.json')
if not test_json.exists() and output_dir.exists():
    test_json_data = {
        "UnmappedAmmo": {
            "01001945": "FE008029",
            "011263AD": "FE0086D6"
        }
    }
    test_json.write_text(json.dumps(test_json_data, indent=2), encoding='utf-8')
    result_json = orchestrator._load_ammo_map(test_json)
    print(f"\n  Loaded {len(result_json)} ammo mappings from JSON")
    for orig, target in result_json.items():
        print(f"    - {orig} -> {target}")
    test_json.unlink()

print("\n" + "=" * 60)
print("  Test Complete")
print("=" * 60)
