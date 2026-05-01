@echo off
setlocal
set ROOT=C:\LumaTrader\INSTITUTIONAL_STACK_V2
set PS=pwsh.exe
%PS% -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\code\START_LUMA_ECOSYSTEM_STACK.ps1" -IncludeICloud
endlocal
