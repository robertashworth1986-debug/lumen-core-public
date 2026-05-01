param(
    [switch]$Prime
)

$ErrorActionPreference = 'Stop'

$Code = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code'
$Py = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\python.exe'
$Ps = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

function Get-WorkerProcess {
    param(
        [string]$NamePattern,
        [string]$CommandPattern
    )

    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -like $NamePattern -and $_.CommandLine -like $CommandPattern
    }
}

Set-Location $Code

$dashboardLoop = @(Get-WorkerProcess -NamePattern 'python*' -CommandPattern '*dashboard_unified_refresh.py*--loop*')
$sectorApi = @(Get-WorkerProcess -NamePattern 'python*' -CommandPattern '*execution.sector_opp_gain_server:app*')
$infraLoop = @(Get-WorkerProcess -NamePattern 'python*' -CommandPattern '*build_infra_audit_dashboard.py*--loop*')
$paperTrader = @(Get-WorkerProcess -NamePattern 'powershell*' -CommandPattern '*RUN_ALPACA_PAPER_247.ps1*')

$started = New-Object System.Collections.Generic.List[string]
$skipped = New-Object System.Collections.Generic.List[string]

if ($dashboardLoop.Count -eq 0) {
    if ($Prime) {
        & $Py dashboard_unified_refresh.py
    }
    Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList 'dashboard_unified_refresh.py','--loop' -WorkingDirectory $Code
    $started.Add('dashboard loop') | Out-Null
} else {
    $skipped.Add('dashboard loop') | Out-Null
}

if ($sectorApi.Count -eq 0) {
    Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList '-m','uvicorn','execution.sector_opp_gain_server:app','--host','127.0.0.1','--port','7700' -WorkingDirectory $Code
    $started.Add('sector API') | Out-Null
} else {
    $skipped.Add('sector API') | Out-Null
}

if ($infraLoop.Count -eq 0) {
    Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution\build_infra_audit_dashboard.py','--loop','--interval','30' -WorkingDirectory $Code
    $started.Add('infra loop') | Out-Null
} else {
    $skipped.Add('infra loop') | Out-Null
}

if ($paperTrader.Count -eq 0) {
    Start-Process -WindowStyle Minimized -FilePath $Ps -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\RUN_ALPACA_PAPER_247.ps1' -WorkingDirectory $Code
    $started.Add('paper trader') | Out-Null
} else {
    $skipped.Add('paper trader') | Out-Null
}

Write-Host ('[OK] Started: ' + ($(if ($started.Count) { $started -join ', ' } else { 'none' })))
Write-Host ('[OK] Already running: ' + ($(if ($skipped.Count) { $skipped -join ', ' } else { 'none' })))