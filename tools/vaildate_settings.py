import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path('.').resolve()
STRATEGY = ROOT / 'strategy.json'
CATEGORIES = ROOT / 'ammo_categories.json'

def load_json(p: Path) -> Any:
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[ERROR] Failed to read/parse {p}: {e}")
        return None

def check_strategy(data: dict) -> int:
    errs = 0
    if not isinstance(data, dict):
        print("[ERROR] strategy.json: top-level is not an object")
        return 1
    # Expected sections
    for key in ('ammo_classification', 'allocation_matrix', 'faction_leveled_lists'):
        if key not in data:
            print(f"[WARN] strategy.json: missing top-level key '{key}'")
    ac = data.get('ammo_classification', {})
    if not isinstance(ac, dict):
        print("[ERROR] strategy.json: 'ammo_classification' is not an object")
        errs += 1
    else:
        for fid, info in ac.items():
            if not isinstance(info, dict):
                print(f"[ERROR] ammo_classification[{fid}] is not an object")
                errs += 1
                continue
            cat = info.get('Category')
            pw = info.get('Power')
            if not isinstance(cat, str) or not cat.strip():
                print(f"[ERROR] ammo_classification[{fid}].Category missing or empty")
                errs += 1
            if not (isinstance(pw, int) or isinstance(pw, float)):
                print(f"[ERROR] ammo_classification[{fid}].Power missing or not numeric")
                errs += 1
    return errs

def check_categories(data: dict) -> int:
    errs = 0
    if not isinstance(data, dict):
        print("[ERROR] ammo_categories.json: top-level is not an object")
        return 1
    rules = data.get('classification_rules')
    if not isinstance(rules, list):
        print("[ERROR] ammo_categories.json: 'classification_rules' missing or not an array")
        return 1
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            print(f"[ERROR] classification_rules[{idx}] is not an object")
            errs += 1
            continue
        keywords = rule.get('keywords')
        cat = rule.get('Category')
        pw = rule.get('Power')
        if not isinstance(keywords, list) or not keywords:
            print(f"[ERROR] classification_rules[{idx}].keywords missing or empty")
            errs += 1
        if not isinstance(cat, str) or not cat.strip():
            print(f"[ERROR] classification_rules[{idx}].Category missing or empty")
            errs += 1
        if not (isinstance(pw, int) or isinstance(pw, float)):
            print(f"[ERROR] classification_rules[{idx}].Power missing or not numeric")
            errs += 1
    return errs

def main():
    total_errs = 0
    if not STRATEGY.is_file():
        print(f"[ERROR] Missing file: {STRATEGY}")
        total_errs += 1
    else:
        s = load_json(STRATEGY)
        if s is None:
            total_errs += 1
        else:
            total_errs += check_strategy(s)

    if not CATEGORIES.is_file():
        print(f"[ERROR] Missing file: {CATEGORIES}")
        total_errs += 1
    else:
        c = load_json(CATEGORIES)
        if c is None:
            total_errs += 1
        else:
            total_errs += check_categories(c)

    if total_errs == 0:
        print("OK: strategy.json and ammo_categories.json passed basic validation.")
        return 0
    else:
        print(f"[RESULT] Validation completed: {total_errs} issue(s) found.")
        return 2

if __name__ == '__main__':
    sys.exit(main())