#!/usr/bin/env python3
"""
Parse xEdit/FO4Edit logs for [PROBE_WEAPON], [PROBE_FORMID_RAW], [PROBE_FORMID_HEX] lines and
produce a mapping editor_id -> full_form_hex, then fill `weapon_omod_map.repaired.json` accordingly.

Usage: python parse_and_fill_from_logs.py <repaired.json> <out.json>
It will scan common log locations under E:\fo4mod\xedit for lines.
"""
import re
import json
import sys
from pathlib import Path

LOG_DIR = Path('E:/fo4mod/xedit')
LOG_PATTERNS = ['xEdit64Exception.log', 'xEdit64Exception1.log', 'xEdit64Exception2.log', 'FO4Script_log.txt', 'FO4Edit_log.txt']

probe_weapon_re = re.compile(r"\[PROBE_WEAPON\].*editor=([^\s]+)\s+form=([^\s]*)")
probe_raw_re = re.compile(r"\[PROBE_FORMID_RAW\]\s+editor=([^\s]+)\s+raw=(\d+)")
probe_hex_re = re.compile(r"\[PROBE_FORMID_HEX\]\s+editor=([^\s]+)\s+hex=([^\s]*)")

# convert raw integer to LO+Form (if raw > 0xFFFFFF then hi byte(s) encode load order)
def raw_to_hex(raw_int: int):
    # If raw fits in 24 bits, assume loadorder 00
    if raw_int <= 0xFFFFFF:
        lo = 0
        fid = raw_int & 0xFFFFFF
    else:
        lo = (raw_int >> 24) & 0xFF
        fid = raw_int & 0xFFFFFF
    return f"{lo:02X}{fid:06X}"


def scan_logs():
    mappings = {}
    for name in LOG_PATTERNS:
        path = LOG_DIR / name
        if not path.exists():
            continue
        try:
            with path.open('r', errors='ignore', encoding='utf-8', newline='') as fh:
                for line in fh:
                    m = probe_raw_re.search(line)
                    if m:
                        editor = m.group(1).strip()
                        raw = int(m.group(2))
                        mappings[editor] = raw_to_hex(raw)
                        continue
                    m2 = probe_hex_re.search(line)
                    if m2:
                        editor = m2.group(1).strip()
                        hexv = m2.group(2).strip()
                        if hexv:
                            mappings[editor] = hexv.upper()
                        continue
        except Exception as e:
            print('Failed to read', path, e)
    return mappings


def fill_json(repaired_path: Path, out_path: Path, mappings: dict):
    data = json.loads(repaired_path.read_text(encoding='utf-8'))
    filled = 0
    for obj in data:
        if not obj.get('weapon_form_id'):
            editor = obj.get('weapon_editor_id')
            if editor in mappings:
                obj['weapon_form_id'] = mappings[editor]
                filled += 1
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return filled, len(data)


def main():
    if len(sys.argv) < 3:
        print('Usage: parse_and_fill_from_logs.py <repaired.json> <out.json>')
        sys.exit(2)
    repaired = Path(sys.argv[1])
    out = Path(sys.argv[2])
    if not repaired.exists():
        print('Repaired JSON not found:', repaired)
        sys.exit(2)
    mappings = scan_logs()
    print('Mappings extracted from logs:', len(mappings))
    # print sample
    for i,(k,v) in enumerate(list(mappings.items())[:20]):
        print(k, '->', v)
    filled, total = fill_json(repaired, out, mappings)
    print(f'Filled {filled} of {total} entries; output: {out}')

if __name__ == '__main__':
    main()
