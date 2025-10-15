$src = 'E:\Munition_AutoPatcher_v1.1\pas_scripts\lib\AutoPatcherLib.pas'
$dstDir = 'E:\fo4mod\xedit\Edit Scripts\lib'
if(-not (Test-Path $src)) { Write-Error "Source not found: $src"; Exit 1 }
if(-not (Test-Path $dstDir)) { New-Item -Path $dstDir -ItemType Directory -Force | Out-Null }
Copy-Item -Path $src -Destination $dstDir -Force
Write-Output "Copied $src -> $dstDir"
Get-ChildItem -Path $dstDir -Filter 'AutoPatcherLib.pas' | Select-Object FullName,Length
