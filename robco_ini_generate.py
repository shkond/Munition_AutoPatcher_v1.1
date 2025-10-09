"""
Robco Patcher INI Generator Module

This module generates Robco Patcher INI files based on:
- strategy.json (ammo_classification, allocation_matrix)
- ammo_map.json (preferred) or ammo_map.ini [UnmappedAmmo] (fallback)
- WeaponLeveledLists_Export.csv (preferred) or leveled_lists.json (fallback)
- weapon_ammo_details.txt or weapon_records.csv (if present) for weapon Plugin|FormID

Generates:
- robco_ammo_patch.ini with [robcoammopatch] section containing filterByAmmos
"""

import json
import csv
import configparser
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RobcoIniGenerator:
    """Generate Robco Patcher INI files from extracted data."""

    def __init__(self, strategy_file: Path, output_dir: Path, robco_patcher_dir: Path,
                 ammo_map_file: Optional[Path] = None):
        """
        Initialize the generator.
        
        Args:
            strategy_file: Path to strategy.json
            output_dir: Path to output directory containing extracted data
            robco_patcher_dir: Path to Robco Patcher directory for output
            ammo_map_file: Optional path to ammo_map.ini
        """
        self.strategy_file = strategy_file
        self.output_dir = output_dir
        self.robco_patcher_dir = robco_patcher_dir
        self.ammo_map_file = ammo_map_file
        
        self.strategy_data: Dict = {}
        self.ammo_map: Dict[str, str] = {}
        self.leveled_lists: Dict = {}
        self.weapons: List[Dict] = []

    def load_strategy(self) -> bool:
        """Load strategy.json containing ammo_classification and allocation_matrix."""
        try:
            if not self.strategy_file.is_file():
                logging.error(f"[RobcoINI] strategy.json not found: {self.strategy_file}")
                return False
            
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                self.strategy_data = json.load(f)
            
            if 'ammo_classification' not in self.strategy_data:
                logging.error("[RobcoINI] strategy.json missing 'ammo_classification'")
                return False
            
            logging.info(f"[RobcoINI] Loaded strategy.json with {len(self.strategy_data.get('ammo_classification', {}))} ammo classifications")
            return True
        except Exception as e:
            logging.error(f"[RobcoINI] Failed to load strategy.json: {e}", exc_info=True)
            return False

    def load_ammo_map(self) -> bool:
        """
        Load ammo mapping data.
        Prefers ammo_map.json, falls back to ammo_map.ini [UnmappedAmmo].
        """
        # Try ammo_map.json first
        ammo_map_json = self.output_dir / 'ammo_map.json'
        if ammo_map_json.is_file():
            try:
                with open(ammo_map_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ammo_map = {k.lower(): v.lower() for k, v in data.items()}
                logging.info(f"[RobcoINI] Loaded ammo_map.json with {len(self.ammo_map)} mappings")
                return True
            except Exception as e:
                logging.warning(f"[RobcoINI] Failed to load ammo_map.json: {e}")
        
        # Fallback to ammo_map.ini
        if self.ammo_map_file and self.ammo_map_file.is_file():
            try:
                parser = configparser.ConfigParser()
                parser.read(self.ammo_map_file, encoding='utf-8')
                if parser.has_section('UnmappedAmmo'):
                    self.ammo_map = {k.lower(): v.lower() for k, v in parser.items('UnmappedAmmo')}
                    logging.info(f"[RobcoINI] Loaded ammo_map.ini with {len(self.ammo_map)} mappings")
                    return True
            except Exception as e:
                logging.warning(f"[RobcoINI] Failed to load ammo_map.ini: {e}")
        
        logging.info("[RobcoINI] No ammo mapping file found, proceeding without mappings")
        return True

    def load_leveled_lists(self) -> bool:
        """
        Load leveled list data.
        Prefers WeaponLeveledLists_Export.csv, falls back to leveled_lists.json.
        """
        # Try WeaponLeveledLists_Export.csv first
        csv_file = self.output_dir / 'WeaponLeveledLists_Export.csv'
        if csv_file.is_file():
            try:
                with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        faction = row.get('Faction', '').strip()
                        list_name = row.get('LeveledListName', '').strip()
                        if faction and list_name:
                            self.leveled_lists[faction] = list_name
                logging.info(f"[RobcoINI] Loaded WeaponLeveledLists_Export.csv with {len(self.leveled_lists)} leveled lists")
                return True
            except Exception as e:
                logging.warning(f"[RobcoINI] Failed to load WeaponLeveledLists_Export.csv: {e}")
        
        # Fallback to leveled_lists.json
        json_file = self.output_dir / 'leveled_lists.json'
        if json_file.is_file():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.leveled_lists = json.load(f)
                logging.info(f"[RobcoINI] Loaded leveled_lists.json with {len(self.leveled_lists)} leveled lists")
                return True
            except Exception as e:
                logging.error(f"[RobcoINI] Failed to load leveled_lists.json: {e}", exc_info=True)
                return False
        
        logging.error("[RobcoINI] No leveled list file found")
        return False

    def load_weapons(self) -> bool:
        """
        Load weapon data.
        Tries weapon_ammo_details.txt, then weapon_records.csv, then weapon_ammo_map.json.
        """
        # Try weapon_ammo_details.txt
        txt_file = self.output_dir / 'weapon_ammo_details.txt'
        if txt_file.is_file():
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('|')
                        if len(parts) >= 4:
                            self.weapons.append({
                                'plugin': parts[0].strip(),
                                'form_id': parts[1].strip(),
                                'editor_id': parts[2].strip(),
                                'ammo_form_id': parts[3].strip()
                            })
                logging.info(f"[RobcoINI] Loaded weapon_ammo_details.txt with {len(self.weapons)} weapons")
                return True
            except Exception as e:
                logging.warning(f"[RobcoINI] Failed to load weapon_ammo_details.txt: {e}")
        
        # Try weapon_records.csv
        csv_file = self.output_dir / 'weapon_records.csv'
        if csv_file.is_file():
            try:
                with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.weapons.append({
                            'plugin': row.get('Plugin', '').strip(),
                            'form_id': row.get('FormID', '').strip(),
                            'editor_id': row.get('EditorID', '').strip(),
                            'ammo_form_id': row.get('AmmoFormID', '').strip()
                        })
                logging.info(f"[RobcoINI] Loaded weapon_records.csv with {len(self.weapons)} weapons")
                return True
            except Exception as e:
                logging.warning(f"[RobcoINI] Failed to load weapon_records.csv: {e}")
        
        # Fallback to weapon_ammo_map.json (legacy format)
        json_file = self.output_dir / 'weapon_ammo_map.json'
        if json_file.is_file():
            try:
                # Try UTF-8 first
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except UnicodeDecodeError:
                # Fallback to system default encoding
                import locale
                enc = locale.getpreferredencoding()
                logging.warning(f"[RobcoINI] UTF-8 failed, trying {enc} encoding")
                with open(json_file, 'r', encoding=enc, errors='replace') as f:
                    data = json.load(f)
            
            for item in data:
                self.weapons.append({
                    'plugin': '',  # Not available in legacy format
                    'form_id': '',  # Not available in legacy format
                    'editor_id': item.get('editor_id', ''),
                    'ammo_form_id': item.get('ammo_form_id', '')
                })
            logging.info(f"[RobcoINI] Loaded weapon_ammo_map.json with {len(self.weapons)} weapons")
            return True
        
        logging.error("[RobcoINI] No weapon data file found")
        return False

    def generate_robco_ammo_patch_ini(self) -> bool:
        """
        Generate robco_ammo_patch.ini with [robcoammopatch] section.
        """
        try:
            output_path = self.robco_patcher_dir / 'robco_ammo_patch.ini'
            self.robco_patcher_dir.mkdir(parents=True, exist_ok=True)
            
            lines = [
                "; Generated by Munitions Auto Patcher",
                f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "[robcoammopatch]",
                "filterByAmmos=Munitions - An Ammo Expansion.esl|",
                ""
            ]
            
            output_path.write_text('\n'.join(lines), encoding='utf-8')
            logging.info(f"[RobcoINI] Generated {output_path.name}")
            return True
        except Exception as e:
            logging.error(f"[RobcoINI] Failed to generate robco_ammo_patch.ini: {e}", exc_info=True)
            return False

    def generate_all(self) -> bool:
        """
        Load all data sources and generate all Robco INI files.
        
        Returns:
            True if all steps succeeded, False otherwise
        """
        if not self.load_strategy():
            return False
        
        if not self.load_ammo_map():
            return False
        
        if not self.load_leveled_lists():
            return False
        
        if not self.load_weapons():
            return False
        
        if not self.generate_robco_ammo_patch_ini():
            return False
        
        logging.info("[RobcoINI] All Robco INI files generated successfully")
        return True


def generate_robco_inis(strategy_file: Path, output_dir: Path, robco_patcher_dir: Path,
                        ammo_map_file: Optional[Path] = None) -> bool:
    """
    Main entry point for generating Robco Patcher INI files.
    
    Args:
        strategy_file: Path to strategy.json
        output_dir: Path to output directory containing extracted data
        robco_patcher_dir: Path to Robco Patcher directory for output
        ammo_map_file: Optional path to ammo_map.ini
    
    Returns:
        True if generation succeeded, False otherwise
    """
    generator = RobcoIniGenerator(strategy_file, output_dir, robco_patcher_dir, ammo_map_file)
    return generator.generate_all()
