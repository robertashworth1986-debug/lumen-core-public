param(
    [string]$RootPath = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2',
    [int]$PremiumStaleHours = 24,
    [switch]$InstallRecommendedPackages,
    [switch]$SkipPremiumSync,
    [switch]$SkipInvestorProofSweep,
    [int]$PremiumSyncTimeoutSec = 300,
    [int]$StepTimeoutSec = 900,
    [int]$InvestorProofTimeoutSec = 1800,
    [int]$HeartbeatSec = 20
)

$ErrorActionPreference = 'Stop'

function Get-UtcIso {
    return (Get-Date).ToUniversalTime().ToString('o')
}

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
}

function Read-JsonFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        return Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Tail-Log {
    param(
        [string]$Path,
        [int]$Lines = 40
    )

    if (-not (Test-Path $Path)) {
        return @()
    }

    return Get-Content -Path $Path -Tail $Lines -Encoding UTF8
}

function Resolve-CommandPath {
    param([string]$Command)

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $null
    }

    if (Test-Path $Command) {
        return (Resolve-Path $Command).Path
    }

    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    return $null
}

$ResolvedRoot = (Resolve-Path $RootPath).Path
$WorkspaceRoot = Split-Path -Parent $ResolvedRoot
$OpsPath = Join-Path $ResolvedRoot 'code\ops'
$OutOps = Join-Path $ResolvedRoot 'out\ops'
$Stamp = Get-UtcStamp
$RunDir = Join-Path $OutOps ("stack_modernization_sweep_{0}" -f $Stamp)
$SummaryJson = Join-Path $RunDir 'stack_modernization_summary.json'
$SummaryMd = Join-Path $RunDir 'stack_modernization_summary.md'
$PackageRecJson = Join-Path $RunDir 'cutting_edge_package_recommendations.json'

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

$steps = New-Object System.Collections.Generic.List[object]

function Invoke-Step {
    param(
        [string]$Name,
        [string]$Command,
        [string[]]$StepArgs,
        [string]$WorkingDirectory,
        [int]$TimeoutSec = 900,
        [int]$HeartbeatSeconds = 20
    )

    $safeName = ($Name -replace '[^A-Za-z0-9_-]', '_')
    $stdoutPath = Join-Path $RunDir ("{0}.stdout.log" -f $safeName)
    $stderrPath = Join-Path $RunDir ("{0}.stderr.log" -f $safeName)

    $resolvedCommand = Resolve-CommandPath -Command $Command
    $exists = ($null -ne $resolvedCommand)

    if (-not $exists) {
        $row = [PSCustomObject]@{
            name = $Name
            ok = $false
            return_code = -404
            duration_sec = 0
            timed_out = $false
            stdout_log = $stdoutPath
            stderr_log = $stderrPath
            stdout_tail = @()
            stderr_tail = @("Missing command/script: $Command")
        }
        $steps.Add($row)
        return $row
    }

    Write-Output ("[STACK_SWEEP][START] step={0} timeout_sec={1}" -f $Name, $TimeoutSec)

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $rc = 1
    $timedOut = $false
    $heartbeatWindow = [Math]::Max(5, $HeartbeatSeconds)
    try {
        $proc = Start-Process -FilePath $resolvedCommand -ArgumentList $StepArgs -WorkingDirectory $WorkingDirectory -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $nextHeartbeat = (Get-Date).AddSeconds($heartbeatWindow)

        while (-not $proc.HasExited) {
            Start-Sleep -Milliseconds 500
            $proc.Refresh()

            if ((Get-Date) -ge $nextHeartbeat) {
                Write-Output ("[STACK_SWEEP][RUNNING] step={0} elapsed_sec={1}" -f $Name, [Math]::Round($sw.Elapsed.TotalSeconds, 1))
                $nextHeartbeat = (Get-Date).AddSeconds($heartbeatWindow)
            }

            if ($sw.Elapsed.TotalSeconds -ge $TimeoutSec) {
                $timedOut = $true
                Write-Output ("[STACK_SWEEP][TIMEOUT] step={0} elapsed_sec={1}" -f $Name, [Math]::Round($sw.Elapsed.TotalSeconds, 1))
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                break
            }
        }

        if (-not $timedOut) {
            $proc.WaitForExit()
            $rc = [int]$proc.ExitCode
        } else {
            $rc = 124
            Add-Content -Path $stderrPath -Value ("Timed out after {0} seconds" -f $TimeoutSec) -Encoding UTF8
        }
    } catch {
        $_ | Out-File -FilePath $stderrPath -Append -Encoding UTF8
        $rc = 1
    } finally {
        $sw.Stop()
    }

    $row = [PSCustomObject]@{
        name = $Name
        ok = ($rc -eq 0)
        return_code = [int]$rc
        duration_sec = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
        timed_out = $timedOut
        stdout_log = $stdoutPath
        stderr_log = $stderrPath
        stdout_tail = Tail-Log -Path $stdoutPath -Lines 40
        stderr_tail = Tail-Log -Path $stderrPath -Lines 40
    }
    $steps.Add($row)
    Write-Output ("[STACK_SWEEP][END] step={0} ok={1} rc={2} duration_sec={3}" -f $Name, $row.ok, $row.return_code, $row.duration_sec)
    return $row
}

