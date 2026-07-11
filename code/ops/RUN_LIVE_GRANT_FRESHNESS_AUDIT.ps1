[CmdletBinding()]
param(
    [string]$StackRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [int]$Limit = 120,
    [int]$GateTop = 8,
    [switch]$SkipGitPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Started = Get-Date
$Desktop = [Environment]::GetFolderPath("Desktop")
$OpsRoot = Join-Path $StackRoot "code\ops"
$OutOps = Join-Path $StackRoot "out\ops"
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $StackRoot "code\.venv\Scripts\python.exe"),
        (Join-Path $StackRoot ".venv\Scripts\python.exe"),
        "python",
        "py"
    )
    foreach ($cand in $candidates) {
        if ($cand -in @("python","py")) {
            $cmd = Get-Command $cand -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
        } elseif (Test-Path -LiteralPath $cand) {
            return $cand
        }
    }
    return $null
}

function Read-JsonSafe {
    param([string]$Path)
    try {
        if (Test-Path -LiteralPath $Path) {
            return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -Depth 100
        }
    } catch {}
    return $null
}

function Age-Row {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return [ordered]@{
            path = $Path
            exists = $false
            age_hours = $null
            freshness = "MISSING"
        }
    }
    $item = Get-Item -LiteralPath $Path
    $age = [math]::Round(((Get-Date).ToUniversalTime() - $item.LastWriteTimeUtc).TotalHours, 2)
    $fresh = if ($age -le 24) { "FRESH" } elseif ($age -le 72) { "AGING" } else { "STALE" }
    return [ordered]@{
        path = $Path
        exists = $true
        modified_utc = $item.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
        age_hours = $age
        freshness = $fresh
    }
}

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    $t0 = Get-Date
    $row = [ordered]@{
        name = $Name
        started_utc = $t0.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        status = "ok"
        elapsed_sec = 0
        error = ""
    }
    Write-Host "STEP_START $Name"
    try {
        $output = & $Action 2>&1
        foreach ($line in @($output)) { Write-Host $line }
    } catch {
        $row.status = "error"
        $row.error = $_.Exception.Message
        Write-Host "STEP_ERROR $Name $($row.error)"
    }
    $row.elapsed_sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    Write-Host "STEP_DONE $Name status=$($row.status)"
    return $row
}

Ensure-Dir $OutOps
$Python = Resolve-Python
if (-not $Python) { throw "Python not found." }

$Steps = New-Object "System.Collections.Generic.List[object]"

Push-Location $StackRoot
try {
    $Scripts = @(
        @{ name = "grant_hunter_v2"; path = Join-Path $StackRoot "code\grant_hunter_v2.py"; args = @("--profile", (Join-Path $StackRoot "code\grants_profile_lumencore.json"), "hunt") },
        @{ name = "grant_submission_readiness_audit"; path = Join-Path $OpsRoot "BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py"; args = @() },
        @{ name = "grant_waiting_actions"; path = Join-Path $OpsRoot "BUILD_GRANT_WAITING_ACTIONS.py"; args = @() },
        @{ name = "grant_followup_tracker"; path = Join-Path $OpsRoot "BUILD_GRANT_FOLLOWUP_TRACKER.py"; args = @() },
        @{ name = "grant_dashboard_status_feed"; path = Join-Path $OpsRoot "BUILD_GRANT_DASHBOARD_STATUS_FEED.py"; args = @() }
    )

    $Fastlane = Join-Path $OpsRoot "RUN_GRANT_FACTORY_FASTLANE.ps1"
    if (Test-Path -LiteralPath $Fastlane) {
        $Steps.Add((Run-Step -Name "grant_factory_fastlane" -Action {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Fastlane -State APPROVED -Limit $Limit -GateTop $GateTop -RunParityAudit
            if ($LASTEXITCODE -ne 0) { throw "Fastlane exit code $LASTEXITCODE" }
        }))
    }

    foreach ($s in $Scripts) {
        if (Test-Path -LiteralPath $s.path) {
            $Steps.Add((Run-Step -Name $s.name -Action {
                & $Python $s.path @($s.args)
                if ($LASTEXITCODE -ne 0) { throw "$($s.name) exit code $LASTEXITCODE" }
            }))
        }
    }
} finally {
    Pop-Location
}

