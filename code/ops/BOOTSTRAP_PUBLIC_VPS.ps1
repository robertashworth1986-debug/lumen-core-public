param(
    [string]$Domain = "lumen-core.ai",
    [string]$RootPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$RunReconnect,
    [switch]$RunEliteOptimizer,
    [switch]$InstallScheduledTasks
)

$ErrorActionPreference = "Stop"

function Require-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        throw "Run this script as Administrator."
    }
}

Require-Admin

$CodePath = Join-Path $RootPath "code"
$OpsPath = Join-Path $CodePath "ops"
$PublicRunner = Join-Path $OpsPath "RUN_PUBLIC_STACK.ps1"
$CaddyDir = "C:\caddy"
$CaddyExe = Join-Path $CaddyDir "caddy.exe"
$Caddyfile = Join-Path $CaddyDir "Caddyfile"

Write-Host "Bootstrap public VPS for $Domain" -ForegroundColor Cyan
Write-Host "RootPath: $RootPath"

if (-not (Test-Path $PublicRunner)) {
    throw "Missing public runner: $PublicRunner"
}

# Firewall
if (-not (Get-NetFirewallRule -DisplayName "LumenCore HTTP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "LumenCore HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow | Out-Null
}
if (-not (Get-NetFirewallRule -DisplayName "LumenCore HTTPS" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "LumenCore HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow | Out-Null
}

# Install Caddy
if (-not (Test-Path $CaddyExe)) {
    New-Item -Path $CaddyDir -ItemType Directory -Force | Out-Null
    $zip = Join-Path $env:TEMP "caddy_windows_amd64.zip"
    $dl = "https://github.com/caddyserver/caddy/releases/latest/download/caddy_windows_amd64.zip"
    Invoke-WebRequest -Uri $dl -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $CaddyDir -Force
}

# Generate Caddyfile
$caddyText = @"
$Domain {
    encode zstd gzip

    @lamascout path /ui* /health* /api*
    handle @lamascout {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        reverse_proxy 127.0.0.1:5016
    }
}
"@
Set-Content -Path $Caddyfile -Value $caddyText -Encoding UTF8

# Launch app stack
$runnerArgs = @("-ExecutionPolicy","Bypass","-File",$PublicRunner)
if ($RunReconnect) { $runnerArgs += "-RunReconnect" }
if ($RunEliteOptimizer) { $runnerArgs += "-RunEliteOptimizer" }
Start-Process -FilePath "powershell.exe" -ArgumentList $runnerArgs -WorkingDirectory $CodePath -WindowStyle Minimized | Out-Null

# Launch Caddy
Start-Process -FilePath $CaddyExe -ArgumentList @("run","--config",$Caddyfile) -WorkingDirectory $CaddyDir -WindowStyle Minimized | Out-Null

if ($InstallScheduledTasks) {
    $ps = "powershell.exe"
    $task1Action = New-ScheduledTaskAction -Execute $ps -Argument "-ExecutionPolicy Bypass -File `"$PublicRunner`" -RunReconnect -RunEliteOptimizer"
    $task1Trigger = New-ScheduledTaskTrigger -AtStartup
    Register-ScheduledTask -TaskName "LumenCorePublicStack" -Action $task1Action -Trigger $task1Trigger -RunLevel Highest -Force | Out-Null

    $task2Action = New-ScheduledTaskAction -Execute $CaddyExe -Argument "run --config `"$Caddyfile`""
    $task2Trigger = New-ScheduledTaskTrigger -AtStartup
    Register-ScheduledTask -TaskName "LumenCoreCaddy" -Action $task2Action -Trigger $task2Trigger -RunLevel Highest -Force | Out-Null
}

Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Public URL (after DNS A-record points here): https://$Domain"
Write-Host "App local: http://127.0.0.1:5016"
Write-Host "LamaScout local: http://127.0.0.1:8000/ui"
Write-Host "Note: GitHub Pages can host static pages only, not this live Python stack."
