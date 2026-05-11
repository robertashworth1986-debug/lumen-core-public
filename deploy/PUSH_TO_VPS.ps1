$ErrorActionPreference = "Stop"

# =============================================================================
# LUMEN-CORE.AI — Push Stack to VPS
# VPS IP:     157.151.148.234
# SSH User:   ubuntu  (Oracle Cloud default)
# Domain:     lumen-core.ai
# Stack root: /opt/lumencore
# =============================================================================

$VPS_IP   = "157.151.148.234"
$VPS_USER = "ubuntu"
$VPS_ROOT = "/opt/lumencore"
$ROOT     = "C:\LumaTrader\INSTITUTIONAL_STACK_V2"

# You need scp/ssh available — uses OpenSSH from Windows 10+
# If you have a key file, set: $SSH_KEY = "-i C:\path\to\key.pem"
$SSH_KEY  = ""   # e.g. "-i C:\Users\Novac\.ssh\oracle_vps.pem"

function ssh_cmd($cmd) {
    if ($SSH_KEY) {
        ssh $SSH_KEY "${VPS_USER}@${VPS_IP}" $cmd
    } else {
        ssh "${VPS_USER}@${VPS_IP}" $cmd
    }
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " LUMEN-CORE.AI — VPS STACK UPLOAD" -ForegroundColor Cyan
Write-Host " Target: ${VPS_USER}@${VPS_IP}:${VPS_ROOT}" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Step 1: Upload the deploy script and run it
Write-Host "[1/5] Uploading deploy script..." -ForegroundColor Yellow
if ($SSH_KEY) {
    scp $SSH_KEY "$ROOT\deploy\VPS_DEPLOY.sh" "${VPS_USER}@${VPS_IP}:/tmp/VPS_DEPLOY.sh"
} else {
    scp "$ROOT\deploy\VPS_DEPLOY.sh" "${VPS_USER}@${VPS_IP}:/tmp/VPS_DEPLOY.sh"
}

Write-Host "[1/5] Running deploy script on VPS (installs all system deps + Python venv)..." -ForegroundColor Yellow
ssh_cmd "chmod +x /tmp/VPS_DEPLOY.sh && sudo bash /tmp/VPS_DEPLOY.sh"

# Step 2: Upload trading stack code
Write-Host "[2/5] Uploading trading stack code..." -ForegroundColor Yellow
if ($SSH_KEY) {
    scp -r $SSH_KEY "$ROOT\code\*" "${VPS_USER}@${VPS_IP}:${VPS_ROOT}/code/"
} else {
    scp -r "$ROOT\code\*" "${VPS_USER}@${VPS_IP}:${VPS_ROOT}/code/"
}

# Step 3: Upload LamaScout
Write-Host "[3/5] Uploading LamaScout..." -ForegroundColor Yellow
if ($SSH_KEY) {
    scp -r $SSH_KEY "$ROOT\LamaScout\*" "${VPS_USER}@${VPS_IP}:${VPS_ROOT}/LamaScout/"
} else {
    scp -r "$ROOT\LamaScout\*" "${VPS_USER}@${VPS_IP}:${VPS_ROOT}/LamaScout/"
}

# Step 4: Fix permissions and start services
Write-Host "[4/5] Setting permissions and starting services..." -ForegroundColor Yellow
ssh_cmd "sudo chown -R lumencore:lumencore /opt/lumencore && sudo systemctl start lamascout-api luma-dashboard lamascout-loop"

# Step 5: Status check
Write-Host "[5/5] Service status..." -ForegroundColor Yellow
ssh_cmd "sudo systemctl status lamascout-api luma-dashboard --no-pager"

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host " UPLOAD COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host " DNS: Point lumen-core.ai A record -> 157.151.148.234" -ForegroundColor Cyan
Write-Host " Then run SSL cert:"
Write-Host "   ssh ${VPS_USER}@${VPS_IP}"
Write-Host "   sudo certbot --nginx -d lumen-core.ai -d www.lumen-core.ai --non-interactive --agree-tos -m admin@lumen-core.ai"
Write-Host ""
Write-Host " Live endpoints (after SSL):"
Write-Host "   https://lumen-core.ai/dashboard/  -> Institutional Crypto Dashboard"
Write-Host "   https://lumen-core.ai/api/scout/  -> LamaScout API"
Write-Host "   https://lumen-core.ai/proof/      -> Proof artifacts & reports"
Write-Host "=====================================================" -ForegroundColor Green
