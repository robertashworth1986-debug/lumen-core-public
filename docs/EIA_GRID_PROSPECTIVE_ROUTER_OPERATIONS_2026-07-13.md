# EIA Grid Prospective Router Operations

Prepared: 2026-07-13

## One-Command Cycle

Run:

```powershell
tools\Run-EiaProspectiveRouterCycle.ps1
```

The cycle performs four bounded actions:

1. verifies the existing prediction and settlement hash chains;
2. seals only currently eligible pre-target forecasts;
3. settles only previously sealed predictions whose actuals are now available; and
4. appends an operational receipt and refreshes the prospective status report.

The wrapper does not trade, submit a grant, change a route map, backfill a forecast, alter a hyperparameter, or make a promotion claim.

## Unattended Collection

Register the current-user Windows task:

```powershell
tools\Register-EiaProspectiveRouterTask.ps1 -IntervalMinutes 30
```

Preview the registration without changing Task Scheduler:

```powershell
tools\Register-EiaProspectiveRouterTask.ps1 -IntervalMinutes 30 -WhatIfOnly
```

The task runs only in the current user's interactive session, reads the EIA key from the user environment, ignores overlapping invocations, and has a ten-minute execution limit. Quiet runs preserve their latest stdout and append failures under `out/eia_grid_prospective_hybrid_router`.

## Outputs

- `out/eia_grid_prospective_hybrid_router/sealed_predictions.jsonl`
- `out/eia_grid_prospective_hybrid_router/settlements.jsonl`
- `out/eia_grid_prospective_hybrid_router/operational_runs.jsonl`
- `out/eia_grid_prospective_hybrid_router/prospective_status_latest.json`

All three ledgers are append-only SHA-256 chains. The cycle rejects duplicate prediction keys, duplicate settlements, orphan settlements, chain tampering, and overlapping runs.

## Timing Rule

A prediction is eligible only when the official EIA day-ahead forecast exists, the corresponding actual is absent, and the seal occurs before target-local midnight. A no-op cycle is valid when no target satisfies every condition.

The current first allowed target is 2026-07-14. Historical or late forecasts cannot be inserted into the prospective chain.

## Status Interpretation

The status report tracks prediction and settlement counts by authority, complete common days, route hit rate, regret to the oracle, router MASE, and the current best fixed specialist. Thirty, ninety, and 180 common days indicate only sample readiness. They do not by themselves satisfy the protocol's statistical, robustness, or external-replication gates.

## Claim Boundary

This operations layer preserves prospective public-data software evidence. It does not establish patent validity, utility field control, realized savings, grid reliability improvement, production readiness, trading edge, or universal model superiority.
