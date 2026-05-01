# PowerShell Launch Blocks for Investor Demo

# 1. Activate Python venv
& c:\LumaTrader\INSTITUTIONAL_STACK_V2\.venv\Scripts\Activate.ps1

# 2. Run LumaTrader (robust, all pairs, fallback ready)
python .\champion_core_out\app\luma_trader.py

# 3. Rebuild all dashboards
python out/build_live_sources_dashboard.py
python out/build_kraken_execution_dashboard.py
python out/build_dashboard.py
python out/build_credibility_dashboard.py
python out/build_fundable_dashboard_patch.py

# 4. Open dashboards (replace with your preferred browser or viewer)
# Start-Process chrome.exe .\out\dashboard.html
# Start-Process chrome.exe .\out\kraken_execution_dashboard.html
# Start-Process chrome.exe .\out\credibility_dashboard.html
# Start-Process chrome.exe .\out\fundable_dashboard_patch.html
# Start-Process chrome.exe .\out\live_sources_dashboard.html

# 5. (Optional) Tail logs for debug
# Get-Content .\champion_core_out\app\luma_trader.log -Wait
