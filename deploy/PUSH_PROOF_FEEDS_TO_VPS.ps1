param(
  [string]$VpsIp = $env:LUMA_VPS_HOST,
  [string]$VpsUser = $env:LUMA_VPS_USER,
  [string]$SshKeyPath = $env:LUMA_VPS_SSH_KEY,
  [string]$KnownHostsPath = $env:LUMA_SSH_KNOWN_HOSTS,
  [string]$BundleRoot = "",
  [string[]]$RemoteWebRoots = @("/opt/lumencore/dashboard", "/var/www/lumatrader", "/var/www/lumen-core"),
  [switch]$DryRun,
  [switch]$Apply
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

  # Do not let native child processes inherit the HumanUnlock secret.
  Remove-Item Env:LUMA_HUMAN_UNLOCK_TOKEN -ErrorAction SilentlyContinue
}

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList
  )

  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) {
    throw "Native command failed with exit code ${LASTEXITCODE}: $FilePath $($ArgumentList -join ' ')"
  }
}

function Invoke-CheckedNativeWithSecretStdin {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList,
    [Parameter(Mandatory = $true)][string]$SecretInput
  )

  $SecretInput | & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) {
    throw "Native command failed with exit code ${LASTEXITCODE}: $FilePath"
  }
}

function Resolve-RepoRoot {
  $scriptRoot = Split-Path -Parent $MyInvocation.ScriptName
  return (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Resolve-SshKey {
  param([string]$ExplicitPath)

  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath) -and (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
    return (Resolve-Path -LiteralPath $ExplicitPath).Path
  }

  throw "No SSH key found. Set LUMA_VPS_SSH_KEY or pass -SshKeyPath."
}

function Resolve-KnownHosts {
  param([string]$ExplicitPath)

  if ([string]::IsNullOrWhiteSpace($ExplicitPath) -and $env:USERPROFILE) {
    $ExplicitPath = Join-Path $env:USERPROFILE ".ssh\known_hosts"
  }
  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath) -and (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
    return (Resolve-Path -LiteralPath $ExplicitPath).Path
  }

  throw "No known-hosts file found. Set LUMA_SSH_KNOWN_HOSTS or pass -KnownHostsPath."
}

function Resolve-BundleRoot {
  param([string]$ExplicitBundleRoot, [string]$RepoRoot)

  if ($ExplicitBundleRoot) {
    if (-not (Test-Path -LiteralPath $ExplicitBundleRoot)) {
      throw "BundleRoot does not exist: $ExplicitBundleRoot"
    }
    return (Resolve-Path -LiteralPath $ExplicitBundleRoot).Path
  }

  $stageRoot = Join-Path $RepoRoot ".deploy_stage"
  $latest = Get-ChildItem -LiteralPath $stageRoot -Directory -Filter "live_domain_proof_feeds_*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if (-not $latest) {
    throw "No live_domain_proof_feeds_* bundle found. Run python .\code\ops\BUILD_LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE.py first."
  }

  return $latest.FullName
}

function Assert-BundleSafe {
  param([string]$ResolvedBundleRoot)

  $manifestPath = Join-Path $ResolvedBundleRoot "manifest.json"
  if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Bundle manifest missing: $manifestPath"
  }

  $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
  if (-not $manifest.summary.feed_only_deploy_ready) {
    throw "Bundle is not marked feed_only_deploy_ready."
  }
  if ($manifest.summary.publishes_config_or_secrets) {
    throw "Bundle says it publishes config or secrets. Refusing deploy."
  }
  if ($manifest.summary.service_restart_required) {
    throw "Bundle says a service restart is required. Refusing feed-only deploy."
  }

  $bad = Get-ChildItem -LiteralPath $ResolvedBundleRoot -Recurse -File |
    Where-Object {
      $_.Name -match '\.env|secret|private|credential|token|api_key|apikey|\.csv$|\.jsonl$|\.zip$|\.parquet$'
    }
  if ($bad) {
    $names = ($bad | Select-Object -ExpandProperty FullName) -join "`n"
    throw "Forbidden file(s) in proof feed bundle:`n$names"
  }

  return $manifest
}

