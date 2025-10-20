import psutil
for p in psutil.process_iter(['pid','name','cmdline']):
    if p.info['name'] and p.info['name'].lower() in ('xedit.exe','fo4edit.exe','tes5edit.exe','fo4vredit.exe'):
        print(p.info['pid'], p.info['cmdline'])