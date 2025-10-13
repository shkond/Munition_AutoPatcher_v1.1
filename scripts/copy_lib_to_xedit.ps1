$src = 'E:\Munition_AutoPatcher_v1.1\pas_scripts\lib'
$dst = 'E:\fo4mod\xedit\lib'
Write-Output "Source: $src"
Write-Output "Dest:   $dst"
if (-not (Test-Path $src)) { Write-Output 'Source not found'; exit 2 }
try {
    New-Item -Path $dst -ItemType Directory -Force | Out-Null
    Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
    Write-Output 'Copied:'
    Get-ChildItem -Path $dst -File | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
} catch {
    Write-Output 'ERROR'
    Write-Output $_.Exception.Message
    exit 1
}