$premiumRoot = Join-Path $WorkspaceRoot 'premium_packages_mirror'
$premiumLatestPath = Join-Path $premiumRoot 'premium_package_mirror_latest.json'
$premiumLatest = Read-JsonFile -Path $premiumLatestPath
$premiumAgeHours = $null
$premiumFresh = $false

if ($premiumLatest -and $premiumLatest.generated_utc) {
    try {
        $generated = [datetime]::Parse($premiumLatest.generated_utc).ToUniversalTime()
        $premiumAgeHours = [Math]::Round(((Get-Date).ToUniversalTime() - $generated).TotalHours, 2)
        $premiumFresh = ($premiumAgeHours -le $PremiumStaleHours)
    } catch {
        $premiumAgeHours = $null
        $premiumFresh = $false
    }
}

$syncPremium = ((-not $premiumFresh) -and (-not $SkipPremiumSync))
if ($syncPremium) {
    $syncScript = Join-Path $OpsPath 'SYNC_PREMIUM_PACKAGE_MIRROR.ps1'
    Invoke-Step -Name 'sync_premium_package_mirror' -Command 'pwsh' -StepArgs @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        $syncScript,
        '-HashLimitMB',
        '64'
    ) -WorkingDirectory $WorkspaceRoot -TimeoutSec $PremiumSyncTimeoutSec -HeartbeatSeconds $HeartbeatSec | Out-Null
    $premiumLatest = Read-JsonFile -Path $premiumLatestPath
} elseif ($SkipPremiumSync) {
    $skipPremiumRow = [PSCustomObject]@{
        name = 'sync_premium_package_mirror'
        ok = $true
        return_code = 0
        duration_sec = 0
        timed_out = $false
        skipped = $true
        stdout_log = ''
        stderr_log = ''
        stdout_tail = @('Skipped by -SkipPremiumSync')
        stderr_tail = @()
    }
    $steps.Add($skipPremiumRow)
}

Invoke-Step -Name 'dashboard_mirror_parity_audit' -Command 'pwsh' -StepArgs @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    (Join-Path $OpsPath 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1')
) -WorkingDirectory $WorkspaceRoot -TimeoutSec $StepTimeoutSec -HeartbeatSeconds $HeartbeatSec | Out-Null

Invoke-Step -Name 'live_key_measurement_audit' -Command 'pwsh' -StepArgs @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    (Join-Path $OpsPath 'RUN_LIVE_KEY_MEASUREMENT_AUDIT.ps1')
) -WorkingDirectory $WorkspaceRoot -TimeoutSec $StepTimeoutSec -HeartbeatSeconds $HeartbeatSec | Out-Null

if (-not $SkipInvestorProofSweep) {
    Invoke-Step -Name 'investor_proof_sweep' -Command 'pwsh' -StepArgs @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        (Join-Path $OpsPath 'RUN_INVESTOR_PROOF_SWEEP.ps1')
    ) -WorkingDirectory $WorkspaceRoot -TimeoutSec $InvestorProofTimeoutSec -HeartbeatSeconds $HeartbeatSec | Out-Null
} else {
    $skipRow = [PSCustomObject]@{
        name = 'investor_proof_sweep'
        ok = $true
        return_code = 0
        duration_sec = 0
        timed_out = $false
        skipped = $true
        stdout_log = ''
        stderr_log = ''
        stdout_tail = @('Skipped by -SkipInvestorProofSweep')
        stderr_tail = @()
    }
    $steps.Add($skipRow)
}

$dashboardPackagePath = Join-Path $ResolvedRoot 'dashboard\package.json'
$dashboardPackage = Read-JsonFile -Path $dashboardPackagePath
$currentDeps = @{}
if ($dashboardPackage -and $dashboardPackage.dependencies) {
    $currentDeps = @{}
    $dashboardPackage.dependencies.PSObject.Properties | ForEach-Object {
        $currentDeps[$_.Name] = [string]$_.Value
    }
}

$recommended = @(
    [PSCustomObject]@{ name = 'three'; category = '3d-core'; reason = 'Core 3D renderer' },
    [PSCustomObject]@{ name = 'postprocessing'; category = '3d-postfx'; reason = 'Cinematic effects pipeline' },
    [PSCustomObject]@{ name = 'gsap'; category = 'motion'; reason = 'Timeline animation engine' },
    [PSCustomObject]@{ name = 'echarts'; category = 'viz'; reason = 'High-density charting' },
    [PSCustomObject]@{ name = 'echarts-gl'; category = 'viz-3d'; reason = '3D charting for dense telemetry' },
    [PSCustomObject]@{ name = '@google/model-viewer'; category = '3d-viewer'; reason = 'Web component 3D model viewing' },
    [PSCustomObject]@{ name = 'animejs'; category = 'motion'; reason = 'Cinematic motion choreography' },
    [PSCustomObject]@{ name = 'stats.js'; category = 'perf'; reason = 'Runtime FPS and performance telemetry' },
    [PSCustomObject]@{ name = '@xenova/transformers'; category = 'ai-browser'; reason = 'On-device browser AI inference' }
)

