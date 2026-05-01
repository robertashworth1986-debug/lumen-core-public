$root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$dashDir = Join-Path $root 'dashboard'
$outDir = Join-Path $root 'out'

$files = Get-ChildItem $dashDir -Filter *.html
$rows = @()

foreach ($f in $files) {
  $txt = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue

  $fetchTargets = [regex]::Matches($txt, 'fetch\s*\(\s*["''][^"'']+["'']') | ForEach-Object {
    ($_.Value -replace '^fetch\s*\(\s*["'']', '') -replace '["'']$', ''
  }

  $jsonTargets = [regex]::Matches($txt, '["'']([^"'']+\.json(?:\?[^"'']*)?)["'']') | ForEach-Object {
    $_.Groups[1].Value
  }

  $liveBridge = $txt -match 'live_registry_bridge\.js'
  $score = ($fetchTargets.Count * 3) + ($jsonTargets.Count) + ($(if ($liveBridge) { 5 } else { 0 }))

  $status = 'stale'
  if ($liveBridge -or $fetchTargets.Count -ge 2) {
    $status = 'live'
  } elseif ($jsonTargets.Count -ge 1) {
    $status = 'partial'
  }

  if ($fetchTargets.Count -eq 0 -and $jsonTargets.Count -eq 0 -and -not $liveBridge) {
    $status = 'retire_candidate'
  }

  $rows += [pscustomobject]@{
    dashboard       = $f.Name
    last_write_utc  = $f.LastWriteTimeUtc.ToString('o')
    size_kb         = [math]::Round($f.Length / 1KB, 1)
    fetch_calls     = $fetchTargets.Count
    json_refs       = $jsonTargets.Count
    has_live_bridge = $liveBridge
    status          = $status
    score           = $score
    fetch_targets   = @($fetchTargets | Select-Object -Unique)
    json_targets    = @($jsonTargets | Select-Object -Unique)
  }
}

$manifest = [ordered]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  root = $root
  canonical_live_sources = @(
    '../out/sports_intelligence/_dk_alpha_board.json',
    '../out/sports_intelligence/_dk_advanced_stack_report.json',
    '../out/sports_intelligence/_dk_macro_regime.json',
    '../execution_status.json',
    '../infra_live_status.json'
  )
  dashboards = ($rows | Sort-Object @{ Expression = 'score'; Descending = $true }, @{ Expression = 'dashboard'; Descending = $false })
}

$retire = [ordered]@{
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  retire_candidates = ($rows | Where-Object { $_.status -eq 'retire_candidate' } | Sort-Object dashboard | Select-Object dashboard, last_write_utc, size_kb, status)
  partial_candidates = ($rows | Where-Object { $_.status -eq 'partial' } | Sort-Object dashboard | Select-Object dashboard, last_write_utc, size_kb, status)
}

$manifestPath = Join-Path $outDir 'dashboard_source_manifest.json'
$retirePath = Join-Path $outDir 'dashboard_retire_candidates.json'

$manifest | ConvertTo-Json -Depth 8 | Set-Content $manifestPath -Encoding UTF8
$retire | ConvertTo-Json -Depth 6 | Set-Content $retirePath -Encoding UTF8

Write-Host "WROTE $manifestPath"
Write-Host "WROTE $retirePath"
