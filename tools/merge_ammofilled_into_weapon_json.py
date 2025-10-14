from pathlib import Path
import json

out_dir = Path('Output')
base_path = out_dir / 'weapon_omod_map.json'
fill_path = out_dir / 'weapon_omod_map.ammofilled.details.json'
backup_path = out_dir / 'weapon_omod_map.json.bak'

if not base_path.exists():
    print('Base weapon_omod_map.json not found:', base_path)
    raise SystemExit(1)
if not fill_path.exists():
    print('Ammofilled details not found:', fill_path)
    raise SystemExit(1)

base = json.loads(base_path.read_text(encoding='utf-8'))
fill = json.loads(fill_path.read_text(encoding='utf-8'))

# index base by weapon_form_id and by ammo_editor_id
by_wfid = { (e.get('weapon_form_id') or '').strip().upper(): e for e in base }
by_aeditor = { (e.get('ammo_editor_id') or '').strip(): e for e in base }

modified = 0
for f in fill:
    wf = (f.get('weapon_form_id') or '').strip().upper()
    ae = (f.get('ammo_editor_id') or '').strip()
    target = None
    if wf and wf in by_wfid:
        target = by_wfid[wf]
    elif ae and ae in by_aeditor:
        target = by_aeditor[ae]
    if target is not None:
        # update ammo fields and omods
        if f.get('ammo_form_id'):
            target['ammo_form_id'] = f.get('ammo_form_id')
        if f.get('ammo_plugin'):
            target['ammo_plugin'] = f.get('ammo_plugin')
        if f.get('omods'):
            target['omods'] = f.get('omods')
        modified += 1

# backup and write
backup_path.write_text(base_path.read_text(encoding='utf-8'), encoding='utf-8')
base_path.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding='utf-8')
print('Modified entries:', modified)
print('Backup created at', backup_path)
