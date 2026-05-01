param(
  [int]$EcosystemIntervalSec = 300,
  [switch]$IncludeICloud,
  [switch]$IncludeSystemCrawl,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$starter = Join-Path $PSScriptRoot "START_LUMA_ECOSYSTEM_STACK.ps1"

if (-not (Test-Path $starter)) {
  throw "Starter script not found: $starter"
}

$argList = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", ('"' + $starter + '"'),
  "-EcosystemIntervalSec", [string]$EcosystemIntervalSec
)
if ($IncludeICloud) { $argList += "-IncludeICloud" }
if ($IncludeSystemCrawl) { $argList += "-IncludeSystemCrawl" }

$taskName = "LumaEcosystemAutoStart"
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument ($argList -join " ")
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and -not $Force) {
  throw "Task '$taskName' already exists. Re-run with -Force to replace it."
}
if ($existing -and $Force) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -ErrorAction Stop | Out-Null

Write-Host "[TASK] Registered: $taskName"
Write-Host "[TASK] Runs at logon and starts gateway + ecosystem daemon"
Write-Host "[TASK] Start manually once with: pwsh -ExecutionPolicy Bypass -File `"$starter`""
