param(
    [switch]$RunParityAudit
)

$ErrorActionPreference = 'Stop'

$stackRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$pythonCandidates = @(
    (Join-Path $stackRoot "..\venv3.11\Scripts\python.exe"),
    (Join-Path $stackRoot ".venv\Scripts\python.exe"),
    "python"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python") {
        $pythonExe = "python"
        break
    }
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    throw "No Python executable found."
}

$profileScript = Join-Path $stackRoot "code\social_platform_profile_engine_v1.py"
$feedScript = Join-Path $stackRoot "code\ops\BUILD_SOCIAL_PRO_DASHBOARD_FEED.py"
$parityScript = Join-Path $stackRoot "code\ops\AUDIT_DASHBOARD_MIRROR_PARITY.ps1"
$stackSocialDashboard = Join-Path $stackRoot "dashboard\social_pro_dashboard.html"
$rootSocialDashboard = Join-Path $stackRoot "..\dashboard\social_pro_dashboard.html"

Write-Host "[social-pro] Building social profile payload..."
& $pythonExe $profileScript --publish-mode dry_run

Write-Host "[social-pro] Building social pro dashboard feed..."
& $pythonExe $feedScript

if (Test-Path $stackSocialDashboard) {
    Write-Host "[social-pro] Mirroring social dashboard to root dashboard..."
    Copy-Item -Path $stackSocialDashboard -Destination $rootSocialDashboard -Force
}

if ($RunParityAudit) {
    Write-Host "[social-pro] Running dashboard mirror parity audit..."
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $parityScript
}

Write-Host "[social-pro] Refresh complete."
