import os
paths = [r'E:\Munition_AutoPatcher_v1.1\Output', r'E:\fo4mod\xedit\Edit Scripts\Output']
for p in paths:
    print('Checking', p)
    try:
        for fn in os.listdir(p):
            if 'minimal' in fn.lower():
                st = os.stat(os.path.join(p,fn))
                print(' -', fn, st.st_mtime, st.st_size)
    except Exception as e:
        print('  (error)', e)