$Watch = @(
    "out\grant_approval_queue.json",
    "out\grants\grants_ranked_v2.json",
    "out\ops\grant_submit_fit_pack\grant_submit_fit_pack_latest.json",
    "out\ops\grant_factory_fastlane_latest.json",
    "out\ops\grant_submission_readiness_audit_latest.json",
    "out\ops\grant_dashboard_status_feed_latest.json",
    "dashboard\data\grant_readiness_status.json",
    "out\ops\grants_live_submission_ledger_latest.json",
    "out\ops\grants_email_receipts_latest.json",
    "out\ops\mission_control_support\mission_control_support_latest.json"
)

$Freshness = @()
foreach ($rel in $Watch) {
    $Freshness += ,(Age-Row -Path (Join-Path $StackRoot $rel))
}

$Errors = @($Steps | Where-Object { $_.status -ne "ok" }).Count
$Missing = @($Freshness | Where-Object { $_.freshness -eq "MISSING" }).Count
$Stale = @($Freshness | Where-Object { $_.freshness -eq "STALE" }).Count
$StepRows = @($Steps.ToArray())
$FreshnessRows = @($Freshness)

$Overall = if ($Errors -gt 0) {
    "ERRORS_NEED_REVIEW"
} elseif ($Missing -gt 0) {
    "MISSING_ARTIFACTS"
} elseif ($Stale -gt 0) {
    "STALE_ARTIFACTS"
} else {
    "FRESH"
}

$Payload = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    scope = "live_grant_freshness_audit"
    stack_root = $StackRoot
    overall = $Overall
    step_errors = $Errors
    missing_artifacts = $Missing
    stale_artifacts = $Stale
    steps = $StepRows
    artifact_freshness = $FreshnessRows
    boundaries = @(
        "This audit does not submit grants.",
        "Portal certifications and final submission remain user-controlled.",
        "Modeled values are not revenue or audited savings.",
        "No flight control, drone swarm control, weapons, autonomous physical actuation, medical diagnosis, or certified safety claim is created."
    )
}

$Json = Join-Path $OutOps "live_grant_freshness_audit_$Stamp.json"
$JsonLatest = Join-Path $OutOps "live_grant_freshness_audit_latest.json"
$Md = Join-Path $OutOps "live_grant_freshness_audit_$Stamp.md"
$MdLatest = Join-Path $OutOps "live_grant_freshness_audit_latest.md"
$DesktopMd = Join-Path $Desktop "LumenCore_Live_Grant_Freshness_Audit.md"

$Payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Json -Encoding UTF8
$Payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonLatest -Encoding UTF8

$Lines = New-Object "System.Collections.Generic.List[string]"
$Lines.Add("# LumenCore Live Grant Freshness Audit")
$Lines.Add("")
$Lines.Add("Generated UTC: $($Payload.generated_utc)")
$Lines.Add("Overall: $Overall")
$Lines.Add("")
$Lines.Add("## Step Results")
foreach ($s in $Steps) {
    $line = "- $($s.name): $($s.status) in $($s.elapsed_sec)s"
    if ($s.error) { $line += " | $($s.error)" }
    $Lines.Add($line)
}
$Lines.Add("")
$Lines.Add("## Artifact Freshness")
foreach ($r in $Freshness) {
    $Lines.Add("- $($r.freshness): $($r.path) | age_hours=$($r.age_hours)")
}
$Lines.Add("")
$Lines.Add("## Boundaries")
foreach ($b in $Payload.boundaries) {
    $Lines.Add("- $b")
}

$Text = ($Lines -join "`n") + "`n"
$Text | Set-Content -LiteralPath $Md -Encoding UTF8
$Text | Set-Content -LiteralPath $MdLatest -Encoding UTF8
$Text | Set-Content -LiteralPath $DesktopMd -Encoding UTF8

Write-Host ""
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_OVERALL=$Overall"
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_JSON=$JsonLatest"
Write-Host "LIVE_GRANT_FRESHNESS_AUDIT_MD=$MdLatest"
Write-Host "DESKTOP_COPY=$DesktopMd"

if ($Overall -eq "ERRORS_NEED_REVIEW") { exit 2 }
if ($Overall -eq "MISSING_ARTIFACTS") { exit 3 }
if ($Overall -eq "STALE_ARTIFACTS") { exit 4 }
exit 0
