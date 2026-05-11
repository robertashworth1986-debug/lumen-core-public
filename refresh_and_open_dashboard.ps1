# PowerShell script to refresh the LumenCore dashboard and open it in the browser

# Activate the Python virtual environment
& "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\Activate.ps1"

# Run the dashboard refresh script
C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\python.exe C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\dashboard_unified_refresh.py

# Open the dashboard in the default browser
Start-Process "C:\LumaTrader\dashboard\infra_institutional_live_dashboard.html"
