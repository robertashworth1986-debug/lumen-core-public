$ErrorActionPreference = 'Stop'

$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -like 'powershell*' -or $_.Name -like 'pwsh*') -and (
        $_.CommandLine -like '*RUN_CROSS_SECTOR_INTEL_STACK.ps1*' -or
        $_.CommandLine -like '*RUN_SECTOR_OPP_GAIN_DASHBOARD.ps1*' -or
        $_.CommandLine -like '*_clean_restart_live_loops.ps1*' -or
        $_.CommandLine -like '*_force_singleton_live.ps1*' -or
        $_.CommandLine -like '*START_LUMENCORE_CORE.ps1*' -or
        $_.CommandLine -like '*_start_all_live_now.ps1*'
    )
}

$targets | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-List