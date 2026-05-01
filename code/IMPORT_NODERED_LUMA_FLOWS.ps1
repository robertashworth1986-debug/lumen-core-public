
$NodeRedBase = $null
$FlowFile = $null

for ($i = 0; $i -lt $args.Count; $i++) {
  switch -Regex ($args[$i]) {
    '^-NodeRedBase$|^--base$' {
      if ($i + 1 -lt $args.Count) { $NodeRedBase = $args[$i + 1]; $i++ }
    }
    '^-FlowFile$|^--flow-file$' {
      if ($i + 1 -lt $args.Count) { $FlowFile = $args[$i + 1]; $i++ }
    }
  }
}

if (-not $NodeRedBase) {
  $NodeRedBase = "http://127.0.0.1:1880"
}
if (-not $FlowFile) {
  $FlowFile = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\node_red\flows_luma_bidirectional.json"
}

$ErrorActionPreference = 'Stop'

$root = "C:\LumaTrader\INSTITUTIONAL_STACK_V2\code"
$python = Join-Path $root ".venv\Scripts\python.exe"
$ensureFlowScript = Join-Path $root "ENSURE_NODERED_LUMA_FLOWS.py"

if (-not (Test-Path $python)) {
  throw "Python runtime not found at $python"
}
if (-not (Test-Path $ensureFlowScript)) {
  throw "Missing helper script: $ensureFlowScript"
}

& $python $ensureFlowScript --base $NodeRedBase --flow-file $FlowFile --min-nodes 11
if ($LASTEXITCODE -ne 0) {
  throw "Flow ensure failed with exit code $LASTEXITCODE"
}

Write-Host "[OK] Node-RED flows verified."
