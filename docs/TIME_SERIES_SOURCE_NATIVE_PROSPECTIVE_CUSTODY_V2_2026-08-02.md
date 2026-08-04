# LumenCore Source-Native Prospective Forecast Custody V2

Status: `NONCONFIRMATORY_PILOT_SEALED_AND_SUPERSEDED_BY_V3`

Result status: 15 locally sealed predictions, 0 settlements, 0 eligible future
observations, and no verified independent timestamp. V2 is closed as an
engineering pilot. No performance, trading-alpha, field-savings, valuation, or
universal-superiority claim is authorized.

V2 prediction terminal SHA-256:
`9548569419d41cc4c6e8b2b06299d9ecfd2ed2bee92989acfdbbde02570d8081`.
V2 protocol payload SHA-256:
`2f82f02cc3fb4f70f2ab51e6f896f559af1f6b03bb415ba6eaf29344fc45c2fc`.

## Why V2 Exists

Version 1 froze a scientific hypothesis, candidate, baselines, and sample gates,
but did not operationally bind the complete prediction-before-release chain.
Version 2 superseded it before any eligible future observation. Version 1 is
preserved unchanged and its zero-observation state is hash-bound in the V2
protocol.

The current local source-native ledger contains 140 registered geometry
families, 35 implementations, and 105 implementation gaps. It records zero
globally Holm-corrected individual wins and zero candidates that beat every
source-native baseline after global correction. Those are research inventory
facts, not a negative or positive prospective result.

## Frozen Question

Does the registered `fractal_brownian_surface` forecasting heuristic improve
first-vintage absolute error by at least five percent against each of eight
named baselines, after one-sided Holm familywise correction, on the frozen FRED
and Twelve Data source arms and horizons 1, 3, and 5?

The question is intentionally narrow. A pass would apply only to the named
sources, series, horizons, periods, transformations, and decision rule. It
would not establish a universal geometry advantage or a tradable strategy.

## Target Identity

- A horizon is the ordinal count of new native observations after the sealed
  origin, not elapsed calendar time.
- FRED targets are provider initial-release observations requested with
  `output_type=4`. The seal must precede 00:00 UTC on the reported
  `first_vintage_date`; this is conservative because no intraday release time
  is inferred. Historical initial releases are collected through frozen,
  non-overlapping 1,460-day real-time windows so each JSON request remains
  below FRED's 2,000-vintage limit; every response part is retained separately.
  Each series begins at its provider-reported first available ALFRED vintage,
  which is rechecked against the frozen value on every cycle. Earlier
  observations without archived first-release custody are excluded.
- Twelve Data targets are `adjust=splits` AAPL daily closes in exchange-local
  time. A valid target must first be retained on the same exchange session
  date, after the frozen 18:00 America/New_York collection boundary. A missed
  same-session poll is not backfilled into the primary set.

Official API semantics used by the protocol:

- FRED series observations: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- Twelve Data API parameters and daily timezone behavior: https://twelvedata.com/docs/advanced

## Operational Custody

For every source cycle, the collector now performs all semantic and forecast
preflight checks before an append. Production ledgers accept only retained live
provider responses; test fixtures are rejected. Raw responses and normalized
snapshots are content-addressed. Prediction, settlement, and operational-run
records are append-only JSONL chains with prior-record hashes and `fsync` after
each append.

Each prediction records the protocol hash, model and collector hashes, source
snapshot hash, history hash, exact source parameters, runtime fingerprint,
origin, horizon, all nine forecasts, and an explicit `actual_known_at_seal:
false` assertion. A settlement can reference only a verified prediction record
hash and cannot replace a prior settlement.

When a prediction terminal changes, the collector emits a content-addressed
external-anchor request. That request is only a pending payload. It is not an
independent timestamp and it does not make any row scoreable.

## Independent-Time Gate

Primary scoring remains `INVALID_NOT_SCOREABLE` until the applicable
pre-release prediction terminal receives a cryptographically verifiable
independent timestamp or immutable external inclusion receipt. Local clocks,
local hashes, file modification times, and locally generated anchor requests do
not satisfy this gate.

An external receipt must bind at least:

1. protocol payload SHA-256;
2. prediction terminal SHA-256;
3. prediction count covered by that terminal;
4. independently established receipt time; and
5. successful signature or inclusion-proof verification.

## Analysis Discipline

- Every candidate-baseline contrast is retained; no best-looking baseline is
  selected after outcomes.
- Overlapping origins are preserved, while inference counts unique targets and
  synchronizes resampling by target period within each source-series arm.
- Missing, late, schema-drifted, duplicate, nonfinite, unanchored, or
  first-vintage-unproven cells remain invalid or missing. They are not silently
  compressed.
- No interim leaderboard, optional stopping, sample-gate reduction, replacement
  prediction, or outcome-dependent protocol change is allowed.
- Promotion requires the preregistered sample gates, effect floor, uncertainty
  rule, familywise correction, no materially worse cell, and an independent
  prospective replication period.

## Reviewer Reproduction

```powershell
py -3.11 code\time_series_source_native_prospective_collector.py verify
py -3.11 code\time_series_source_native_prospective_collector.py status
py -3.11 -m pytest -q tests\test_time_series_source_native_prospective_collector.py
```

The wrapper `code\RUN_TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE.ps1` verifies the
frozen artifacts before source access, checks only whether required environment
keys are present, and never prints or persists their values.

## Closed Pilot Disposition

No V2 row is admissible to the V3 confirmatory ledger. V3 restarts before any
settled or eligible V2 outcome and repairs direct-provider provenance,
independent RFC 3161 verification, fixed periods, complete inference, and joint
cross-series dependence handling.

That is the credibility path: a smaller claim, a complete custody trail, a
hostile-to-self-deception decision rule, and enough time for reality to answer.
