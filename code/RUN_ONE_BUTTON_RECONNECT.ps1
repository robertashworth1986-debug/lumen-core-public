param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 5016,
    [double]$RefreshSeconds = 15,
    [switch]$ForceNormalize,
    [switch]$KillAllStackProcesses,
    [switch]$DryRunKillAll,
    [switch]$KillAllAndStartAutopilot,
    [switch]$StartAutopilot,
    [switch]$OpenResumePrompt,
    [switch]$RunEliteOptimizer
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$OUT_EXEC = Join-Path $ROOT "out\execution"

$TickerRunner = Join-Path $CODE "RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1"
$DashboardRunner = Join-Path $CODE "RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1"
$DashboardHealthcheckRunner = Join-Path $CODE "RUN_INSTITUTIONAL_DASHBOARD_HEALTHCHECK.ps1"
$SnapshotRunner = Join-Path $CODE "RUN_BUILD_MASTER_CONTEXT_SNAPSHOT.ps1"
$EliteOptimizerRunner = Join-Path $CODE "RUN_ELITE_STACK_OPTIMIZER.ps1"
$AutopilotRunner = Join-Path $CODE "RUN_ZERO_TOUCH_AUTOPILOT.ps1"

$HealthLatest = Join-Path $OUT_EXEC "institutional_crypto_dashboard_health_latest.json"
$HealthHistory = Join-Path $OUT_EXEC "institutional_crypto_dashboard_health_history.jsonl"
$ResumePrompt = Join-Path $OUT_EXEC "copilot_resume_prompt.txt"
$SnapshotJson = Join-Path $OUT_EXEC "master_context_snapshot.json"
$PackageInventory = Join-Path $OUT_EXEC "python_package_inventory.json"
$TickerStatusJson = Join-Path $OUT_EXEC "multi_exchange_paper_ticker_status.json"
$InstitutionalScorecardJson = Join-Path $OUT_EXEC "institutional_metrics_scorecard.json"
$ReconnectStatusLatest = Join-Path $OUT_EXEC "institutional_reconnect_status_latest.json"
$ReconnectStatusHistory = Join-Path $OUT_EXEC "institutional_reconnect_status_history.jsonl"

Write-Host "One-button reconnect launcher" -ForegroundColor Cyan
Write-Host "Workspace: $ROOT"
Write-Host "Dashboard URL target: http://${BindHost}:$Port"

function Get-AutopilotProcesses {
    @(
        Get-CimInstance Win32_Process |
            Where-Object {
                ($_.Name -like "*powershell*") -and
                $_.CommandLine -like "*RUN_ZERO_TOUCH_AUTOPILOT.ps1*"
            }
    )
}

function Get-TickerProcesses {
    @(
        Get-CimInstance Win32_Process |
            Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*multi_exchange_paper_ticker.py*" }
    )
}

function Get-DashboardProcesses {
    @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "python.exe" -and
                $_.CommandLine -like "*build_institutional_crypto_paper_dashboard.py*" -and
                $_.CommandLine -like "*--mode serve*" -and
                $_.CommandLine -like "*--port $Port*"
            }
    )
}

function Stop-Processes {
    param([array]$Processes)
    foreach ($proc in $Processes) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Get-StackKillCandidates {
    $patterns = @(
        "*multi_exchange_paper_ticker.py*",
        "*build_institutional_crypto_paper_dashboard.py*",
        "*RUN_ZERO_TOUCH_AUTOPILOT.ps1*",
        "*src.dashboard_api:app*",
        "*artist_scout_engine*",
        "*kraken_swing_hunter.py*"
    )

    @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $cmd = [string]$_.CommandLine
                ($_.Name -eq "python.exe" -or $_.Name -like "*powershell*") -and
                $_.ProcessId -ne $PID -and
                (($cmd -like "*$ROOT*") -or ($cmd -like "*src.dashboard_api:app*")) -and
                ($patterns | Where-Object { $cmd -like $_ }).Count -gt 0
            }
    )
}

