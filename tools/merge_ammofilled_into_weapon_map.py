import json, shutil, os, datetime

BASE = r'e:\Munition_AutoPatcher_v1.1\Output\weapon_omod_map.json'
AMMO = r'e:\Munition_AutoPatcher_v1.1\Output\weapon_omod_map.ammofilled.details.json'

def backup(path, suffix):
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = path + f'.{suffix}.{now}.bak'
    shutil.copy(path, dst)
    return dst

print('Files:')
print(' BASE=', BASE)
print(' AMMO=', AMMO)

if not os.path.exists(BASE):
    print('ERROR: base file not found:', BASE)
    raise SystemExit(1)
if not os.path.exists(AMMO):
    print('ERROR: ammofilled file not found:', AMMO)
    raise SystemExit(1)

# Backup base before changing
bak = backup(BASE, 'premerge')
print('Backed up base to', bak)

with open(BASE, 'r', encoding='utf-8') as f:
    base_list = json.load(f)
with open(AMMO, 'r', encoding='utf-8') as f:
    ammo_list = json.load(f)

# index base by (weapon_plugin.lower(), weapon_form_id.lower())
index = {}
for i, w in enumerate(base_list):
    key = ( (w.get('weapon_plugin') or '').lower(), (w.get('weapon_form_id') or '').lower() )
    if key in index:
        # keep first; duplicates unlikely
        pass
    index[key] = i

matched = 0
updated = 0
added = 0
skipped = 0

for a in ammo_list:
    key = ( (a.get('weapon_plugin') or '').lower(), (a.get('weapon_form_id') or '').lower() )
    if key in index:
        matched += 1
        idx = index[key]
        base = base_list[idx]
        changed = False
        # fields to copy if non-empty
        for fld in ('ammo_plugin','ammo_form_id','ammo_editor_id'):
            aval = a.get(fld)
            if aval and aval != '':
                if base.get(fld) != aval:
                    base[fld] = aval
                    changed = True
        # merge omods: combine unique by (omod_plugin, omod_form_id)
        a_omods = a.get('omods') or []
        if a_omods:
            base_omods = base.get('omods') or []
            sig = set((o.get('omod_plugin') or '').lower() + '|' + (o.get('omod_form_id') or '').lower() for o in base_omods)
            appended = 0
            for om in a_omods:
                keyo = (om.get('omod_plugin') or '').lower() + '|' + (om.get('omod_form_id') or '').lower()
                if keyo not in sig:
                    base_omods.append(om)
                    sig.add(keyo)
                    appended += 1
                    changed = True
            if appended:
                base['omods'] = base_omods
        if changed:
            updated += 1
    else:
        # Not found in base: append entire record
        base_list.append(a)
        added += 1

# write merged result
out_path = BASE
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(base_list, f, ensure_ascii=False, indent=2)

print('Merge finished:')
print(' total ammo entries processed:', len(ammo_list))
print(' matched base entries:', matched)
print(' updated base entries:', updated)
print(' appended new entries:', added)
print(' backup saved at:', bak)

# quick validation
try:
    with open(out_path,'r',encoding='utf-8') as f:
        obj = json.load(f)
    print('Validation OK: resulting JSON entries=', len(obj))
except Exception as e:
    print('Validation failed:', e)
    # restore backup
    r = backup(bak, 'restorefail')
    shutil.copy(bak, BASE)
    print('Restored original from', bak)
    raise
