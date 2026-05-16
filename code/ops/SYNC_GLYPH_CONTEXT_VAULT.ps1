param(
    [string]$GlyphRoot = 'E:\GLYPH_DRIVE',
    [string]$VaultName = 'Luma_Context_Vault',
    [string]$WorkspaceRoot = 'C:\LumaTrader',
    [string]$ICloudRoot = 'C:\Users\Novac\iCloudDrive',
    [string]$ContextScanRoot = 'C:\LumaTrader\out\ops\context_scan_20260510_200619',
    [string]$MemoryExportRoot = 'C:\LumaTrader\out\ops\copilot_memory_export_latest',
    [string]$CopilotSessionContextRoot = 'C:\LumaTrader\out\ops\copilot_session_context_latest',
    [string]$CopilotPromptsRoot = 'C:\Users\Novac\AppData\Roaming\Code\User\prompts',
    [string]$NodeRedUserRoot = 'C:\Users\Novac\.node-red',
    [string]$NodeRedInstallRoot = 'C:\Users\Novac\AppData\Roaming\npm\node_modules\node-red',
    [string]$UnityLumaExperienceRoot = 'C:\LumaTrader\LumaExperience',
    [string]$NodeRedStackFlowRoot = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\node_red',
    [string]$FrozenDeltaOutRoot = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out',
    [switch]$WhatIfOnly,
    [switch]$ApplyHardlinkDedupe,
    [int]$HashLimitMB = 64,
    [int]$RoboCopyThreads = 16,
    [int]$MaxDedupeCandidates = 200000
)

$ErrorActionPreference = 'Stop'

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Normalize-SourceName {
    param([string]$Raw)
    $safe = ($Raw -replace '[^A-Za-z0-9._-]', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return 'source'
    }
    return $safe.ToLowerInvariant()
}

function Invoke-RoboSync {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [Parameter(Mandatory = $true)][string]$LogPath,
        [switch]$ListOnly,
        [int]$Threads = 16
    )

    Ensure-Directory -Path $DestinationPath

    $excludeDirs = @(
        '.git',
        'node_modules',
        '__pycache__',
        '.mypy_cache',
        '.pytest_cache',
        '.ruff_cache',
        '.venv',
        'venv',
        'venv3.11',
        'env',
        'env311',
        'site-packages',
        '.next',
        'dist',
        'build',
        '.idea',
        '.vs'
    )

    $args = @(
        $SourcePath,
        $DestinationPath,
        '/E',
        '/Z',
        '/FFT',
        '/COPY:DAT',
        '/DCOPY:DAT',
        '/R:1',
        '/W:1',
        '/XJ',
        "/MT:$Threads",
        '/XO',
        '/NP',
        '/NFL',
        '/NDL',
        "/LOG+:$LogPath"
    )

    if ($ListOnly) {
        $args += '/L'
    }

    if ($excludeDirs.Count -gt 0) {
        $args += '/XD'
        $args += $excludeDirs
    }

    $prevErrorAction = $ErrorActionPreference
    $hadNativePref = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue)
    $prevNativePref = $false
    if ($hadNativePref) {
        $prevNativePref = [bool]$Global:PSNativeCommandUseErrorActionPreference
        $Global:PSNativeCommandUseErrorActionPreference = $false
    }

    $ErrorActionPreference = 'Continue'
    try {
        & robocopy @args
    }
    finally {
        $ErrorActionPreference = $prevErrorAction
        if ($hadNativePref) {
            $Global:PSNativeCommandUseErrorActionPreference = $prevNativePref
        }
    }

    $code = [int]$LASTEXITCODE

    return [PSCustomObject]@{
        robocopy_exit_code = $code
        success = ($code -lt 8)
        list_only = [bool]$ListOnly
    }
}