function Reduce-ToSingle {
    param(
        [array]$Processes,
        [string]$Label
    )
    if ($Processes.Count -le 1) {
        return
    }
    $keep = $Processes | Sort-Object ProcessId -Descending | Select-Object -First 1
    foreach ($proc in $Processes) {
        if ($proc.ProcessId -ne $keep.ProcessId) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Warning "Force-normalize: reduced $Label to single PID $($keep.ProcessId)."
}

function Get-RootProcessCount {
    param([array]$Processes)
    if ($null -eq $Processes -or $Processes.Count -eq 0) {
        return 0
    }
    $idSet = @{}
    foreach ($proc in $Processes) {
        $idSet[[string]$proc.ProcessId] = $true
    }
    $roots = 0
    foreach ($proc in $Processes) {
        if (-not $idSet.ContainsKey([string]$proc.ParentProcessId)) {
            $roots += 1
        }
    }
    return $roots
}

$autopilotProcs = Get-AutopilotProcesses
$autopilotManaged = ($autopilotProcs.Count -gt 0)
$autopilotPausedForNormalize = $false
$autopilotResumedAfterNormalize = $false
$autopilotResumeRequested = $false
$autopilotStartIssued = $false
$eliteOptimizerRan = $false
$eliteOptimizerOk = $false
$killAllStackStoppedCount = 0
$killAllCandidatesCount = 0

if ($KillAllAndStartAutopilot) {
    $KillAllStackProcesses = $true
    $ForceNormalize = $true
    $StartAutopilot = $true
    $RunEliteOptimizer = $true
    Write-Host "Preset enabled: KillAllAndStartAutopilot (kill-all + normalize + elite optimize + start autopilot)." -ForegroundColor Yellow
}

if ($KillAllStackProcesses) {
    Write-Host "Kill-all mode enabled: stopping known stack processes before reconnect bootstrap." -ForegroundColor Yellow
    $killTargets = Get-StackKillCandidates
    $killAllCandidatesCount = $killTargets.Count
    if ($killTargets.Count -gt 0) {
        if ($DryRunKillAll) {
            Write-Warning "Dry-run enabled. Would stop $($killTargets.Count) stack process(es)."
            $killTargets | Select-Object ProcessId, Name, CommandLine | Format-List | Out-Host
        } else {
            $killAllStackStoppedCount = $killTargets.Count
            Stop-Processes -Processes $killTargets
            Write-Warning "Stopped $killAllStackStoppedCount stack process(es)."
        }
    } else {
        Write-Host "No stack processes matched kill-all patterns."
    }
    $autopilotProcs = Get-AutopilotProcesses
    $autopilotManaged = ($autopilotProcs.Count -gt 0)
}

if ($autopilotManaged) {
    Write-Host "Detected active autopilot supervisor. Reconnect will use supervisor-aware mode."
}

if ($ForceNormalize) {
    Write-Host "Force-normalize mode enabled: enforcing single-instance ownership for ticker/dashboard." -ForegroundColor Yellow
    if ($autopilotManaged) {
        Write-Warning "Temporarily pausing autopilot supervisor during normalization."
        Stop-Processes -Processes $autopilotProcs
        $autopilotPausedForNormalize = $true
        $autopilotResumeRequested = $true
        $autopilotManaged = $false
    }
}

if (Test-Path $TickerRunner) {
    Write-Host "[1/5] Ensuring institutional ticker is running..."
    if ($autopilotManaged) {
        Write-Host "Ticker ownership is delegated to autopilot; skipping direct ticker launch."
    } else {
        $tickerBefore = @(Get-TickerProcesses).Count
        if ($tickerBefore -gt 1) {
            Write-Warning "Detected duplicate ticker processes ($tickerBefore). Performing controlled restart."
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $TickerRunner -Institutional -Restart -Detach
        } else {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $TickerRunner -Institutional -Detach
        }
        if ($ForceNormalize) {
            Reduce-ToSingle -Processes (Get-TickerProcesses) -Label "ticker"
        }
    }
} else {
    Write-Warning "Ticker runner missing: $TickerRunner"
}

if (Test-Path $DashboardRunner) {
    Write-Host "[2/5] Ensuring institutional dashboard is running..."
    if ($autopilotManaged) {
        Write-Host "Dashboard ownership is delegated to autopilot; skipping direct dashboard launch."
    } else {
        $dashboardBefore = Get-DashboardProcesses
        if ($dashboardBefore.Count -gt 1) {
            Write-Warning "Detected duplicate dashboard processes ($($dashboardBefore.Count)). Performing controlled restart."
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DashboardRunner -Mode serve -BindHost $BindHost -Port $Port -RefreshSeconds $RefreshSeconds -Restart -Detach
        } else {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DashboardRunner -Mode serve -BindHost $BindHost -Port $Port -RefreshSeconds $RefreshSeconds -Detach
        }
    }
} else {
    Write-Warning "Dashboard runner missing: $DashboardRunner"
}

if (Test-Path $DashboardHealthcheckRunner) {
    Write-Host "[3/5] Running dashboard healthcheck..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DashboardHealthcheckRunner `
        -BindHost $BindHost `
        -Port $Port `
        -MaxHeartbeatAgeSeconds 180 `
        -LatestFile $HealthLatest `
        -HistoryFile $HealthHistory
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Dashboard healthcheck did not pass immediately. Inspect: $HealthLatest"
        if (Test-Path $DashboardRunner) {
            Write-Warning "Attempting one dashboard restart+healthcheck recovery pass."
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DashboardRunner -Mode serve -BindHost $BindHost -Port $Port -RefreshSeconds $RefreshSeconds -Restart -Detach
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DashboardHealthcheckRunner `
                -BindHost $BindHost `
                -Port $Port `
                -MaxHeartbeatAgeSeconds 180 `
                -LatestFile $HealthLatest `
                -HistoryFile $HealthHistory
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Dashboard recovery pass still failed."
            }
        }
    }
} else {
    Write-Warning "Dashboard healthcheck runner missing: $DashboardHealthcheckRunner"
}

if (Test-Path $SnapshotRunner) {
    Write-Host "[4/5] Refreshing master context snapshot..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $SnapshotRunner
} else {
    Write-Warning "Master context snapshot runner missing: $SnapshotRunner"
}

if ($RunEliteOptimizer) {
    if (Test-Path $EliteOptimizerRunner) {
        Write-Host "[4.5/5] Running elite optimizer pipeline..." -ForegroundColor Yellow
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $EliteOptimizerRunner
        $eliteOptimizerRan = $true
        $eliteOptimizerOk = ($LASTEXITCODE -eq 0)
        if (-not $eliteOptimizerOk) {
            Write-Warning "Elite optimizer pipeline reported a non-zero exit code."
        }
    } else {
        Write-Warning "Elite optimizer runner missing: $EliteOptimizerRunner"
    }
}

if ($ForceNormalize -and $autopilotResumeRequested) {
    $StartAutopilot = $true
}

if ($StartAutopilot) {
    if (Test-Path $AutopilotRunner) {
        $autopilotNow = Get-AutopilotProcesses
        if ($autopilotNow.Count -gt 0) {
            Write-Host "[5/5] Autopilot already running."
        } else {
            Write-Host "[5/5] Starting zero-touch autopilot in detached terminal..."
            $startedAutopilotProc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", $AutopilotRunner
            ) -WorkingDirectory $CODE -WindowStyle Minimized -PassThru
            if ($null -ne $startedAutopilotProc) {
                $autopilotStartIssued = $true
                if ($autopilotResumeRequested) {
                    $autopilotResumedAfterNormalize = $true
                }
            }
        }
    } else {
        Write-Warning "Autopilot runner missing: $AutopilotRunner"
    }
} else {
    Write-Host "[5/5] Autopilot not started (use -StartAutopilot to enable)."
}

Write-Host "Reconnect complete." -ForegroundColor Green
Write-Host "Resume prompt file: $ResumePrompt"

if ($OpenResumePrompt -and (Test-Path $ResumePrompt)) {
    Invoke-Item $ResumePrompt
}

$tickerProcs = @(Get-TickerProcesses)
$dashboardProcs = @(Get-DashboardProcesses)
$tickerCount = $tickerProcs.Count
$dashboardCount = $dashboardProcs.Count
$tickerRootCount = Get-RootProcessCount -Processes $tickerProcs
$dashboardRootCount = Get-RootProcessCount -Processes $dashboardProcs
$autopilotProcs = Get-AutopilotProcesses
$autopilotManaged = ($autopilotProcs.Count -gt 0 -or $autopilotResumedAfterNormalize -or $autopilotStartIssued)

$healthObj = $null
if (Test-Path $HealthLatest) {
    try {
        $healthObj = Get-Content $HealthLatest -Raw | ConvertFrom-Json
    } catch {
        $healthObj = $null
    }
}

$snapshotAgeSeconds = $null
if (Test-Path $SnapshotJson) {
    try {
        $snap = Get-Content $SnapshotJson -Raw | ConvertFrom-Json
        $snapTs = [datetimeoffset]::Parse($snap.generated_utc)
        $snapshotAgeSeconds = [math]::Round((([datetimeoffset]::UtcNow - $snapTs).TotalSeconds), 2)
    } catch {
        $snapshotAgeSeconds = $null
    }
}

$packageInventoryFresh = $false
$packageInventoryAgeSeconds = $null
if (Test-Path $PackageInventory) {
    try {
        $pkg = Get-Content $PackageInventory -Raw | ConvertFrom-Json
        $pkgTs = [datetimeoffset]::Parse($pkg.generated_utc)
        $packageInventoryAgeSeconds = [math]::Round((([datetimeoffset]::UtcNow - $pkgTs).TotalSeconds), 2)
        $packageInventoryFresh = ($packageInventoryAgeSeconds -le 86400)
    } catch {
        $packageInventoryFresh = $false
        $packageInventoryAgeSeconds = $null
    }
}

$tickerStatusFresh = $false
$tickerStatusAgeSeconds = $null
if (Test-Path $TickerStatusJson) {
    try {
        $tickerStatus = Get-Content $TickerStatusJson -Raw | ConvertFrom-Json
        $tickerTs = [datetimeoffset]::Parse($tickerStatus.timestamp_utc)
        $tickerStatusAgeSeconds = [math]::Round((([datetimeoffset]::UtcNow - $tickerTs).TotalSeconds), 2)
        $tickerStatusFresh = ($tickerStatusAgeSeconds -le 300)
    } catch {
        $tickerStatusFresh = $false
        $tickerStatusAgeSeconds = $null
    }
}

$scorecardFresh = $false
$scorecardAgeSeconds = $null
if (Test-Path $InstitutionalScorecardJson) {
    try {
        $scorecard = Get-Content $InstitutionalScorecardJson -Raw | ConvertFrom-Json
        $scorecardTs = [datetimeoffset]::Parse($scorecard.generated_utc)
        $scorecardAgeSeconds = [math]::Round((([datetimeoffset]::UtcNow - $scorecardTs).TotalSeconds), 2)
        $scorecardFresh = ($scorecardAgeSeconds -le 21600)
    } catch {
        $scorecardFresh = $false
        $scorecardAgeSeconds = $null
    }
}

$healthOk = $false
if ($null -ne $healthObj -and $healthObj.PSObject.Properties.Name -contains "healthy") {
    $healthOk = [bool]$healthObj.healthy
}

$snapshotFresh = $false
if ($null -ne $snapshotAgeSeconds) {
    $snapshotFresh = ($snapshotAgeSeconds -le 300)
}

if ($ForceNormalize) {
    $tickerHealthy = ($tickerRootCount -eq 1 -or $tickerStatusFresh)
    $overallHealthy = ($tickerHealthy -and $dashboardRootCount -eq 1 -and $healthOk -and $snapshotFresh)
} elseif ($autopilotManaged) {
    $tickerHealthy = ($tickerRootCount -ge 1 -or $tickerStatusFresh)
    $overallHealthy = ($tickerHealthy -and $dashboardRootCount -ge 1 -and $healthOk -and $snapshotFresh)
} else {
    $tickerHealthy = ($tickerRootCount -eq 1 -or $tickerStatusFresh)
    $overallHealthy = ($tickerHealthy -and $dashboardRootCount -eq 1 -and $healthOk -and $snapshotFresh)
}

$statusPayload = [ordered]@{
    timestamp_utc = [datetime]::UtcNow.ToString("o")
    target_dashboard_url = "http://$BindHost`:$Port"
    checks = [ordered]@{
        ticker_process_count = $tickerCount
        ticker_root_count = $tickerRootCount
        dashboard_process_count = $dashboardCount
        dashboard_root_count = $dashboardRootCount
        dashboard_health_ok = $healthOk
        snapshot_fresh = $snapshotFresh
        snapshot_age_seconds = $snapshotAgeSeconds
        package_inventory_fresh = $packageInventoryFresh
        package_inventory_age_seconds = $packageInventoryAgeSeconds
        ticker_status_fresh = $tickerStatusFresh
        ticker_status_age_seconds = $tickerStatusAgeSeconds
        institutional_scorecard_fresh = $scorecardFresh
        institutional_scorecard_age_seconds = $scorecardAgeSeconds
        autopilot_managed = $autopilotManaged
        autopilot_process_count = $autopilotProcs.Count
        autopilot_start_issued = $autopilotStartIssued
        force_normalize_requested = [bool]$ForceNormalize
        kill_all_stack_requested = [bool]$KillAllStackProcesses
        kill_all_dry_run_requested = [bool]$DryRunKillAll
        kill_all_and_start_autopilot_requested = [bool]$KillAllAndStartAutopilot
        kill_all_candidates_count = $killAllCandidatesCount
        kill_all_stack_stopped_count = $killAllStackStoppedCount
        autopilot_paused_for_normalize = $autopilotPausedForNormalize
        autopilot_resumed_after_normalize = $autopilotResumedAfterNormalize
        elite_optimizer_requested = [bool]$RunEliteOptimizer
        elite_optimizer_ran = $eliteOptimizerRan
        elite_optimizer_ok = $eliteOptimizerOk
    }
    overall_healthy = $overallHealthy
    resume_prompt_file = $ResumePrompt
    snapshot_file = $SnapshotJson
    health_latest_file = $HealthLatest
}

$statusJson = $statusPayload | ConvertTo-Json -Depth 8
Set-Content -Path $ReconnectStatusLatest -Value $statusJson -Encoding UTF8
Add-Content -Path $ReconnectStatusHistory -Value ($statusJson -replace "`r?`n", "") -Encoding UTF8

if ($overallHealthy) {
    Write-Host "Reconnect status: HEALTHY" -ForegroundColor Green
} else {
    Write-Warning "Reconnect status: DEGRADED (inspect $ReconnectStatusLatest)"
}
