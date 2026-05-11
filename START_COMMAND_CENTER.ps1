param(
    [ValidateSet('dashboard', 'core', 'full')]
    [string]$StackGroup = 'core',

    [ValidateSet('investor', 'ops', 'full')]
    [string]$TabPreset = 'investor',

    [int]$HealthTimeoutSec = 60,

    [switch]$Restart,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$manager = Join-Path $root 'code\ops\MANAGE_LOCAL_STACK.ps1'

if (-not (Test-Path $manager)) {
    throw "Runtime manager not found at $manager"
}

$action = if ($Restart) { 'restart' } else { 'start' }
Write-Output "[COMMAND_CENTER] runtime action=$action group=$StackGroup"
& $manager -Action $action -StackGroup $StackGroup -Force:$Restart

$base = 'http://127.0.0.1:8787'
$healthUri = "$base/health"
$briefUri = "$base/api/investor/brief"
$metricsUri = "$base/api/system/metrics-summary"

$ready = $false
$deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
$brief = $null

while ((Get-Date) -lt $deadline) {
    try {
        $null = Invoke-RestMethod -Uri $healthUri -TimeoutSec 3 -ErrorAction Stop
        $brief = Invoke-RestMethod -Uri $briefUri -TimeoutSec 3 -ErrorAction Stop
        if ($brief -and $brief.headline) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 800
    }
}

if (-not $ready) {
    throw "Gateway health check timed out after $HealthTimeoutSec seconds. Check managed stack status with .\\code\\ops\\MANAGE_LOCAL_STACK.ps1 -Action status -StackGroup $StackGroup"
}

$servicesUp = $brief.headline.services_up
$supervisorTick = $brief.headline.supervisor_tick
Write-Output "[COMMAND_CENTER] healthy services=$servicesUp supervisor_tick=$supervisorTick"

try {
    $metrics = Invoke-RestMethod -Uri $metricsUri -TimeoutSec 3 -ErrorAction Stop
    Write-Output "[COMMAND_CENTER] metrics services_up=$($metrics.services_up)/$($metrics.services_total) restarts=$($metrics.total_restarts)"
} catch {
    Write-Output "[COMMAND_CENTER] metrics summary unavailable"
}

$heartbeatPath = Join-Path $root 'out\execution\live_executor_heartbeat.json'
if (Test-Path $heartbeatPath) {
    try {
        $hb = Get-Content $heartbeatPath -Raw | ConvertFrom-Json
        Write-Output "[COMMAND_CENTER] heartbeat status=$($hb.status) reason=$($hb.reason) symbol=$($hb.selected_symbol) universe_candidate_count=$($hb.universe_candidate_count)"
    } catch {
        Write-Output '[COMMAND_CENTER] heartbeat unreadable'
    }
}

if ($NoBrowser) {
    Write-Output '[COMMAND_CENTER] browser launch skipped by -NoBrowser'
    return
}

$tabs = switch ($TabPreset) {
    'investor' {
        @(
            "$base/investor_command_room.html",
            "$base/quant_lab.html#investor_command_room",
            "$base/mission_control.html",
            "$base/api/investor/brief"
        )
    }
    'ops' {
        @(
            "$base/mission_control.html",
            "$base/quant_lab.html#mission_control",
            $healthUri,
            $metricsUri
        )
    }
    'full' {
        @(
            "$base/mission_control.html",
            "$base/quant_lab.html#investor_command_room",
            "$base/investor_command_room.html",
            "$base/scenario_mission.html",
            "$base/luma_experience.html",
            $healthUri,
            $briefUri,
            $metricsUri
        )
    }
}

foreach ($url in $tabs) {
    Start-Process $url | Out-Null
    Start-Sleep -Milliseconds 200
}

Write-Output "[COMMAND_CENTER] opened $($tabs.Count) tab(s) preset=$TabPreset"
