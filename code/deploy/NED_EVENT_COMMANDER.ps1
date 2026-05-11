param(
  [string]$BaseUrl = "https://lumen-core.ai",
  [switch]$IncludeSshChecks,
  [string]$SshUser = "opc",
  [string]$SshHost = "157.151.148.234",
  [string]$SshKeyPath = "C:\Users\Novac\Downloads\ssh-key-2026-04-23.key",
  [string]$LeadCsvPath = "",
  [string]$SlotsCsvPath = "",
  [int]$SlotsPerLead = 2,
  [string]$OutputDir = "",
  [switch]$GenerateQrLanePack,
  [string]$QrCampaignTag = "ned2026",
  [string]$QrOutDir = "",
  [switch]$GenerateWarroomSnapshot,
  [string]$WarroomOutputPath = "",
  [switch]$OpenOutput
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$reportsRoot = Join-Path $workspaceRoot "reports\NED_Showcase_2026-05-21"

$preflightScript = Join-Path $PSScriptRoot "NED_EVENT_PREFLIGHT.ps1"
$pipelineScript = Join-Path $PSScriptRoot "NED_LEAD_PIPELINE_AUTOMATION.ps1"
$qrPackScript = Join-Path $PSScriptRoot "NED_QR_LANE_PACK.ps1"
$warroomScript = Join-Path $PSScriptRoot "NED_WARROOM_SNAPSHOT.ps1"

if ([string]::IsNullOrWhiteSpace($LeadCsvPath)) {
  $LeadCsvPath = Join-Path $reportsRoot "LEAD_CAPTURE_TEMPLATE.csv"
}

if ([string]::IsNullOrWhiteSpace($SlotsCsvPath)) {
  $SlotsCsvPath = Join-Path $reportsRoot "MEETING_SLOTS_TEMPLATE.csv"
}

if (-not (Test-Path $preflightScript)) {
  throw "Missing script: $preflightScript"
}

if (-not (Test-Path $pipelineScript)) {
  throw "Missing script: $pipelineScript"
}

if ($GenerateQrLanePack -and -not (Test-Path $qrPackScript)) {
  throw "Missing script: $qrPackScript"
}

if ($GenerateWarroomSnapshot -and -not (Test-Path $warroomScript)) {
  throw "Missing script: $warroomScript"
}

Write-Host ""
Write-Host "Running preflight checks..."

$preflightParams = @{
  BaseUrl = $BaseUrl
  SshUser = $SshUser
  SshHost = $SshHost
  SshKeyPath = $SshKeyPath
  OutFile = (Join-Path $reportsRoot "preflight_latest.json")
}
if ($IncludeSshChecks) {
  $preflightParams.IncludeSshChecks = $true
}

& $preflightScript @preflightParams
if ($LASTEXITCODE -ne 0) {
  throw "Preflight failed. Resolve issues before continuing."
}

Write-Host ""
Write-Host "Preflight passed. Building lead follow-up artifacts..."

$pipelineParams = @{
  LeadCsvPath = $LeadCsvPath
  SlotsCsvPath = $SlotsCsvPath
  SlotsPerLead = $SlotsPerLead
}
if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
  $pipelineParams.OutputDir = $OutputDir
}
if ($OpenOutput) {
  $pipelineParams.OpenOutput = $true
}

& $pipelineScript @pipelineParams
if ($LASTEXITCODE -ne 0) {
  throw "Lead pipeline automation failed."
}

if ($GenerateQrLanePack) {
  Write-Host ""
  Write-Host "Generating QR lane pack..."

  $qrParams = @{
    BaseUrl = $BaseUrl
    CampaignTag = $QrCampaignTag
  }
  if (-not [string]::IsNullOrWhiteSpace($QrOutDir)) {
    $qrParams.OutDir = $QrOutDir
  }
  if ($OpenOutput) {
    $qrParams.OpenOutput = $true
  }

  & $qrPackScript @qrParams
  if ($LASTEXITCODE -ne 0) {
    throw "QR lane pack generation failed."
  }
}

if ($GenerateWarroomSnapshot) {
  Write-Host ""
  Write-Host "Generating war room snapshot..."

  $warroomParams = @{}
  if (-not [string]::IsNullOrWhiteSpace($WarroomOutputPath)) {
    $warroomParams.OutputPath = $WarroomOutputPath
  }
  if ($OpenOutput) {
    $warroomParams.OpenOutput = $true
  }

  & $warroomScript @warroomParams
  if ($LASTEXITCODE -ne 0) {
    throw "War room snapshot generation failed."
  }
}

Write-Host ""
Write-Host "NED event commander complete"
Write-Host "- preflight status: pass"
Write-Host "- lead automation: complete"
if ($GenerateQrLanePack) {
  Write-Host "- qr lane pack:   complete"
}
if ($GenerateWarroomSnapshot) {
  Write-Host "- warroom status: complete"
}
Write-Host ""
