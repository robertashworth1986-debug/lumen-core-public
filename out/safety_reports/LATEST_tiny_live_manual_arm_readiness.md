# Tiny-Live Manual Arm Readiness

- Generated UTC: `2026-06-16T01:26:29.839391+00:00`
- Mode: `design_only`
- Live trading active: `False`
- Tiny-live ready: `False`
- Reason: `manual_arm_not_enabled_design_only`

## Audit Counts

- `files_with_raw_live_references`: `33`
- `files_with_safe_references`: `18`

## Checks

| Check | Passed |
|---|---|
| `policy_exists` | `True` |
| `policy_enabled_false` | `True` |
| `policy_activation_not_active` | `True` |
| `confirmation_file_absent` | `True` |
| `safe_launcher_exists` | `True` |
| `order_safety_gate_exists` | `True` |
| `safe_live_executor_exists` | `True` |
| `live_data_no_orders_gate_exists` | `True` |
| `router_uses_safety_gate_exists` | `True` |
| `live_gate_report_present` | `True` |
| `safe_executor_report_present` | `True` |
| `entrypoint_audit_report_present` | `True` |
| `redirect_report_present` | `True` |
| `ledger_present` | `True` |
| `live_gate_blocks_orders` | `True` |
| `safe_executor_did_not_call_executor` | `True` |
| `safe_executor_blocked` | `True` |
| `raw_entrypoint_count_known` | `True` |
| `safe_reference_count_known` | `True` |

## Blockers

- None for design-only mode.

## Future Manual Arm Steps

- Review raw live entrypoint audit and redirect remaining high-risk launchers.
- Confirm live-data no-orders gate passes.
- Confirm safe_live_executor blocks orders before executor call.
- Create a separate deliberate manual-arm patch.
- Create LIVE_TINY_MANUAL_ARM.confirm only for tiny-live testing.
- Set max_order_usd no higher than 5 for first live test.
- Verify exchange/broker balance read works without placing orders.
- Run one tiny test only after human confirmation.

## Meaning

- This patch prepares the future tiny-live path but does not activate it.
- The confirmation file must be absent in design-only mode.
- The current safe state is live-data/no-orders.