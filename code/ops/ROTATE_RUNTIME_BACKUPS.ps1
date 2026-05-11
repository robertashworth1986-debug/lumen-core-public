param(
  [int]$KeepCount = 40,
  [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$configRoot = Join-Path $repoRoot 'config'
$archiveRoot = Join-Path $repoRoot 'out/runtime_backups_archive'
$opsOut = Join-Path $repoRoot 'out/ops'
$summaryPath = Join-Path $opsOut 'runtime_backup_rotation_summary.json'

if (-not (Test-Path $configRoot)) {
  throw "Config folder not found: $configRoot"
}

New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
New-Item -ItemType Directory -Path $opsOut -Force | Out-Null

$patterns = @(
  'runtime_control.backup_*.json',
  'runtime_control.burst_backup_*.json',
  'runtime_control.*_backup_*.json',
  'runtime_control.fractal_backup_*.json',
  'runtime_control.lightning_backup_*.json'
)

$all = @()
foreach ($pattern in $patterns) {
  $all += Get-ChildItem -Path $configRoot -Filter $pattern -File -ErrorAction SilentlyContinue
}

$files = $all |
  Sort-Object -Property FullName -Unique |
  Sort-Object -Property LastWriteTime -Descending

$total = $files.Count
$keep = @($files | Select-Object -First $KeepCount)
$move = @($files | Select-Object -Skip $KeepCount)

$moved = @()
foreach ($f in $move) {
  $dateFolder = $f.LastWriteTime.ToString('yyyyMMdd')
  $destDir = Join-Path $archiveRoot $dateFolder
  $destPath = Join-Path $destDir $f.Name

  if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
  }

  if ($WhatIf) {
    $moved += [PSCustomObject]@{
      source = $f.FullName
      destination = $destPath
      moved = $false
      mode = 'whatif'
    }
  }
  else {
    Move-Item -Path $f.FullName -Destination $destPath -Force
    $moved += [PSCustomObject]@{
      source = $f.FullName
      destination = $destPath
      moved = $true
      mode = 'execute'
    }
  }
}

$summary = [ordered]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  repo_root = $repoRoot
  config_root = $configRoot
  archive_root = $archiveRoot
  keep_count = $KeepCount
  total_detected = $total
  kept = $keep.Count
  selected_to_move = $move.Count
  moved_count = @($moved | Where-Object { $_.moved }).Count
  whatif = [bool]$WhatIf
  patterns = $patterns
  kept_files = @($keep | ForEach-Object { $_.Name })
  moved_files = $moved
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Output "ROTATION_SUMMARY=$summaryPath"
Write-Output "TOTAL_DETECTED=$total"
Write-Output "KEPT=$($keep.Count)"
Write-Output "MOVED=$(@($moved | Where-Object { $_.moved }).Count)"
Write-Output "WHATIF=$([bool]$WhatIf)"
