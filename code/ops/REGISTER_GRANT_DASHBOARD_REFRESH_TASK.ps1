[CmdletBinding()]
param(
    [string]$TaskName = 'Luma Elite Grant Dashboard Auto Refresh',
    [int]$EveryHours = 2,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($EveryHours -lt 1) {
    throw 'EveryHours must be >= 1'
}

$stackRoot = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$scriptPath = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\ops\RUN_GRANT_DASHBOARD_AUTO_REFRESH.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing refresh script: $scriptPath"
}

$powerShell = Get-Command pwsh.exe -ErrorAction Stop
$powerShellPath = $powerShell.Source
$taskArguments = (
    "-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden " +
    "-ExecutionPolicy Bypass -File `"$scriptPath`" -RefreshOpportunities"
)

$plan = [ordered]@{
    schema = 'lumencore.grant_dashboard_refresh_task_stage.v2'
    status = if ($Apply) { 'apply_requested' } else { 'dry_run' }
    task_name = $TaskName
    interval_hours = $EveryHours
    executable = $powerShellPath
    script_path = $scriptPath
    refresh_opportunities = $true
    hidden = $true
    noninteractive = $true
    start_when_available = $true
    multiple_instances = 'Queue'
    execution_time_limit_minutes = 30
    restart_count = 3
    restart_interval_minutes = 5
    allow_start_on_batteries = $true
    stop_on_battery_transition = $false
    wake_to_run = $true
    requires_interactive_logon = $true
    mutation_performed = $false
    apply_requires_human_unlock = $true
    apply_requires_administrator = $true
}

if (-not $Apply) {
    $plan | ConvertTo-Json -Depth 4
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:LUMA_HUMAN_UNLOCK_TOKEN)) {
    throw 'Apply is blocked: LUMA_HUMAN_UNLOCK_TOKEN is not configured in the private environment.'
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalCheck = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principalCheck.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Apply is blocked: an elevated local session is required.'
}

$action = New-ScheduledTaskAction `
    -Execute $powerShellPath `
    -Argument $taskArguments `
    -WorkingDirectory $stackRoot
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours $EveryHours)
$settings = New-ScheduledTaskSettingsSet `
    -Hidden `
    -MultipleInstances Queue `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $identity.Name `
    -LogonType Interactive `
    -RunLevel Highest
$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Description 'Fail-closed grant opportunity, deadline, packet, and human-action refresh. No external submission.'

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

$registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$registeredAction = $registered.Actions[0]
$registeredTrigger = $registered.Triggers[0]
if ([string]$registeredAction.Execute -ne $powerShellPath -or
    [string]$registeredAction.Arguments -notmatch '-NonInteractive' -or
    [string]$registeredAction.Arguments -notmatch '-RefreshOpportunities' -or
    [string]$registered.Settings.MultipleInstances -ne 'Queue' -or
    $registered.Settings.StartWhenAvailable -ne $true -or
    $registered.Settings.Hidden -ne $true -or
    [string]$registeredTrigger.Repetition.Interval -ne ("PT{0}H" -f $EveryHours)) {
    throw 'Registered grant dashboard refresh task failed the post-apply verification gate.'
}

$plan.status = 'applied'
$plan.mutation_performed = $true
$plan.registered_state = [string]$registered.State
$plan.registered_user = [string]$registered.Principal.UserId
$plan.registered_run_level = [string]$registered.Principal.RunLevel
$plan.registered_logon_type = [string]$registered.Principal.LogonType
$plan | ConvertTo-Json -Depth 4
