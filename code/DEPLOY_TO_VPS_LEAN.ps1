param(
    [string]$TargetHost = "opc@157.151.148.234",
    [string]$KeyPath = "C:/Users/Novac/Downloads/ssh-key-2026-04-23.key",
    [string]$RemoteRoot = "/home/opc/LumaTrader",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root ".deploy_stage"
$archive = Join-Path $root "deploy_bundle.tar.gz"

Write-Host "[1/5] Building lean deployment stage"
if (Test-Path $stage) {
    Remove-Item $stage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage | Out-Null

$stageCode = Join-Path $stage "code"
$stageScout = Join-Path $stage "LamaScout"
New-Item -ItemType Directory -Path $stageCode | Out-Null
New-Item -ItemType Directory -Path $stageScout | Out-Null

robocopy (Join-Path $root "code") $stageCode /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP `
    /XD ".venv" "__pycache__" "archive" "out" ".git" ".deploy_stage" `
    /XF "*.pyc" "*.pyo" "*.log" | Out-Null

robocopy (Join-Path $root "LamaScout") $stageScout /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP `
    /XD ".venv" "__pycache__" "data" "out" "logs" "reports" ".git" `
    /XF "*.pyc" "*.pyo" "*.log" | Out-Null

Copy-Item (Join-Path $root "INVESTOR_BRIEF.md") (Join-Path $stage "INVESTOR_BRIEF.md") -ErrorAction SilentlyContinue

Write-Host "[2/5] Creating compressed bundle"
if (Test-Path $archive) {
    Remove-Item $archive -Force
}
tar -czf $archive -C $stage .

Write-Host "[3/5] Uploading bundle to VPS"
scp -C -i $KeyPath $archive "${TargetHost}:/home/opc/deploy_bundle.tar.gz"

Write-Host "[4/5] Extracting bundle on VPS"
ssh -i $KeyPath $TargetHost "rm -rf $RemoteRoot/.last_deploy; mkdir -p $RemoteRoot/.last_deploy; tar -xzf /home/opc/deploy_bundle.tar.gz -C $RemoteRoot/.last_deploy; mkdir -p $RemoteRoot; cp -r $RemoteRoot/.last_deploy/* $RemoteRoot/"

if (-not $SkipInstall) {
    Write-Host "[5/5] Installing runtime dependencies on VPS"
    ssh -i $KeyPath $TargetHost "cd $RemoteRoot/code && python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && if [ -f ../LamaScout/requirements.txt ]; then pip install -r ../LamaScout/requirements.txt; fi"
} else {
    Write-Host "[5/5] Skipped dependency install"
}

Write-Host ""
Write-Host "Lean deploy complete."
Write-Host "Remote path: $RemoteRoot"
Write-Host "Run on VPS: cd $RemoteRoot/code && . .venv/bin/activate && python run_triplet_complete.py"