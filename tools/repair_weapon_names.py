#!/usr/bin/env python3
"""
Repair mojibake in `weapon_name` fields by trying common decode/encode heuristics and selecting the candidate
with the highest count of CJK characters.

Usage: python repair_weapon_names.py <fixed.json> [<out.json>]
"""
import json
import sys
from pathlib import Path

CJK_RANGES = [
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
]


def cjk_score(s: str) -> int:
    score = 0
    for ch in s:
        cp = ord(ch)
        for a, b in CJK_RANGES:
            if a <= cp <= b:
                score += 1
                break
    return score


CANDIDATE_DECODINGS = [
    ('latin1', 'utf-8'),
    ('latin1', 'cp932'),
    ('latin1', 'shift_jis'),
    ('latin1', 'cp1252'),
    ('cp1252', 'utf-8'),
    ('cp1252', 'cp932'),
    ('utf-8', 'cp932'),
]


def best_repair(s: str) -> (str, str):
    """Return (best_string, method_description)."""
    best = s
    best_method = 'original'
    best_score = cjk_score(s)
    # If original already has CJK, keep it
    if best_score > 0:
        return best, best_method

    for enc_from, enc_to in CANDIDATE_DECODINGS:
        try:
            b = s.encode(enc_from, errors='replace')
            candidate = b.decode(enc_to, errors='replace')
            score = cjk_score(candidate)
            if score > best_score:
                best = candidate
                best_score = score
                best_method = f'{enc_from}-> {enc_to}'
        except Exception:
            continue
    return best, best_method


def main():
    if len(sys.argv) < 2:
        print('Usage: repair_weapon_names.py <fixed.json> [<out.json>]')
        sys.exit(2)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) >= 3 else inp.with_suffix('.repaired.json')
    data = json.loads(inp.read_text(encoding='utf-8'))
    changes = 0
    methods = {}
    for obj in data:
        name = obj.get('weapon_name', '')
        repaired, method = best_repair(name)
        if repaired != name:
            obj['weapon_name'] = repaired
            changes += 1
            methods[method] = methods.get(method, 0) + 1
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(data)} objects to {out}. weapon_name changed for {changes} objects.')
    print('Method counts:', methods)
    print('\n--- Sample head ---')
    print('\n'.join(out.read_text(encoding='utf-8').splitlines()[:120]))


if __name__ == '__main__':
    main()
