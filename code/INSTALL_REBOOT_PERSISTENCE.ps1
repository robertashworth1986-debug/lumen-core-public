$ErrorActionPreference = "Stop"

$Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$Code = Join-Path $Root "code"
$Py = Join-Path $Code ".venv\Scripts\python.exe"
$Ps = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $Py)) {
    throw "Python executable not found: $Py"
}

function Register-LumaTask {
    param(
        [string]$TaskName,
        [string]$Command,
        [string]$Arguments
    )

    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    }

    $action = New-ScheduledTaskAction -Execute $Command -Argument $Arguments
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Write-Host "[OK] Registered task: $TaskName"
}

$dashArgs = "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$Code'; & '$Py' 'dashboard_unified_refresh.py' --loop`""
$tradeArgs = "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$Code'; & '.\\RUN_ALPACA_PAPER_247.ps1'`""
$crossArgs = "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$Code'; & '.\\RUN_CROSS_SECTOR_INTEL_STACK.ps1' -Detach -Port 7700 -InfraRefreshSeconds 30`""
$tunnelArgs = "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$Code'; & '.\\RUN_PUBLIC_DASHBOARD_TUNNEL.ps1'`""

Register-LumaTask -TaskName "Luma-DashboardRefreshLoop" -Command $Ps -Arguments $dashArgs
Register-LumaTask -TaskName "Luma-PaperTraderLoop" -Command $Ps -Arguments $tradeArgs
Register-LumaTask -TaskName "Luma-CrossSectorStack" -Command $Ps -Arguments $crossArgs
Register-LumaTask -TaskName "Luma-PublicDashboardTunnel" -Command $Ps -Arguments $tunnelArgs

Write-Host ""
Write-Host "[DONE] Reboot persistence installed."
Write-Host "Tasks:"
Write-Host " - Luma-DashboardRefreshLoop"
Write-Host " - Luma-PaperTraderLoop"
Write-Host " - Luma-CrossSectorStack"
Write-Host " - Luma-PublicDashboardTunnel"