function Get-Sha256Safe {
    param([string]$Path)
    try {
        return (Get-FileHash -Path $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
    }
    catch {
        return ''
    }
}

function Build-FileIndex {
    param(
        [Parameter(Mandatory = $true)][string]$SourcesRoot,
        [Parameter(Mandatory = $true)][string]$RunDir,
        [long]$HashLimitBytes = 67108864
    )

    $indexCsv = Join-Path $RunDir 'vault_file_index.csv'
    $summaryJson = Join-Path $RunDir 'vault_file_index_summary.json'

    $rows = New-Object System.Collections.Generic.List[object]
    $sourceCounts = @{}
    $extCounts = @{}

    $files = Get-ChildItem -Path $SourcesRoot -Recurse -File -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        $relative = $f.FullName.Substring($SourcesRoot.Length).TrimStart([char]'\', [char]'/')
        $parts = $relative -split '[\\/]'
        $sourceSlot = if ($parts.Count -gt 0) { $parts[0] } else { 'unknown' }
        $ext = [string]$f.Extension

        if (-not $sourceCounts.ContainsKey($sourceSlot)) { $sourceCounts[$sourceSlot] = 0 }
        $sourceCounts[$sourceSlot] = [int]$sourceCounts[$sourceSlot] + 1

        if (-not $extCounts.ContainsKey($ext)) { $extCounts[$ext] = 0 }
        $extCounts[$ext] = [int]$extCounts[$ext] + 1

        $sha = ''
        if ([long]$f.Length -le $HashLimitBytes) {
            $sha = Get-Sha256Safe -Path $f.FullName
        }

        $rows.Add([PSCustomObject]@{
            source_slot = $sourceSlot
            relative_path = $relative
            full_path = $f.FullName
            size_bytes = [long]$f.Length
            last_write_utc = $f.LastWriteTimeUtc.ToString('o')
            extension = $ext
            sha256_if_small = $sha
        })
    }

    $rows | Export-Csv -Path $indexCsv -NoTypeInformation -Encoding UTF8

    $summary = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString('o')
        sources_root = $SourcesRoot
        hash_limit_bytes = [long]$HashLimitBytes
        total_files = $rows.Count
        by_source_slot = $sourceCounts
        by_extension = $extCounts
        file_index_csv = $indexCsv
    }

    $summary | ConvertTo-Json -Depth 12 | Set-Content -Path $summaryJson -Encoding UTF8

    return [PSCustomObject]@{
        file_index_csv = $indexCsv
        summary_json = $summaryJson
        total_files = $rows.Count
    }
}

function Build-DuplicateAudit {
    param(
        [Parameter(Mandatory = $true)][string]$IndexCsv,
        [Parameter(Mandatory = $true)][string]$RunDir,
        [switch]$ApplyHardlinks,
        [switch]$ListOnly,
        [int]$MaxRows = 200000
    )

    $dupeCsv = Join-Path $RunDir 'vault_duplicate_audit.csv'
    $dupeJson = Join-Path $RunDir 'vault_duplicate_audit_summary.json'

    $rows = Import-Csv -Path $IndexCsv
    $smallRows = @($rows | Where-Object { -not [string]::IsNullOrWhiteSpace($_.sha256_if_small) })

    if ($smallRows.Count -gt $MaxRows) {
        $smallRows = @($smallRows | Select-Object -First $MaxRows)
    }

    $groups = $smallRows | Group-Object sha256_if_small | Where-Object { $_.Count -gt 1 }

    $auditRows = New-Object System.Collections.Generic.List[object]
    $hardlinkApplied = 0
    $hardlinkFailed = 0

    foreach ($g in $groups) {
        $ordered = @($g.Group | Sort-Object full_path)
        if ($ordered.Count -lt 2) { continue }

        $canonical = $ordered[0]
        for ($i = 1; $i -lt $ordered.Count; $i++) {
            $dup = $ordered[$i]
            $action = 'indexed_only'
            $detail = ''

            if ($ApplyHardlinks -and -not $ListOnly) {
                try {
                    if (Test-Path -LiteralPath $dup.full_path) {
                        Remove-Item -LiteralPath $dup.full_path -Force
                        & fsutil hardlink create $dup.full_path $canonical.full_path | Out-Null
                        if ($LASTEXITCODE -eq 0) {
                            $action = 'hardlinked'
                            $hardlinkApplied++
                        }
                        else {
                            $action = 'hardlink_failed'
                            $detail = "fsutil_exit=$LASTEXITCODE"
                            $hardlinkFailed++
                        }
                    }
                    else {
                        $action = 'missing_before_hardlink'
                    }
                }
                catch {
                    $action = 'hardlink_failed'
                    $detail = $_.Exception.Message
                    $hardlinkFailed++
                }
            }

            $auditRows.Add([PSCustomObject]@{
                sha256 = $g.Name
                canonical_path = $canonical.full_path
                duplicate_path = $dup.full_path
                size_bytes = [long]$dup.size_bytes
                action = $action
                detail = $detail
            })
        }
    }

    $auditRows | Export-Csv -Path $dupeCsv -NoTypeInformation -Encoding UTF8

    $summary = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString('o')
        indexed_rows_with_hash = $smallRows.Count
        duplicate_groups = $groups.Count
        duplicate_rows = $auditRows.Count
        apply_hardlinks = [bool]$ApplyHardlinks
        list_only = [bool]$ListOnly
        hardlinks_applied = $hardlinkApplied
        hardlinks_failed = $hardlinkFailed
        duplicate_audit_csv = $dupeCsv
    }

    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $dupeJson -Encoding UTF8

    return [PSCustomObject]@{
        duplicate_audit_csv = $dupeCsv
        summary_json = $dupeJson
        duplicate_rows = $auditRows.Count
        hardlinks_applied = $hardlinkApplied
        hardlinks_failed = $hardlinkFailed
    }
}

