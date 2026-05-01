$ErrorActionPreference = "Stop"

$Code = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$Ps = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
New-Item -ItemType Directory -Force -Path $startup | Out-Null

$coreCmd = @"
@echo off
cd /d "$Code"
start "Luma Core" /min "$Ps" -NoProfile -ExecutionPolicy Bypass -File "$Code\START_LUMENCORE_CORE.ps1" -Prime
start "Luma Public Tunnel" /min "$Ps" -NoProfile -ExecutionPolicy Bypass -File "$Code\RUN_PUBLIC_DASHBOARD_TUNNEL.ps1"
start "Luma Core Boot Selfcheck" /min "$Ps" -NoProfile -ExecutionPolicy Bypass -File "$Code\_startup_boot_selfcheck.ps1" -WaitSeconds 45
"@

Remove-Item -Path (Join-Path $startup "Luma_Dashboard_Refresh_Autostart.cmd") -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $startup "Luma_CrossSector_Autostart.cmd") -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $startup "Luma_PaperTrader_Autostart.cmd") -Force -ErrorAction SilentlyContinue

Set-Content -Path (Join-Path $startup "Luma_Core_Autostart.cmd") -Value $coreCmd -Encoding ASCII

Write-Host "[OK] Installed user startup autorun launchers in: $startup"
Write-Host " - Luma_Core_Autostart.cmd"
Write-Host " - Includes public dashboard tunnel bootstrap"
