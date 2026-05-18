[CmdletBinding()]
param(
	[int]$Hours = 48,
	[int]$CycleMinutes = 5,
	[int]$MaxSymbols = 1200,
	[int]$TopN = 32,
	[switch]$EnableOrders,
	[switch]$RunOnce
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codeDir = Join-Path $stackRoot "code"
$execOut = Join-Path $stackRoot "out\execution"
$opsRoot = Join-Path $stackRoot "out\ops\institutional_sprint_48h"

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$runDir = Join-Path $opsRoot $stamp
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$cycleJsonlPath = Join-Path $runDir "trading_vs_infrastructure_cycles.jsonl"
$cycleCsvPath = Join-Path $runDir "trading_vs_infrastructure_cycles.csv"
$latestCyclePath = Join-Path $runDir "cycle_latest.json"
$summaryPath = Join-Path $runDir "sprint_summary.json"
$summaryMdPath = Join-Path $runDir "sprint_summary.md"
$latestSummaryPath = Join-Path $opsRoot "latest_summary.json"
$runLogPath = Join-Path $runDir "run.log"

$pythonCandidates = @(
	(Join-Path $stackRoot ".venv\Scripts\python.exe"),
	(Join-Path (Split-Path -Parent $stackRoot) "venv3.11\Scripts\python.exe"),
	(Join-Path $stackRoot "venv3.11\Scripts\python.exe")
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
	if (Test-Path $candidate) {
		$pythonExe = (Resolve-Path $candidate).Path
		break
	}
}
if (-not $pythonExe) {
	$cmd = Get-Command python -ErrorAction SilentlyContinue
	if ($cmd) {
		$pythonExe = $cmd.Source
	}
}
if (-not $pythonExe) {
	throw "Python executable not found. Activate a venv or install python."
}

function Write-Log {
	param([Parameter(Mandatory = $true)][string]$Message)
	$line = "[{0}] {1}" -f ((Get-Date).ToUniversalTime().ToString("o")), $Message
	Add-Content -Path $runLogPath -Value $line -Encoding UTF8
	Write-Host $line
}

function Read-JsonFile {
	param([Parameter(Mandatory = $true)][string]$Path)
	if (-not (Test-Path $Path)) {
		return $null
	}
	try {
		return (Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
	}
	catch {
		return $null
	}
}

function Invoke-PythonStep {
	param(
		[Parameter(Mandatory = $true)][string]$Name,
		[Parameter(Mandatory = $true)][string]$Script,
		[Parameter(Mandatory = $false)][string[]]$Args = @()
	)

	$scriptPath = Join-Path $codeDir $Script
	if (-not (Test-Path $scriptPath)) {
		throw "Missing script: $scriptPath"
	}

	Write-Log ("step:start name={0} script={1}" -f $Name, $Script)
	$out = & $pythonExe $scriptPath @Args 2>&1
	$rc = $LASTEXITCODE

	if ($out) {
		foreach ($line in @($out)) {
			Add-Content -Path $runLogPath -Value ("[python] {0}" -f $line) -Encoding UTF8
		}
	}

	Write-Log ("step:end name={0} rc={1}" -f $Name, $rc)
	if ($rc -ne 0) {
		throw "Step failed: $Name (rc=$rc)"
	}
}

function Get-LiveSourceMetrics {
	param([Parameter(Mandatory = $true)][string]$RegistryPath)

	$registry = Read-JsonFile -Path $RegistryPath
	$sources = @()
	if ($registry -and $registry.sources) {
		$sources = @($registry.sources)
	}

	$total = [int]$sources.Count
	$liveSources = @($sources | Where-Object { [string]$_.status -like "LIVE_KEY_PRESENT*" })
	$liveCount = [int]$liveSources.Count
	$sectorsPresent = @($sources | Where-Object { $_.sector } | Select-Object -ExpandProperty sector -Unique)
	$coverage = 0.0
	if ($total -gt 0) {
		$coverage = [Math]::Round(($liveCount * 100.0) / $total, 4)
	}

	return [ordered]@{
		total_sources = $total
		live_key_sources = $liveCount
		live_key_coverage_pct = $coverage
		sectors_present = [int]$sectorsPresent.Count
	}
}

$startedUtc = (Get-Date).ToUniversalTime()
$deadlineUtc = $startedUtc.AddHours([double]$Hours)
$cycle = 0

Write-Log "====================================================="
Write-Log "INSTITUTIONAL 48H SPRINT"
Write-Log ("stack_root={0}" -f $stackRoot)
Write-Log ("python={0}" -f $pythonExe)
Write-Log ("hours={0} cycle_minutes={1} max_symbols={2} top_n={3} enable_orders={4}" -f $Hours, $CycleMinutes, $MaxSymbols, $TopN, [bool]$EnableOrders)
Write-Log "====================================================="

while ($true) {
	$nowUtc = (Get-Date).ToUniversalTime()
	if (-not $RunOnce -and $nowUtc -ge $deadlineUtc -and $cycle -gt 0) {
		break
	}

	$cycle += 1
	$cycleStartUtc = (Get-Date).ToUniversalTime()
	Write-Log ("cycle:start n={0}" -f $cycle)

	Invoke-PythonStep -Name "Alpaca Symbol Agents Full Breath" -Script "execution\alpaca_symbol_agents.py" -Args @("--max-symbols", "$MaxSymbols", "--scan-mode", "full")

	$orchArgs = @("--max-symbols", "$MaxSymbols", "--top-n", "$TopN", "--status-only-when-closed")
	if (-not $EnableOrders) {
		$orchArgs += "--no-orders"
	}
	Invoke-PythonStep -Name "Alpaca Paper Orchestrator" -Script "execution\alpaca_paper_orchestrator.py" -Args $orchArgs

	$breathPath = Join-Path $execOut "alpaca_breath_cycle_metrics.json"
	$orchPath = Join-Path $execOut "alpaca_orchestrator_status.json"
	$sourcePath = Join-Path $stackRoot "config\live_source_registry.json"

	$breath = Read-JsonFile -Path $breathPath
	$orch = Read-JsonFile -Path $orchPath
	$liveMetrics = Get-LiveSourceMetrics -RegistryPath $sourcePath

	$selectedCount = 0
	if ($orch -and $orch.runtime_symbol_selection -and $orch.runtime_symbol_selection.selected_count) {
		$selectedCount = [int]$orch.runtime_symbol_selection.selected_count
	}

	$marketOpen = $false
	if ($orch -and $orch.market_open -ne $null) {
		$marketOpen = [bool]$orch.market_open
	}

	$executorStatus = "unknown"
	if ($orch -and $orch.status) {
		$executorStatus = [string]$orch.status
	}

	$liveSyncAttempted = $false
	$liveSyncOk = $false
	$liveSyncReason = ""
	if ($orch -and $orch.live_sync) {
		if ($orch.live_sync.attempted -ne $null) {
			$liveSyncAttempted = [bool]$orch.live_sync.attempted
		}
		if ($orch.live_sync.ok -ne $null) {
			$liveSyncOk = [bool]$orch.live_sync.ok
		}
		if ($orch.live_sync.reason) {
			$liveSyncReason = [string]$orch.live_sync.reason
		}
	}

	$cycleRecord = [ordered]@{
		generated_utc = (Get-Date).ToUniversalTime().ToString("o")
		scope = "institutional_sprint_48h_cycle"
		run_stamp = $stamp
		cycle = $cycle
		cycle_minutes = $CycleMinutes
		trading_lane = [ordered]@{
			scan_mode = if ($breath -and $breath.scan_mode) { [string]$breath.scan_mode } else { "full" }
			max_symbols_requested = if ($breath -and $breath.max_symbols_requested) { [int]$breath.max_symbols_requested } else { [int]$MaxSymbols }
			dynamic_symbol_baseline = if ($breath -and $breath.dynamic_symbol_baseline) { [int]$breath.dynamic_symbol_baseline } else { 0 }
			universe_total = if ($breath -and $breath.universe_total) { [int]$breath.universe_total } else { 0 }
			scanned_symbols = if ($breath -and $breath.scanned_symbols) { [int]$breath.scanned_symbols } else { 0 }
			coverage_pct = if ($breath -and $breath.scan_coverage_pct) { [double]$breath.scan_coverage_pct } else { 0.0 }
			symbols_per_sec = if ($breath -and $breath.symbols_per_sec) { [double]$breath.symbols_per_sec } else { 0.0 }
			execution_ready_count = if ($breath -and $breath.execution_ready_count) { [int]$breath.execution_ready_count } else { 0 }
			selected_count = $selectedCount
			market_open = $marketOpen
			executor_status = $executorStatus
			no_orders = [bool](-not $EnableOrders)
		}
		infrastructure_lane = [ordered]@{
			total_sources = [int]$liveMetrics.total_sources
			live_key_sources = [int]$liveMetrics.live_key_sources
			live_key_coverage_pct = [double]$liveMetrics.live_key_coverage_pct
			sectors_present = [int]$liveMetrics.sectors_present
			live_sync_attempted = $liveSyncAttempted
			live_sync_ok = $liveSyncOk
			live_sync_reason = $liveSyncReason
		}
		evidence_paths = [ordered]@{
			breath_metrics = $breathPath
			orchestrator_status = $orchPath
			live_source_registry = $sourcePath
		}
	}

	$cycleFile = Join-Path $runDir ("cycle_{0:D4}.json" -f $cycle)
	$cycleRecord | ConvertTo-Json -Depth 8 | Set-Content -Path $cycleFile -Encoding UTF8
	$cycleRecord | ConvertTo-Json -Depth 8 | Set-Content -Path $latestCyclePath -Encoding UTF8
	Add-Content -Path $cycleJsonlPath -Value ($cycleRecord | ConvertTo-Json -Depth 8 -Compress) -Encoding UTF8

	$csvRow = [pscustomobject]@{
		generated_utc = $cycleRecord.generated_utc
		cycle = $cycle
		dynamic_symbol_baseline = [int]$cycleRecord.trading_lane.dynamic_symbol_baseline
		universe_total = [int]$cycleRecord.trading_lane.universe_total
		scanned_symbols = [int]$cycleRecord.trading_lane.scanned_symbols
		coverage_pct = [double]$cycleRecord.trading_lane.coverage_pct
		symbols_per_sec = [double]$cycleRecord.trading_lane.symbols_per_sec
		execution_ready_count = [int]$cycleRecord.trading_lane.execution_ready_count
		selected_count = [int]$cycleRecord.trading_lane.selected_count
		market_open = [bool]$cycleRecord.trading_lane.market_open
		total_sources = [int]$cycleRecord.infrastructure_lane.total_sources
		live_key_sources = [int]$cycleRecord.infrastructure_lane.live_key_sources
		live_key_coverage_pct = [double]$cycleRecord.infrastructure_lane.live_key_coverage_pct
		sectors_present = [int]$cycleRecord.infrastructure_lane.sectors_present
		live_sync_ok = [bool]$cycleRecord.infrastructure_lane.live_sync_ok
		executor_status = [string]$cycleRecord.trading_lane.executor_status
	}
	if (-not (Test-Path $cycleCsvPath)) {
		$csvRow | Export-Csv -Path $cycleCsvPath -NoTypeInformation -Encoding UTF8
	}
	else {
		$csvRow | Export-Csv -Path $cycleCsvPath -NoTypeInformation -Encoding UTF8 -Append
	}

	$cycleElapsedSec = [Math]::Round(((Get-Date).ToUniversalTime() - $cycleStartUtc).TotalSeconds, 3)
	Write-Log ("cycle:end n={0} elapsed_sec={1} selected={2} scanned={3} live_keys={4}/{5}" -f $cycle, $cycleElapsedSec, $selectedCount, [int]$cycleRecord.trading_lane.scanned_symbols, [int]$liveMetrics.live_key_sources, [int]$liveMetrics.total_sources)

	if ($RunOnce) {
		break
	}

	if ((Get-Date).ToUniversalTime() -ge $deadlineUtc) {
		break
	}

	$sleepSec = [Math]::Max(30, [int]($CycleMinutes * 60))
	Start-Sleep -Seconds $sleepSec
}

$endedUtc = (Get-Date).ToUniversalTime()
$summary = [ordered]@{
	generated_utc = $endedUtc.ToString("o")
	scope = "institutional_sprint_48h"
	run_stamp = $stamp
	started_utc = $startedUtc.ToString("o")
	ended_utc = $endedUtc.ToString("o")
	target_hours = $Hours
	cycle_minutes = $CycleMinutes
	cycles_completed = $cycle
	max_symbols = $MaxSymbols
	top_n = $TopN
	enable_orders = [bool]$EnableOrders
	status = "completed"
	artifact_paths = [ordered]@{
		run_dir = $runDir
		cycles_jsonl = $cycleJsonlPath
		cycles_csv = $cycleCsvPath
		cycle_latest = $latestCyclePath
		summary_json = $summaryPath
		run_log = $runLogPath
	}
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $latestSummaryPath -Encoding UTF8

$md = @(
	"# Institutional Sprint Summary",
	"",
	"- generated_utc: $($summary.generated_utc)",
	"- scope: $($summary.scope)",
	"- run_stamp: $($summary.run_stamp)",
	"- cycles_completed: $($summary.cycles_completed)",
	"- max_symbols: $($summary.max_symbols)",
	"- top_n: $($summary.top_n)",
	"- enable_orders: $($summary.enable_orders)",
	"- cycles_csv: $cycleCsvPath",
	"- cycles_jsonl: $cycleJsonlPath",
	"- cycle_latest: $latestCyclePath",
	"- run_log: $runLogPath"
)
$md -join "`r`n" | Set-Content -Path $summaryMdPath -Encoding UTF8

Write-Log ("summary={0}" -f $summaryPath)
Write-Output ("SUMMARY={0}" -f $summaryPath)
