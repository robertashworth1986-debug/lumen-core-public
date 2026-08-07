[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$DriveRoot = 'E:\',

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$VaultRoot = 'E:\LumaProofVault',

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$OutputRoot = 'E:\LumaProofVault\PRIVATE_CONTROLS'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-DirectorySummary {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter()]
        [string]$Privacy = 'NON_PRIVATE_OR_MIXED'
    )

    $files = @(
        Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue
    )
    $newest = $null
    if ($files.Count -gt 0) {
        $newest = (
            $files |
                Sort-Object LastWriteTimeUtc -Descending |
                Select-Object -First 1 -ExpandProperty LastWriteTimeUtc
        ).ToString('o')
    }
    $bytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
    $manifestCount = @(
        $files |
            Where-Object {
                $_.Name -match '(?i)(manifest|receipt|index|chain|sha256|handoff|gate)'
            }
    ).Count

    [pscustomobject][ordered]@{
        label = $Label
        privacy = $Privacy
        file_count = $files.Count
        bytes = $bytes
        newest_utc = $newest
        manifest_like_file_count = $manifestCount
    }
}

function ConvertTo-GiB {
    param([int64]$Bytes)
    [math]::Round($Bytes / 1GB, 3)
}

$resolvedDrive = (Resolve-Path -LiteralPath $DriveRoot).Path
$resolvedVault = (Resolve-Path -LiteralPath $VaultRoot).Path
$resolvedOutput = (Resolve-Path -LiteralPath $OutputRoot).Path

