param(
    [string]$TaskName = "LumenCore-EIA-Prospective-Hourly-Router",
    [ValidateRange(15, 1440)]
    [int]$IntervalMinutes = 30,
    [ValidateRange(30, 300)]
    [int]$TimeoutSeconds = 90,
    [switch]$WhatIfOnly,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $RepoRoot "tools\Run-EiaProspectiveHourlyRouterCycle.ps1"

if ($Unregister) {
    $Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $Existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    return
}

$UserKeyPresent =
    [bool][Environment]::GetEnvironmentVariable("EIA_API_KEY", "User") -or
    [bool][Environment]::GetEnvironmentVariable("EIA_API_KEY_PREMIUM", "User")
if (-not $UserKeyPresent) {
    throw "No user-level EIA API key is configured; refusing unattended registration."
}
$PowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$Arguments =
    "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`" " +
    "-TimeoutSeconds $TimeoutSeconds -Quiet -PythonExe `"$PythonExe`""
$StartAt = (Get-Date).AddMinutes(2)

if ($WhatIfOnly) {
    [pscustomobject]@{
        TaskName = $TaskName
        IntervalMinutes = $IntervalMinutes
        StartAt = $StartAt
        Execute = $PowerShell
        PythonExe = $PythonExe
        Arguments = $Arguments
        WorkingDirectory = $RepoRoot
        UserKeyPresent = $UserKeyPresent
        Registered = $false
    }
    return
}

$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Arguments -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Once -At $StartAt `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $Existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
Register-ScheduledTask -TaskName $TaskName `
    -Description "Seal and settle the frozen EIA hourly router before target intervals without backfill." `
    -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal | Out-Null

$Task = Get-ScheduledTask -TaskName $TaskName
$Info = Get-ScheduledTaskInfo -TaskName $TaskName
[pscustomobject]@{
    TaskName = $Task.TaskName
    State = $Task.State
    NextRunTime = $Info.NextRunTime
    LastRunTime = $Info.LastRunTime
    LastTaskResult = $Info.LastTaskResult
    IntervalMinutes = $IntervalMinutes
    WorkingDirectory = $RepoRoot
}
