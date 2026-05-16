param(
  [string]$BaseUrl = "https://lumen-core.ai",
  [string]$ReportsRoot = "",
  [string]$OutOpsRoot = "",
  [string]$QrCampaignTag = "ned2026",
  [switch]$IncludeWarroomSnapshot,
  [switch]$OpenOutput
)

$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

function To-RelativePath {
  param(
    [string]$Root,
    [string]$Path
  )

  $rootResolved = (Resolve-Path $Root).Path.TrimEnd('\\') + "\\"
  $pathResolved = (Resolve-Path $Path).Path

  if ($pathResolved.StartsWith($rootResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $pathResolved.Substring($rootResolved.Length).Replace('\\', '/')
  }

  return $pathResolved.Replace('\\', '/')
}

function Add-UniquePath {
  param(
    [System.Collections.Generic.HashSet[string]]$Seen,
    [System.Collections.Generic.List[string]]$Paths,
    [string]$RelativePath
  )

  if ([string]::IsNullOrWhiteSpace($RelativePath)) {
    return
  }

  $normalized = $RelativePath.Replace('\\', '/').Trim()
  if ($Seen.Add($normalized)) {
    $Paths.Add($normalized)
  }
}

$workspaceRoot = Get-WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($ReportsRoot)) {
  $ReportsRoot = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21"
}

if ([string]::IsNullOrWhiteSpace($OutOpsRoot)) {
  $OutOpsRoot = Join-Path $workspaceRoot "out\ops"
}

$utcStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$generatedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$exportDir = Join-Path $OutOpsRoot ("ned_final_print_export_" + $utcStamp)
New-Item -ItemType Directory -Path $exportDir -Force | Out-Null

$qrPackScript = Join-Path $PSScriptRoot "NED_QR_LANE_PACK.ps1"
$warroomScript = Join-Path $PSScriptRoot "NED_WARROOM_SNAPSHOT.ps1"
$packetManifestPath = Join-Path $ReportsRoot "print_packet_manifest.json"

if (-not (Test-Path $qrPackScript)) {
  throw "Missing script: $qrPackScript"
}

if (-not (Test-Path $packetManifestPath)) {
  throw "Missing print packet manifest: $packetManifestPath"
}

if ($IncludeWarroomSnapshot -and -not (Test-Path $warroomScript)) {
  throw "Missing script: $warroomScript"
}

Write-Host ""
Write-Host "Refreshing QR lane pack..."
& $qrPackScript -BaseUrl $BaseUrl -CampaignTag $QrCampaignTag

if ($IncludeWarroomSnapshot) {
  Write-Host ""
  Write-Host "Refreshing war room snapshot..."
  & $warroomScript
}

$packetManifest = Get-Content -Path $packetManifestPath -Raw | ConvertFrom-Json

$artifactPaths = New-Object System.Collections.Generic.List[string]
$seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)

foreach ($artifact in $packetManifest.artifacts) {
  if ($null -ne $artifact.path) {
    Add-UniquePath -Seen $seen -Paths $artifactPaths -RelativePath $artifact.path
  }
}

$extraArtifacts = @(
  "reports/NED_Showcase_2026-05-21/QR_INVESTOR_HANDOUT_2026-05-21.html",
  "reports/NED_Showcase_2026-05-21/qr_lane_pack/index.html",
  "reports/NED_Showcase_2026-05-21/qr_lane_pack/QR_LINKS.md",
  "reports/NED_Showcase_2026-05-21/qr_lane_pack/qr_manifest.json",
  "reports/NED_Showcase_2026-05-21/print_packet_manifest.json",
  "reports/NED_Showcase_2026-05-21/PRINT_PACKET_INDEX.md",
  "reports/NED_Showcase_2026-05-21/INVESTOR_AI_VALUATION_KIT.md",
  "reports/NED_Showcase_2026-05-21/WARROOM_STATUS.md"
)

foreach ($path in $extraArtifacts) {
  Add-UniquePath -Seen $seen -Paths $artifactPaths -RelativePath $path
}

$copied = New-Object System.Collections.Generic.List[object]
$missing = New-Object System.Collections.Generic.List[object]

