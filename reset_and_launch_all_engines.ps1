# PowerShell script to kill all Python/trading engine processes and launch all engines
# Run this from your main stack directory

# --- KILL ALL ENGINES ---
Write-Host "Killing all Python and engine processes..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Optionally, kill any lingering PowerShell or dashboard HTML processes (uncomment if needed)
# Get-Process pwsh -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Get-Process "msedge" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# --- LAUNCH ALL ENGINES ---
Write-Host "Launching all trading engines..."
$engines = @(
    'code/execution/execution_orchestrator.py',
    'code/execution/rolling_capital_engine_multi.py',
    'dashboard/dashboard_analytics.py',
    'code/execution/live_executor.py',
    'code/execution/live_runtime_guard.py',
    'code/execution/liquidity_guard.py',
    'code/execution/order_router.py',
    'code/execution/harmonic_signal_connector.py'
)

$venv = ".venv/Scripts/python.exe"
$cwd = Split-Path -Parent $MyInvocation.MyCommand.Definition

foreach ($engine in $engines) {
    $scriptPath = Join-Path $cwd $engine
    Start-Process -NoNewWindow -WorkingDirectory $cwd $venv -ArgumentList $scriptPath
}

Write-Host "All trading engines launched in background."
