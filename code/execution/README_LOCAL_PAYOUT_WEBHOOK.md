# Local Payout Webhook (Built for LUMENCORE)

This gives you a local webhook URL for payout dispatch:

- URL: `http://127.0.0.1:8787/payout-webhook`
- Health: `http://127.0.0.1:8787/health`

## Files

- `code/execution/payout_webhook_receiver.py` — local webhook server
- `code/execution/payout_webhook_probe.py` — sends a probe payload

## Run receiver

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/payout_webhook_receiver.py
```

## Probe it

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/payout_webhook_probe.py
```

## Bridge dispatch test

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/payout_bridge.py --max-items 5
```

## Output artifacts

- `out/execution/payout_webhook_received.jsonl` — append-only receive log
- `out/execution/payout_webhook_latest.json` — latest payload snapshot
- `out/execution/payout_intents.json` — intent lifecycle (`PENDING`, `DISPATCHED`, `DISPATCH_FAILED`)

## Auth behavior

Receiver checks bearer token if available from these keys:

- `LUMA_PAYOUT_TOKEN`
- `PAYOUT_WEBHOOK_AUTH_BEARER`
- `WEBHOOK_SHARED_SECRET`

If one exists, request must send `Authorization: Bearer <token>`.
