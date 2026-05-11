param(
  [string]$RootDashboardPath = "C:\\LumaTrader\\dashboard",
  [string]$StackDashboardPath = "C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\dashboard",
  [string]$OutputRoot = "C:\\LumaTrader\\out\\ops\\universe_map_20260510_213648"
)

$ErrorActionPreference = 'Stop'

$files = @(
  'mission_control.html',
  'quant_lab.html',
  'investor_command_room.html',
  'kraken_execution_dashboard.html',
  'luma_experience.html',
  'scenario_mission.html',
  'grants.html',
  'investor_wallboard.html'
)

if (-not (Test-Path $OutputRoot)) {
  New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

$rows = @()
foreach ($f in $files) {
  $rootFile = Join-Path $RootDashboardPath $f
  $stackFile = Join-Path $StackDashboardPath $f

  $rootExists = Test-Path $rootFile
  $stackExists = Test-Path $stackFile

  $rootHash = ''
  $stackHash = ''
  $sameHash = $false

  $rootAbsWin = 0
  $stackAbsWin = 0
  $rootRootedRefs = 0
  $stackRootedRefs = 0
  $rootRelativeRefs = 0
  $stackRelativeRefs = 0

  if ($rootExists) {
    $rootHash = (Get-FileHash -Path $rootFile -Algorithm SHA256).Hash
    $rootContent = Get-Content -Path $rootFile -Raw
    $rootAbsWin = ([regex]::Matches($rootContent, '[A-Za-z]:\\\\')).Count
    $rootRootedRefs = ([regex]::Matches($rootContent, '(?:src|href)=\"/(?!/)')).Count
    $rootRelativeRefs = ([regex]::Matches($rootContent, '(?:src|href)=\"\\./')).Count
  }

  if ($stackExists) {
    $stackHash = (Get-FileHash -Path $stackFile -Algorithm SHA256).Hash
    $stackContent = Get-Content -Path $stackFile -Raw
    $stackAbsWin = ([regex]::Matches($stackContent, '[A-Za-z]:\\\\')).Count
    $stackRootedRefs = ([regex]::Matches($stackContent, '(?:src|href)=\"/(?!/)')).Count
    $stackRelativeRefs = ([regex]::Matches($stackContent, '(?:src|href)=\"\\./')).Count
  }

  if ($rootExists -and $stackExists) {
    $sameHash = ($rootHash -eq $stackHash)
  }

  $rows += [PSCustomObject]@{
    file = $f
    root_exists = $rootExists
    stack_exists = $stackExists
    same_hash = $sameHash
    root_sha256 = $rootHash
    stack_sha256 = $stackHash
    root_abs_windows_refs = $rootAbsWin
    stack_abs_windows_refs = $stackAbsWin
    root_rooted_web_refs = $rootRootedRefs
    stack_rooted_web_refs = $stackRootedRefs
    root_relative_refs = $rootRelativeRefs
    stack_relative_refs = $stackRelativeRefs
  }
}

$csvPath = Join-Path $OutputRoot 'dashboard_mirror_parity_audit.csv'
$rows | Export-Csv -NoTypeInformation -Path $csvPath -Encoding UTF8

$drift = @($rows | Where-Object { $_.root_exists -and $_.stack_exists -and -not $_.same_hash }).Count
$missing = @($rows | Where-Object { -not $_.root_exists -or -not $_.stack_exists }).Count
$risk = @($rows | Where-Object { $_.root_abs_windows_refs -gt 0 -or $_.stack_abs_windows_refs -gt 0 }).Count

$mdPath = Join-Path $OutputRoot 'dashboard_mirror_parity_audit.md'
$md = @()
$md += '# Dashboard Mirror Parity Audit'
$md += "Generated UTC: $((Get-Date).ToUniversalTime().ToString('o'))"
$md += ''
$md += "- Compared files: $($rows.Count)"
$md += "- Hash drift pairs: $drift"
$md += "- Missing-side files: $missing"
$md += "- Files with absolute Windows-path refs: $risk"
$md += ''
$md += '| File | Root Exists | Stack Exists | Same Hash | Root Abs Win Refs | Stack Abs Win Refs | Root ./ refs | Stack ./ refs |'
$md += '|---|---|---|---|---:|---:|---:|---:|'
foreach ($r in $rows) {
  $md += "| $($r.file) | $($r.root_exists) | $($r.stack_exists) | $($r.same_hash) | $($r.root_abs_windows_refs) | $($r.stack_abs_windows_refs) | $($r.root_relative_refs) | $($r.stack_relative_refs) |"
}
Set-Content -Path $mdPath -Value ($md -join [Environment]::NewLine) -Encoding UTF8

Write-Output "PARITY_CSV=$csvPath"
Write-Output "PARITY_MD=$mdPath"
Write-Output "DRIFT=$drift MISSING=$missing ABSWIN=$risk"
