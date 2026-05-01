# Payout Bridge (Chime Milestones)

This bridge dispatches pending payout intents from `out/execution/payout_intents.json`.

## Runtime keys (`config/runtime_control.json`)

- `payout_auto_dispatch_enabled`: enable/disable outbound dispatch.
- `payout_dispatch_mode`: currently supports `webhook`.
- `payout_webhook_url`: destination endpoint for payout intents.
- `payout_webhook_auth_bearer`: optional bearer token.
- `payout_webhook_timeout_sec`: HTTP timeout.

## Quick run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/payout_bridge.py --dry-run
```

## Live dispatch run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/payout_bridge.py --max-items 20
```

## Notes

- The orchestrator now queues payout intents at configured milestone levels.
- If auto-dispatch is enabled and webhook is set, orchestrator attempts immediate dispatch.
- This bridge provides an independent retry path for any `PENDING` intents.
