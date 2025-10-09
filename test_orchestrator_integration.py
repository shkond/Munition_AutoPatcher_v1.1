#!/usr/bin/env python3
"""
Integration test for Orchestrator with new robco_ini_generate module.
Tests that Orchestrator can successfully call the new module.
"""

import sys
import logging
from pathlib import Path
from unittest.mock import Mock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Orchestrator import Orchestrator


def test_orchestrator_integration():
    """Test that Orchestrator can use the new robco_ini_generate module."""
    print("=" * 60)
    print("Testing Orchestrator Integration with robco_ini_generate")
    print("=" * 60)
    
    # Create a mock config manager
    project_root = Path(__file__).parent
    
    class MockConfig:
        def get_path(self, section, option):
            paths = {
                ('Paths', 'strategy_file'): project_root / 'strategy.json',
                ('Paths', 'ammo_map_file'): project_root / 'ammo_map.ini',
                ('Paths', 'output_dir'): project_root / 'Output',
                ('Paths', 'robco_patcher_dir'): project_root / 'Robco Patcher',
            }
            return paths.get((section, option), project_root / 'dummy')
        
        def get_string(self, section, option):
            return None
    
    config = MockConfig()
    orchestrator = Orchestrator(config)
    
    print("\n[Test] Calling Orchestrator._generate_robco_ini()...")
    success = orchestrator._generate_robco_ini()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Test PASSED: Orchestrator successfully called robco_ini_generate")
        print("=" * 60)
        
        # Verify output file
        output_file = project_root / 'Robco Patcher' / 'robco_ammo_patch.ini'
        if output_file.is_file():
            print(f"\n✓ Output file exists: {output_file}")
            return True
        else:
            print(f"\n✗ Output file not found: {output_file}")
            return False
    else:
        print("\n" + "=" * 60)
        print("✗ Test FAILED: Orchestrator failed to generate Robco INI")
        print("=" * 60)
        return False


if __name__ == '__main__':
    success = test_orchestrator_integration()
    sys.exit(0 if success else 1)
