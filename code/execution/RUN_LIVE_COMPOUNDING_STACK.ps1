$ErrorActionPreference = "Stop"

Write-Error @"
RETIRED_LIVE_ARMING: this launcher is preserved only as a historical entrypoint.
Repository policy permits live public market data, deterministic simulation,
paper execution, and validate-only requests. It does not start an executor,
approval autofire daemon, or any live-order process.
"@
exit 2
