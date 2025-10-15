# Move non-essential files from Output to Output\archives
$p = 'E:\Munition_AutoPatcher_v1.1'
$out = Join-Path $p 'Output'
$archives = Join-Path $out 'archives'
$keep = @('unique_ammo_for_mapping.ini','munitions_ammo_ids.ini','weapon_omod_map.json','weapon_ammo_map.json','WeaponLeveledLists_Export.csv')

Write-Output "Output folder: $out"
Write-Output "Archives folder: $archives"
Write-Output "Essential files kept: $($keep -join ', ')"

if(-not (Test-Path $archives)) {
    Write-Output "Creating archives folder..."
    New-Item -Path $archives -ItemType Directory | Out-Null
}

$moved = @()
$items = Get-ChildItem -Path $out -File -ErrorAction SilentlyContinue | Where-Object { $keep -notcontains $_.Name }

foreach($it in $items) {
    $dest = Join-Path $archives $it.Name
    try {
        Move-Item -Path $it.FullName -Destination $dest -Force
        $moved += $it.Name
    } catch {
        Write-Warning "Failed to move $($it.FullName): $_"
    }
}

Write-Output ''
Write-Output 'Moved files:'
if($moved.Count -eq 0){ Write-Output '  (none)'} else { foreach($n in $moved) { Write-Output "  $n" } }

Write-Output ''
Write-Output 'Files now in Output folder:'
Get-ChildItem -Path $out -File | Select-Object Name | Format-Table -AutoSize

Write-Output ''
Write-Output 'Files now in archives folder:'
Get-ChildItem -Path $archives -File | Select-Object Name | Format-Table -AutoSize
