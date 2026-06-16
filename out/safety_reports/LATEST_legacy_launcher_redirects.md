# Legacy Live Launcher Redirects

Generated: 2026-06-15T20:22:44.4710704-05:00

These legacy live launchers now route into code/execution/RUN_LIVE_STACK_SAFE_NO_ORDERS.ps1.

## Redirected Files

- code\execution\RUN_LIVE_COMPOUNDING_STACK.ps1
  Backup: code\execution\RUN_LIVE_COMPOUNDING_STACK.ps1.bak_pre_safe_redirect
- code\execution\SUPERVISE_LIVE_COMPOUNDING_STACK.ps1
  Backup: code\execution\SUPERVISE_LIVE_COMPOUNDING_STACK.ps1.bak_pre_safe_redirect

## Safety Meaning

- Stage is forced to live-data-no-orders.
- Broker order calls remain blocked.
- Old launchers cannot bypass order_safety_gate.py through these entrypoints.
- Future tiny-live requires a separate deliberate manual-arm patch.
