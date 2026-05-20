param(
    [int]$WaitSeconds = 45
)

$ErrorActionPreference = 'Stop'

if ($WaitSeconds -gt 0) {
    Start-Sleep -Seconds $WaitSeconds
}

$root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$outDir = Join-Path $root 'out\execution'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Get-JsonOrNull {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    try {
        return (Get-Content -Raw -Path $Path | ConvertFrom-Json -AsHashtable)
    }
    catch {
        return $null
    }
}

function Get-Prop {
    param(
        [object]$Obj,
        [string]$Name,
        [object]$Default = $null
    )
    if ($null -eq $Obj) {
        return $Default
    }
    if ($Obj -is [System.Collections.IDictionary]) {
        if ($Obj.Contains($Name)) {
            return $Obj[$Name]
        }
        return $Default
    }
    if ($Obj.PSObject -and $Obj.PSObject.Properties[$Name]) {
        return $Obj.$Name
    }
    return $Default
}

$all = Get-CimInstance Win32_Process

$dashboard = @($all | Where-Object {
    (
        $_.Name -like 'python*' -and (
            $_.CommandLine -like '*dashboard_unified_refresh.py*' -or
            $_.CommandLine -like '*build_institutional_crypto_paper_dashboard.py*'
        )
    ) -or (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and
        $_.CommandLine -like '*RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1*'
    )
}).Count

$sector = @($all | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*sector_opp_gain_server*'
}).Count

$infra = @($all | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*build_infra_audit_dashboard.py*'
}).Count

$paper = @($all | Where-Object {
    (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and (
            $_.CommandLine -like '*RUN_ALPACA_PAPER_247.ps1*' -or
            $_.CommandLine -like '*RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1*'
        )
    ) -or (
        $_.Name -like 'python*' -and
        $_.CommandLine -like '*multi_exchange_paper_ticker.py*'
    )
}).Count

$opportunity = @($all | Where-Object {
    (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and (
            $_.CommandLine -like '*RUN_OPPORTUNITY_AUTONOMY_LOOP.ps1*' -or
            $_.CommandLine -like '*RUN_OPPORTUNITY_ENGINE_V2.ps1*'
        )
    ) -or (
        $_.Name -like 'python*' -and (
            $_.CommandLine -like '*opportunity_harvester.py*' -or
            $_.CommandLine -like '*opportunity_filler.py*' -or
            $_.CommandLine -like '*job_application_factory.py*'
        )
    )
}).Count

$email = @($all | Where-Object {
    (
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and (
            $_.CommandLine -like '*RUN_EMAIL_OPPORTUNITY_WATCHER.ps1*' -or
            $_.CommandLine -like '*RUN_EMAIL_RESPONSE_WATCHER.ps1*' -or
            $_.CommandLine -like '*RUN_EMAIL_RESUME_DISPATCHER.ps1*'
        )
    ) -or (
        $_.Name -like 'python*' -and (
            $_.CommandLine -like '*email_opportunity_finder.py*' -or
            $_.CommandLine -like '*email_response_watcher.py*' -or
            $_.CommandLine -like '*email_resume_dispatcher.py*'
        )
    )
}).Count

$linkedin = @($all | Where-Object {
    $_.Name -like 'python*' -and (
        $_.CommandLine -like '*lumalinkedin_resume_engine_v1.py*' -or
        $_.CommandLine -like '*linkedin_publish_evidence.py*' -or
        $_.CommandLine -like '*linkedin_router.py*'
    )
}).Count

$grant = @($all | Where-Object {
    $_.Name -like 'python*' -and (
        $_.CommandLine -like '*grant_hunter_v2.py*' -or
        $_.CommandLine -like '*grant_application_factory.py*' -or
        $_.CommandLine -like '*grants_api.py*'
    )
}).Count

$dockerDesktop = @(Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue).Count
$dockerBackend = @(Get-Process -Name 'com.docker.backend' -ErrorAction SilentlyContinue).Count
$dockerEngine = @(Get-Process -Name 'dockerd' -ErrorAction SilentlyContinue).Count
$dockerRunning = (($dockerDesktop + $dockerBackend + $dockerEngine) -gt 0)

$laneIntegrityPath = Join-Path $outDir 'lane_integrity_report.json'
$apiKeyRegistryPath = Join-Path $outDir 'api_key_registry_report.json'
$opportunityCyclePath = Join-Path $root 'out\ops\opportunity_autonomy_loop\cycle_latest.json'
$emailFinderManifestPath = Join-Path $root 'out\ops\email_opportunity_finder\email_opportunity_manifest_latest.json'
$emailDispatchManifestPath = Join-Path $root 'out\ops\email_resume_dispatcher\email_resume_dispatch_manifest_latest.json'
$emailResponseManifestPath = Join-Path $root 'out\ops\email_response_watcher\email_response_manifest_latest.json'
$linkedinBuildPath = Join-Path $root 'out\ops\lumalinkedin_v1_build_latest.json'
$grantsQueuePath = Join-Path $root 'out\grants\_queue\index.json'
$runtimeControlPath = Join-Path $root 'config\runtime_control.json'

$laneIntegrity = Get-JsonOrNull -Path $laneIntegrityPath
$apiKeyRegistry = Get-JsonOrNull -Path $apiKeyRegistryPath
$opportunityCycle = Get-JsonOrNull -Path $opportunityCyclePath
$emailFinderManifest = Get-JsonOrNull -Path $emailFinderManifestPath
$emailDispatchManifest = Get-JsonOrNull -Path $emailDispatchManifestPath
$emailResponseManifest = Get-JsonOrNull -Path $emailResponseManifestPath
$linkedinBuild = Get-JsonOrNull -Path $linkedinBuildPath
$grantsQueue = Get-JsonOrNull -Path $grantsQueuePath
$runtimeControl = Get-JsonOrNull -Path $runtimeControlPath

