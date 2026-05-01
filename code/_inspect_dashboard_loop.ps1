$ErrorActionPreference = 'Stop'

Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like 'python*' -and
        $_.CommandLine -like '*dashboard_unified_refresh.py*'
    } |
    Select-Object ProcessId, Name, CommandLine |
    Format-List
