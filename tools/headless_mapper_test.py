#!/usr/bin/env python3
"""
Headless test for AmmoMapperApp: instantiate the app with a Tk root, call load_data() and build_ui_rows(), and print diagnostics.
"""
import sys
from pathlib import Path
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mapper import AmmoMapperApp


def run_test(ammo_file, munitions_file, output_file):
    root = tk.Tk()
    # keep the window hidden
    root.withdraw()
    app = AmmoMapperApp(root, ammo_file, munitions_file, output_file)
    # call reload which calls load_data + build_ui_rows
    app.reload_data_and_build_ui()
    print('[headless-test] ammo_to_map len:', len(app.ammo_to_map))
    print('[headless-test] munitions_ammo_list len:', len(app.munitions_ammo_list))
    total_with_omods = sum(1 for r in app.ammo_to_map if r.get('omods_info'))
    print('[headless-test] rows with omods:', total_with_omods)
    # count widgets
    children = [c for c in app.content_frame.winfo_children() if int(c.grid_info().get('row', 0)) > 0]
    print('[headless-test] content_frame child widgets count:', len(children))
    # destroy root
    root.destroy()

if __name__ == '__main__':
    ammo = Path('Output') / 'unique_ammo_for_mapping.ini'
    mun = Path('Output') / 'munitions_ammo_ids.ini'
    out = Path('ammo_map.ini')
    run_test(ammo, mun, out)
