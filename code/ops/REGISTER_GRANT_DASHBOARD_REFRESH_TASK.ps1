[CmdletBinding()]
param(
    [string]$TaskName = 'Luma Elite Grant Dashboard Auto Refresh',
    [int]$EveryHours = 2,
    [string]$StartTime = '08:00'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($EveryHours -lt 1) {
    throw 'EveryHours must be >= 1'
}

$scriptPath = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\ops\RUN_GRANT_DASHBOARD_AUTO_REFRESH.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing refresh script: $scriptPath"
}

$taskCmd = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$arguments = @(
    '/Create',
    '/TN', $TaskName,
    '/TR', $taskCmd,
    '/SC', 'HOURLY',
    '/MO', [string]$EveryHours,
    '/ST', $StartTime,
    '/F'
)

& schtasks.exe @arguments | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "schtasks create failed with exit code $LASTEXITCODE"
}

$queryArgs = @('/Query', '/TN', $TaskName, '/V', '/FO', 'LIST')
& schtasks.exe @queryArgs | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "schtasks query failed with exit code $LASTEXITCODE"
}

Write-Output "REGISTER_GRANT_DASHBOARD_REFRESH_TASK_DONE"
Write-Output "task_name=$TaskName"
Write-Output "every_hours=$EveryHours"
Write-Output "start_time=$StartTime"