$laneSummary = Get-Prop -Obj $laneIntegrity -Name 'summary' -Default @{}

$services = @(
    [PSCustomObject]@{ Service = 'dashboard_loop'; Required = $true; Running = ($dashboard -gt 0); ProcessCount = $dashboard },
    [PSCustomObject]@{ Service = 'sector_api'; Required = $true; Running = ($sector -gt 0); ProcessCount = $sector },
    [PSCustomObject]@{ Service = 'infra_loop'; Required = $true; Running = ($infra -gt 0); ProcessCount = $infra },
    [PSCustomObject]@{ Service = 'paper_trader'; Required = $true; Running = ($paper -gt 0); ProcessCount = $paper },
    [PSCustomObject]@{ Service = 'opportunity_lane'; Required = $false; Running = ($opportunity -gt 0); ProcessCount = $opportunity },
    [PSCustomObject]@{ Service = 'email_lane'; Required = $false; Running = ($email -gt 0); ProcessCount = $email },
    [PSCustomObject]@{ Service = 'linkedin_lane'; Required = $false; Running = ($linkedin -gt 0); ProcessCount = $linkedin },
    [PSCustomObject]@{ Service = 'grant_lane'; Required = $false; Running = ($grant -gt 0); ProcessCount = $grant }
)

$allHealthy = (@($services | Where-Object { $_.Required -and -not $_.Running }).Count -eq 0)

$payload = [ordered]@{
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    wait_seconds = $WaitSeconds
    all_healthy = $allHealthy
    required_services_healthy = $allHealthy
    optional_services_running = @($services | Where-Object { -not $_.Required -and $_.Running }).Count
    services = $services
    docker_health = [ordered]@{
        running = $dockerRunning
        docker_desktop = $dockerDesktop
        docker_backend = $dockerBackend
        dockerd = $dockerEngine
        note = if ($dockerRunning) { 'Docker processes detected.' } else { 'Docker processes not detected at snapshot time.' }
    }
    lane_health = [ordered]@{
        api_key_registry = [ordered]@{
            available = ($null -ne $apiKeyRegistry)
            coverage_pct = [double](Get-Prop -Obj $apiKeyRegistry -Name 'coverage_pct' -Default 0.0)
            present_keys = [int](Get-Prop -Obj $apiKeyRegistry -Name 'present_keys' -Default 0)
            total_keys = [int](Get-Prop -Obj $apiKeyRegistry -Name 'total_keys' -Default 0)
        }
        lane_integrity = [ordered]@{
            available = ($null -ne $laneIntegrity)
            status = [string](Get-Prop -Obj $laneIntegrity -Name 'status' -Default 'not_ready')
            cross_lane_key_count = [int](Get-Prop -Obj $laneSummary -Name 'cross_lane_key_count' -Default 0)
            critical_missing_count = [int](Get-Prop -Obj $laneSummary -Name 'critical_missing_count' -Default 0)
        }
        runtime_gate = [ordered]@{
            mode = [string](Get-Prop -Obj $runtimeControl -Name 'mode' -Default 'unknown')
            allow_live_orders = [bool](Get-Prop -Obj $runtimeControl -Name 'allow_live_orders' -Default $false)
            hard_safety_only_mode = [bool](Get-Prop -Obj $runtimeControl -Name 'hard_safety_only_mode' -Default $false)
        }
        opportunity_lane = [ordered]@{
            status = [string](Get-Prop -Obj $opportunityCycle -Name 'status' -Default 'not_ready')
            generated_utc = [string](Get-Prop -Obj $opportunityCycle -Name 'generated_utc' -Default '')
        }
        linkedin_lane = [ordered]@{
            status = [string](Get-Prop -Obj $linkedinBuild -Name 'status' -Default 'not_ready')
            generated_utc = [string](Get-Prop -Obj $linkedinBuild -Name 'generated_utc' -Default '')
        }
        email_lane = [ordered]@{
            finder_status = [string](Get-Prop -Obj $emailFinderManifest -Name 'status' -Default 'not_ready')
            dispatch_status = [string](Get-Prop -Obj $emailDispatchManifest -Name 'status' -Default 'not_ready')
            response_status = [string](Get-Prop -Obj $emailResponseManifest -Name 'status' -Default 'not_ready')
        }
        grants_lane = [ordered]@{
            queue_total = [int](Get-Prop -Obj $grantsQueue -Name 'n_total' -Default 0)
            draft = [int](Get-Prop -Obj $grantsQueue -Name 'n_draft' -Default 0)
            approved = [int](Get-Prop -Obj $grantsQueue -Name 'n_approved' -Default 0)
            submitted = [int](Get-Prop -Obj $grantsQueue -Name 'n_submitted' -Default 0)
        }
    }
}

$latest = Join-Path $outDir 'startup_boot_health_latest.json'
$history = Join-Path $outDir 'startup_boot_health_history.jsonl'

$json = $payload | ConvertTo-Json -Depth 6
Set-Content -Path $latest -Value $json -Encoding ASCII
Add-Content -Path $history -Value ($json -replace "`r?`n", '') -Encoding ASCII

Write-Host ('[OK] Startup boot self-check written: ' + $latest)
Write-Host ('[OK] All services healthy: ' + $allHealthy)
