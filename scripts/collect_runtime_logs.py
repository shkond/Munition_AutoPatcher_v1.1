#!/usr/bin/env python3
from pathlib import Path
import sys

def tail(path: Path, lines=400):
    if not path.exists():
        return None
    # read last approx bytes then splitlines
    try:
        with path.open('rb') as f:
            f.seek(0, 2)
            end = f.tell()
            size = min(end, 200_000)
            f.seek(end - size)
            data = f.read().decode('utf-8', errors='replace')
    except Exception:
        try:
            return path.read_text(encoding='utf-8', errors='replace').splitlines()[-lines:]
        except Exception:
            return None
    parts = data.splitlines()
    return parts[-lines:]

def print_header(h):
    print('\n---', h, '---')

def main():
    project_out = Path(r'E:\Munition_AutoPatcher_v1.1\Output')
    # latest session log
    sess = None
    if project_out.exists():
        logs = sorted(project_out.glob('xEdit_session*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            sess = logs[0]

    if sess:
        print_header(f'Project session log: {sess}')
        lines = tail(sess, 400)
        if lines is None:
            print('(could not read session log)')
        else:
            print('\n'.join(lines))
    else:
        print_header('No project xEdit_session*.log found')

    exlog = Path(r'E:\fo4mod\xedit\xEditException.log')
    print_header(f'xEditException.log tail: {exlog}')
    ex_lines = tail(exlog, 400)
    if ex_lines is None:
        print('(no xEditException.log found or could not read)')
    else:
        print('\n'.join(ex_lines))

    edit_out = Path(r'E:\fo4mod\xedit\Edit Scripts\Output')
    print_header(f'Edit Scripts\\Output listing: {edit_out}')
    if edit_out.exists():
        for p in sorted(edit_out.iterdir(), key=lambda x: x.name.lower()):
            try:
                stat = p.stat()
                print(f"{p.name}\t{stat.st_size}\t{stat.st_mtime}")
            except Exception:
                print(p.name)
    else:
        print('(Edit Scripts\\Output not found)')

if __name__ == '__main__':
    main()
