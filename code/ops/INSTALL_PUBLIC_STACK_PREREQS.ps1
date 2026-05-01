param(
    [string]$RootPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-PythonLauncher {
    $candidates = @(
        @{ Exe = "py"; Args = @("-3.11") },
        @{ Exe = "py"; Args = @("-3") },
        @{ Exe = "python"; Args = @() },
        @{ Exe = "python3"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) {
            continue
        }

        try {
            $null = & $candidate.Exe @($candidate.Args + @("-c", "import sys")) 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
        }
    }

    return $null
}

function Invoke-CommandLine {
    param(
        [string]$Exe,
        [string[]]$CommandArgs,
        [string]$Label
    )

    Write-Host "[STEP] $Label" -ForegroundColor Yellow
    Write-Host ("  {0} {1}" -f $Exe, ($CommandArgs -join " ")) -ForegroundColor DarkGray
    if (-not $DryRun) {
        & $Exe @CommandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "$Label failed with exit code $LASTEXITCODE"
        }
    }
}

$CodePath = Join-Path $RootPath "code"
$LamaRoot = Join-Path $RootPath "LamaScout"
$VenvPath = Join-Path $CodePath ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Requirements = Join-Path $LamaRoot "requirements.txt"
$RequirementsExtra = Join-Path $LamaRoot "requirements-extra.txt"

Write-Host "Install public stack prerequisites" -ForegroundColor Cyan
Write-Host "RootPath: $RootPath"
Write-Host "DryRun: $DryRun"

if (-not (Test-Path $CodePath)) {
    throw "Missing code path: $CodePath"
}
if (-not (Test-Path $LamaRoot)) {
    throw "Missing LamaScout path: $LamaRoot"
}
if (-not (Test-Path $Requirements)) {
    throw "Missing requirements file: $Requirements"
}

$python = Get-PythonLauncher
if ($null -eq $python) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Invoke-CommandLine -Exe "winget" -CommandArgs @(
            "install",
            "--id", "Python.Python.3.11",
            "-e",
            "--accept-package-agreements",
            "--accept-source-agreements"
        ) -Label "Install Python 3.11 with winget"
        $python = Get-PythonLauncher
    }
}

if ($null -eq $python) {
    throw "Python 3.11 was not found and could not be installed automatically. Install Python 3.11, then rerun this script."
}

if (-not (Test-Path $VenvPython)) {
    Invoke-CommandLine -Exe $python.Exe -CommandArgs (@($python.Args) + @("-m", "venv", $VenvPath)) -Label "Create code virtual environment"
}
else {
    Write-Host "[STEP] Reusing existing virtual environment" -ForegroundColor Yellow
    Write-Host "  $VenvPython" -ForegroundColor DarkGray
}

Invoke-CommandLine -Exe $VenvPython -CommandArgs @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel") -Label "Upgrade pip tooling"
Invoke-CommandLine -Exe $VenvPython -CommandArgs @("-m", "pip", "install", "-r", $Requirements) -Label "Install LamaScout core requirements"

if (Test-Path $RequirementsExtra) {
    Invoke-CommandLine -Exe $VenvPython -CommandArgs @("-m", "pip", "install", "-r", $RequirementsExtra) -Label "Install dashboard and UI extras"
}

Write-Host "Prerequisite install complete." -ForegroundColor Green
Write-Host "Next command:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\ops\BOOTSTRAP_PUBLIC_VPS.ps1 -Domain lumen-core.ai -RunReconnect -RunEliteOptimizer -InstallScheduledTasks"