[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$RetireLegacyObservers,
    [string]$StateDirectory = 'E:\LumaProofVault\PRIVATE_CONTEXT\SYSTEM_HEALTH_V2'
)

$ErrorActionPreference = 'Stop'
$TaskName = 'Luma-LocalSystemHealthObserver-v2'
$LegacyObserverTaskNames = @('WhiteHole-Watchdog', 'WhiteHole-DockerWatchdog')
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ProtocolPath = Join-Path $RepoRoot 'config\local_system_health_observer_protocol_v2.json'
$CollectorPath = Join-Path $RepoRoot 'code\ops\COLLECT_LOCAL_SYSTEM_HEALTH_V2.py'
$Protocol = Get-Content -LiteralPath $ProtocolPath -Raw | ConvertFrom-Json
$IntervalMinutes = [int]$Protocol.cadence.interval_minutes

$Plan = [ordered]@{
    schema = 'luma.local_system_health_task_stage.v2'
    status = if ($Apply) { 'apply_requested' } else { 'dry_run' }
    task_alias = 'local_system_health_observer_v2'
    interval_minutes = $IntervalMinutes
    hidden = $true
    noninteractive = $true
    principal = 'local_system_service_account'
    observation_only = $true
    legacy_observer_retirement_requested = [bool]$RetireLegacyObservers
    legacy_observer_count = if ($RetireLegacyObservers) { $LegacyObserverTaskNames.Count } else { 0 }
    legacy_system_health_collector_retired = $false
    state_location = 'private_proof_vault'
    legacy_files_or_logs_changed = $false
    mutation_performed = $false
    apply_requires_human_unlock = $true
}

if (-not $Apply) {
    $Plan | ConvertTo-Json -Depth 4
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:LUMA_HUMAN_UNLOCK_TOKEN)) {
    throw 'Apply is blocked: LUMA_HUMAN_UNLOCK_TOKEN is not configured in the private environment.'
}

$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$PrincipalCheck = New-Object Security.Principal.WindowsPrincipal($Identity)
if (-not $PrincipalCheck.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Apply is blocked: an elevated local session is required.'
}

$PythonCommand = Get-Command python.exe -ErrorAction Stop
$PythonPath = $PythonCommand.Source
$PowerShellPath = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $PowerShellPath)) {
    $PowerShellPath = (Get-Command powershell.exe -ErrorAction Stop).Source
}

function ConvertTo-SingleQuotedLiteral([string]$Value) {
    return "'" + $Value.Replace("'", "''") + "'"
}

if (-not [System.IO.Path]::IsPathRooted($StateDirectory)) {
    throw 'Apply is blocked: StateDirectory must be an absolute private path.'
}
$StateRoot = [System.IO.Path]::GetPathRoot($StateDirectory)
$StateDriveName = $StateRoot.TrimEnd('\').TrimEnd(':')
$StateDrive = Get-PSDrive -Name $StateDriveName -ErrorAction Stop
$StateCapacity = [double]$StateDrive.Used + [double]$StateDrive.Free
if ($StateCapacity -le 0 -or ([double]$StateDrive.Free / $StateCapacity) -lt 0.10) {
    throw 'Apply is blocked: the private state volume must have at least 10 percent free space.'
}
New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null

$QuotedPython = ConvertTo-SingleQuotedLiteral $PythonPath
$QuotedCollector = ConvertTo-SingleQuotedLiteral $CollectorPath
$QuotedStateDirectory = ConvertTo-SingleQuotedLiteral ([System.IO.Path]::GetFullPath($StateDirectory))
$Command = "& $QuotedPython $QuotedCollector --state-dir $QuotedStateDirectory *> `$null; exit `$LASTEXITCODE"
$Arguments = "-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$Command`""

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellPath `
    -Argument $Arguments `
    -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$Settings = New-ScheduledTaskSettingsSet `
    -Hidden `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes ([int]$Protocol.cadence.single_run_timeout_minutes)) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$TaskPrincipal = New-ScheduledTaskPrincipal `
    -UserId 'SYSTEM' `
    -LogonType ServiceAccount `
    -RunLevel Highest
$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $TaskPrincipal `
    -Description 'Observation-only local health v2 collector; no remediation or external actions.'

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

if ($RetireLegacyObservers) {
    foreach ($LegacyTaskName in $LegacyObserverTaskNames) {
        $LegacyTask = Get-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue
        if ($null -ne $LegacyTask) {
            Disable-ScheduledTask -TaskName $LegacyTaskName | Out-Null
        }
    }
}

$Registered = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$RegisteredArguments = [string]$Registered.Actions[0].Arguments
if ($Registered.Settings.Hidden -ne $true -or
    $RegisteredArguments -notmatch '-NonInteractive' -or
    $RegisteredArguments -notmatch '-WindowStyle Hidden') {
    throw 'Registered task failed the hidden/noninteractive verification gate.'
}

$Plan.status = 'applied'
$Plan.mutation_performed = $true
$Plan.registered_hidden = [bool]$Registered.Settings.Hidden
$Plan.registered_noninteractive = $true
$Plan | ConvertTo-Json -Depth 4
