param(
    [string]$RootPath = "C:\",
    [int]$StaleDays = 180,
    [int]$TopN = 300,
    [int]$MaxFiles = 650000,
    [int]$MaxDocPages = 8,
    [int]$PreviewMaxDocs = 40,
    [int]$PreviewMaxImages = 4,
    [int]$ProgressEvery = 20000
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\LumaTrader"
$scriptPath = Join-Path $workspaceRoot "INSTITUTIONAL_STACK_V2\code\ops\CURATE_ICLOUD_TOP_ASSETS.py"

if (-not (Test-Path $scriptPath)) {
    throw "Curation script missing: $scriptPath"
}

$pythonCandidates = @(
    (Join-Path $workspaceRoot "venv3.11\Scripts\python.exe"),
    (Join-Path $workspaceRoot ".venv\Scripts\python.exe"),
    "python"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python") {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) {
            $pythonExe = "python"
            break
        }
        continue
    }

    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    throw "No Python executable found for local C-drive curation run."
}

Write-Host "[CURATE] RootPath: $RootPath"
Write-Host "[CURATE] Python:   $pythonExe"
Write-Host "[CURATE] Script:   $scriptPath"
Write-Host "[CURATE] MaxFiles: $MaxFiles"

& $pythonExe $scriptPath `
    --scan-root "$RootPath" `
    --output-root "C:\LumaTrader\out\ops" `
    --stale-days $StaleDays `
    --top-n $TopN `
    --max-files $MaxFiles `
    --max-doc-pages $MaxDocPages `
    --preview-max-docs $PreviewMaxDocs `
    --preview-max-images $PreviewMaxImages `
    --progress-every $ProgressEvery

if ($LASTEXITCODE -ne 0) {
    throw "Local C-drive curation failed with exit code $LASTEXITCODE"
}

Write-Host "[CURATE] Complete. Check C:\LumaTrader\out\ops\local_top_assets_latest.json"
