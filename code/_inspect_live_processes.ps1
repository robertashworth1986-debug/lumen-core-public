$ErrorActionPreference = 'Stop'

function Get-ServiceKey {
    param([string]$CommandLine)

    if ($CommandLine -like '*dashboard_unified_refresh.py*') { return 'dashboard_loop' }
    if ($CommandLine -like '*sector_opp_gain_server*') { return 'sector_api' }
    if ($CommandLine -like '*build_infra_audit_dashboard.py*') { return 'infra_loop' }
    if ($CommandLine -like '*alpaca_paper_loop_builder.py*' -or $CommandLine -like '*RUN_ALPACA_PAPER_247.ps1*') { return 'paper_trader' }
    return $null
}

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

if ($hits.Count -eq 0) {
    Write-Host '[INFO] No live workers found.'
    exit 0
}

$serviceByPid = @{}
foreach ($proc in $hits) {
    $serviceKey = Get-ServiceKey -CommandLine $proc.CommandLine
    if ($serviceKey) {
        $serviceByPid[[string]$proc.ProcessId] = $serviceKey
    }
}

$roots = foreach ($proc in $hits) {
    $serviceKey = Get-ServiceKey -CommandLine $proc.CommandLine
    if (-not $serviceKey) { continue }

    $parentKey = $serviceByPid[[string]$proc.ParentProcessId]
    if ($parentKey -eq $serviceKey) {
        continue
    }

    $related = @($hits | Where-Object { (Get-ServiceKey -CommandLine $_.CommandLine) -eq $serviceKey })
    [PSCustomObject]@{
        Service = $serviceKey
        ProcessId = $proc.ProcessId
        Name = $proc.Name
        ProcessCount = $related.Count
        CommandLine = $proc.CommandLine
    }
}

$roots | Sort-Object Service | Format-List
