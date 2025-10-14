#!/usr/bin/env python3
from pathlib import Path
import tkinter as tk
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mapper import AmmoMapperApp

root = tk.Tk()
root.withdraw()
app = AmmoMapperApp(root, Path('Output') / 'unique_ammo_for_mapping.ini', Path('Output') / 'munitions_ammo_ids.ini', Path('ammo_map.ini'))
# ensure build
app.reload_data_and_build_ui()
children = app.content_frame.winfo_children()
print('total children:', len(children))
for i, c in enumerate(children[:50]):
    try:
        info = c.grid_info()
    except Exception as e:
        info = f'grid_info_error: {e}'
    print(i, c.__class__.__name__, info)
root.destroy()
