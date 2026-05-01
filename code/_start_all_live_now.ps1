$ErrorActionPreference = 'Stop'

$Code = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code'
$Py = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\.venv\Scripts\python.exe'
$Ps = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

Set-Location $Code

& $Ps -NoProfile -ExecutionPolicy Bypass -File "$Code\START_LUMENCORE_CORE.ps1" -Prime
