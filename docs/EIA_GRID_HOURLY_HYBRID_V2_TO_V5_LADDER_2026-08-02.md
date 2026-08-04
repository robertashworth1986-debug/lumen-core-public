# EIA Grid Hourly Hybrid V2 To V5 Ladder

**Frozen:** 2026-08-02T09:24:17Z
**Current action:** preserve v2 and begin a separate v3 future-only confirmation chain
**Performance claim:** none

## Current Truth

Version 2 already exists as `EIA_GRID_ALL_AUTHORITY_DIRECT_HOURLY_20260716`. It seals one atomic prediction panel for all eight balancing authorities before the target interval and uses no target-hour official forecast. It is preserved unchanged.

The v2 sample counter has crossed its 168-hour preliminary threshold. That is sample readiness only. The parent status still reports no completed promotion evaluation and no confirmatory result.

## Version Ladder

| Version | Role | Start rule | Exit rule |
|---|---|---|---|
| v2 | Existing development and operational baseline | Already active | Preserve every panel, settlement, non-win, and chain receipt |
| v3 | One frozen constrained convex hybrid | New targets only after the 2026-08-02 freeze, sealed 60 to 120 minutes before interval start | 2,160 common hours, 90 complete UTC days, frozen inference, and every preregistered gate |
| v4 | Disjoint temporal replication | May start only after the v3 window and result are frozen | Repeat the identical executable and weights on the next disjoint 2,160 common hours; no pooling to rescue either period |
| v5 | Independent replication | May start only under a named evaluator with independent timestamps and retained raw provider responses | Accepted protocol, independent reproduction, complete result receipt, and no operator substitution |

Version numbers are protocol stages, not evidence-maturity claims. V4 and v5 are deliberately deferred because their required future and independent evidence do not exist yet.

## V3 Candidate

For each authority, v3 combines the six candidate forecasts already sealed in the parent v2 panel:

- seasonal naive at 24 hours;
- seasonal naive at 168 hours;
- equal seasonal blend;
- direct ridge;
- direct XGBoost;
- direct LightGBM.

Each authority's nonnegative weights are derived only from the frozen historical design artifact ending 2026-07-13. The raw weight is `1 / historical_validation_MASE^2`, normalized across the six candidates. The weights never update from v2 or v3 prospective outcomes.

V3 rejects a panel when any of these conditions fail:

- the parent v2 chain, protocol hash, or protocol commit is invalid;
- the panel is not complete across the same eight authorities;
- a target actual was present at parent seal;
- the v3 seal would be less than 60 or more than 120 minutes before interval start;
- the target predates the v3 window;
- the target was already sealed or would be a replacement/backfill;
- the protocol, runtime, historical design artifact, or parent record cannot be hash-bound.

## Evaluation Boundary

Aggregate scores remain suppressed while the 2,160-hour confirmation window is open. Settlement records preserve paired losses for later frozen analysis, but the operating status reports counts and custody only.

The confirmatory analysis requires complete 24-hour UTC days, equal authority-day weighting, synchronized circular seven-day block bootstrap, Holm correction across the two co-primary comparisons, a minimum 1% relative improvement, wins in at least six authorities, at least 60% UTC-day wins, bounded authority regression, and bounded tail error.

The v3 parent source did not retain every raw provider response body. V3 binds the source receipt and panel hashes available from v2, records that limitation, and does not claim independent reconstructability from provider bytes. V5 must close that gap under evaluator control.

## Reproduce

```powershell
python code/eia_grid_hourly_hybrid_confirmation.py --check
python -m pytest -q tests/test_eia_grid_hourly_hybrid_confirmation.py
```

The Windows scheduler wrapper is `tools/Run-EiaHourlyHybridConfirmationCycle.ps1`. Its output is isolated under `out/eia_grid_hourly_hybrid_confirmation_v3` and does not mutate the v1 or v2 chains.
