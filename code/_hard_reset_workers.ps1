$ErrorActionPreference = 'Continue'

$ps = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$code = 'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code'

for ($round = 1; $round -le 5; $round++) {
  $targets = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and (
      $_.CommandLine -like '*dashboard_unified_refresh.py*' -or
      $_.CommandLine -like '*execution.sector_opp_gain_server:app*' -or
      $_.CommandLine -like '*build_infra_audit_dashboard.py --loop*'
    )
  }

  Write-Host "Round $round :: found $($targets.Count) worker processes"
  if ($targets.Count -eq 0) { break }

  foreach ($p in $targets) {
    Write-Host "Try kill PID=$($p.ProcessId) :: $($p.CommandLine)"
    try {
      Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
      Write-Host "  -> KILLED"
    } catch {
      Write-Host "  -> FAILED: $($_.Exception.Message)"
    }
  }

  Start-Sleep -Seconds 1
}

Start-Sleep -Seconds 1

& $ps -NoProfile -ExecutionPolicy Bypass -File "$code\START_LUMENCORE_CORE.ps1" -Prime
