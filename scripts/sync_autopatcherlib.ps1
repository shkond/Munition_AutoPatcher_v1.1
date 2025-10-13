$ErrorActionPreference='Stop'
$src = 'E:\Munition_AutoPatcher_v1.1\pas_scripts\lib\AutoPatcherLib.pas'
$root = 'E:\fo4mod\xedit\Edit Scripts'
Write-Host "Source: $src"
if(-not (Test-Path $src)) { Write-Host 'Source file not found'; exit 1 }
$targets = Get-ChildItem -Path $root -Recurse -Filter 'AutoPatcherLib.pas' -File -ErrorAction SilentlyContinue
if($targets.Count -eq 0) { Write-Host 'No targets found under runtime Edit Scripts'; exit 0 }
foreach($t in $targets){
  try{
    Copy-Item -LiteralPath $src -Destination $t.FullName -Force
    Write-Host "Copied to: $($t.FullName)"
  } catch {
    Write-Host "Failed to copy to: $($t.FullName) - $_"
  }
}
Write-Host '--- Occurrences of AP_LOG_PREFIX after copy ---'
Get-ChildItem -Path $root -Recurse -Filter '*.pas' -File -ErrorAction SilentlyContinue | Select-String -Pattern 'AP_LOG_PREFIX' -SimpleMatch | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber) -> $($_.Line.Trim())" }
