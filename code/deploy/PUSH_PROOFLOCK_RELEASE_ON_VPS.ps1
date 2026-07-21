[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-f]{40}$")]
    [string]$SourceCommit,

    [ValidateSet("HOLD", "DEPLOY_PROOFLOCK_EXACT_SNAPSHOT")]
    [string]$Approval = "HOLD",

    [switch]$Execute,

    [string]$RepoRoot = "",
    [string]$RequiredRemoteRef = "origin/build-week/prooflock-judge-ready",
    [string]$OutputDirectory = "",
    [string]$VpsHost = $env:LUMA_VPS_HOST,
    [string]$VpsUser = "opc",
    [string]$SshKeyPath = $env:LUMA_VPS_SSH_KEY,
    [string]$KnownHostsPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RequiredApproval = "DEPLOY_PROOFLOCK_EXACT_SNAPSHOT"
$ReleaseFileCount = 15
$ApplyRepoPath = "code/deploy/APPLY_PROOFLOCK_RELEASE_ON_VPS.sh"

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command is unavailable: $Name"
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Label
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Invoke-GitText {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & git -C $script:ResolvedRepoRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed"
    }
    return (($output | ForEach-Object { "$_" }) -join "`n").Trim()
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Write-OperatorReceipt {
    $rendered = ($script:Receipt | ConvertTo-Json -Depth 8) + "`n"
    Write-Utf8NoBom -Path $script:ReceiptPath -Text $rendered
}

Require-Command -Name "git"
Require-Command -Name "python"
Require-Command -Name "tar"

if (-not $RepoRoot) {
    $RepoRoot = Join-Path $PSScriptRoot "..\.."
}
$ResolvedRepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

$headCommit = Invoke-GitText -Arguments @("rev-parse", "HEAD")
if ($headCommit -ne $SourceCommit) {
    throw "SourceCommit must equal the current worktree HEAD"
}
$resolvedCommit = Invoke-GitText -Arguments @(
    "rev-parse",
    "--verify",
    "${SourceCommit}^{commit}"
)
if ($resolvedCommit -ne $SourceCommit) {
    throw "SourceCommit did not resolve to the exact requested commit"
}