if (-not (Test-Path -LiteralPath $GlyphRoot)) {
    throw "Glyph root does not exist: $GlyphRoot"
}

$vaultRoot = Join-Path $GlyphRoot $VaultName
$sourcesRoot = Join-Path $vaultRoot 'sources'
$opsRoot = Join-Path $vaultRoot 'ops'
$runId = Get-UtcStamp
$runDir = Join-Path $opsRoot (Join-Path 'sync_runs' $runId)
$copyLog = Join-Path $runDir 'robocopy.log'
$sourceSummaryCsv = Join-Path $runDir 'source_copy_summary.csv'
$summaryJson = Join-Path $runDir 'glyph_sync_summary.json'
$ledgerTxt = Join-Path $runDir 'glyph_sync_chain_of_custody.sha256.txt'
$latestJson = Join-Path $vaultRoot 'glyph_sync_latest.json'

$hashLimitBytes = [long]$HashLimitMB * 1024L * 1024L

if (-not $WhatIfOnly) {
    Ensure-Directory -Path $runDir
    Ensure-Directory -Path $sourcesRoot
}
else {
    Ensure-Directory -Path $runDir
}

$sourceSpecs = @(
    [PSCustomObject]@{ name = 'lumatrader_workspace'; path = $WorkspaceRoot },
    [PSCustomObject]@{ name = 'icloud_drive'; path = $ICloudRoot },
    [PSCustomObject]@{ name = 'context_scan_baseline'; path = $ContextScanRoot },
    [PSCustomObject]@{ name = 'copilot_memory_export'; path = $MemoryExportRoot },
    [PSCustomObject]@{ name = 'copilot_session_context'; path = $CopilotSessionContextRoot },
    [PSCustomObject]@{ name = 'copilot_prompts'; path = $CopilotPromptsRoot },
    [PSCustomObject]@{ name = 'nodered_user_home'; path = $NodeRedUserRoot },
    [PSCustomObject]@{ name = 'nodered_install'; path = $NodeRedInstallRoot },
    [PSCustomObject]@{ name = 'unity_luma_experience'; path = $UnityLumaExperienceRoot },
    [PSCustomObject]@{ name = 'nodered_stack_flows'; path = $NodeRedStackFlowRoot },
    [PSCustomObject]@{ name = 'frozen_delta_out'; path = $FrozenDeltaOutRoot }
)

$copyRows = New-Object System.Collections.Generic.List[object]

