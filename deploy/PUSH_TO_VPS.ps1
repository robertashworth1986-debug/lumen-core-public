param(
    [string]$VpsIp = "157.151.148.234",
    [string]$VpsUser = "ubuntu",
    [string]$VpsRoot = "/opt/lumencore",
    [string]$Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [string]$SshKeyPath = ""
)

$ErrorActionPreference = "Stop"

# =============================================================================
# LUMEN-CORE.AI — Push Stack to VPS
# VPS IP:     157.151.148.234
# Domain:     lumen-core.ai
# Stack root: /opt/lumencore
# =============================================================================

function Invoke-Scp {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [Parameter(Mandatory = $true)]
        [string]$StepLabel
    )

    $scpArgs = @()
    if ($SshKeyPath) {
        $scpArgs += @("-i", $SshKeyPath)
    }
    $scpArgs += $Args

    & scp @scpArgs
    if ($LASTEXITCODE -ne 0) {
        throw "[$StepLabel] scp failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Ssh {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RemoteCommand,
        [Parameter(Mandatory = $true)]
        [string]$StepLabel
    )

    $sshArgs = @()
    if ($SshKeyPath) {
        $sshArgs += @("-i", $SshKeyPath)
    }
    $sshArgs += @("${VpsUser}@${VpsIp}", $RemoteCommand)

    & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "[$StepLabel] ssh failed with exit code $LASTEXITCODE"
    }
}

$deployScript = Join-Path $Root "deploy\VPS_DEPLOY.sh"
$codeDir = Join-Path $Root "code"
$lamaScoutDir = Join-Path $Root "LamaScout"

if (-not (Test-Path $deployScript)) {
    throw "Deploy script not found: $deployScript"
}
if (-not (Test-Path $codeDir)) {
    throw "Code directory not found: $codeDir"
}
if (-not (Test-Path $lamaScoutDir)) {
    throw "LamaScout directory not found: $lamaScoutDir"
}
if ($SshKeyPath -and -not (Test-Path $SshKeyPath)) {
    throw "SSH key path not found: $SshKeyPath"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " LUMEN-CORE.AI — VPS STACK UPLOAD" -ForegroundColor Cyan
Write-Host " Target: ${VpsUser}@${VpsIp}:${VpsRoot}" -ForegroundColor Cyan
if ($SshKeyPath) {
    Write-Host " Key: $SshKeyPath" -ForegroundColor Cyan
}
Write-Host "=====================================================" -ForegroundColor Cyan

# Step 1: Upload the deploy script and run it
Write-Host "[1/5] Uploading deploy script..." -ForegroundColor Yellow
Invoke-Scp -StepLabel "1/5 Upload deploy script" -Args @(
    $deployScript,
    "${VpsUser}@${VpsIp}:/tmp/VPS_DEPLOY.sh"
)

Write-Host "[1/5] Running deploy script on VPS (installs all system deps + Python venv)..." -ForegroundColor Yellow
Invoke-Ssh -StepLabel "1/5 Run VPS deploy script" -RemoteCommand "chmod +x /tmp/VPS_DEPLOY.sh && sudo bash /tmp/VPS_DEPLOY.sh"

# Step 2: Upload trading stack code
Write-Host "[2/5] Uploading trading stack code..." -ForegroundColor Yellow
Invoke-Scp -StepLabel "2/5 Upload code" -Args @(
    "-r",
    $codeDir,
    "${VpsUser}@${VpsIp}:${VpsRoot}/"
)

# Step 3: Upload LamaScout
Write-Host "[3/5] Uploading LamaScout..." -ForegroundColor Yellow
Invoke-Scp -StepLabel "3/5 Upload LamaScout" -Args @(
    "-r",
    $lamaScoutDir,
    "${VpsUser}@${VpsIp}:${VpsRoot}/"
)

# Step 4: Fix permissions and start services
Write-Host "[4/5] Setting permissions and starting services..." -ForegroundColor Yellow
Invoke-Ssh -StepLabel "4/5 Start services" -RemoteCommand "sudo chown -R lumencore:lumencore ${VpsRoot} && sudo systemctl start lamascout-api luma-dashboard lamascout-loop"

# Step 5: Status check
Write-Host "[5/5] Service status..." -ForegroundColor Yellow
Invoke-Ssh -StepLabel "5/5 Service status" -RemoteCommand "sudo systemctl status lamascout-api luma-dashboard --no-pager"

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host " UPLOAD COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host " DNS: Point lumen-core.ai A record -> 157.151.148.234" -ForegroundColor Cyan
Write-Host " Then run SSL cert:"
Write-Host "   ssh ${VpsUser}@${VpsIp}"
Write-Host "   sudo certbot --nginx -d lumen-core.ai -d www.lumen-core.ai --non-interactive --agree-tos -m admin@lumen-core.ai"
Write-Host ""
Write-Host " Live endpoints (after SSL):"
Write-Host "   https://lumen-core.ai/dashboard/  -> Institutional Crypto Dashboard"
Write-Host "   https://lumen-core.ai/api/scout/  -> LamaScout API"
Write-Host "   https://lumen-core.ai/proof/      -> Proof artifacts & reports"
Write-Host "=====================================================" -ForegroundColor Green
