param(
    [string]$VpsIp = $(if ($env:LUMA_VPS_HOST) { $env:LUMA_VPS_HOST } else { "157.151.148.234" }),
    [string]$VpsUser = "opc",
    [string]$VpsRoot = "/opt/lumencore",
    [string]$Root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    [string]$SshKeyPath = $env:LUMA_VPS_SSH_KEY,
    [switch]$Apply,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($Apply -and $DryRun) {
    throw "-Apply and -DryRun cannot be used together."
}

$humanUnlockToken = $null
if ($Apply) {
    $humanUnlockToken = [string]$env:LUMA_HUMAN_UNLOCK_TOKEN
    if ([string]::IsNullOrWhiteSpace($humanUnlockToken) -or $humanUnlockToken.Length -lt 32) {
        throw "Apply is blocked: LUMA_HUMAN_UNLOCK_TOKEN must be configured with at least 32 characters."
    }

    # Keep the secret out of all child-process environments. It is sent only
    # through SSH standard input when the guarded remote installer is invoked.
    Remove-Item Env:LUMA_HUMAN_UNLOCK_TOKEN -ErrorAction SilentlyContinue
}

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
    $scpArgs += @("-o", "BatchMode=yes")
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
    $sshArgs += @("-o", "BatchMode=yes")
    $sshArgs += @("${VpsUser}@${VpsIp}", $RemoteCommand)

    & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "[$StepLabel] ssh failed with exit code $LASTEXITCODE"
    }
}

function Invoke-SshWithHumanUnlock {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RemoteCommand,
        [Parameter(Mandatory = $true)]
        [string]$StepLabel,
        [Parameter(Mandatory = $true)]
        [string]$HumanUnlockToken
    )

    $sshArgs = @()
    if ($SshKeyPath) {
        $sshArgs += @("-i", $SshKeyPath)
    }
    $sshArgs += @("-o", "BatchMode=yes")

    $guardedRemoteCommand = @(
        "set -e"
        "IFS= read -r LUMA_HUMAN_UNLOCK_TOKEN"
        "export LUMA_HUMAN_UNLOCK_TOKEN"
        "export LUMA_VPS_DEPLOY_APPLY=1"
        $RemoteCommand
    ) -join "; "
    $sshArgs += @("${VpsUser}@${VpsIp}", $guardedRemoteCommand)

    $HumanUnlockToken | & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "[$StepLabel] ssh failed with exit code $LASTEXITCODE"
    }
}

$deployScript = Join-Path $Root "code\deploy\deploy_vps.sh"
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

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " LUMEN-CORE.AI — VPS STACK DEPLOYMENT" -ForegroundColor Cyan
Write-Host " Target: ${VpsUser}@${VpsIp}:${VpsRoot}" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

if (-not $Apply) {
    Write-Host "PRECHECK ONLY: local deployment inputs are present." -ForegroundColor Yellow
    Write-Host "No network calls, archives, copies, remote extraction, proxy reloads, or service restarts were performed." -ForegroundColor Yellow
    Write-Host "Use -Apply with a private LUMA_HUMAN_UNLOCK_TOKEN of at least 32 characters to run the existing deployment." -ForegroundColor Yellow
    exit 0
}

