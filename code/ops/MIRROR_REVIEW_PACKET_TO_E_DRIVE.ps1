[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$SourceRoot,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$VaultRoot,

    [Parameter(Mandatory)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$SnapshotLabel,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string[]]$RelativePath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$resolvedSource = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\')
$resolvedVault = (Resolve-Path -LiteralPath $VaultRoot).Path.TrimEnd('\')
$sourceCommit = (& git -C $resolvedSource rev-parse HEAD 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '^[0-9a-f]{40,64}$') {
    throw "SourceRoot must be a Git worktree with a resolvable HEAD: $resolvedSource"
}
$sourceStatus = @(& git -C $resolvedSource status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect Git worktree state: $resolvedSource"
}
if (($sourceStatus -join '').Length -ne 0) {
    throw "SourceRoot must be clean before a commit-bound mirror is created."
}
$generatedUtc = (Get-Date).ToUniversalTime()
$stamp = $generatedUtc.ToString('yyyyMMddTHHmmssZ')
$snapshotRoot = Join-Path $resolvedVault "OPPORTUNITIES\$SnapshotLabel`_$stamp"

if (Test-Path -LiteralPath $snapshotRoot) {
    throw "Snapshot target already exists: $snapshotRoot"
}
New-Item -ItemType Directory -Path $snapshotRoot -Force | Out-Null

$manifestRows = @()
foreach ($relative in $RelativePath) {
    if ([IO.Path]::IsPathRooted($relative)) {
        throw "RelativePath must be relative: $relative"
    }
    $sourceCandidate = Join-Path $resolvedSource $relative
    $resolvedItem = Resolve-Path -LiteralPath $sourceCandidate -ErrorAction Stop
    $sourcePath = $resolvedItem.Path
    if (-not $sourcePath.StartsWith(
        $resolvedSource + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Source path escaped SourceRoot: $relative"
    }
    $item = Get-Item -LiteralPath $sourcePath
    if ($item.PSIsContainer) {
        throw "Only explicit files are accepted: $relative"
    }

    $destinationPath = Join-Path $snapshotRoot $relative
    $destinationDirectory = Split-Path -Parent $destinationPath
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath

    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $destinationHash = (
        Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($sourceHash -ne $destinationHash) {
        throw "Hash mismatch after copy: $relative"
    }
    $manifestRows += [ordered]@{
        relative_path = $relative.Replace('\', '/')
        bytes = $item.Length
        sha256 = $sourceHash
    }
}

$manifest = [ordered]@{
    schema = 'lumencore.e_drive_non_destructive_mirror.v1'
    generated_utc = $generatedUtc.ToString('o')
    source_root = $resolvedSource
    source_commit = $sourceCommit
    source_worktree_clean = $true
    snapshot_label = $SnapshotLabel
    snapshot_root = $snapshotRoot
    destructive_delete_used = $false
    overwrite_existing_snapshot_used = $false
    file_count = $manifestRows.Count
    files = @($manifestRows | Sort-Object -Property relative_path)
}
$manifestPath = Join-Path $snapshotRoot 'MIRROR_MANIFEST.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifestHash = (
    Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
$manifestHash |
    Set-Content -LiteralPath (Join-Path $snapshotRoot 'MIRROR_MANIFEST.sha256') -Encoding ascii

[ordered]@{
    status = 'COMPLETE'
    snapshot_root = $snapshotRoot
    file_count = $manifestRows.Count
    manifest_sha256 = $manifestHash
} | ConvertTo-Json -Depth 3
