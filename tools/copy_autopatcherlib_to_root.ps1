$src = 'E:\Munition_AutoPatcher_v1.1\pas_scripts\lib\AutoPatcherLib.pas'
$dst = 'E:\fo4mod\xedit\Edit Scripts\AutoPatcherLib.pas'
if(-not (Test-Path $src)) { Write-Error "Source not found: $src"; exit 1 }
Copy-Item -Path $src -Destination $dst -Force
# Strip leading/trailing ``` fences if present
$content = Get-Content -Raw -Path $dst -Encoding UTF8
$lines = $content -split "\r?\n"
$changed = $false
if($lines.Count -gt 0 -and $lines[0] -match '^```') { $lines = $lines[1..($lines.Count - 1)]; $changed = $true }
if($lines.Count -gt 0 -and $lines[$lines.Count - 1] -match '^```') { $lines = $lines[0..($lines.Count - 2)]; $changed = $true }
if($changed) { Set-Content -Path $dst -Value ($lines -join "`r`n") -Encoding UTF8; Write-Output "Stripped code fences from $dst" }
Write-Output "Copied to: $dst"
Get-ChildItem -Path (Split-Path $dst) -Filter 'AutoPatcherLib.pas' | Select-Object FullName,Length,LastWriteTime