if (-not $SshKeyPath -or -not (Test-Path $SshKeyPath)) {
    $keyCandidates = @(
        $env:LUMA_VPS_SSH_KEY,
        "C:\Users\Novac\Downloads\ssh-key-2026-04-23.key",
        $(if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".ssh\id_ed25519" }),
        $(if ($env:USERPROFILE) { Join-Path $env:USERPROFILE ".ssh\id_rsa" })
    )
    foreach ($candidate in $keyCandidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $SshKeyPath = (Resolve-Path $candidate).Path
            break
        }
    }
}
if ($SshKeyPath -and -not (Test-Path $SshKeyPath)) {
    throw "SSH key path not found: $SshKeyPath"
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$codeArchive = Join-Path $env:TEMP "lumencore_code_$stamp.tgz"
$lamaArchive = Join-Path $env:TEMP "lumencore_lamascout_$stamp.tgz"

# Step 1: Verify the target before packaging or changing services.
Write-Host "[1/5] Checking VPS connectivity and capacity..." -ForegroundColor Yellow
Invoke-Ssh -StepLabel "1/5 VPS preflight" -RemoteCommand "set -e; test -d ${VpsRoot}; df -Pk ${VpsRoot}; test `$(df -Pk ${VpsRoot} | awk 'NR==2 {print `$4}') -gt 2097152"

# Step 2: Upload trading stack code + dashboard + core ops artifacts
Write-Host "[2/5] Uploading trading stack + dashboard + ops artifacts..." -ForegroundColor Yellow
if (Test-Path $codeArchive) { Remove-Item $codeArchive -Force }
$bundleTargets = @(
    "code",
    "dashboard",
    "config/runtime_control.json",
    "config/paper_trader_runtime.json",
    "config/autobuy.json",
    "config/accounts/ALPACA_PRIMARY/runtime_control.json",
    "config/accounts/KRAKEN_PRIMARY/runtime_control.json",
    "symbol_registry_auto.py"
)
foreach ($dataFile in @("data/grant_catalog.json", "data/company_profile.json")) {
    if (Test-Path (Join-Path $Root $dataFile)) {
        $bundleTargets += $dataFile
    }
}
if (Test-Path (Join-Path $Root "out\ops")) {
    $bundleTargets += "out/ops"
}
if (Test-Path (Join-Path $Root "out\grant_approval_queue.json")) {
    $bundleTargets += "out/grant_approval_queue.json"
}

$tarArgs = @(
    "-czf", $codeArchive,
    "-C", $Root,
    "--exclude=code/.venv",
    "--exclude=code/**/__pycache__",
    "--exclude=code/**/*.pyc",
    "--exclude=code/**/*.tgz",
    "--exclude=code/**/*.tar.gz",
    "--exclude=dashboard/node_modules",
    "--exclude=code/archive"
) + $bundleTargets

& tar @tarArgs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $codeArchive)) {
    throw "[2/5 Package code] tar archive build failed"
}
Invoke-Scp -StepLabel "2/5 Upload code archive" -Args @(
    $codeArchive,
    "${VpsUser}@${VpsIp}:/tmp/lumencore_code.tgz"
)
Invoke-Ssh -StepLabel "2/5 Extract code archive" -RemoteCommand "set -e; sudo mkdir -p ${VpsRoot}; sudo tar -xzf /tmp/lumencore_code.tgz --no-same-owner -C ${VpsRoot}; rm -f /tmp/lumencore_code.tgz"
Remove-Item $codeArchive -Force

# Step 3: Upload LamaScout
Write-Host "[3/5] Uploading LamaScout..." -ForegroundColor Yellow
if (Test-Path $lamaArchive) { Remove-Item $lamaArchive -Force }
tar -czf $lamaArchive -C $Root LamaScout
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $lamaArchive)) {
    throw "[3/5 Package LamaScout] tar archive build failed"
}
Invoke-Scp -StepLabel "3/5 Upload LamaScout archive" -Args @(
    $lamaArchive,
    "${VpsUser}@${VpsIp}:/tmp/lumencore_lamascout.tgz"
)
Invoke-Ssh -StepLabel "3/5 Extract LamaScout archive" -RemoteCommand "sudo mkdir -p ${VpsRoot} && sudo tar -xzf /tmp/lumencore_lamascout.tgz --overwrite -C ${VpsRoot} && rm -f /tmp/lumencore_lamascout.tgz"
Remove-Item $lamaArchive -Force

