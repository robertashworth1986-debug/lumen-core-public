param(
  [string]$VpsIp = $(if ($env:LUMA_VPS_HOST) { $env:LUMA_VPS_HOST } else { "157.151.148.234" }),
  [string]$VpsUser = $(if ($env:LUMA_VPS_USER) { $env:LUMA_VPS_USER } else { "opc" }),
  [string]$SshKeyPath = $env:LUMA_VPS_SSH_KEY,
  [string]$BundleRoot = "",
  [string[]]$RemoteWebRoots = @("/opt/lumencore/dashboard", "/var/www/lumatrader", "/var/www/lumen-core"),
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

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

function Resolve-RepoRoot {
  $scriptRoot = Split-Path -Parent $MyInvocation.ScriptName
  return (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Resolve-SshKey {
  param([string]$ExplicitPath)

  $candidates = @()
  if ($ExplicitPath) { $candidates += $ExplicitPath }
  if ($env:USERPROFILE) {
    $candidates += (Join-Path $env:USERPROFILE "Downloads\ssh-key-2026-04-23.key")
    $candidates += (Join-Path $env:USERPROFILE "Downloads\oracle_new")
    $candidates += (Join-Path $env:USERPROFILE ".ssh\luma_vps")
    $candidates += (Join-Path $env:USERPROFILE ".ssh\id_rsa")
    $candidates += (Join-Path $env:USERPROFILE ".ssh\id_ed25519")
  }

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }

  throw "No SSH key found. Set LUMA_VPS_SSH_KEY or pass -SshKeyPath."
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
$sshKey = Resolve-SshKey -ExplicitPath $SshKeyPath
$archive = New-BundleArchive -ResolvedBundleRoot $resolvedBundleRoot
$remoteArchive = "/tmp/luma_proof_feeds.tar.gz"
$remoteTmp = "/tmp/luma_proof_feeds"
$rootArgs = ($RemoteWebRoots | ForEach-Object { "'$_'" }) -join " "

$remoteScript = @"
set -e
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
Write-Host "Archive: $archive" -ForegroundColor Cyan
Write-Host "Required ready: $($manifest.summary.required_ready_count)/$($manifest.summary.required_feed_count)" -ForegroundColor Cyan
Write-Host "Target: $VpsUser@$VpsIp" -ForegroundColor Cyan
Write-Host "SSH key: $sshKey" -ForegroundColor Cyan
Write-Host "Remote web roots: $($RemoteWebRoots -join ', ')" -ForegroundColor Cyan

if ($DryRun) {
  Write-Host "DRY RUN: no files uploaded." -ForegroundColor Yellow
  Write-Host "scp command:" -ForegroundColor Yellow
  Write-Host "scp -i `"$sshKey`" `"$archive`" $VpsUser@$VpsIp`:$remoteArchive"
  Write-Host "remote script:" -ForegroundColor Yellow
  Write-Host $remoteScript
  exit 0
}

Invoke-CheckedNative -FilePath scp -ArgumentList @("-i", $sshKey, $archive, "$VpsUser@$VpsIp`:$remoteArchive")
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteScript))
Invoke-CheckedNative -FilePath ssh -ArgumentList @("-i", $sshKey, "$VpsUser@$VpsIp", "echo $encoded | base64 -d | bash")

Write-Host "Feed-only deploy complete. Run verification:" -ForegroundColor Green
Write-Host "python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8" -ForegroundColor Green
