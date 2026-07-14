param(
    [int]$ProofZipCount = 8,
    [switch]$SkipMirror,
    [switch]$SkipMap,
    [switch]$SkipCatalog,
    [switch]$SkipBoothBrief,
    [switch]$SkipAutopilot,
    [switch]$ArmAutopilot,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$mirrorScript = Join-Path $PSScriptRoot 'SYNC_PREMIUM_PACKAGE_MIRROR.ps1'
$mapScript = Join-Path $stackRoot 'code\build_lumencore_universe_map.py'
$catalogScript = Join-Path $stackRoot 'code\build_nobel_tier_engine_catalog.py'
$boothBriefScript = Join-Path $stackRoot 'code\build_booth_explainer_brief.py'
$autopilotScript = Join-Path $stackRoot 'ARM_REAL_AUTOPILOT.ps1'

$pythonCandidates = @(
    'C:\LumaTrader\.venv\Scripts\python.exe',
    (Join-Path $stackRoot '.venv\Scripts\python.exe'),
    (Join-Path $stackRoot '..\venv3.11\Scripts\python.exe')
)
$python = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $python = $candidate
        break
    }
}
if (-not $python) {
    throw 'Python runtime not found for map/catalog generation.'
}
$userHome = [Environment]::GetFolderPath('UserProfile').Replace('\', '/')

Write-Output "[WARROOM] stack_root=$stackRoot"
Write-Output "[WARROOM] python=$python"

if (-not $SkipMirror) {
    if (-not (Test-Path $mirrorScript)) {
        throw "Mirror script not found: $mirrorScript"
    }
    Write-Output "[WARROOM] Step 1/5: Sync premium package mirror"
    & $mirrorScript -LatestZipCountFromProofs $ProofZipCount -HashLimitMB 32
}

if (-not $SkipMap) {
    if (-not (Test-Path $mapScript)) {
        throw "Universe map script not found: $mapScript"
    }
    Write-Output "[WARROOM] Step 2/5: Build cross-root universe map"
    $mapArgs = @(
        '--max-files', '240000',
        '--per-root-max-files', '35000',
        '--hash-limit-mb', '15',
        '--max-hash-files', '2200',
        '--roots',
        'C:/LumaTrader',
        'C:/LumaTrader/INSTITUTIONAL_STACK_V2',
        'C:/LumaTrader/premium_packages_mirror',
        'C:/WhiteHole',
        'C:/WhiteHoleLab',
        'C:/LumenCore',
        'C:/LumenLab',
        "$userHome/iCloudDrive",
        "$userHome/OneDrive"
    )
    & $python $mapScript @mapArgs
}

if (-not $SkipCatalog) {
    if (-not (Test-Path $catalogScript)) {
        throw "Catalog script not found: $catalogScript"
    }
    Write-Output "[WARROOM] Step 3/5: Build Nobel tier engine catalog"
    & $python $catalogScript
}

if (-not $SkipBoothBrief) {
    if (-not (Test-Path $boothBriefScript)) {
        throw "Booth brief script not found: $boothBriefScript"
    }
    Write-Output "[WARROOM] Step 4/5: Build booth explainer brief"
    & $python $boothBriefScript --recent-trade-rows 120
}

if ($ArmAutopilot -and -not $SkipAutopilot) {
    if ([string]::IsNullOrWhiteSpace($env:LUMA_HUMAN_UNLOCK_TOKEN)) {
        throw 'LUMA_HUMAN_UNLOCK_TOKEN is required with -ArmAutopilot.'
    }
    if (-not (Test-Path $autopilotScript)) {
        throw "Autopilot script not found: $autopilotScript"
    }
    Write-Output "[WARROOM] Step 5/5: Arm live autopilot"
    & $autopilotScript -StackGroup core -TabPreset investor -NoBrowser:$NoBrowser
} else {
    Write-Output '[WARROOM] Step 5/5: Autopilot skipped (safe default; requires -ArmAutopilot and HumanUnlock token)'
}

Write-Output '[WARROOM] refresh complete.'