# Step 3b: Upload public landing page (index.html, robots.txt, sitemap.xml, assets/)
$landingDir = Join-Path $Root "deploy\landing"
if (Test-Path $landingDir) {
    Write-Host "[3b] Uploading public landing page (SEO assets)..." -ForegroundColor Yellow
    $landingArchive = Join-Path $env:TEMP "lumencore_landing_$stamp.tgz"
    if (Test-Path $landingArchive) { Remove-Item $landingArchive -Force }
    tar -czf $landingArchive -C $landingDir .
    if ($LASTEXITCODE -eq 0 -and (Test-Path $landingArchive)) {
        Invoke-Scp -StepLabel "3b Upload landing archive" -Args @(
            $landingArchive,
            "${VpsUser}@${VpsIp}:/tmp/lumencore_landing.tgz"
        )
        Invoke-Ssh -StepLabel "3b Extract landing to web root" -RemoteCommand "sudo mkdir -p /var/www/lumen-core/assets && sudo tar -xzf /tmp/lumencore_landing.tgz --overwrite -C /var/www/lumen-core/ && rm -f /tmp/lumencore_landing.tgz && sudo chown -R caddy:caddy /var/www/lumen-core/ 2>/dev/null || true"
        Remove-Item $landingArchive -Force
        Write-Host "[3b] Landing page pushed OK" -ForegroundColor Green
    } else {
        Write-Warning "[3b] Landing tar failed — skipping landing upload"
    }
}

# Step 4: Install current units after current source is in place.
Write-Host "[4/5] Installing and restarting canonical production services..." -ForegroundColor Yellow
$installServicesCmd = 'set -e; sudo find ' + $VpsRoot + '/code/deploy -type f -name "*.sh" -exec sed -i "s/\r$//" {} +; sudo bash -n ' + $VpsRoot + '/code/deploy/deploy_vps.sh; sudo chown -R lumencore:lumencore ' + $VpsRoot + '; sudo --preserve-env=LUMA_HUMAN_UNLOCK_TOKEN,LUMA_VPS_DEPLOY_APPLY env LUMA_SERVICE_USER=lumencore LUMA_DOMAIN=lumen-core.ai bash ' + $VpsRoot + '/code/deploy/deploy_vps.sh lumen-core.ai; sudo systemctl restart luma-gateway luma-dashboard-refresh luma-paper-ticker luma-symbol-awareness luma-kraken-history'
Invoke-SshWithHumanUnlock -StepLabel "4/5 Install services" -RemoteCommand $installServicesCmd -HumanUnlockToken $humanUnlockToken
$humanUnlockToken = $null

# Step 5: Status check
Write-Host "[5/5] Service status..." -ForegroundColor Yellow
$statusCmd = 'for svc in luma-gateway luma-dashboard-refresh luma-paper-ticker luma-symbol-awareness luma-kraken-history lamascout-api luma-dashboard luma-intel-api; do if sudo systemctl list-unit-files --type=service | grep -q "^${svc}\.service"; then echo "--- ${svc} ---"; sudo systemctl --no-pager --full status "$svc" | sed -n "1,12p"; fi; done; curl -fsS http://127.0.0.1:8787/health >/dev/null; curl -fsS http://127.0.0.1:8787/api/snapshot >/dev/null'
Invoke-Ssh -StepLabel "5/5 Service status" -RemoteCommand $statusCmd

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host " UPLOAD COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host " DNS: Point lumen-core.ai A record -> $VpsIp" -ForegroundColor Cyan
Write-Host " Then run SSL cert:"
Write-Host "   ssh ${VpsUser}@${VpsIp}"
Write-Host "   sudo certbot --nginx -d lumen-core.ai -d www.lumen-core.ai -d app.lumen-core.ai -d research.lumen-core.ai --non-interactive --agree-tos -m admin@lumen-core.ai"
Write-Host ""
Write-Host " Live endpoints (after SSL):"
Write-Host "   https://lumen-core.ai/dashboard/  -> Institutional Crypto Dashboard"
Write-Host "   https://lumen-core.ai/api/scout/  -> LamaScout API"
Write-Host "   https://lumen-core.ai/intel/      -> Cross-sector opportunity API"
Write-Host "   https://lumen-core.ai/proof/      -> Proof artifacts & reports"
Write-Host "   https://app.lumen-core.ai/        -> Investor app dashboard"
Write-Host "   https://research.lumen-core.ai/   -> Research/scout dashboard"
Write-Host "=====================================================" -ForegroundColor Green
