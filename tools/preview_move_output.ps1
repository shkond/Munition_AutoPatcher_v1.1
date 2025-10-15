# Preview which files in Output would be moved to Output\archives (exclude essential files)
$p = 'E:\Munition_AutoPatcher_v1.1'
$out = Join-Path $p 'Output'
$archives = Join-Path $out 'archives'
$keep = @('unique_ammo_for_mapping.ini','munitions_ammo_ids.ini','weapon_omod_map.json','weapon_ammo_map.json','WeaponLeveledLists_Export.csv')

Write-Output "Output folder: $out"
Write-Output "Essential files kept: $($keep -join ', ')"
Write-Output ""
Write-Output 'Files that WOULD be moved (Name | FullName):'
Get-ChildItem -Path $out -File -ErrorAction SilentlyContinue | Where-Object { $keep -notcontains $_.Name } | Select-Object Name,FullName | Format-Table -AutoSize
