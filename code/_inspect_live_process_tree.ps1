$ErrorActionPreference = 'Stop'

$all = Get-CimInstance Win32_Process
$hits = $all | Where-Object {
    $_.Name -like 'python*' -and (
        $_.CommandLine -like '*dashboard_unified_refresh.py*' -or
        $_.CommandLine -like '*alpaca_paper_loop_builder.py*' -or
        $_.CommandLine -like '*sector_opp_gain_server*' -or
        $_.CommandLine -like '*build_infra_audit_dashboard.py*'
    )
}

$rows = foreach ($proc in $hits) {
    $parent = $all | Where-Object { $_.ProcessId -eq $proc.ParentProcessId } | Select-Object -First 1
    [PSCustomObject]@{
        ProcessId = $proc.ProcessId
        ParentProcessId = $proc.ParentProcessId
        Name = $proc.Name
        ParentName = $(if ($parent) { $parent.Name } else { '' })
        CommandLine = $proc.CommandLine
        ParentCommandLine = $(if ($parent) { $parent.CommandLine } else { '' })
    }
}

$rows | Format-List