function New-BundleArchive {
  param([string]$ResolvedBundleRoot)

  $archive = Join-Path ([System.IO.Path]::GetTempPath()) ("luma_proof_feeds_{0}.tar.gz" -f ([DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")))
  tar -czf $archive -C $ResolvedBundleRoot manifest.json data dashboard
  if (-not (Test-Path -LiteralPath $archive)) {
    throw "Failed to create archive: $archive"
  }
  return $archive
}

$repoRoot = Resolve-RepoRoot
$resolvedBundleRoot = Resolve-BundleRoot -ExplicitBundleRoot $BundleRoot -RepoRoot $repoRoot
$manifest = Assert-BundleSafe -ResolvedBundleRoot $resolvedBundleRoot
$remoteArchive = "/tmp/luma_proof_feeds.tar.gz"
$remoteTmp = "/tmp/luma_proof_feeds"
$rootArgs = ($RemoteWebRoots | ForEach-Object { "'$_'" }) -join " "

$remoteScript = @"
set -e
if [ "`${LUMA_VPS_DEPLOY_APPLY:-0}" != "1" ]; then
  echo "ERROR apply flag missing; proof-feed deploy refused." >&2
  exit 64
fi
human_unlock_token="`${LUMA_HUMAN_UNLOCK_TOKEN:-}"
if [ "`${#human_unlock_token}" -lt 32 ]; then
  echo "ERROR HumanUnlock is not configured with at least 32 characters; proof-feed deploy refused." >&2
  exit 65
fi
unset human_unlock_token LUMA_HUMAN_UNLOCK_TOKEN
rm -rf "$remoteTmp"
mkdir -p "$remoteTmp"
tar -xzf "$remoteArchive" -C "$remoteTmp"
updated_count=0
for root in $rootArgs; do
  if [ -d "`$root" ]; then
    sudo mkdir -p "`$root/data" "`$root/dashboard/data"
    sudo cp "$remoteTmp/data/"*.json "`$root/data/"
    sudo cp "$remoteTmp/dashboard/data/"*.json "`$root/dashboard/data/"
    sudo chmod 644 "`$root/data/"*.json "`$root/dashboard/data/"*.json
    echo "UPDATED `$root"
    updated_count=`$((updated_count + 1))
  else
    echo "SKIPPED missing `$root"
  fi
done
if [ "`$updated_count" -eq 0 ]; then
  echo "ERROR no remote web roots existed; no proof feeds were deployed." >&2
  exit 3
fi
sudo systemctl reload nginx 2>/dev/null || sudo systemctl reload caddy 2>/dev/null || true
"@

Write-Host "Feed-only bundle: $resolvedBundleRoot" -ForegroundColor Cyan
Write-Host "Required ready: $($manifest.summary.required_ready_count)/$($manifest.summary.required_feed_count)" -ForegroundColor Cyan
Write-Host "Remote web roots: $($RemoteWebRoots -join ', ')" -ForegroundColor Cyan

if (-not $Apply) {
  Write-Host "DRY RUN: local bundle checks passed; no archive was created and no network or remote mutation was attempted." -ForegroundColor Yellow
  Write-Host "Use -Apply with a private LUMA_HUMAN_UNLOCK_TOKEN of at least 32 characters to deploy this bundle." -ForegroundColor Yellow
  exit 0
}

if ([string]::IsNullOrWhiteSpace($VpsIp)) {
  throw "Apply blocked: set LUMA_VPS_HOST or pass -VpsIp."
}
if ([string]::IsNullOrWhiteSpace($VpsUser)) {
  throw "Apply blocked: set LUMA_VPS_USER or pass -VpsUser."
}
$sshKey = Resolve-SshKey -ExplicitPath $SshKeyPath
$knownHosts = Resolve-KnownHosts -ExplicitPath $KnownHostsPath
$sshSecurityArgs = @(
  "-o", "BatchMode=yes",
  "-o", "StrictHostKeyChecking=yes",
  "-o", "UserKnownHostsFile=$knownHosts"
)
$archive = New-BundleArchive -ResolvedBundleRoot $resolvedBundleRoot
Write-Host "Archive: $archive" -ForegroundColor Cyan
Write-Host "Apply transport inputs validated; host and key values are not echoed." -ForegroundColor Cyan

Invoke-CheckedNative -FilePath scp -ArgumentList ($sshSecurityArgs + @("-i", $sshKey, $archive, "$VpsUser@$VpsIp`:$remoteArchive"))
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteScript))
$guardedRemoteCommand = "set -e; IFS= read -r LUMA_HUMAN_UNLOCK_TOKEN; export LUMA_HUMAN_UNLOCK_TOKEN; export LUMA_VPS_DEPLOY_APPLY=1; echo $encoded | base64 -d | bash"
Invoke-CheckedNativeWithSecretStdin -FilePath ssh -ArgumentList ($sshSecurityArgs + @("-i", $sshKey, "$VpsUser@$VpsIp", $guardedRemoteCommand)) -SecretInput $humanUnlockToken
$humanUnlockToken = $null

Write-Host "Feed-only deploy complete. Run verification:" -ForegroundColor Green
Write-Host "python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8" -ForegroundColor Green
