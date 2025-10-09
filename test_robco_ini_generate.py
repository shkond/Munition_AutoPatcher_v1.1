#!/usr/bin/env python3
"""
Test script for robco_ini_generate module.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from robco_ini_generate import generate_robco_inis

def test_robco_ini_generation():
    """Test the Robco INI generation with real files."""
    project_root = Path(__file__).parent
    strategy_file = project_root / 'strategy.json'
    output_dir = project_root / 'Output'
    robco_patcher_dir = project_root / 'Robco Patcher'
    ammo_map_file = project_root / 'ammo_map.ini'
    
    print("=" * 60)
    print("Testing Robco INI Generation")
    print("=" * 60)
    print(f"Strategy file: {strategy_file}")
    print(f"Output dir: {output_dir}")
    print(f"Robco Patcher dir: {robco_patcher_dir}")
    print(f"Ammo map file: {ammo_map_file}")
    print("=" * 60)
    
    success = generate_robco_inis(
        strategy_file=strategy_file,
        output_dir=output_dir,
        robco_patcher_dir=robco_patcher_dir,
        ammo_map_file=ammo_map_file if ammo_map_file.is_file() else None
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Test PASSED: Robco INI generation succeeded")
        print("=" * 60)
        
        # Check if output file exists
        output_file = robco_patcher_dir / 'robco_ammo_patch.ini'
        if output_file.is_file():
            print(f"\n✓ Output file created: {output_file}")
            print("\nFile contents:")
            print("-" * 60)
            print(output_file.read_text(encoding='utf-8'))
            print("-" * 60)
        else:
            print(f"\n✗ Output file not found: {output_file}")
            return False
        
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ Test FAILED: Robco INI generation failed")
        print("=" * 60)
        return False

if __name__ == '__main__':
    success = test_robco_ini_generation()
    sys.exit(0 if success else 1)
