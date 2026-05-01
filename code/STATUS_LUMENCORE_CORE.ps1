$ErrorActionPreference = 'Stop'

$Root = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2'
$Code = Join-Path $Root 'code'
$Out = Join-Path $Root 'out'
$Dash = 'C:\LumaTrader\dashboard'

function Get-ServiceKey {
    param([string]$CommandLine)

    if ($CommandLine -like '*dashboard_unified_refresh.py*') { return 'dashboard_loop' }
    if ($CommandLine -like '*sector_opp_gain_server*') { return 'sector_api' }
    if ($CommandLine -like '*build_infra_audit_dashboard.py*') { return 'infra_loop' }
    if ($CommandLine -like '*alpaca_paper_loop_builder.py*' -or $CommandLine -like '*RUN_ALPACA_PAPER_247.ps1*') { return 'paper_trader' }
    return $null
}

function Get-LogicalServices {
    $allProcesses = Get-CimInstance Win32_Process
    $pythonHits = $allProcesses | Where-Object {
        $_.Name -like 'python*' -and (
            $_.CommandLine -like '*dashboard_unified_refresh.py*' -or
            $_.CommandLine -like '*alpaca_paper_loop_builder.py*' -or
            $_.CommandLine -like '*sector_opp_gain_server*' -or
            $_.CommandLine -like '*build_infra_audit_dashboard.py*'
        )
    }
    $powerShellHits = $allProcesses | Where-Object {
        ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and $_.CommandLine -like '*RUN_ALPACA_PAPER_247.ps1*'
    }

    $hits = @($pythonHits + $powerShellHits)
    $serviceByPid = @{}
    foreach ($proc in $hits) {
        $serviceKey = Get-ServiceKey -CommandLine $proc.CommandLine
        if ($serviceKey) {
            $serviceByPid[[string]$proc.ProcessId] = $serviceKey
        }
    }

    foreach ($proc in $hits) {
        $serviceKey = Get-ServiceKey -CommandLine $proc.CommandLine
        if (-not $serviceKey) { continue }

        $parentKey = $serviceByPid[[string]$proc.ParentProcessId]
        if ($parentKey -eq $serviceKey) { continue }

        $related = @($hits | Where-Object { (Get-ServiceKey -CommandLine $_.CommandLine) -eq $serviceKey })
        [PSCustomObject]@{
            Service = $serviceKey
            Running = $true
            RootPid = $proc.ProcessId
            ProcessCount = $related.Count
            CommandLine = $proc.CommandLine
        }
    }
}

function Get-ArtifactStatus {
    param(
        [string]$Label,
        [string]$Path
    )

    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        Artifact = $Label
        Exists = ($null -ne $item)
        LastWriteUtc = $(if ($item) { $item.LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ') } else { '' })
        Path = $Path
    }
}

$services = @(Get-LogicalServices)
$expectedServices = @('dashboard_loop', 'sector_api', 'infra_loop', 'paper_trader')
$serviceRows = foreach ($name in $expectedServices) {
    $row = $services | Where-Object { $_.Service -eq $name } | Select-Object -First 1
    if ($row) {
        $row
    } else {
        [PSCustomObject]@{
            Service = $name
            Running = $false
            RootPid = $null
            ProcessCount = 0
            CommandLine = ''
        }
    }
}

$artifacts = @(
    (Get-ArtifactStatus -Label 'master_dashboard' -Path (Join-Path $Dash 'LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html')),
    (Get-ArtifactStatus -Label 'paper_dashboard' -Path (Join-Path $Dash 'alpaca_paper_live_dashboard.html')),
    (Get-ArtifactStatus -Label 'infra_dashboard' -Path (Join-Path $Dash 'infra_institutional_live_dashboard.html')),
    (Get-ArtifactStatus -Label 'advanced_validation' -Path (Join-Path $Dash 'advanced_fleet_validation.html')),
    (Get-ArtifactStatus -Label 'lane_audit' -Path (Join-Path $Dash 'lane_separation_audit.html')),
    (Get-ArtifactStatus -Label 'lumascout_dashboard' -Path (Join-Path $Dash 'lumascout_dashboard.html')),
    (Get-ArtifactStatus -Label 'gov_summary' -Path (Join-Path $Out 'gov_live_canonical_summary.json')),
    (Get-ArtifactStatus -Label 'advanced_validation_json' -Path (Join-Path $Out 'advanced_fleet_validation.json')),
    (Get-ArtifactStatus -Label 'lane_audit_json' -Path (Join-Path $Out 'lane_separation_audit.json')),
    (Get-ArtifactStatus -Label 'chain_of_custody' -Path (Join-Path $Out 'unified_dashboard_chain_of_custody_sha256.json'))
)

Write-Host '=== LumenCore Core Services ==='
$serviceRows | Sort-Object Service | Format-List

Write-Host ''
Write-Host '=== LumenCore Core Artifacts ==='
$artifacts | Format-Table -AutoSize