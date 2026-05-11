param(
    [string]$DestinationRoot = 'C:\LumaTrader\premium_packages_mirror',
    [int]$LatestZipCountFromProofs = 40,
    [int]$HashLimitMB = 64,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = 'Stop'

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
}

function Get-FileHashSafe {
    param(
        [string]$Path,
        [long]$Length,
        [long]$HashLimitBytes
    )

    if ($Length -gt $HashLimitBytes) {
        return ''
    }

    try {
        return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
    } catch {
        return ''
    }
}

function Collect-ProofFileSet {
    param(
        [string]$SourcePath,
        [int]$LatestZipCount
    )

    $files = New-Object 'System.Collections.Generic.List[System.IO.FileInfo]'

    $patterns = @(
        '*.txt', '*.md', '*.csv', '*.json', '*.jsonl', '*.sha256.txt', '*.manifest.txt'
    )

    foreach ($pattern in $patterns) {
        Get-ChildItem -Path $SourcePath -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            $files.Add($_)
        }
    }

    Get-ChildItem -Path $SourcePath -Recurse -File -Filter '*.zip' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First $LatestZipCount |
        ForEach-Object { $files.Add($_) }

    return @($files | Sort-Object FullName -Unique)
}

$sourceSpecs = @(
    @{ Name = 'whitehole_proofs'; Path = 'C:\WhiteHole\proofs'; Mode = 'proofs' },
    @{ Name = 'whiteholelab_universe_out'; Path = 'C:\WhiteHoleLab\universe_out'; Mode = 'full' },
    @{ Name = 'whiteholelab_lumenweb_site'; Path = 'C:\WhiteHoleLab\LumenWeb\site'; Mode = 'full' },
    @{ Name = 'whitehole_hypercore_validation'; Path = 'C:\WhiteHole\HyperCore_Validation'; Mode = 'full' },
    @{ Name = 'whitehole_identity_lock'; Path = 'C:\WhiteHole\IdentityArchitecture_Lock'; Mode = 'full' },
    @{ Name = 'whitehole_federal_ask'; Path = 'C:\WhiteHole\federal_ask'; Mode = 'full' },
    @{ Name = 'whitehole_federal_outreach'; Path = 'C:\WhiteHole\federal_outreach'; Mode = 'full' }
)

$ts = Get-UtcStamp
$runDir = Join-Path $DestinationRoot (Join-Path '_mirror_runs' $ts)
$hashLimitBytes = [long]$HashLimitMB * 1024L * 1024L

if (-not $WhatIfOnly) {
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
}

$manifest = New-Object 'System.Collections.Generic.List[object]'
$summary = New-Object 'System.Collections.Generic.List[object]'

foreach ($spec in $sourceSpecs) {
    $sourcePath = [string]$spec.Path
    $sourceName = [string]$spec.Name
    $mode = [string]$spec.Mode

    if (-not (Test-Path $sourcePath)) {
        $summary.Add([PSCustomObject]@{
            source = $sourceName
            source_path = $sourcePath
            mode = $mode
            exists = $false
            files_seen = 0
            files_copied = 0
            bytes_total = 0
        })
        continue
    }

    $files = @()
    if ($mode -eq 'proofs') {
        $files = Collect-ProofFileSet -SourcePath $sourcePath -LatestZipCount $LatestZipCountFromProofs
    } else {
        $files = Get-ChildItem -Path $sourcePath -Recurse -File -ErrorAction SilentlyContinue
    }

    $destBase = Join-Path $DestinationRoot $sourceName
    if (-not $WhatIfOnly) {
        New-Item -ItemType Directory -Force -Path $destBase | Out-Null
    }

    $filesSeen = 0
    $filesCopied = 0
    $bytesTotal = 0L

    foreach ($file in $files) {
        $filesSeen += 1
        $bytesTotal += [long]$file.Length

        $relative = $file.FullName.Substring($sourcePath.Length).TrimStart([char]'\', [char]'/')
        $destPath = Join-Path $destBase $relative
        $destDir = Split-Path -Parent $destPath

        $copyNeeded = $true
        if (Test-Path $destPath) {
            try {
                $destInfo = Get-Item $destPath -ErrorAction Stop
                if ($destInfo.Length -eq $file.Length -and $destInfo.LastWriteTimeUtc -eq $file.LastWriteTimeUtc) {
                    $copyNeeded = $false
                }
            } catch {
                $copyNeeded = $true
            }
        }

        if ($copyNeeded -and -not $WhatIfOnly) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
            Copy-Item -Path $file.FullName -Destination $destPath -Force
            try {
                (Get-Item $destPath).LastWriteTimeUtc = $file.LastWriteTimeUtc
            } catch {
                # Keep default timestamp if assignment fails.
            }
            $filesCopied += 1
        }

        $sha256 = Get-FileHashSafe -Path $file.FullName -Length ([long]$file.Length) -HashLimitBytes $hashLimitBytes

        $manifest.Add([PSCustomObject]@{
            source = $sourceName
            source_path = $sourcePath
            destination_path = $destPath
            relative_path = $relative
            size_bytes = [long]$file.Length
            last_write_utc = $file.LastWriteTimeUtc.ToString('o')
            copied_this_run = [bool]$copyNeeded
            sha256_if_small = $sha256
        })
    }

    $summary.Add([PSCustomObject]@{
        source = $sourceName
        source_path = $sourcePath
        mode = $mode
        exists = $true
        files_seen = $filesSeen
        files_copied = $filesCopied
        bytes_total = $bytesTotal
    })
}