foreach ($relativePath in $artifactPaths) {
  $sourcePath = Join-Path $workspaceRoot ($relativePath.Replace('/', '\\'))

  if (Test-Path $sourcePath) {
    $destPath = Join-Path $exportDir ($relativePath.Replace('/', '\\'))
    $destDir = Split-Path -Path $destPath -Parent
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Copy-Item -Path $sourcePath -Destination $destPath -Force

    $copied.Add([pscustomobject]@{
      relative_path = $relativePath
      source_path = $sourcePath
      exported_path = $destPath
    })
  }
  else {
    $missing.Add([pscustomobject]@{
      relative_path = $relativePath
      expected_source_path = $sourcePath
    })
  }
}

$exportManifestPath = Join-Path $exportDir "export_manifest.json"
$exportSummaryPath = Join-Path $exportDir "export_summary.md"

$exportManifest = [pscustomobject]@{
  generated_utc = $generatedUtc
  scope = "NED final print and export package"
  export_dir = $exportDir
  source_manifest = To-RelativePath -Root $workspaceRoot -Path $packetManifestPath
  qr_lane_pack_refreshed = $true
  warroom_snapshot_included = [bool]$IncludeWarroomSnapshot
  copied_count = $copied.Count
  missing_count = $missing.Count
  copied = $copied
  missing = $missing
}

$exportManifest | ConvertTo-Json -Depth 8 | Set-Content -Path $exportManifestPath -Encoding UTF8

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# NED Final Print Export")
$lines.Add("")
$lines.Add("Generated UTC: $generatedUtc")
$lines.Add("Scope: Final event print and export package with AI valuation reproducibility assets.")
$lines.Add("")
$lines.Add("## Actions Completed")
$lines.Add("")
$lines.Add("- Refreshed QR lane pack via NED_QR_LANE_PACK.ps1")
if ($IncludeWarroomSnapshot) {
  $lines.Add("- Refreshed war room snapshot via NED_WARROOM_SNAPSHOT.ps1")
}
$lines.Add("- Copied packet assets into deterministic export directory")
$lines.Add("")
$lines.Add("## Export Counts")
$lines.Add("")
$lines.Add("- Copied files: $($copied.Count)")
$lines.Add("- Missing files: $($missing.Count)")
$lines.Add("")
$lines.Add("## Evidence Paths")
$lines.Add("")
$lines.Add("- Source packet manifest: $($packetManifestPath)")
$lines.Add("- Export manifest: $($exportManifestPath)")
$lines.Add("- Export summary: $($exportSummaryPath)")
$lines.Add("")
$lines.Add("## Run Command")
$lines.Add("")
$lines.Add('```powershell')
$lines.Add('./INSTITUTIONAL_STACK_V2/code/deploy/NED_FINAL_PRINT_EXPORT.ps1 -IncludeWarroomSnapshot -OpenOutput')
$lines.Add('```')
$lines.Add("")
$lines.Add("## Primary Print Files")
$lines.Add("")
$lines.Add("- reports/NED_Showcase_2026-05-21/PRINT_PACKET_2026-05-21.html")
$lines.Add("- reports/NED_Showcase_2026-05-21/QR_INVESTOR_HANDOUT_2026-05-21.html")
$lines.Add("- reports/NED_Showcase_2026-05-21/INVESTOR_AI_VALUATION_KIT.md")

$lines | Set-Content -Path $exportSummaryPath -Encoding UTF8

Write-Host ""
Write-Host "NED final print export complete"
Write-Host "- export dir:      $exportDir"
Write-Host "- copied files:    $($copied.Count)"
Write-Host "- missing files:   $($missing.Count)"
Write-Host "- manifest:        $exportManifestPath"
Write-Host "- summary:         $exportSummaryPath"

if ($OpenOutput) {
  Invoke-Item -Path $exportDir

  $printDeckPath = Join-Path $exportDir "reports\NED_Showcase_2026-05-21\PRINT_PACKET_2026-05-21.html"
  $qrSheetPath = Join-Path $exportDir "reports\NED_Showcase_2026-05-21\QR_INVESTOR_HANDOUT_2026-05-21.html"

  if (Test-Path $printDeckPath) {
    Invoke-Item -Path $printDeckPath
  }

  if (Test-Path $qrSheetPath) {
    Invoke-Item -Path $qrSheetPath
  }
}
