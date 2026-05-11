param(
  [string]$ReportsRoot = "",
  [string]$OutputPath = "",
  [switch]$OpenOutput
)

$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

function Get-LatestAutomationDir {
  param([string]$AutomationRoot)

  if (-not (Test-Path $AutomationRoot)) {
    return $null
  }

  $dirs = Get-ChildItem -Path $AutomationRoot -Directory | Sort-Object LastWriteTime -Descending
  if ($dirs.Count -eq 0) {
    return $null
  }

  return $dirs[0].FullName
}

$workspaceRoot = Get-WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($ReportsRoot)) {
  $ReportsRoot = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = Join-Path $ReportsRoot "WARROOM_STATUS.md"
}

$preflightPath = Join-Path $ReportsRoot "preflight_latest.json"
$automationRoot = Join-Path $ReportsRoot "automation_out"
$qrManifestPath = Join-Path $ReportsRoot "qr_lane_pack\qr_manifest.json"

$preflight = $null
if (Test-Path $preflightPath) {
  $preflight = Get-Content -Path $preflightPath -Raw | ConvertFrom-Json
}

$latestAutomationDir = Get-LatestAutomationDir -AutomationRoot $automationRoot
$leadSummary = $null
if ($latestAutomationDir) {
  $leadSummaryPath = Join-Path $latestAutomationDir "lead_summary.json"
  if (Test-Path $leadSummaryPath) {
    $leadSummary = Get-Content -Path $leadSummaryPath -Raw | ConvertFrom-Json
  }
}

$qrCount = 0
if (Test-Path $qrManifestPath) {
  $qrManifest = Get-Content -Path $qrManifestPath -Raw | ConvertFrom-Json
  if ($qrManifest -is [array]) {
    $qrCount = $qrManifest.Count
  }
  elseif ($null -ne $qrManifest) {
    $qrCount = 1
  }
}

$healthStatus = "unknown"
if ($preflight) {
  $healthStatus = if ($preflight.overall_ready) { "ready" } else { "attention needed" }
}

$leadCount = if ($leadSummary) { [int]$leadSummary.total_leads } else { 0 }
$p1Count = if ($leadSummary) { [int]$leadSummary.p1_ready_now } else { 0 }
$slotCount = if ($leadSummary) { [int]$leadSummary.slots_loaded } else { 0 }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# NED War Room Status")
$lines.Add("")
$lines.Add("Generated: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))")
$lines.Add("")
$lines.Add("## Executive Summary")
$lines.Add("")
$lines.Add("- Platform health: $healthStatus")
$lines.Add("- Leads in pipeline: $leadCount")
$lines.Add("- P1 leads: $p1Count")
$lines.Add("- Meeting slots loaded: $slotCount")
$lines.Add("- QR lanes available: $qrCount")
$lines.Add("")

$lines.Add("## Source Artifacts")
$lines.Add("")
$lines.Add("- Preflight: $preflightPath")
$lines.Add("- Latest automation: $latestAutomationDir")
$lines.Add("- QR manifest: $qrManifestPath")
$lines.Add("")

if ($preflight) {
  $lines.Add("## Preflight Snapshot")
  $lines.Add("")
  $lines.Add("- overall_ready: $($preflight.overall_ready)")
  $lines.Add("- http_checks_failed: $($preflight.http_checks_failed) / $($preflight.http_checks_total)")
  $lines.Add("- ssh_checks_failed: $($preflight.ssh_checks_failed) / $($preflight.ssh_checks_total)")
  $lines.Add("")
}

if ($leadSummary) {
  $lines.Add("## Lead Pipeline Snapshot")
  $lines.Add("")
  $lines.Add("- total_leads: $($leadSummary.total_leads)")
  $lines.Add("- with_email: $($leadSummary.with_email)")
  $lines.Add("- with_phone: $($leadSummary.with_phone)")
  $lines.Add("- with_linkedin: $($leadSummary.with_linkedin)")
  $lines.Add("- meeting_intent_detected: $($leadSummary.meeting_intent_detected)")
  $lines.Add("")
}

$lines.Add("## Operator Commands")
$lines.Add("")
$lines.Add('```powershell')
$lines.Add('./INSTITUTIONAL_STACK_V2/code/deploy/NED_EVENT_COMMANDER.ps1 -IncludeSshChecks -LeadCsvPath ./reports/NED_Showcase_2026-05-21/LEAD_CAPTURE_TEMPLATE.csv -SlotsCsvPath ./reports/NED_Showcase_2026-05-21/MEETING_SLOTS_TEMPLATE.csv -GenerateQrLanePack -GenerateWarroomSnapshot')
$lines.Add('./INSTITUTIONAL_STACK_V2/code/deploy/NED_WARROOM_SNAPSHOT.ps1')
$lines.Add('```')

$lines | Set-Content -Path $OutputPath -Encoding UTF8

Write-Host ""
Write-Host "NED war room snapshot generated"
Write-Host "- output: $OutputPath"

if ($OpenOutput) {
  Invoke-Item -Path $OutputPath
}