if ($WhatIfOnly) {
    Write-Output '[SYNC_PREMIUM] WhatIfOnly enabled. No files copied.'
    $summary | Format-Table -AutoSize
    exit 0
}

$manifestCsv = Join-Path $runDir 'premium_package_manifest.csv'
$summaryJson = Join-Path $runDir 'premium_package_summary.json'
$summaryCsv = Join-Path $runDir 'premium_package_summary.csv'
$ledgerTxt = Join-Path $runDir 'premium_package_chain_of_custody.sha256.txt'
$latestJson = Join-Path $DestinationRoot 'premium_package_mirror_latest.json'

$manifest | Export-Csv -Path $manifestCsv -NoTypeInformation -Encoding UTF8
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryJson -Encoding UTF8
$summary | Export-Csv -Path $summaryCsv -NoTypeInformation -Encoding UTF8

$manifestHash = (Get-FileHash -Algorithm SHA256 -Path $manifestCsv).Hash.ToLowerInvariant()
$summaryHash = (Get-FileHash -Algorithm SHA256 -Path $summaryJson).Hash.ToLowerInvariant()
$summaryCsvHash = (Get-FileHash -Algorithm SHA256 -Path $summaryCsv).Hash.ToLowerInvariant()

@(
    "generated_utc=$((Get-Date).ToUniversalTime().ToString('o'))",
    "manifest_csv=$manifestCsv",
    "manifest_csv_sha256=$manifestHash",
    "summary_json=$summaryJson",
    "summary_json_sha256=$summaryHash",
    "summary_csv=$summaryCsv",
    "summary_csv_sha256=$summaryCsvHash"
) | Set-Content -Path $ledgerTxt -Encoding UTF8

$latest = [PSCustomObject]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    destination_root = $DestinationRoot
    run_dir = $runDir
    manifest_csv = $manifestCsv
    summary_json = $summaryJson
    summary_csv = $summaryCsv
    chain_of_custody_sha256 = $ledgerTxt
    total_sources = $summary.Count
    total_files_seen = ($summary | Measure-Object -Property files_seen -Sum).Sum
    total_files_copied = ($summary | Measure-Object -Property files_copied -Sum).Sum
    total_bytes_seen = ($summary | Measure-Object -Property bytes_total -Sum).Sum
    hash_limit_mb = $HashLimitMB
    latest_zip_count_from_proofs = $LatestZipCountFromProofs
}

$latest | ConvertTo-Json -Depth 8 | Set-Content -Path $latestJson -Encoding UTF8

Write-Output "[SYNC_PREMIUM] destination_root=$DestinationRoot"
Write-Output "[SYNC_PREMIUM] run_dir=$runDir"
Write-Output "[SYNC_PREMIUM] files_seen=$($latest.total_files_seen) files_copied=$($latest.total_files_copied)"
Write-Output "[SYNC_PREMIUM] manifest_csv=$manifestCsv"
Write-Output "[SYNC_PREMIUM] summary_json=$summaryJson"
Write-Output "[SYNC_PREMIUM] chain_of_custody_sha256=$ledgerTxt"
