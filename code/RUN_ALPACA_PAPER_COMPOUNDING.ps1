$ErrorActionPreference = "Stop"

param(
    [switch]$StatusOnly,
    [switch]$NoOrders,
    [switch]$Loop
)

$Python = "C:/Python314/python.exe"
$Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$Exec = Join-Path $Root "code\execution\alpaca_paper_executor.py"
$Dash = Join-Path $Root "code\execution\build_alpaca_paper_dashboard.py"

$argsList = @()
if ($StatusOnly) { $argsList += "--status-only" }
if ($NoOrders) { $argsList += "--no-orders" }
if ($Loop) { $argsList += "--loop" }

Write-Host "Using Python:" $Python
Write-Host "Executor:" $Exec
Write-Host "Dashboard Builder:" $Dash

& $Python $Exec @argsList
& $Python $Dash

Write-Host ""
Write-Host "Alpaca paper execution path completed." -ForegroundColor Green
Write-Host "Dashboard:" (Join-Path $Root "dashboard\alpaca_paper_dashboard.html")