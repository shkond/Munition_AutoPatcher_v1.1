#!/usr/bin/env python3
"""
Usage:
  python check_first40_lines.py AutoPatcherLib.pas

What it does:
- Detects common BOMs in the file.
- Prints first 40 lines with line numbers.
- Replaces invisible/suspicious chars with <U+XXXX> markers.
- Lists occurrences of suspicious codepoints (zero-width, BOM, NBSP, control chars).
- Dumps first 256 bytes as hex.
"""
import sys
import codecs

SUSPICIOUS = {0xFEFF, 0x200B, 0x00A0, 0x200E, 0x200F}
ALLOWED_CONTROL = {0x09, 0x0A, 0x0D}  # tab, lf, cr

def detect_bom(b):
    if b.startswith(b'\xEF\xBB\xBF'):
        return "UTF-8 BOM (EF BB BF)"
    if b.startswith(b'\xFF\xFE\x00\x00'):
        return "UTF-32 LE BOM (FF FE 00 00)"
    if b.startswith(b'\x00\x00\xFE\xFF'):
        return "UTF-32 BE BOM (00 00 FE FF)"
    if b.startswith(b'\xFF\xFE'):
        return "UTF-16 LE BOM (FF FE)"
    if b.startswith(b'\xFE\xFF'):
        return "UTF-16 BE BOM (FE FF)"
    return "None detected"

def visual_line(s):
    out = []
    for ch in s:
        cp = ord(ch)
        if (32 <= cp <= 126) or cp in ALLOWED_CONTROL:
            out.append(ch)
        else:
            out.append(f"<U+{cp:04X}>")
    return ''.join(out)

def analyze(path):
    with open(path, 'rb') as f:
        raw = f.read(4096)
    print("BOM:", detect_bom(raw[:8]))
    print("First 256 bytes (hex):")
    print(' '.join(f"{b:02X}" for b in raw[:256]))
    print()

    # Try reading lines with common encodings
    encodings = ['utf-8', 'utf-16', 'utf-16-be', 'latin-1', 'cp1252']
    lines = None
    used_enc = None
    for e in encodings:
        try:
            with codecs.open(path, 'r', encoding=e, errors='strict') as f:
                all_lines = f.readlines()
            lines = all_lines[:40]
            used_enc = e
            break
        except Exception:
            continue
    if lines is None:
        # fallback: decode as utf-8 with replace
        with open(path, 'rb') as f:
            data = f.read()
        lines = data.decode('utf-8', errors='replace').splitlines()[:40]
        used_enc = 'utf-8 (replace)'

    print("Used encoding (attempt):", used_enc)
    print(f"First {len(lines)} lines (visualized):")
    issues = []
    for i, ln in enumerate(lines, start=1):
        vis = visual_line(ln)
        print(f"{i:3}: {vis}")
        for col, ch in enumerate(ln, start=1):
            cp = ord(ch)
            if (cp < 32 and cp not in ALLOWED_CONTROL) or (cp in SUSPICIOUS) or (127 < cp < 160):
                issues.append((i, col, cp, f"U+{cp:04X}", repr(ch)))
    print()
    if issues:
        print("Suspicious characters found (line, col, codepoint, repr):")
        for it in issues:
            print(f"  Line {it[0]:3}, Col {it[1]:3}: {it[3]}  {it[4]}")
    else:
        print("No suspicious invisible/control characters found in the first lines.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check_first40_lines.py <path>")
        sys.exit(1)
    analyze(sys.argv[1])