$present = @()
$missing = @()
foreach ($pkg in $recommended) {
    if ($currentDeps.ContainsKey($pkg.name)) {
        $present += [PSCustomObject]@{
            name = $pkg.name
            version = $currentDeps[$pkg.name]
            category = $pkg.category
            reason = $pkg.reason
        }
    } else {
        $missing += $pkg
    }
}

$installResult = $null
if ($InstallRecommendedPackages -and $missing.Count -gt 0) {
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd) {
        $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    }

    if ($npmCmd) {
        $installArgs = @('install') + @($missing | ForEach-Object { $_.name })
        $installResult = Invoke-Step -Name 'install_cutting_edge_dashboard_packages' -Command $npmCmd.Source -StepArgs $installArgs -WorkingDirectory (Join-Path $ResolvedRoot 'dashboard') -TimeoutSec $StepTimeoutSec -HeartbeatSeconds $HeartbeatSec
    } else {
        $installResult = [PSCustomObject]@{
            name = 'install_cutting_edge_dashboard_packages'
            ok = $false
            return_code = 127
            duration_sec = 0
            stdout_log = ''
            stderr_log = ''
            stdout_tail = @()
            stderr_tail = @('npm command not found in PATH')
        }
        $steps.Add($installResult)
    }
}

$packageRec = [PSCustomObject]@{
    generated_utc = Get-UtcIso
    dashboard_package_json = $dashboardPackagePath
    present = $present
    missing = $missing
    install_attempted = [bool]$InstallRecommendedPackages
    install_result = $installResult
}
$packageRec | ConvertTo-Json -Depth 8 | Set-Content -Path $PackageRecJson -Encoding UTF8

$summary = [ordered]@{
    generated_utc = Get-UtcIso
    scope = 'live-stack modernization + premium mirror + AI/3D readiness'
    root_path = $ResolvedRoot
    run_dir = $RunDir
    premium = [ordered]@{
        root = $premiumRoot
        latest_path = $premiumLatestPath
        age_hours = $premiumAgeHours
        stale_threshold_hours = $PremiumStaleHours
        sync_timeout_sec = $PremiumSyncTimeoutSec
        skip_premium_sync_requested = [bool]$SkipPremiumSync
        was_fresh_before_run = $premiumFresh
        sync_executed = $syncPremium
        latest_after_run = $premiumLatest
    }
    package_recommendations_json = $PackageRecJson
    steps = $steps
    totals = [ordered]@{
        steps = $steps.Count
        ok = @($steps | Where-Object { $_.ok }).Count
        failed = @($steps | Where-Object { -not $_.ok }).Count
    }
    artifacts = [ordered]@{
        summary_json = $SummaryJson
        summary_md = $SummaryMd
        package_recommendations_json = $PackageRecJson
    }
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $SummaryJson -Encoding UTF8

$md = @()
$md += '# Stack Modernization Sweep'
$md += ''
$md += ('Generated UTC: {0}' -f $summary.generated_utc)
$md += ('Root Path: {0}' -f $summary.root_path)
$md += ('Run Dir: {0}' -f $summary.run_dir)
$md += ''
$md += '## Premium Mirror'
$md += ('- Latest marker: {0}' -f $summary.premium.latest_path)
$md += ('- Age hours before run: {0}' -f ($summary.premium.age_hours -as [string]))
$md += ('- Stale threshold hours: {0}' -f $summary.premium.stale_threshold_hours)
$md += ('- Sync executed: {0}' -f $summary.premium.sync_executed)
$md += ''
$md += '## Step Results'
foreach ($s in $steps) {
    $md += ('- {0}: ok={1} rc={2} duration_sec={3}' -f $s.name, $s.ok, $s.return_code, $s.duration_sec)
}
$md += ''
$md += '## Package Recommendations'
$md += ('- Present recommended packages: {0}' -f $present.Count)
$md += ('- Missing recommended packages: {0}' -f $missing.Count)
if ($missing.Count -gt 0) {
    foreach ($m in $missing) {
        $md += ('- Missing: {0} ({1}) - {2}' -f $m.name, $m.category, $m.reason)
    }
}
$md += ''
$md += '## Artifacts'
$md += ('- Summary JSON: {0}' -f $SummaryJson)
$md += ('- Summary MD: {0}' -f $SummaryMd)
$md += ('- Package Recommendations JSON: {0}' -f $PackageRecJson)

$md | Set-Content -Path $SummaryMd -Encoding UTF8

Write-Output ('[STACK_SWEEP] run_dir={0}' -f $RunDir)
Write-Output ('[STACK_SWEEP] summary_json={0}' -f $SummaryJson)
Write-Output ('[STACK_SWEEP] summary_md={0}' -f $SummaryMd)
Write-Output ('[STACK_SWEEP] package_recommendations_json={0}' -f $PackageRecJson)
Write-Output ('[STACK_SWEEP] steps_total={0} ok={1} failed={2}' -f $summary.totals.steps, $summary.totals.ok, $summary.totals.failed)
