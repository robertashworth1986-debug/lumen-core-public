param(
    [string]$RootPath = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2',
    [int]$PremiumStaleHours = 24,
    [switch]$InstallRecommendedPackages
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
        [string[]]$Args,
        [string]$WorkingDirectory
    )

    $safeName = ($Name -replace '[^A-Za-z0-9_-]', '_')
    $stdoutPath = Join-Path $RunDir ("{0}.stdout.log" -f $safeName)
    $stderrPath = Join-Path $RunDir ("{0}.stderr.log" -f $safeName)

    $exists = $true
    if ($Command -like '*.ps1' -and -not (Test-Path $Command)) {
        $exists = $false
    }

    if (-not $exists) {
        $row = [PSCustomObject]@{
            name = $Name
            ok = $false
            return_code = -404
            duration_sec = 0
            stdout_log = $stdoutPath
            stderr_log = $stderrPath
            stdout_tail = @()
            stderr_tail = @("Missing command/script: $Command")
        }
        $steps.Add($row)
        return $row
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location $WorkingDirectory
    try {
        & $Command @Args 1> $stdoutPath 2> $stderrPath
        $rc = $LASTEXITCODE
        if ($null -eq $rc) {
            $rc = 0
        }
    } catch {
        $_ | Out-File -FilePath $stderrPath -Append -Encoding UTF8
        $rc = 1
    } finally {
        Pop-Location
        $sw.Stop()
    }

    $row = [PSCustomObject]@{
        name = $Name
        ok = ($rc -eq 0)
        return_code = [int]$rc
        duration_sec = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
        stdout_log = $stdoutPath
        stderr_log = $stderrPath
        stdout_tail = Tail-Log -Path $stdoutPath -Lines 40
        stderr_tail = Tail-Log -Path $stderrPath -Lines 40
    }
    $steps.Add($row)
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

$syncPremium = (-not $premiumFresh)
if ($syncPremium) {
    $syncScript = Join-Path $OpsPath 'SYNC_PREMIUM_PACKAGE_MIRROR.ps1'
    Invoke-Step -Name 'sync_premium_package_mirror' -Command 'pwsh' -Args @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        $syncScript,
        '-HashLimitMB',
        '64'
    ) -WorkingDirectory $WorkspaceRoot | Out-Null
    $premiumLatest = Read-JsonFile -Path $premiumLatestPath
}

Invoke-Step -Name 'dashboard_mirror_parity_audit' -Command 'pwsh' -Args @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    (Join-Path $OpsPath 'AUDIT_DASHBOARD_MIRROR_PARITY.ps1')
) -WorkingDirectory $WorkspaceRoot | Out-Null

Invoke-Step -Name 'live_key_measurement_audit' -Command 'pwsh' -Args @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    (Join-Path $OpsPath 'RUN_LIVE_KEY_MEASUREMENT_AUDIT.ps1')
) -WorkingDirectory $WorkspaceRoot | Out-Null

Invoke-Step -Name 'investor_proof_sweep' -Command 'pwsh' -Args @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    (Join-Path $OpsPath 'RUN_INVESTOR_PROOF_SWEEP.ps1')
) -WorkingDirectory $WorkspaceRoot | Out-Null

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
        $installResult = Invoke-Step -Name 'install_cutting_edge_dashboard_packages' -Command $npmCmd.Source -Args $installArgs -WorkingDirectory (Join-Path $ResolvedRoot 'dashboard')
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
