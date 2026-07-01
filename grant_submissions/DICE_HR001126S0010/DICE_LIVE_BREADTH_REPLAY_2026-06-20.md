# DICE Live Breadth Replay

Generated UTC: `2026-06-24T19:22:40.339202+00:00`

## Evidence Boundary

- Evidence mode: primary_live_pulled_source_rows_with_deterministic_replay_labels
- Primary evidence source: frozen_live_pulled_rows
- Synthetic role: secondary_control_labels_ablation_and_failure_injection_only

Frozen live-pulled time-series replay adapter. Source rows are live-pulled or previously live-fetched operational/market signals, but task roles, risk tiers, and adversary knobs are deterministic derived labels for replay. Results do not establish DICE metric attainment, operational DoD performance, field validation, semantic correctness, or adversarial security.

## Replay Scope

- Source count: 6
- Scenario windows: 14
- Agents per scenario: 180
- Roles: 8
- Task multiplier per live row: 3

## Paired Replay Metrics

| Metric | Mean delta | Favorable fraction | Scenario count |
|---|---:|---:|---:|
| Safe completion | +0.0437 | 0.857 | 14 |
| Constraint violation | -0.1216 | 0.929 | 14 |
| Messages per safe completion | -2.8157 | 1.000 | 14 |
| False rejection | +0.0514 | 0.000 | 14 |

## Source Windows

| Source | Type | Windows | Rows | SHA-256 prefix |
|---|---|---:|---:|---|
| KRAKEN:WLD/USD | market_execution | 3 | 720 | a09c265f28ea |
| KRAKEN:CC/USD | market_execution | 3 | 720 | b8305cb208b9 |
| KRAKEN:ESPORTS/USD | market_execution | 3 | 720 | f01a4ec1d5d6 |
| KRAKEN:PEAQ/USD | market_execution | 3 | 720 | 2ade6cfad808 |
| EIA:CISO | power_grid | 1 | 48 | 0e1932712c97 |
| EIA:ISNE | power_grid | 1 | 48 | 0258173309b1 |

## Claim Gate

- ready_for_portal_upload: false
- ready_for_submit: false
- live_replay_proves_dice_metric_attainment: false
- live_replay_proves_operational_performance: false
- live_replay_proves_trading_profit: false
- synthetic_primary_evidence: false
