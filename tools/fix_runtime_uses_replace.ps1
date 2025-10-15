$path = 'E:\fo4mod\xedit\Edit Scripts\ExtractWeaponAmmoMappingLogic.pas'
$bak = $path + '.bak'
if(-not (Test-Path $path)) { Write-Error "Runtime file not found: $path"; exit 1 }
Copy-Item -Path $path -Destination $bak -Force
$content = Get-Content -Raw -Path $path -Encoding UTF8
$new = $content -replace "'lib/AutoPatcherLib'","AutoPatcherLib"
if($new -ne $content) {
    Set-Content -Path $path -Value $new -Encoding UTF8
    Write-Output "Replaced 'lib/AutoPatcherLib' with AutoPatcherLib in $path"
} else {
    Write-Output "No replacement performed (pattern not found)"
}
# Show leading 20 lines for quick inspection
Get-Content -Path $path -Encoding UTF8 -TotalCount 40 | ForEach-Object { Write-Output $_ }
Write-Output "Backup saved to $bak"