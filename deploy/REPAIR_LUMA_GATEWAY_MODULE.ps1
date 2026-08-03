param(
    [string]$VpsIp = $(if ($env:LUMA_VPS_HOST) { $env:LUMA_VPS_HOST } else { "157.151.148.234" }),
    [string]$VpsUser = $(if ($env:LUMA_VPS_USER) { $env:LUMA_VPS_USER } else { "opc" }),
    [string]$SshKeyPath = $env:LUMA_VPS_SSH_KEY,
    [string]$ModulePath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\booth_public_contract.py",
    [string]$RemoteCodeRoot = "/opt/lumencore/code",
    [string]$ApprovedModuleSha256 = "",
    [switch]$Apply,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($Apply -and $DryRun) {
    throw "-Apply and -DryRun cannot be used together."
}

function Resolve-SshKey {
    param([string]$ExplicitPath)

    $candidates = @()
    if ($ExplicitPath) {
        $candidates += $ExplicitPath
    }
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE "Downloads\ssh-key-2026-04-23.key")
        $candidates += (Join-Path $env:USERPROFILE "Downloads\oracle_new")
        $candidates += (Join-Path $env:USERPROFILE ".ssh\luma_vps")
        $candidates += (Join-Path $env:USERPROFILE ".ssh\id_ed25519")
        $candidates += (Join-Path $env:USERPROFILE ".ssh\id_rsa")
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "No SSH key found. Set LUMA_VPS_SSH_KEY or pass -SshKeyPath."
}

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Native command failed with exit code ${LASTEXITCODE}: $FilePath"
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

if (-not (Test-Path -LiteralPath $ModulePath -PathType Leaf)) {
    throw "Required gateway module is missing: $ModulePath"
}

$resolvedModulePath = (Resolve-Path -LiteralPath $ModulePath).Path
$moduleName = Split-Path -Leaf $resolvedModulePath
if ($moduleName -ne "booth_public_contract.py") {
    throw "This bounded repair accepts only booth_public_contract.py."
}

$moduleSha256 = (Get-FileHash -LiteralPath $resolvedModulePath -Algorithm SHA256).Hash.ToLowerInvariant()
$moduleBytes = (Get-Item -LiteralPath $resolvedModulePath).Length

Write-Host "LumenCore gateway repair preflight" -ForegroundColor Cyan
Write-Host "Module: $moduleName" -ForegroundColor Cyan
Write-Host "SHA-256: $moduleSha256" -ForegroundColor Cyan
Write-Host "Bytes: $moduleBytes" -ForegroundColor Cyan
Write-Host "Target service: luma-gateway" -ForegroundColor Cyan
Write-Host "Remote destination: $RemoteCodeRoot/$moduleName" -ForegroundColor Cyan

if (-not $Apply) {
    Write-Host "DRY RUN: no network call, upload, restart, or remote mutation was performed." -ForegroundColor Yellow
    Write-Host "Apply requires the exact module SHA-256 and a private LUMA_HUMAN_UNLOCK_TOKEN." -ForegroundColor Yellow
    exit 0
}

if ($ApprovedModuleSha256 -cne $moduleSha256) {
    throw "Apply blocked: -ApprovedModuleSha256 must exactly match the current module SHA-256."
}

$humanUnlockToken = [string]$env:LUMA_HUMAN_UNLOCK_TOKEN
if ([string]::IsNullOrWhiteSpace($humanUnlockToken) -or $humanUnlockToken.Length -lt 32) {
    throw "Apply blocked: LUMA_HUMAN_UNLOCK_TOKEN must be configured with at least 32 characters."
}

# Do not let native child processes inherit the HumanUnlock secret.
Remove-Item Env:LUMA_HUMAN_UNLOCK_TOKEN -ErrorAction SilentlyContinue

$sshKey = Resolve-SshKey -ExplicitPath $SshKeyPath
$remoteStage = "/tmp/lumencore_gateway_repair_$($moduleSha256.Substring(0, 16)).py"
$remoteDestination = "$RemoteCodeRoot/$moduleName"

$remotePreflight = @"
set -eu
test -d '$RemoteCodeRoot'
test -x /opt/lumencore/.venv/bin/python
test -f '$RemoteCodeRoot/luma_experience_gateway.py'
if [ -f '$remoteDestination' ]; then
  sha256sum '$remoteDestination' | awk '{print "REMOTE_MODULE_SHA256=" `$1}'
else
  echo 'REMOTE_MODULE_SHA256=MISSING'
fi
systemctl show luma-gateway -p LoadState -p ActiveState -p SubState -p NRestarts --no-pager
"@

Invoke-CheckedNative -FilePath "ssh" -ArgumentList @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=12",
    "-i", $sshKey,
    "$VpsUser@$VpsIp",
    $remotePreflight
)

Invoke-CheckedNative -FilePath "scp" -ArgumentList @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=12",
    "-i", $sshKey,
    $resolvedModulePath,
    "$VpsUser@$VpsIp`:$remoteStage"
)

$remoteApply = @"
set -euo pipefail
IFS= read -r LUMA_HUMAN_UNLOCK_TOKEN
if [ "`${#LUMA_HUMAN_UNLOCK_TOKEN}" -lt 32 ]; then
  echo 'ERROR HumanUnlock is not configured with at least 32 characters.' >&2
  exit 65
fi
unset LUMA_HUMAN_UNLOCK_TOKEN
expected_sha='$moduleSha256'
stage='$remoteStage'
destination='$remoteDestination'
observed_sha=`$(sha256sum "`$stage" | awk '{print `$1}')
if [ "`$observed_sha" != "`$expected_sha" ]; then
  echo 'ERROR staged module hash mismatch.' >&2
  exit 66
fi
if [ -f "`$destination" ]; then
  current_sha=`$(sha256sum "`$destination" | awk '{print `$1}')
  if [ "`$current_sha" != "`$expected_sha" ]; then
    echo 'ERROR destination now exists with a different hash; refusing overwrite.' >&2
    exit 67
  fi
  echo 'MODULE_ACTION=NOOP_EXACT_MATCH'
else
  sudo install -o lumencore -g lumencore -m 0644 "`$stage" "`$destination"
  echo 'MODULE_ACTION=INSTALLED_MISSING_MODULE'
fi
rm -f "`$stage"
cd '$RemoteCodeRoot'
/opt/lumencore/.venv/bin/python -B -c 'import booth_public_contract; from booth_public_contract import public_booth_projection; assert callable(public_booth_projection)'
sudo systemctl restart luma-gateway
healthy=0
for attempt in `$(seq 1 30); do
  if systemctl is-active --quiet luma-gateway && curl -fsS http://127.0.0.1:8787/health >/dev/null; then
    healthy=1
    break
  fi
  sleep 1
done
if [ "`$healthy" -ne 1 ]; then
  systemctl show luma-gateway -p ActiveState -p SubState -p Result -p ExecMainStatus --no-pager
  journalctl -u luma-gateway -n 40 --no-pager
  exit 68
fi
printf 'REMOTE_MODULE_SHA256='
sha256sum "`$destination" | awk '{print `$1}'
systemctl show luma-gateway -p ActiveState -p SubState -p Result -p NRestarts --no-pager
echo 'LOCAL_GATEWAY_HEALTH=PASS'
"@

Invoke-CheckedNativeWithSecretStdin -FilePath "ssh" -ArgumentList @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=12",
    "-i", $sshKey,
    "$VpsUser@$VpsIp",
    $remoteApply
) -SecretInput $humanUnlockToken

$humanUnlockToken = $null

Write-Host "Gateway repair applied. Verify the public service contract and dashboard routes next." -ForegroundColor Green
