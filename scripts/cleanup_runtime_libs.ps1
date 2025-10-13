param()

Write-Host "--- cleanup_runtime_libs.ps1: stop xEdit processes and move duplicate AutoPatcherLib.pas ---"

# 1) Stop xEdit processes if any
$names = @('xedit64','xedit','fo4edit')
$ps = @()
foreach ($n in $names) {
    $found = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($found) { $ps += $found }
}
if ($ps.Count -gt 0) {
    Write-Host "Found running processes:"; $ps | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize
    Write-Host "Stopping processes..."; $ps | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "Stopped processes."
} else {
    Write-Host "No xEdit/FO4Edit processes running."
}

# 2) Locate AutoPatcherLib.pas copies
$canonical = "E:\\fo4mod\\xedit\\Edit Scripts\\lib\\AutoPatcherLib.pas"
$searchRoots = @('E:\\fo4mod\\xedit','E:\\mo2data\\overwrite','E:\\Munition_AutoPatcher_v1.1')
Write-Host "Searching for AutoPatcherLib.pas under:"; $searchRoots | ForEach-Object { Write-Host " - $_" }
$foundFiles = @()
foreach ($r in $searchRoots) {
    if (Test-Path $r) {
        $found = Get-ChildItem -Path $r -Filter 'AutoPatcherLib.pas' -Recurse -ErrorAction SilentlyContinue
        if ($found) { $foundFiles += $found }
    }
}

if ($foundFiles.Count -eq 0) {
    Write-Host "No AutoPatcherLib.pas files found under the given roots."
} else {
    Write-Host "Found files:"; $foundFiles | Select-Object FullName,DirectoryName,LastWriteTime | Format-Table -AutoSize

    # prepare backup folder
    $ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
    $destRoot = "E:\\fo4mod\\xedit\\disabled_lib_backups_move_$ts"
    New-Item -ItemType Directory -Path $destRoot -Force | Out-Null

    foreach ($f in $foundFiles) {
        $full = $f.FullName
        if ($full -ieq $canonical) {
            Write-Host "Keeping canonical: $full"
            continue
        }
        # create a unique filename in dest
        $leaf = $f.Name
        $safe = ($full -replace ':','' -replace '[\\/:]','_')
        $target = Join-Path $destRoot $safe
        try {
            Move-Item -LiteralPath $full -Destination $target -Force
            Write-Host "Moved: $full -> $target"
        } catch {
            Write-Host "Failed to move $full : $_"
        }
    }

    Write-Host "Final check: remaining AutoPatcherLib.pas under E:\\fo4mod\\xedit\\Edit Scripts"
    Get-ChildItem -Path 'E:\\fo4mod\\xedit\\Edit Scripts' -Filter 'AutoPatcherLib.pas' -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
}

Write-Host 'Done.'
