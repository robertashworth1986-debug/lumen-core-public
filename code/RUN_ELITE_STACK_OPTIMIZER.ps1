param(
    [switch]$OpenWallboards,
    [switch]$OpenDashboard,
    [switch]$IncludeAdaptiveUniverse
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) { $PY = "python" }

Write-Host "Elite Stack Optimizer" -ForegroundColor Cyan
Write-Host "Root: $ROOT"
Write-Host "Python: $PY"

function Run-Step {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$Command,
        [string]$WorkingDirectory = $CODE
    )
    Write-Host "`n[$Label]" -ForegroundColor Yellow
    Push-Location $WorkingDirectory
    try {
        Invoke-Expression $Command
    }
    finally {
        Pop-Location
    }
}

Run-Step -Label "1/10 Sync provider registry + source truth" -Command "& '$PY' '$CODE\FIX_REGISTRY_FROM_LUMA_ENV.py'"
Run-Step -Label "2/10 Rebuild measured source audit" -Command "& '$PY' '$CODE\FIX_MEASURED_SOURCE_AUDIT.py'"
Run-Step -Label "3/10 Rebuild institutional command center" -Command "& '$PY' '$CODE\execution\build_institutional_crypto_paper_dashboard.py' --mode export"
Run-Step -Label "4/10 Rebuild stage wallboard" -Command "powershell -ExecutionPolicy Bypass -File '$CODE\RUN_INVESTOR_WALLBOARD.ps1' -StageMode -Mode export"
Run-Step -Label "5/10 Build investor evidence pack" -Command "& '$PY' '$CODE\build_investor_evidence_pack.py'"
Run-Step -Label "6/10 Build audit derivation pack" -Command "& '$PY' '$CODE\BUILD_AUDIT_GRADE_DERIVATION_PACK.py'"
Run-Step -Label "7/11 Build approved source breadth" -Command "& '$PY' '$CODE\BUILD_APPROVED_SOURCE_BREADTH.py'"
Run-Step -Label "8/11 Build institutional metrics scorecard" -Command "& '$PY' '$CODE\BUILD_INSTITUTIONAL_METRICS_SCORECARD.py'"
Run-Step -Label "9/12 Build investor breadth page" -Command "& '$PY' '$CODE\BUILD_INVESTOR_BREADTH_PAGE.py'"
Run-Step -Label "10/12 Refresh unified dashboards" -Command "& '$PY' '$CODE\dashboard_unified_refresh.py'"
if ($IncludeAdaptiveUniverse) {
    Run-Step -Label "11/12 Adaptive universe rebuild" -Command "& '$PY' '$CODE\BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py'"
} else {
    Write-Host "`n[11/12 Adaptive universe rebuild] SKIPPED (use -IncludeAdaptiveUniverse to enable)" -ForegroundColor DarkYellow
}
Run-Step -Label "12/12 Refresh master context snapshot" -Command "& '$PY' '$CODE\build_master_context_snapshot.py'"

Write-Host "`n[Verification Snapshot]" -ForegroundColor Yellow
$registry = Join-Path $ROOT "config\live_source_registry.json"
$brief = Join-Path $ROOT "out\execution\institutional_opportunity_executive_brief.json"
$orch = Join-Path $ROOT "out\execution\live_engine_heartbeat.json"
$evidenceDir = Join-Path $ROOT "out\evidence_pack"
$auditPack = Join-Path $ROOT "out\AUDIT_GRADE_DERIVATION_PACK.json"
$unifiedDash = Join-Path $ROOT "dashboard\lumascout_dashboard.html"
$scorecard = Join-Path $ROOT "out\execution\institutional_metrics_scorecard.json"
$breadth = Join-Path $ROOT "out\approved_source_breadth_registry.json"
$investorBreadthPage = Join-Path $ROOT "dashboard\investor_breadth_credibility.html"

if (Test-Path $registry) {
    $r = Get-Content $registry -Raw | ConvertFrom-Json
    $rows = @($r.rows)
    $enabled = @($rows | Where-Object { $_.enabled -eq $true })
    Write-Host ("Enabled Sources: {0}/{1} across {2} sectors" -f $enabled.Count, $rows.Count, (@($enabled.sector | Where-Object {$_} | Sort-Object -Unique).Count)) -ForegroundColor Green
}
if (Test-Path $brief) {
    $b = Get-Content $brief -Raw | ConvertFrom-Json
    Write-Host ("Measured Lanes: sectors={0}, rows={1}, measured/hr={2}" -f $b.sectors, @($b.top_rows).Count, $b.measured_total_hour_usd) -ForegroundColor Green
}
if (Test-Path $orch) {
    $o = Get-Content $orch -Raw | ConvertFrom-Json
    Write-Host ("Execution Orchestrator: status={0}, stream={1}" -f $o.status, $o.stream_brief) -ForegroundColor Green
}
if (Test-Path $auditPack) {
    Write-Host ("Audit derivation pack: {0}" -f $auditPack) -ForegroundColor Green
}
if (Test-Path $scorecard) {
    $sc = Get-Content $scorecard -Raw | ConvertFrom-Json
    Write-Host ("Institutional scorecard: tier={0}, score={1}" -f $sc.readiness_tier, $sc.readiness_score) -ForegroundColor Green
}
if (Test-Path $breadth) {
    $br = Get-Content $breadth -Raw | ConvertFrom-Json
    Write-Host ("Source breadth: key={0}, open={1}, combined={2}" -f $br.key_backed_enabled_sources, $br.open_access_approved_sources, $br.combined_approved_sources) -ForegroundColor Green
}
if (Test-Path $investorBreadthPage) {
    Write-Host ("Investor breadth page: {0}" -f $investorBreadthPage) -ForegroundColor Green
}
if (Test-Path $evidenceDir) {
    $latestZip = Get-ChildItem -Path $evidenceDir -Filter "institutional_evidence_pack_*.zip" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $latestZip) {
        Write-Host ("Latest evidence pack: {0}" -f $latestZip.FullName) -ForegroundColor Green
    }
}
if (Test-Path $unifiedDash) {
    Write-Host ("Unified dashboard surface: {0}" -f $unifiedDash) -ForegroundColor Green
}

$dashboard = Join-Path $ROOT "dashboard\institutional_crypto_paper_dashboard.html"
$stage = Join-Path $ROOT "dashboard\stage_wallboard.html"

if ($OpenDashboard -and (Test-Path $dashboard)) { Invoke-Item $dashboard }
if ($OpenWallboards -and (Test-Path $stage)) { Invoke-Item $stage }

Write-Host "`nElite stack optimization complete." -ForegroundColor Cyan
