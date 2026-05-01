param(
    [ValidateSet("export", "serve")]
    [string]$Mode = "serve",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 5016,
    [double]$RefreshSeconds = 30,
    [switch]$IncludeCrossSector,
    [switch]$Autoreload,
    [switch]$Restart,
    [switch]$Detach
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    $PY = "python"
}

$Script = Join-Path $CODE "execution\build_institutional_crypto_paper_dashboard.py"
if (-not (Test-Path $Script)) {
    throw "Missing script: $Script"
}

function Get-DashboardProcesses {
    if ($Mode -ne "serve") {
        return @()
    }
    @(Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -like "*build_institutional_crypto_paper_dashboard.py*" -and
            $_.CommandLine -like "*--mode serve*" -and
            $_.CommandLine -like "*--port $Port*"
        })
}

if ($Mode -eq "serve" -and $Restart) {
    $running = Get-DashboardProcesses
    foreach ($proc in $running) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

if ($Mode -eq "serve" -and -not $Restart) {
    $running = Get-DashboardProcesses
    if ($running.Count -gt 0) {
        Write-Host "Dashboard already running on port $Port. Refusing duplicate launch." -ForegroundColor Yellow
        $running | Select-Object ProcessId, CommandLine | Format-List | Out-Host
        Write-Host "Use -Restart to recycle the dashboard process." -ForegroundColor Yellow
        exit 0
    }
}

$argsList = @($Script, "--mode", $Mode)
if ($Mode -eq "serve") {
    $argsList += @("--host", $BindHost, "--port", "$Port", "--refresh-seconds", "$RefreshSeconds")
    if ($Autoreload) {
        $argsList += "--autoreload"
    }
}
if ($IncludeCrossSector) {
    $argsList += "--include-cross-sector"
}

Write-Host "Institutional crypto dashboard launcher" -ForegroundColor Cyan
Write-Host "Mode: $Mode"
Write-Host "Python: $PY"
Write-Host "Script: $Script"
if ($Mode -eq "serve") {
    Write-Host "URL: http://${BindHost}:$Port"
    Write-Host "Refresh Seconds: $RefreshSeconds"
    Write-Host "Include Cross-Sector: $IncludeCrossSector"
}

if ($Detach) {
    $proc = Start-Process -FilePath $PY -ArgumentList $argsList -WorkingDirectory $CODE -PassThru
    Write-Host "Dashboard process started with PID $($proc.Id)." -ForegroundColor Green
    exit 0
}

& $PY @argsList