foreach ($src in $sourceSpecs) {
    $srcPath = [string]$src.path
    $srcName = Normalize-SourceName -Raw ([string]$src.name)
    $destPath = Join-Path $sourcesRoot $srcName
    $exists = Test-Path -LiteralPath $srcPath

    $started = (Get-Date).ToUniversalTime().ToString('o')
    $robocopyCode = -1
    $ok = $false
    $message = ''

    if (-not $exists) {
        $message = 'source_missing'
    }
    else {
        $result = Invoke-RoboSync -SourcePath $srcPath -DestinationPath $destPath -LogPath $copyLog -ListOnly:$WhatIfOnly -Threads $RoboCopyThreads
        $robocopyCode = [int]$result.robocopy_exit_code
        $ok = [bool]$result.success
        $message = if ($ok) { 'ok' } else { 'robocopy_error' }
    }

    $ended = (Get-Date).ToUniversalTime().ToString('o')

    $copyRows.Add([PSCustomObject]@{
        source_name = $srcName
        source_path = $srcPath
        source_exists = [bool]$exists
        destination_path = $destPath
        started_utc = $started
        ended_utc = $ended
        robocopy_exit_code = $robocopyCode
        success = [bool]$ok
        message = $message
        list_only = [bool]$WhatIfOnly
    })
}

$copyRows | Export-Csv -Path $sourceSummaryCsv -NoTypeInformation -Encoding UTF8

$indexResult = $null
$dupeResult = $null

if (-not $WhatIfOnly) {
    $indexResult = Build-FileIndex -SourcesRoot $sourcesRoot -RunDir $runDir -HashLimitBytes $hashLimitBytes
    $dupeResult = Build-DuplicateAudit -IndexCsv $indexResult.file_index_csv -RunDir $runDir -ApplyHardlinks:$ApplyHardlinkDedupe -ListOnly:$WhatIfOnly -MaxRows $MaxDedupeCandidates
}

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    glyph_root = $GlyphRoot
    vault_root = $vaultRoot
    run_id = $runId
    run_dir = $runDir
    what_if_only = [bool]$WhatIfOnly
    apply_hardlink_dedupe = [bool]$ApplyHardlinkDedupe
    hash_limit_mb = $HashLimitMB
    source_copy_summary_csv = $sourceSummaryCsv
    robocopy_log = $copyLog
    sources_total = $copyRows.Count
    sources_present = @($copyRows | Where-Object { $_.source_exists }).Count
    sources_success = @($copyRows | Where-Object { $_.success }).Count
    sources_failed = @($copyRows | Where-Object { $_.source_exists -and -not $_.success }).Count
    index = if ($indexResult) { $indexResult } else { $null }
    duplicates = if ($dupeResult) { $dupeResult } else { $null }
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryJson -Encoding UTF8

$artifacts = @($sourceSummaryCsv, $summaryJson, $copyLog)
if ($indexResult) {
    $artifacts += $indexResult.file_index_csv
    $artifacts += $indexResult.summary_json
}
if ($dupeResult) {
    $artifacts += $dupeResult.duplicate_audit_csv
    $artifacts += $dupeResult.summary_json
}

$ledgerLines = New-Object System.Collections.Generic.List[string]
$ledgerLines.Add("generated_utc=$((Get-Date).ToUniversalTime().ToString('o'))")
$ledgerLines.Add("run_dir=$runDir")
foreach ($a in $artifacts) {
    if (Test-Path -LiteralPath $a) {
        $h = Get-Sha256Safe -Path $a
        $ledgerLines.Add("artifact=$a")
        $ledgerLines.Add("sha256=$h")
    }
}
$ledgerLines | Set-Content -Path $ledgerTxt -Encoding UTF8

$latest = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    run_id = $runId
    run_dir = $runDir
    summary_json = $summaryJson
    chain_of_custody_sha256 = $ledgerTxt
    what_if_only = [bool]$WhatIfOnly
    apply_hardlink_dedupe = [bool]$ApplyHardlinkDedupe
}
$latest | ConvertTo-Json -Depth 8 | Set-Content -Path $latestJson -Encoding UTF8

Write-Output "[GLYPH_SYNC] vault_root=$vaultRoot"
Write-Output "[GLYPH_SYNC] run_dir=$runDir"
Write-Output "[GLYPH_SYNC] summary_json=$summaryJson"
Write-Output "[GLYPH_SYNC] source_copy_summary_csv=$sourceSummaryCsv"
Write-Output "[GLYPH_SYNC] chain_of_custody_sha256=$ledgerTxt"
if ($indexResult) {
    Write-Output "[GLYPH_SYNC] file_index_csv=$($indexResult.file_index_csv)"
}
if ($dupeResult) {
    Write-Output "[GLYPH_SYNC] duplicate_audit_csv=$($dupeResult.duplicate_audit_csv)"
}
