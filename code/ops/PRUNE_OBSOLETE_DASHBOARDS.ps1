param(
    [string]$RootDashboardPath = "C:\LumaTrader\dashboard",
    [string]$StackDashboardPath = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\dashboard",
    [string]$OutputRoot = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops",
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

$liveFiles = @(
    'index.html',
    'dashboard_portal.html',
    'LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html',
    'combined_master_dashboard.html',
    'alpaca_paper_live_dashboard.html',
    'infra_institutional_live_dashboard.html',
    'lumascout_dashboard.html',
    'luma_experience.html',
    'advanced_fleet_validation.html',
    'lane_separation_audit.html',
    'mission_control.html',
    'quant_lab.html',
    'investor_command_room.html',
    'investor_wallboard.html',
    'grants.html',
    'kraken_execution_dashboard.html',
    'scenario_mission.html',
    'staleness_command_center.html',
    'harmonic_proofpack_mission.html',
    'nobel_tier_command_center.html',
    'audit_derivation_pack.html',
    'live_source_registry.html',
    'live_audit_readout.html',
    'hard_truth_live_measurement_audit.html',
    'seed_validation_readout.html',
    'privacy.html',
    'terms.html',
    'explain.html',
    'forecast.html'
)

$liveSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($f in $liveFiles) {
    [void]$liveSet.Add($f)
}

if (-not (Test-Path -LiteralPath $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

$archiveRows = New-Object System.Collections.Generic.List[object]
$syncRows = New-Object System.Collections.Generic.List[object]

function Ensure-Parent {
    param([string]$Path)
    $parent = Split-Path -Path $Path -Parent
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function Get-HashSafe {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return ''
    }
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

$dashboardRoots = @(
    [PSCustomObject]@{ Name = 'root'; Path = $RootDashboardPath },
    [PSCustomObject]@{ Name = 'stack'; Path = $StackDashboardPath }
)

foreach ($root in $dashboardRoots) {
    if (-not (Test-Path -LiteralPath $root.Path)) {
        continue
    }

    $archiveDir = Join-Path $root.Path ("archive\obsolete_live_cleanup_{0}" -f $stamp)
    if (-not $WhatIf) {
        New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
    }

    $htmlFiles = Get-ChildItem -Path $root.Path -File -Filter '*.html' -ErrorAction SilentlyContinue
    foreach ($file in $htmlFiles) {
        if ($liveSet.Contains($file.Name)) {
            continue
        }

        $target = Join-Path $archiveDir $file.Name
        $action = if ($WhatIf) { 'would_archive' } else { 'archived' }

        if (-not $WhatIf) {
            Move-Item -Path $file.FullName -Destination $target -Force
        }

        $archiveRows.Add([PSCustomObject]@{
            generated_utc = (Get-Date).ToUniversalTime().ToString('o')
            scope = $root.Name
            file = $file.Name
            source_path = $file.FullName
            archive_path = $target
            action = $action
            size_bytes = $file.Length
            last_write_utc = $file.LastWriteTimeUtc.ToString('o')
        }) | Out-Null
    }
}

foreach ($name in $liveFiles) {
    $rootFile = Join-Path $RootDashboardPath $name
    $stackFile = Join-Path $StackDashboardPath $name

    $rootExists = Test-Path -LiteralPath $rootFile
    $stackExists = Test-Path -LiteralPath $stackFile

    if ($rootExists -and -not $stackExists) {
        $action = if ($WhatIf) { 'would_copy_root_to_stack' } else { 'copy_root_to_stack' }
        if (-not $WhatIf) {
            Ensure-Parent -Path $stackFile
            Copy-Item -Path $rootFile -Destination $stackFile -Force
        }
        $syncRows.Add([PSCustomObject]@{ file = $name; action = $action; source = $rootFile; destination = $stackFile }) | Out-Null
        continue
    }

    if ($stackExists -and -not $rootExists) {
        $action = if ($WhatIf) { 'would_copy_stack_to_root' } else { 'copy_stack_to_root' }
        if (-not $WhatIf) {
            Ensure-Parent -Path $rootFile
            Copy-Item -Path $stackFile -Destination $rootFile -Force
        }
        $syncRows.Add([PSCustomObject]@{ file = $name; action = $action; source = $stackFile; destination = $rootFile }) | Out-Null
        continue
    }

    if ($rootExists -and $stackExists) {
        $rootHash = Get-HashSafe -Path $rootFile
        $stackHash = Get-HashSafe -Path $stackFile

        if ($rootHash -ne $stackHash) {
            $rootTs = (Get-Item -LiteralPath $rootFile).LastWriteTimeUtc
            $stackTs = (Get-Item -LiteralPath $stackFile).LastWriteTimeUtc

            if ($rootTs -ge $stackTs) {
                $action = if ($WhatIf) { 'would_sync_root_to_stack' } else { 'sync_root_to_stack' }
                if (-not $WhatIf) {
                    Copy-Item -Path $rootFile -Destination $stackFile -Force
                }
                $syncRows.Add([PSCustomObject]@{ file = $name; action = $action; source = $rootFile; destination = $stackFile }) | Out-Null
            }
            else {
                $action = if ($WhatIf) { 'would_sync_stack_to_root' } else { 'sync_stack_to_root' }
                if (-not $WhatIf) {
                    Copy-Item -Path $stackFile -Destination $rootFile -Force
                }
                $syncRows.Add([PSCustomObject]@{ file = $name; action = $action; source = $stackFile; destination = $rootFile }) | Out-Null
            }
        }
    }
}

$summary = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    scope = 'dashboard_live_cleanup'
    what_if = [bool]$WhatIf
    root_dashboard = $RootDashboardPath
    stack_dashboard = $StackDashboardPath
    live_allowlist_count = $liveFiles.Count
    archived_count = $archiveRows.Count
    sync_action_count = $syncRows.Count
    archived = $archiveRows
    sync_actions = $syncRows
}

$jsonPath = Join-Path $OutputRoot ("dashboard_live_cleanup_{0}.json" -f $stamp)
$latestPath = Join-Path $OutputRoot 'dashboard_live_cleanup_latest.json'
$mdPath = Join-Path $OutputRoot ("dashboard_live_cleanup_{0}.md" -f $stamp)
$mdLatest = Join-Path $OutputRoot 'dashboard_live_cleanup_latest.md'

$summaryJson = $summary | ConvertTo-Json -Depth 8
Set-Content -Path $jsonPath -Value $summaryJson -Encoding utf8
Set-Content -Path $latestPath -Value $summaryJson -Encoding utf8

$lines = @()
$lines += '# Dashboard Live Cleanup'
$lines += "Generated UTC: $($summary.generated_utc)"
$lines += "WhatIf: $($summary.what_if)"
$lines += ""
$lines += "- Live allowlist count: $($summary.live_allowlist_count)"
$lines += "- Archived count: $($summary.archived_count)"
$lines += "- Sync actions: $($summary.sync_action_count)"
$lines += ""
$lines += '## Archived Files'
$lines += ''
if ($archiveRows.Count -eq 0) {
    $lines += '- none'
}
else {
    foreach ($row in $archiveRows) {
        $lines += "- [$($row.scope)] $($row.file) -> $($row.archive_path)"
    }
}
$lines += ''
$lines += '## Sync Actions'
$lines += ''
if ($syncRows.Count -eq 0) {
    $lines += '- none'
}
else {
    foreach ($row in $syncRows) {
        $lines += "- $($row.file): $($row.action)"
    }
}

$md = ($lines -join [Environment]::NewLine)
Set-Content -Path $mdPath -Value $md -Encoding utf8
Set-Content -Path $mdLatest -Value $md -Encoding utf8

Write-Output "LIVE_CLEANUP_JSON=$jsonPath"
Write-Output "LIVE_CLEANUP_LATEST=$latestPath"
Write-Output "LIVE_CLEANUP_MD=$mdPath"
Write-Output "ARCHIVED=$($archiveRows.Count) SYNCED=$($syncRows.Count)"
