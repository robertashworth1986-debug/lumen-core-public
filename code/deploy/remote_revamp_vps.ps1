param(
  [Parameter(Mandatory = $true)]
  [Alias('Host')]
  [string]$TargetHost,

  [string]$User = "root",
  [string]$RepoPath = "/opt/lumatrader/INSTITUTIONAL_STACK_V2",
  [string]$Branch = "main",
  [string]$Domain = "lumen-core.ai",
  [string]$RepoUrl = "",
  [string]$SshKeyPath = "",
  [switch]$StrictCoherenceBuild,
  [switch]$StrictPremiumStack,
  [switch]$SkipRepoUpdate,
  [switch]$SkipCertbot
)

$ErrorActionPreference = "Stop"

function Quote-BashValue {
  param([string]$Value)
  if ($null -eq $Value) {
    return "''"
  }
  $escaped = $Value -replace "'", '''"''"'''
  return "'" + $escaped + "'"
}

function Invoke-RemoteScript {
  param(
    [string]$Target,
    [string[]]$SshArgs,
    [string]$Script
  )

  $normalized = $Script -replace "`r", ""
  $normalized | & ssh @SshArgs $Target "bash -s --"
  if ($LASTEXITCODE -ne 0) {
    throw "Remote command failed with exit code $LASTEXITCODE"
  }
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  throw "ssh is required but was not found in PATH. Install OpenSSH client first."
}

$target = "$User@$TargetHost"
$sshArgs = @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
if ($SshKeyPath) {
  $sshArgs += @("-i", $SshKeyPath)
}

$repoPathQ = Quote-BashValue $RepoPath
$branchQ = Quote-BashValue $Branch
$domainQ = Quote-BashValue $Domain
$repoUrlQ = Quote-BashValue $RepoUrl
$strictCoherenceBuildFlag = if ($StrictCoherenceBuild) { "1" } else { "0" }
$strictPremiumStackFlag = if ($StrictPremiumStack) { "1" } else { "0" }
$skipRepoUpdateFlag = if ($SkipRepoUpdate) { "1" } else { "0" }
$skipCertbotFlag = if ($SkipCertbot) { "1" } else { "0" }

Write-Host "[remote] target: $target"
Write-Host "[remote] repo:   $RepoPath"
Write-Host "[remote] branch: $Branch"
Write-Host "[remote] domain: $Domain"

$script = @'
set -euo pipefail

REPO_PATH=__REPO_PATH__
BRANCH=__BRANCH__
DOMAIN=__DOMAIN__
REPO_URL=__REPO_URL__
STRICT_COHERENCE_BUILD=__STRICT_COHERENCE_BUILD__
STRICT_PREMIUM_STACK=__STRICT_PREMIUM_STACK__
SKIP_REPO_UPDATE=__SKIP_REPO_UPDATE__
SKIP_CERTBOT=__SKIP_CERTBOT__

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

if ! command -v git >/dev/null 2>&1; then
  $SUDO apt-get update -qq
  $SUDO apt-get install -y git
fi

echo "==> Host: $(hostname)"
echo "==> Repo path: $REPO_PATH"
echo "==> Domain: $DOMAIN"

if [ ! -d "$REPO_PATH" ]; then
  if [ -z "$REPO_URL" ]; then
    echo "ERROR: repo path does not exist and RepoUrl was not provided." >&2
    exit 20
  fi
  echo "==> Cloning repository..."
  mkdir -p "$(dirname "$REPO_PATH")"
  git clone "$REPO_URL" "$REPO_PATH"
fi

cd "$REPO_PATH"

if [ "$SKIP_REPO_UPDATE" != "1" ]; then
  echo "==> Updating repository..."
  git fetch --all --prune
  git checkout "$BRANCH"
  git pull --ff-only
fi

echo "==> Running deploy revamp..."
export LUMA_DOMAIN="$DOMAIN"
if [ "$STRICT_COHERENCE_BUILD" = "1" ]; then
  export LUMA_STRICT_COHERENCE_BUILD=1
  echo "==> Strict coherence build: enabled"
fi
if [ "$STRICT_PREMIUM_STACK" = "1" ]; then
  export LUMA_STRICT_PREMIUM_STACK=1
  echo "==> Strict premium stack: enabled"
fi
$SUDO -E bash code/deploy/deploy_vps.sh "$DOMAIN"

if [ "$SKIP_CERTBOT" != "1" ]; then
  echo "==> Attempting certbot HTTPS setup..."
  $SUDO certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || true
  $SUDO nginx -t
  $SUDO systemctl reload nginx
fi

echo "==> Post-checks"
curl -fsS "https://$DOMAIN/health" >/tmp/luma_health_live.json
curl -fsS "https://$DOMAIN/api/snapshot" >/tmp/luma_snapshot_live.json

echo "==> Status"
$SUDO systemctl --no-pager --full status luma-gateway | sed -n '1,25p' || true
echo "==> Done"
'@

$script = $script.Replace('__REPO_PATH__', $repoPathQ)
$script = $script.Replace('__BRANCH__', $branchQ)
$script = $script.Replace('__DOMAIN__', $domainQ)
$script = $script.Replace('__REPO_URL__', $repoUrlQ)
$script = $script.Replace('__STRICT_COHERENCE_BUILD__', $strictCoherenceBuildFlag)
$script = $script.Replace('__STRICT_PREMIUM_STACK__', $strictPremiumStackFlag)
$script = $script.Replace('__SKIP_REPO_UPDATE__', $skipRepoUpdateFlag)
$script = $script.Replace('__SKIP_CERTBOT__', $skipCertbotFlag)

Invoke-RemoteScript -Target $target -SshArgs $sshArgs -Script $script

Write-Host "[remote] Revamp completed successfully."
Write-Host "[remote] Verify now:"
Write-Host "  https://$Domain/mission_control.html"
Write-Host "  https://$Domain/api/snapshot"
Write-Host "  https://$Domain/health"