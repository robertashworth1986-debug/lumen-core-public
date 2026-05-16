[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', '', Justification='Function names in this script use singular nouns; suppress persistent stale diagnostic.')]
param(
    [string]$Domain = "lumen-core.ai",
    [string]$RootPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [switch]$FastFirstBoot,
    [switch]$SkipPrereqs,
    [switch]$SkipBootstrap,
    [switch]$SkipReconnect,
    [switch]$SkipEliteOptimizer,
    [switch]$SkipScheduledTasks,
    [switch]$DryRun,
    [switch]$NoElevation
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
}

function Invoke-PowerShellFile {
    param(
        [string]$File,
        [string[]]$CommandArgs,
        [string]$Label
    )

    Write-Host "[STEP] $Label" -ForegroundColor Yellow
    Write-Host ("  powershell -ExecutionPolicy Bypass -File {0} {1}" -f $File, ($CommandArgs -join " ")) -ForegroundColor DarkGray

    if (-not $DryRun) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $File @CommandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "$Label failed with exit code $LASTEXITCODE"
        }
    }
}

$CodePath = Join-Path $RootPath "code"
$OpsPath = Join-Path $CodePath "ops"
$PrereqScript = Join-Path $OpsPath "INSTALL_PUBLIC_STACK_PREREQS.ps1"
$BootstrapScript = Join-Path $OpsPath "BOOTSTRAP_PUBLIC_VPS.ps1"

Write-Host "Fresh Windows VPS one-click runner" -ForegroundColor Cyan
Write-Host "Domain: $Domain"
Write-Host "RootPath: $RootPath"
Write-Host "DryRun: $DryRun"

if ($FastFirstBoot) {
    Write-Host "FastFirstBoot enabled: initial deploy will skip reconnect + elite optimizer." -ForegroundColor Yellow
}

if (-not (Test-Path $PrereqScript)) {
    throw "Missing prerequisite script: $PrereqScript"
}
if (-not (Test-Path $BootstrapScript)) {
    throw "Missing bootstrap script: $BootstrapScript"
}

$needsAdmin = (-not $SkipBootstrap) -and (-not $DryRun)
if ($needsAdmin -and (-not $NoElevation) -and (-not (Test-IsAdmin))) {
    Write-Host "Relaunching as Administrator..." -ForegroundColor Yellow
    $selfArgs = @()
    foreach ($key in $PSBoundParameters.Keys) {
        if ($key -eq "NoElevation") {
            continue
        }

        $value = $PSBoundParameters[$key]
        if ($value -is [switch]) {
            if ($value.IsPresent) {
                $selfArgs += "-$key"
            }
            continue
        }

        $selfArgs += "-$key"
        $selfArgs += "$value"
    }
    $elevatedArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath
    ) + $selfArgs
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $elevatedArgs | Out-Null
    return
}

if (-not $SkipPrereqs) {
    $prereqArgs = @("-RootPath", $RootPath)
    if ($DryRun) {
        $prereqArgs += "-DryRun"
    }
    Invoke-PowerShellFile -File $PrereqScript -CommandArgs $prereqArgs -Label "Install Python and package prerequisites"
}
else {
    Write-Host "[STEP] Skipping prerequisites" -ForegroundColor Yellow
}

if (-not $SkipBootstrap) {
    $bootstrapArgs = @("-Domain", $Domain, "-RootPath", $RootPath)
    if ((-not $SkipReconnect) -and (-not $FastFirstBoot)) {
        $bootstrapArgs += "-RunReconnect"
    }
    if ((-not $SkipEliteOptimizer) -and (-not $FastFirstBoot)) {
        $bootstrapArgs += "-RunEliteOptimizer"
    }
    if (-not $SkipScheduledTasks) {
        $bootstrapArgs += "-InstallScheduledTasks"
    }

    if ($DryRun) {
        Write-Host "[STEP] Bootstrap command preview" -ForegroundColor Yellow
        Write-Host ("  powershell -ExecutionPolicy Bypass -File {0} {1}" -f $BootstrapScript, ($bootstrapArgs -join " ")) -ForegroundColor DarkGray
    }
    else {
        Invoke-PowerShellFile -File $BootstrapScript -CommandArgs $bootstrapArgs -Label "Bootstrap public stack and reverse proxy"
    }
}
else {
    Write-Host "[STEP] Skipping bootstrap" -ForegroundColor Yellow
}

Write-Host "One-click runner complete." -ForegroundColor Green
Write-Host "If DNS is not updated yet, point the A record for $Domain to this VPS public IPv4." -ForegroundColor Cyan
if ($FastFirstBoot) {
    Write-Host "After DNS/HTTPS is stable, run full optimizer:" -ForegroundColor Cyan
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\RUN_ELITE_STACK_OPTIMIZER.ps1" -ForegroundColor DarkGray
}