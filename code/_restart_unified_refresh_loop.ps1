$ErrorActionPreference = 'Stop'

$code = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code'
$python = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\python.exe'

Start-Process -WindowStyle Minimized -FilePath $python -ArgumentList 'dashboard_unified_refresh.py','--loop' -WorkingDirectory $code
