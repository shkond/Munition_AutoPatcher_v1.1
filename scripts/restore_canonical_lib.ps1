Write-Host '--- restore_canonical_lib.ps1 ---'
$root = 'E:\fo4mod\xedit'
$pattern = 'disabled_lib_backups_move_*'
$dest = 'E:\fo4mod\xedit\Edit Scripts\lib\AutoPatcherLib.pas'

if (-not (Test-Path $root)) {
    Write-Error "$root not found"
    exit 1
}

$bk = Get-ChildItem -Path $root -Filter $pattern -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $bk) {
    Write-Host 'No backup folder matching' $pattern 'found under' $root
    exit 0
}

Write-Host 'Using backup folder:' $bk.FullName

$file = Get-ChildItem -Path $bk.FullName -Filter 'AutoPatcherLib.pas' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $file) {
    Write-Host 'No AutoPatcherLib.pas in backup folder.'
    exit 0
}

Write-Host 'Found candidate:' $file.FullName

New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
Move-Item -LiteralPath $file.FullName -Destination $dest -Force
Write-Host 'Restored canonical to' $dest

Write-Host 'Done.'
