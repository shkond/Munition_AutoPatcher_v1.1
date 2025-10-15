# Backup and strip leading/trailing code fences (```...```) from .pas files under the runtime Edit Scripts folder
$es = 'E:\fo4mod\xedit\Edit Scripts'
$bk = Join-Path $es 'backup_pas_before_strip'
New-Item -Path $bk -ItemType Directory -Force | Out-Null
Get-ChildItem -Path $es -Filter '*.pas' -File | ForEach-Object {
    $path = $_.FullName
    Copy-Item -Path $path -Destination $bk -Force
    $content = Get-Content -Raw -Path $path -ErrorAction Stop -Encoding UTF8
    # Normalize line endings and split
    $lines = $content -split "\r?\n"
    $changed = $false
    if($lines.Count -gt 0 -and $lines[0] -match '^```') {
        $lines = $lines[1..($lines.Count - 1)]
        $changed = $true
    }
    if($lines.Count -gt 0 -and $lines[$lines.Count - 1] -match '^```') {
        $lines = $lines[0..($lines.Count - 2)]
        $changed = $true
    }
    if($changed) {
        $new = $lines -join "`r`n"
        Set-Content -Path $path -Value $new -Encoding UTF8
        Write-Output "Cleaned: $path"
    } else {
        Write-Output "Unchanged: $path"
    }
}
Write-Output 'Done.'