$remoteCommit = Invoke-GitText -Arguments @(
    "rev-parse",
    "--verify",
    "${RequiredRemoteRef}^{commit}"
)
& git -C $ResolvedRepoRoot merge-base --is-ancestor $SourceCommit $remoteCommit
if ($LASTEXITCODE -ne 0) {
    throw "SourceCommit is not reachable from $RequiredRemoteRef"
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$shortCommit = $SourceCommit.Substring(0, 12)
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ResolvedRepoRoot "out\releases\prooflock\$timestamp-$shortCommit"
}
if (Test-Path -LiteralPath $OutputDirectory) {
    throw "OutputDirectory already exists; release preparation never overwrites receipts"
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path

$archivePath = Join-Path $OutputDirectory "prooflock-release.tar"
$manifestPath = Join-Path $OutputDirectory "prooflock-release-manifest.json"
$installerArchivePath = Join-Path $OutputDirectory "prooflock-operator-support.tar"
$applyScriptPath = Join-Path $OutputDirectory ($ApplyRepoPath -replace "/", "\")
$ReceiptPath = Join-Path $OutputDirectory "prooflock-manual-release-receipt.json"
$remoteReceiptPath = Join-Path $OutputDirectory "prooflock-remote-deploy-receipt.txt"
$liveGateJsonPath = Join-Path $OutputDirectory "prooflock-live-gate.json"
$liveGateMarkdownPath = Join-Path $OutputDirectory "prooflock-live-gate.md"

$packagerPath = Join-Path $ResolvedRepoRoot "code\deploy\package_prooflock_release.py"
$verifierPath = Join-Path $ResolvedRepoRoot "code\ops\VERIFY_PROOFLOCK_LIVE_RELEASE.py"
if (-not (Test-Path -LiteralPath $packagerPath -PathType Leaf)) {
    throw "Bounded release packager is missing"
}
if (-not (Test-Path -LiteralPath $verifierPath -PathType Leaf)) {
    throw "Current-head live verifier is missing"
}

Invoke-Checked -FilePath "python" -Label "ProofLock immutable package build" -Arguments @(
    $packagerPath,
    "--source-commit", $SourceCommit,
    "--archive", $archivePath,
    "--manifest", $manifestPath,
    "--repo-root", $ResolvedRepoRoot
)

Invoke-Checked -FilePath "git" -Label "ProofLock operator support export" -Arguments @(
    "-C", $ResolvedRepoRoot,
    "archive",
    "--format=tar",
    "--output=$installerArchivePath",
    $SourceCommit,
    "--",
    $ApplyRepoPath
)
Invoke-Checked -FilePath "tar" -Label "ProofLock operator support extraction" -Arguments @(
    "-xf", $installerArchivePath,
    "-C", $OutputDirectory
)

$expectedApplyOid = Invoke-GitText -Arguments @(
    "rev-parse",
    "${SourceCommit}:$ApplyRepoPath"
)
$actualApplyOid = Invoke-GitText -Arguments @("hash-object", "--", $applyScriptPath)
if ($actualApplyOid -ne $expectedApplyOid) {
    throw "Exported apply script does not match the pinned Git blob"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$archiveSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
if ($manifest.schema -ne "lumencore.prooflock_release_manifest.v2") {
    throw "Unexpected release manifest schema"
}
if ($manifest.source_commit -ne $SourceCommit) {
    throw "Release manifest source commit mismatch"
}
if ([int]$manifest.file_count -ne $ReleaseFileCount) {
    throw "Release manifest must contain exactly $ReleaseFileCount files"
}
if ($manifest.archive_sha256 -ne $archiveSha256) {
    throw "Release archive hash does not match the manifest"
}

$Receipt = [ordered]@{
    schema = "lumencore.prooflock_manual_release_operator_receipt.v1"
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    source_commit = $SourceCommit
    required_remote_ref = $RequiredRemoteRef
    remote_ref_commit = $remoteCommit
    status = "PACKAGED_HOLD"
    approval = $Approval
    execute_requested = [bool]$Execute
    deployment_attempted = $false
    deployment_succeeded = $false
    live_verification_succeeded = $false
    file_count = $ReleaseFileCount
    archive_sha256 = $archiveSha256
    apply_script_git_blob_oid = $expectedApplyOid
    paths = [ordered]@{
        archive = $archivePath
        manifest = $manifestPath
        operator_support_archive = $installerArchivePath
        remote_deploy_receipt = $remoteReceiptPath
        live_gate_json = $liveGateJsonPath
        live_gate_markdown = $liveGateMarkdownPath
    }
    claim_boundary = "Packaging proves exact Git-blob identity only. Deployment and current live parity remain false until an explicitly approved execution completes and the 15-file live verifier passes."
}
Write-OperatorReceipt

if (-not $Execute) {
    Write-Output ($Receipt | ConvertTo-Json -Depth 8)
    exit 0
}
if ($Approval -ne $RequiredApproval) {
    throw "Execute requires the exact approval token $RequiredApproval"
}

Require-Command -Name "ssh"
Require-Command -Name "scp"

if (-not $VpsHost -or $VpsHost -notmatch "^[A-Za-z0-9][A-Za-z0-9.-]*$") {
    throw "VpsHost is required and must contain only a hostname or IP address"
}
if (-not $VpsUser -or $VpsUser -notmatch "^[A-Za-z_][A-Za-z0-9_-]*$") {
    throw "VpsUser is invalid"
}
if (-not $KnownHostsPath) {
    $KnownHostsPath = Join-Path $HOME ".ssh\known_hosts"
}
if (-not (Test-Path -LiteralPath $KnownHostsPath -PathType Leaf)) {
    throw "A pinned SSH known_hosts file is required"
}
if ($SshKeyPath -and -not (Test-Path -LiteralPath $SshKeyPath -PathType Leaf)) {
    throw "Configured SSH key file does not exist"
}

$sshOptions = @(
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=12",
    "-o", "UserKnownHostsFile=$KnownHostsPath"
)
if ($SshKeyPath) {
    $sshOptions = @("-i", $SshKeyPath) + $sshOptions
}

$remoteStage = "/tmp/lumencore-prooflock-manual-$timestamp-$PID-$shortCommit"
if ($remoteStage -notmatch "^/tmp/lumencore-prooflock-manual-[0-9]{8}T[0-9]{6}Z-[0-9]+-[0-9a-f]{12}$") {
    throw "Remote staging path failed the bounded-path check"
}
$target = "${VpsUser}@${VpsHost}"
$stageCreated = $false

try {
    $preflightCommand = "set -eu; sudo -n true; test ! -e '$remoteStage'; install -d -m 700 '$remoteStage'; for c in python3 sha256sum stat cp cmp install date mktemp realpath; do command -v `$c >/dev/null; done"
    Invoke-Checked -FilePath "ssh" -Label "ProofLock VPS preflight" -Arguments @(
        $sshOptions + @($target, $preflightCommand)
    )
    $stageCreated = $true

    $destination = "${target}:$remoteStage/"
    Invoke-Checked -FilePath "scp" -Label "ProofLock bounded upload" -Arguments @(
        $sshOptions + @($archivePath, $manifestPath, $applyScriptPath, $destination)
    )

    $remoteApplyScript = "$remoteStage/APPLY_PROOFLOCK_RELEASE_ON_VPS.sh"
    $remoteCommand = "sudo -n bash '$remoteApplyScript' --archive '$remoteStage/prooflock-release.tar' --manifest '$remoteStage/prooflock-release-manifest.json' --source-commit '$SourceCommit' --approval '$RequiredApproval'"
    $Receipt.status = "DEPLOYMENT_STARTED"
    $Receipt.deployment_attempted = $true
    Write-OperatorReceipt

    $deployOutput = & ssh @sshOptions $target $remoteCommand 2>&1
    $deployExitCode = $LASTEXITCODE
    $deployText = (($deployOutput | ForEach-Object { "$_" }) -join "`n") + "`n"
    Write-Utf8NoBom -Path $remoteReceiptPath -Text $deployText
    if ($deployExitCode -ne 0 -or $deployText -notmatch "PROOFLOCK_DEPLOYMENT_OK") {
        throw "Remote bounded deployment did not produce a success receipt"
    }
    $Receipt.deployment_succeeded = $true
    $Receipt.status = "DEPLOYED_LIVE_VERIFICATION_HOLD"
    Write-OperatorReceipt

    & python $verifierPath `
        --source-commit $SourceCommit `
        --output-json $liveGateJsonPath `
        --output-markdown $liveGateMarkdownPath
    $liveVerifierExitCode = $LASTEXITCODE
    if ($liveVerifierExitCode -ne 0) {
        throw "Current-head live verifier did not pass"
    }
    $liveGate = Get-Content -LiteralPath $liveGateJsonPath -Raw | ConvertFrom-Json
    if (
        $liveGate.status -ne "CURRENT_HEAD_DEPLOYED" -or
        $liveGate.submission_gate -ne "PASS" -or
        [int]$liveGate.summary.byte_match_count -ne $ReleaseFileCount -or
        [int]$liveGate.summary.file_count -ne $ReleaseFileCount
    ) {
        throw "Live gate did not prove exact 15-file current-head parity"
    }

    $Receipt.live_verification_succeeded = $true
    $Receipt.status = "DEPLOYED_CURRENT_HEAD_LIVE_MATCH"
    $Receipt.live_gate_sha256 = $liveGate.gate_sha256
    Write-OperatorReceipt
    Write-Output ($Receipt | ConvertTo-Json -Depth 8)
}
catch {
    $Receipt.status = "DEPLOYMENT_OR_VERIFICATION_HOLD"
    $Receipt.error_type = $_.Exception.GetType().FullName
    $Receipt.error_message = $_.Exception.Message
    Write-OperatorReceipt
    throw
}
finally {
    if ($stageCreated) {
        $cleanupCommand = "test '$remoteStage' != /tmp && rm -rf -- '$remoteStage'"
        & ssh @sshOptions $target $cleanupCommand | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $Receipt.remote_cleanup_warning = $true
            Write-OperatorReceipt
        }
    }
}
