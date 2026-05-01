param(
    [ValidateSet("export", "serve")]
    [string]$Mode = "serve",
    [double]$RefreshSeconds = 15,
    [switch]$StageMode,          # Use zero-scroll 6-block Stage Mode wallboard
    [switch]$Detach,
    [switch]$OpenWallboard,
    [switch]$OpenTalkTrack
)

$ErrorActionPreference = "Stop"

$ROOT = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"
$CODE = Join-Path $ROOT "code"
$PY = Join-Path $CODE ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) {
    $PY = "python"
}

# Choose which builder to run
if ($StageMode) {
    $Script   = Join-Path $CODE "execution\build_stage_wallboard.py"
    $Wallboard = Join-Path $ROOT "dashboard\stage_wallboard.html"
    Write-Host "Stage Mode selected - 6-block zero-scroll wallboard" -ForegroundColor Yellow
} else {
    $Script   = Join-Path $CODE "execution\build_investor_wallboard.py"
    $Wallboard = Join-Path $ROOT "dashboard\investor_wallboard.html"
}

if (-not (Test-Path $Script)) {
    throw "Missing script: $Script"
}

$TalkTrack = Join-Path $ROOT "out\execution\investor_talk_track.md"

$argsList = @($Script, "--mode", $Mode, "--refresh-seconds", "$RefreshSeconds")

Write-Host "Investor wallboard launcher" -ForegroundColor Cyan
Write-Host "Mode: $Mode"
Write-Host "Refresh Seconds: $RefreshSeconds"
Write-Host "Python: $PY"

if ($Detach) {
    $proc = Start-Process -FilePath $PY -ArgumentList $argsList -WorkingDirectory $CODE -PassThru
    Write-Host "Wallboard process started with PID $($proc.Id)." -ForegroundColor Green
} else {
    & $PY @argsList
}

if ($OpenWallboard -and (Test-Path $Wallboard)) {
    Invoke-Item $Wallboard
}
if ($OpenTalkTrack -and (Test-Path $TalkTrack)) {
    Invoke-Item $TalkTrack
}