if (-not $resolvedVault.StartsWith($resolvedDrive, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "VaultRoot must be inside DriveRoot."
}

$privateLabels = @(
    'COUNSEL_PACKETS',
    'PRIVATE',
    'PRIVATE_CONTEXT',
    'PRIVATE_CONTROLS',
    'PRIVATE_ENTITY_PROFILE',
    'PRIVATE_ICLOUD_NOTE_INDEX',
    'PRIVATE_MEDIA_REVIEW',
    'PRIVATE_PATENT'
)

$vaultCategories = @()
foreach ($directory in Get-ChildItem -LiteralPath $resolvedVault -Directory -Force) {
    $isPrivate = (
        $directory.Name.StartsWith('PRIVATE', [System.StringComparison]::OrdinalIgnoreCase) -or
        $privateLabels -contains $directory.Name
    )
    $vaultCategories += Get-DirectorySummary `
        -Path $directory.FullName `
        -Label $directory.Name `
        -Privacy $(if ($isPrivate) { 'PRIVATE' } else { 'NON_PRIVATE_OR_MIXED' })
}

$selectedDriveRoots = @(
    'GLYPH_DRIVE',
    'INSTITUTIONAL_STACK_V2',
    'LumaModels',
    'LumaRuntime',
    'LumaValidationScratch',
    'LumenCoreSync'
)
$driveRoots = @()
foreach ($name in $selectedDriveRoots) {
    $path = Join-Path $resolvedDrive $name
    if (Test-Path -LiteralPath $path -PathType Container) {
        $driveRoots += Get-DirectorySummary -Path $path -Label $name
    }
}

$allVaultFiles = @(
    Get-ChildItem -LiteralPath $resolvedVault -Recurse -File -Force -ErrorAction SilentlyContinue
)
$potentialPrivateOutsidePrivateRoots = @(
    $allVaultFiles |
        Where-Object {
            $relative = $_.FullName.Substring($resolvedVault.Length + 1)
            $top = $relative.Split([IO.Path]::DirectorySeparatorChar)[0]
            $topIsPrivate = (
                $top.StartsWith('PRIVATE', [System.StringComparison]::OrdinalIgnoreCase) -or
                $privateLabels -contains $top
            )
            -not $topIsPrivate -and (
                $_.Name -match '(?i)(\.private\.|credential|secret|token|otp)' -or
                $_.FullName -match '(?i)\\private\\'
            )
        }
)

$runtimeLabels = @('PAPER_TRADING_RUNTIME', 'RUNTIME_MIRRORS', 'TEMP', 'TEST_TEMP', 'TOOLS')
$durableLabels = @(
    'CODE_RECEIPTS',
    'COORDINATION',
    'DEPLOYMENTS',
    'OPPORTUNITIES',
    'OUTREACH',
    'PROOF_STACK_RELEASES',
    'SUBMISSIONS',
    'VALIDATION'
)
$runtimeBytes = [int64]((
    $vaultCategories |
        Where-Object { $runtimeLabels -contains $_.label } |
        Measure-Object -Property bytes -Sum
).Sum)
$durableBytes = [int64]((
    $vaultCategories |
        Where-Object { $durableLabels -contains $_.label } |
        Measure-Object -Property bytes -Sum
).Sum)

$generatedUtc = (Get-Date).ToUniversalTime()
$stamp = $generatedUtc.ToString('yyyyMMddTHHmmssZ')
$reportDirectory = Join-Path $resolvedOutput "E_DRIVE_VALUE_INVENTORY_$stamp"
New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null

$inventory = [ordered]@{
    schema = 'lumencore.e_drive_value_inventory.v1'
    generated_utc = $generatedUtc.ToString('o')
    scope = [ordered]@{
        drive = $resolvedDrive
        vault = $resolvedVault
        method = 'metadata_only_no_file_content_export'
    }
    summary = [ordered]@{
        vault_category_count = $vaultCategories.Count
        selected_drive_root_count = $driveRoots.Count
        durable_proof_bytes = $durableBytes
        runtime_temp_tool_bytes = $runtimeBytes
        potential_private_artifacts_outside_private_roots = $potentialPrivateOutsidePrivateRoots.Count
        destructive_action_taken = $false
        private_filenames_exported = $false
    }
    priority_classes = @(
        [ordered]@{
            priority = 1
            class = 'VALIDATION_AND_PROOF_RELEASES'
            reason = 'Reviewer handoffs, reproducibility receipts, manifests, and frozen proof packets.'
        },
        [ordered]@{
            priority = 2
            class = 'CURRENT_SUBMISSIONS_AND_OPPORTUNITIES'
            reason = 'Deadline, authority, duplicate-send, and submission-state records.'
        },
        [ordered]@{
            priority = 3
            class = 'PRIVATE_LEGAL_AND_ENTITY_CONTROLS'
            reason = 'Patent, counsel, entity, and authorization records; keep access-restricted.'
        },
        [ordered]@{
            priority = 4
            class = 'DEPLOYMENT_AND_CODE_RECEIPTS'
            reason = 'Evidence of exact deployed or reviewed source state.'
        },
        [ordered]@{
            priority = 5
            class = 'RUNTIME_MODELS_AND_RAW_DATA'
            reason = 'Potentially reproducible inputs, but high-volume and not proof by themselves.'
        }
    )
    risks = @(
        [ordered]@{
            id = 'PRIVATE_MATERIAL_IN_MIXED_ROOTS'
            count = $potentialPrivateOutsidePrivateRoots.Count
            action = 'Review and relocate only after an explicit, separately approved custody plan; do not delete.'
        },
        [ordered]@{
            id = 'RUNTIME_VOLUME_DOMINATES_DURABLE_PROOF'
            runtime_temp_tool_gib = ConvertTo-GiB $runtimeBytes
            durable_proof_gib = ConvertTo-GiB $durableBytes
            action = 'Use retention tiers and manifests; do not equate file volume with evidentiary value.'
        },
        [ordered]@{
            id = 'DATED_PACKET_DUPLICATION'
            action = 'Designate current packets through a signed index rather than deleting historical custody records.'
        },
        [ordered]@{
            id = 'NON_GIT_MIRROR_ROOTS'
            action = 'Treat E-drive source copies as snapshots unless a manifest binds them to a Git commit.'
        }
    )
    vault_categories = @($vaultCategories | Sort-Object -Property bytes -Descending)
    selected_drive_roots = @($driveRoots | Sort-Object -Property bytes -Descending)
}

$jsonPath = Join-Path $reportDirectory 'E_DRIVE_VALUE_INVENTORY.json'
$markdownPath = Join-Path $reportDirectory 'E_DRIVE_VALUE_INVENTORY.md'
$inventory | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $jsonPath -Encoding utf8

$markdown = @(
    '# E-Drive Value Inventory'
    ''
    "- Generated UTC: $($generatedUtc.ToString('o'))"
    '- Method: metadata only; no private filenames or file contents exported'
    '- Destructive actions: none'
    ''
    '## Highest-Value Classes'
    ''
    '1. Validation and proof releases'
    '2. Current submissions and opportunities'
    '3. Private legal, patent, entity, and authorization controls'
    '4. Deployment and code receipts'
    '5. Runtime, models, and raw public data'
    ''
    '## Key Risks'
    ''
    "- Potential private artifacts outside private roots: $($potentialPrivateOutsidePrivateRoots.Count)"
    "- Runtime/temp/tool volume: $(ConvertTo-GiB $runtimeBytes) GiB"
    "- Durable proof-category volume: $(ConvertTo-GiB $durableBytes) GiB"
    '- Multiple dated packets require a current signed index; historical packets should not be deleted.'
    '- E-drive source copies without Git metadata require commit-bound mirror manifests.'
    ''
    '## Safest Next Actions'
    ''
    '1. Keep current opportunity and reviewer packets in non-destructive, timestamped, hash-manifested snapshots.'
    '2. Create one current index that points to canonical releases without erasing historical custody.'
    '3. Review mixed-root private artifacts under a separately approved custody plan.'
    '4. Apply retention tiers to runtime/temp data only after a reviewed retention policy.'
    ''
)
$markdown -join [Environment]::NewLine |
    Set-Content -LiteralPath $markdownPath -Encoding utf8

$manifest = @()
foreach ($path in @($jsonPath, $markdownPath)) {
    $item = Get-Item -LiteralPath $path
    $manifest += [ordered]@{
        file = $item.Name
        bytes = $item.Length
        sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$manifestPath = Join-Path $reportDirectory 'MANIFEST.json'
[ordered]@{
    schema = 'lumencore.e_drive_inventory_manifest.v1'
    generated_utc = $generatedUtc.ToString('o')
    files = $manifest
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8

[ordered]@{
    status = 'COMPLETE'
    report_directory = $reportDirectory
    potential_private_artifacts_outside_private_roots = $potentialPrivateOutsidePrivateRoots.Count
    runtime_temp_tool_gib = ConvertTo-GiB $runtimeBytes
    durable_proof_gib = ConvertTo-GiB $durableBytes
} | ConvertTo-Json -Depth 3
