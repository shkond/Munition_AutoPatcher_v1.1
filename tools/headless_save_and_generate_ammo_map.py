#!/usr/bin/env python3
"""
Headless save test: set selected_target for each unmapped ammo to the first Munitions ammo candidate,
call save_ini_file() to generate robco_ammo_patch.ini, and additionally write ammo_map.ini mapping.
"""
from pathlib import Path
import sys
import configparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mapper import AmmoMapperApp
import tkinter as tk


def main():
    ammo_file = Path('Output') / 'unique_ammo_for_mapping.ini'
    munitions_file = Path('Output') / 'munitions_ammo_ids.ini'
    ammo_map_out = Path('ammo_map.ini')

    root = tk.Tk()
    root.withdraw()
    app = AmmoMapperApp(root, ammo_file, munitions_file, ammo_map_out)

    # Ensure data loaded
    app.reload_data_and_build_ui()

    # Choose first munitions candidate for all rows if available
    if app.munitions_ammo_list:
        choice = app.munitions_ammo_list[0]
        # normalize to same format used in combobox ("FORMID | EditorID")
        for row in app.ammo_to_map:
            row['selected_target'] = choice
    else:
        print('[headless-save] no munitions candidates available; aborting')
        return

    # Call save to produce robco_ammo_patch.ini
    app.save_ini_file()

    # Additionally, write ammo_map.ini mapping original_formid -> chosen Munitions formid
    cfg = configparser.ConfigParser()
    cfg['UnmappedAmmo'] = {}
    for row in app.ammo_to_map:
        orig = row['original_form_id'].upper()
        sel = row.get('selected_target') or ''
        # selected format may be '00112233 | Mun_Ammo_Example' or '00112233|Mun_Ammo_Example'
        sel_form = sel.split('|')[0].strip().upper() if '|' in sel else sel.strip().upper()
        if orig and sel_form:
            cfg['UnmappedAmmo'][orig] = sel_form

    # write to ammo_map_out
    with open(ammo_map_out, 'w', encoding='utf-8') as f:
        cfg.write(f)

    robco_path = app.output_file_path.parent / 'robco_ammo_patch.ini'
    print('[headless-save] wrote robco ini:', robco_path, 'exists=', robco_path.exists())
    print('[headless-save] wrote ammo_map.ini:', ammo_map_out, 'exists=', ammo_map_out.exists())

    # print small previews
    if robco_path.exists():
        print('\n--- robco_ammo_patch.ini (preview) ---')
        print('\n'.join(robco_path.read_text(encoding='utf-8').splitlines()[:80]))
    if ammo_map_out.exists():
        print('\n--- ammo_map.ini (preview) ---')
        print('\n'.join(ammo_map_out.read_text(encoding='utf-8').splitlines()[:80]))

    root.destroy()

if __name__ == '__main__':
    main()
