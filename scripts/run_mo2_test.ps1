$mo2 = 'E:\MO2\ModOrganizer.exe'
$profile = 'new2'
$moshortcut = 'moshortcut://xEdit'
$scriptArg = '-script:test_export_weapon_omod_only.pas'
$sessionLog = 'E:\Munition_AutoPatcher_v1.1\Output\xEdit_session_manual.log'
$logArg = "-Log:$sessionLog"

Write-Host "Starting MO2 -> xEdit with script test_export_weapon_omod_only.pas..."
Start-Process -FilePath $mo2 -ArgumentList @('-p',$profile,$moshortcut,$scriptArg,$logArg)

# Wait for xEdit process to appear (timeout 60s)
$found = $false
$mo2 = 'E:\MO2\ModOrganizer.exe'
$profile = 'new2'
$moshortcut = 'moshortcut://xEdit'
$scriptArg = '-script:test_export_weapon_omod_only.pas'
$sessionLog = 'E:\Munition_AutoPatcher_v1.1\Output\xEdit_session_manual.log'
$logArg = "-Log:$sessionLog"

Write-Host "Starting MO2 -> xEdit with script test_export_weapon_omod_only.pas..."
Start-Process -FilePath $mo2 -ArgumentList @('-p',$profile,$moshortcut,$scriptArg,$logArg)

# Wait for xEdit process to appear (timeout 60s)
$found = $false
$start = Get-Date
while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds(60)) {
    if (Get-Process -Name xedit64 -ErrorAction SilentlyContinue) { $found = $true; Write-Host 'Detected process: xedit64'; break }
    if (Get-Process -Name xedit -ErrorAction SilentlyContinue) { $found = $true; Write-Host 'Detected process: xedit'; break }
    if (Get-Process -Name fo4edit -ErrorAction SilentlyContinue) { $found = $true; Write-Host 'Detected process: fo4edit'; break }
    Start-Sleep -Seconds 1
}
if (-not $found) { Write-Host 'No xEdit process detected within 60s; continuing to wait for session log or process.' }

# Wait for xEdit processes to exit (timeout 900s)
$start = Get-Date
while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds(900)) {
    $running = $false
    if (Get-Process -Name xedit64 -ErrorAction SilentlyContinue) { $running = $true }
    if (Get-Process -Name xedit -ErrorAction SilentlyContinue) { $running = $true }
    if (Get-Process -Name fo4edit -ErrorAction SilentlyContinue) { $running = $true }
    if (-not $running) { Write-Host 'xEdit processes exited'; break }
    Start-Sleep -Seconds 2
}

Start-Sleep -Seconds 1
Write-Host '--- session log tail ---'
if (Test-Path $sessionLog) { Get-Content -LiteralPath $sessionLog -Tail 400 -Encoding UTF8 } else { Write-Host 'No session log found at' $sessionLog }

Write-Host '--- xEditException.log tail ---'
$exlog = 'E:\fo4mod\xedit\xEditException.log'
if (Test-Path $exlog) { Get-Content -LiteralPath $exlog -Tail 400 -Encoding UTF8 } else { Write-Host 'No xEditException.log found' }

Write-Host '--- Edit Scripts\Output listing ---'
$editOut = 'E:\fo4mod\xedit\Edit Scripts\Output'
if (Test-Path $editOut) { Get-ChildItem -LiteralPath $editOut -File | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize } else { Write-Host 'Edit Scripts\Output not found' }

Write-Host 'Done.'
