# EIA grid hourly hybrid V3 public-safe custody watchdog

## Outcome

This control verifies operational custody for the frozen EIA grid hourly hybrid
confirmation V3 without evaluating or publishing its suppressed performance.
It is deterministic for a fixed input directory, immutable policy, frozen
source tree, and explicit `--as-of-utc` value. It performs no network access,
does not invoke the collector or prediction runtime, and does not modify any
protocol, prediction, settlement, status, receipt, scheduler, or ledger byte.

The V3 source is not present on current public `main`. The watchdog therefore
binds, without cherry-picking or changing it, to the public immutable source
commit `47380e82d9acb45dd5ca3401bf8611a6b431fddf`. The policy records the exact
SHA-256 and Git blob identities for the V3 protocol, V3 runtime, parent V2
protocol, and frozen historical design artifact. When `--source-root` is
provided, the verifier hashes those local bytes and checks the source checkout
commit before inspecting the public-safe custody projection.

## Verified custody contract

The verifier fails closed for corruption or contract drift. It checks:

- the exact frozen protocol, runtime, parent V2, and historical-design source
  identities;
- the V3 runtime's prediction, settlement, status, and operational-receipt
  schema markers;
- the first permitted target period and the inclusive 3,600–7,200 second seal
  lead window;
- absence of target actuals at seal and `backfilled: false`;
- one prediction and at most one matching settlement panel per target;
- the exact ordered set of eight declared balancing authorities in every
  complete panel;
- public-safe prediction and settlement projection self-hashes, prior-record
  chain continuity, and terminal-hash agreement across manifest, status, and
  operational receipt;
- required parent V2 protocol, prediction-panel, and settlement-panel hash
  bindings;
- duplicate targets, missing hourly prediction periods, and earlier settlement
  holes;
- prediction, settlement, unsettled, complete-day, and terminal count
  consistency;
- unsettled backlog and oldest-unsettled lag;
- manifest, status, and operational-receipt freshness;
- complete 24-hour UTC days and the exact 168-, 720-, 2,160-hour and 90-day
  sample-readiness gates; and
- score suppression, no performance evaluation, and
  `automatic_promotion_allowed: false` in every public-safe control surface.

The projection chains are deliberately separate public-safe self-hash chains.
They establish integrity of the custody-only projection supplied to this
watchdog. They do not reconstruct or publish the original metric-bearing
settlement ledger bytes. A producer of a live projection remains responsible
for creating that projection from an authorized local source without changing
the source ledger. The watchdog will not accept forecast, actual, error, score,
weight, comparator, improvement, or win-rate fields in its input projection.

## Classifications

| Classification | Meaning | Workflow result |
|---|---|---|
| `OK` | Custody is valid, fresh, contiguous, and below backlog/lag warnings. | Success |
| `WARN` | Custody is valid, but an allowed gap, backlog, lag, or aging threshold is present. | Success with exact reason codes |
| `STALE` | Custody is valid, but status or operational receipt exceeds the frozen stale threshold. | Success with exact reason codes |
| `FAIL` | Corruption, identity drift, schema drift, leakage, count mismatch, weakened policy, or another fail-closed invariant was detected. | Failure |

`WARN` and `STALE` are explicitly permitted non-failure classifications by the
immutable repository policy. They never imply readiness, promotion, or good
performance. `FAIL` is never converted to a warning.

## Offline use

Run the focused adversarial suite:

```powershell
python -m unittest -v tests.test_eia_grid_hourly_hybrid_v3_custody_watchdog
```

Verify an allowlisted public-safe projection with an explicit observation time:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_HYBRID_V3_CUSTODY.py `
  --input-dir C:\path\to\public-safe-v3-custody-projection `
  --source-root C:\path\to\frozen-v3-source `
  --as-of-utc 2026-08-30T18:00:00Z `
  --json-out out\eia-v3-custody-watchdog\receipt.json `
  --summary-out out\eia-v3-custody-watchdog\summary.md
```

The input directory must contain exactly the five allowlisted files declared in
the policy. Symlinks, extra files, duplicate JSON keys, non-finite values,
oversized inputs, broken file manifests, and score-bearing fields fail closed.

## Scheduled CI boundary

The dedicated workflow is read-only (`contents: read`), concurrency bounded,
time bounded, and pinned to immutable action commits. It checks out the exact
frozen V3 source, builds a synthetic custody-only fixture in runner temporary
storage, runs adversarial tests, and uploads only the public-safe watchdog
receipt and Markdown summary for 30 days. It does not commit generated state,
write to `main`, contact a VPS or provider, collect data, issue predictions,
settle panels, tune a model, deploy, or publish a performance result.

Because current public `main` contains no live V3 custody projection, scheduled
CI proves the verifier contract and frozen-source binding; it is not a live
collector-health receipt. A live operational classification requires a fresh,
authorized public-safe projection supplied locally to the same verifier.

## Truth boundary

This is first-party custody and operational-control evidence only. It does not
establish that the frozen confirmatory window has legally closed, any V3 score,
any model comparison, improvement, validation, grid outcome, savings,
reliability effect, production readiness, deployment, external review, or
promotion decision. Sample readiness is a count-and-calendar condition only.
Automatic promotion remains disabled even when every sample-readiness boolean
is true.
