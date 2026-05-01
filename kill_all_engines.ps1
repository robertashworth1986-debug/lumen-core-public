# PowerShell script to kill all Python and trading engine processes
# Run this before launching all engines to ensure a clean start

# Kill all python.exe processes (forcefully)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Optionally, kill any lingering PowerShell or dashboard HTML processes (uncomment if needed)
# Get-Process pwsh -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Get-Process "msedge" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "All Python and engine processes killed. Ready for clean launch."
