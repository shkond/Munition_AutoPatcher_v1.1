"""
Test Robco INI generation with sample data
"""
import json
import logging
from pathlib import Path
from config_manager import ConfigManager
from Orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# Create test data
output_dir = Path('Output')
output_dir.mkdir(exist_ok=True)

# Sample weapon data
weapon_data = [
    {"editor_id": "TestPistol", "full_name": "Test Pistol", "ammo_form_id": "FE008030"},
    {"editor_id": "TestRifle", "full_name": "Test Rifle", "ammo_form_id": "FE008029"},
    {"editor_id": "TestShotgun", "full_name": "Test Shotgun", "ammo_form_id": "FE008005"},
]

weapon_file = output_dir / 'weapon_ammo_map.json'
weapon_file.write_text(json.dumps(weapon_data, indent=2), encoding='utf-8')

# Sample leveled lists
leveled_lists = {
    "LeveledLists": {
        "LLI_Raider_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D0E"},
        "LLI_Faction_Gunner_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D12"},
        "LLI_Faction_Institute_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D1A"},
        "LLI_Faction_SuperMutant_Weapons": {"plugin": "Fallout4.esm", "formid": "00187D16"}
    }
}

ll_file = output_dir / 'leveled_lists.json'
ll_file.write_text(json.dumps(leveled_lists, indent=2), encoding='utf-8')

# Sample strategy (from existing file)
strategy_file = Path('strategy.json')
if strategy_file.exists():
    print(f"✓ Using existing {strategy_file}")
else:
    print(f"✗ {strategy_file} not found, test may fail")

print("\n" + "=" * 60)
print("  Testing Robco INI Generation")
print("=" * 60)

config = ConfigManager('config.ini')
orchestrator = Orchestrator(config)

# Test the generation
try:
    result = orchestrator._generate_robco_ini()
    
    if result:
        print("\n✓ INI generation succeeded")
        
        # Check output file
        robco_ini = Path('Robco Patcher') / 'robco_ammo_patch.ini'
        if robco_ini.exists():
            print(f"\n✓ Output file created: {robco_ini}")
            print("\nFirst 50 lines:")
            print("-" * 60)
            with open(robco_ini, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 50:
                        print("... (truncated)")
                        break
                    print(line.rstrip())
        else:
            print(f"\n✗ Output file not found: {robco_ini}")
    else:
        print("\n✗ INI generation failed")
        
except Exception as e:
    print(f"\n✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
