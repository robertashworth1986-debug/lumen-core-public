# Safe Live Executor Smoke

- Generated UTC: `2026-06-16T01:20:28.174333+00:00`
- Stage: `live-data-no-orders`
- Approved: `False`
- Blocked: `True`
- Reason: `blocked_by_live_data_no_orders_stage`
- Executor called: `False`

## Live Executor Surface

```json
{
  "candidate_functions_found": [],
  "import_ok": true,
  "order_related_callables": [
    "MultiExchangeRouter",
    "OrderRouter",
    "RouteIntent"
  ]
}
```

## Safety Decision

```json
{
  "approved": false,
  "blockers": [],
  "generated_utc": "2026-06-16T01:20:28.173821+00:00",
  "intent": {
    "notional_usd": 1.0,
    "order_type": "market",
    "quantity": null,
    "side": "buy",
    "source": "safe_live_executor_smoke",
    "symbol": "TEST/USD"
  },
  "reason": "blocked_by_live_data_no_orders_stage",
  "stage": "live-data-no-orders",
  "warnings": [
    "kill_switch_clear_by_file_check",
    "live_order_config_detected_but_stage_blocks_orders",
    "risk_local_basic_pass",
    "signal_local_no_known_gate"
  ]
}
```