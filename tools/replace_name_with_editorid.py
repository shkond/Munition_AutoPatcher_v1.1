#!/usr/bin/env python3
"""
Replace garbled weapon_name with weapon_editor_id when weapon_name contains non-ASCII characters
or is empty. Writes a new JSON and a CSV listing changes.

Usage: python replace_name_with_editorid.py <input.json> [<out.json>] [<changes.csv>]
"""
import sys
import json
from pathlib import Path
import csv


def is_garbled(name: str) -> bool:
    if name is None:
        return True
    name = name.strip()
    if name == '':
        return True
    # If any character is non-ASCII printable, consider it garbled for this use-case
    for ch in name:
        if ord(ch) > 127:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print('Usage: replace_name_with_editorid.py <input.json> [<out.json>] [<changes.csv>]')
        sys.exit(2)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) >= 3 else inp.with_name(inp.stem + '.namefixed.json')
    csvp = Path(sys.argv[3]) if len(sys.argv) >= 4 else inp.with_name('weapon_name_changes.csv')
    if not inp.exists():
        print('Input not found:', inp)
        sys.exit(2)

    data = json.loads(inp.read_text(encoding='utf-8'))
    changes = []
    for obj in data:
        name = obj.get('weapon_name', '')
        if is_garbled(name):
            old = name
            new = obj.get('weapon_editor_id','')
            obj['weapon_name'] = new
            changes.append((obj.get('weapon_editor_id',''), old, new, obj.get('weapon_form_id','')))

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    # write csv
    with csvp.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['weapon_editor_id','old_weapon_name','new_weapon_name','weapon_form_id'])
        for row in changes:
            w.writerow(row)

    print(f'Wrote {len(data)} objects to {out}. Changes: {len(changes)}. CSV: {csvp}')
    # print first 20 changes
    for i,row in enumerate(changes[:20]):
        print(f'{i+1:3d}. editor={row[0]:30s} form={row[3]:10s} old="{row[1]:.40s}" -> new="{row[2]}"')

if __name__ == '__main__':
    main()
