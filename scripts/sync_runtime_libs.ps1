# Sync workspace AutoPatcherLib.pas to runtime Edit Scripts and backups
$ws = 'E:\Munition_AutoPatcher_v1.1\pas_scripts\lib\AutoPatcherLib.pas'
if (-not (Test-Path $ws)) { Write-Host "Workspace lib not found: $ws"; exit 1 }

$targets = @()
$targets += 'E:\fo4mod\xedit\Edit Scripts\lib\AutoPatcherLib.pas'

# include any _lib_backup_* directories under Edit Scripts
Get-ChildItem -Path 'E:\fo4mod\xedit\Edit Scripts' -Directory -Filter '_lib_backup*' -ErrorAction SilentlyContinue | ForEach-Object {
    $candidate = Join-Path $_.FullName 'AutoPatcherLib.pas'
    if (Test-Path $candidate) { $targets += $candidate }
}

# include MO2 overwrite if exists
$mo2path = 'E:\mo2data\overwrite\Edit Scripts\lib\AutoPatcherLib.pas'
if (Test-Path $mo2path) { $targets += $mo2path }

Write-Host '=== Before replace: search AP_LOG_PREFIX in candidate files ==='
foreach ($t in $targets) {
    if (Test-Path $t) {
        Write-Host "FOUND: $t"
        Select-String -Path $t -Pattern 'AP_LOG_PREFIX' -SimpleMatch | ForEach-Object { Write-Host "  $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
    } else {
        Write-Host "MISSING: $t"
    }
}

Write-Host "`
=== Copying workspace lib to targets (will create dirs if missing) ==="
foreach ($t in $targets) {
    $dir = Split-Path $t
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null; Write-Host "Created dir $dir" }
    Copy-Item -LiteralPath $ws -Destination $t -Force
    Write-Host "Copied to $t"
}

Write-Host "`
=== After replace: verify AP_LOG_PREFIX occurrences ==="
foreach ($t in $targets) {
    if (Test-Path $t) {
        Select-String -Path $t -Pattern 'AP_LOG_PREFIX' -SimpleMatch | ForEach-Object { Write-Host "  $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
    }
}

Write-Host "`
=== Listing Edit Scripts\lib content ==="
Get-ChildItem -Path 'E:\fo4mod\xedit\Edit Scripts\lib' -File -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize

Write-Host "`
Done. If xEdit is running, please restart it before retrying the script."
