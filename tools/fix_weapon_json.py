#!/usr/bin/env python3
"""
Fix and normalize weapon_omod_map.json produced by Pascal script running under xEdit.
- Detects encoding among common encodings (utf-8, cp932/shift_jis, euc-jp, latin1, cp1252, utf-16).
- Attempts to parse the file as JSON. If the file is a sequence of objects (not wrapped in an array) it will extract objects and produce a proper JSON array.
- Writes output as UTF-8 JSON with ensure_ascii=False.

Usage: python fix_weapon_json.py <input.json> [<output.json>]
"""

import sys
import json
import re
from pathlib import Path

CANDIDATE_ENCODINGS = ['utf-8', 'utf-8-sig', 'cp932', 'shift_jis', 'euc_jp', 'cp1252', 'latin1', 'utf-16']


def try_parse_text(text):
    """Try to parse text as JSON directly or after sanitizing as an array."""
    import json
    txt = text.strip()
    # Quick direct parse
    try:
        return json.loads(txt)
    except Exception:
        pass

    # If file looks like many objects separated by commas/newlines but not wrapped in array
    # Try to wrap in [ ... ] and remove trailing commas before closing bracket
    candidate = '[\n' + txt + '\n]'
    # remove trailing commas before closing bracket
    candidate = re.sub(r',\s*\]', ']', candidate, flags=re.M)
    candidate = re.sub(r',\s*\n\s*\]', ']', candidate, flags=re.M)
    try:
        return json.loads(candidate)
    except Exception:
        pass

    return None


def extract_objects_by_brace(text):
    """Extract top-level JSON object strings by matching braces. Returns list of strings."""
    objs = []
    stack = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if stack == 0:
                start = i
            stack += 1
        elif ch == '}':
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    objs.append(text[start:i+1])
                    start = None
    return objs


def normalize_objects(objs):
    """Turn list of object texts into python objects, skipping parse errors."""
    res = []
    for s in objs:
        try:
            obj = json.loads(s)
            res.append(obj)
        except Exception:
            # try to sanitize single quotes -> double quotes (risky). Skip if fails.
            try:
                t = s.replace("\r", "\\r").replace("\n", "\\n")
                obj = json.loads(t)
                res.append(obj)
            except Exception:
                continue
    return res


def main():
    if len(sys.argv) < 2:
        print('Usage: fix_weapon_json.py <input.json> [<output.json>]')
        sys.exit(2)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) >= 3 else inp.with_suffix('.fixed.json')
    if not inp.exists():
        print('Input not found:', inp)
        sys.exit(2)

    b = inp.read_bytes()

    parsed = None
    used_encoding = None

    # Try candidate encodings
    for enc in CANDIDATE_ENCODINGS:
        try:
            text = b.decode(enc)
        except Exception:
            continue
        parsed = try_parse_text(text)
        if parsed is not None:
            used_encoding = enc
            data = parsed
            break

    if parsed is None:
        # Try to extract objects by scanning braces for each decoding candidate
        for enc in CANDIDATE_ENCODINGS:
            try:
                text = b.decode(enc)
            except Exception:
                continue
            objs_text = extract_objects_by_brace(text)
            if not objs_text:
                continue
            objs = normalize_objects(objs_text)
            if objs:
                used_encoding = enc
                data = objs
                parsed = True
                break

    if parsed is None:
        print('Failed to parse JSON with candidates. Will attempt latin1 decode and try again.')
        try:
            text = b.decode('latin1')
            objs_text = extract_objects_by_brace(text)
            objs = normalize_objects(objs_text)
            if objs:
                used_encoding = 'latin1'
                data = objs
                parsed = True
        except Exception:
            pass

    if parsed is None:
        print('Unable to parse file as JSON or extract objects. Exiting.')
        sys.exit(1)

    # At this point, data is either a list or dict
    if isinstance(data, dict):
        data = [data]
    # If it's not a list, coerce
    if not isinstance(data, list):
        print('Parsed JSON is not an array; converting to array-like structure.')
        data = list(data)

    # Basic normalization: ensure keys exist and types
    keys = ['weapon_plugin', 'weapon_form_id', 'weapon_editor_id', 'weapon_name', 'ammo_plugin', 'ammo_form_id', 'ammo_editor_id', 'omods']
    empty_form_id = 0
    for obj in data:
        for k in keys:
            if k not in obj:
                obj[k] = '' if k != 'omods' else []
        if not obj.get('weapon_form_id'):
            empty_form_id += 1

    # Write out with UTF-8
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Wrote {len(data)} objects to {out} using encoding guess: {used_encoding}. Empty weapon_form_id: {empty_form_id}')

    # Print sample head
    head = '\n'.join(out.read_text(encoding='utf-8').splitlines()[:80])
    print('--- Head of fixed JSON ---')
    print(head)


if __name__ == '__main__':
    main()
