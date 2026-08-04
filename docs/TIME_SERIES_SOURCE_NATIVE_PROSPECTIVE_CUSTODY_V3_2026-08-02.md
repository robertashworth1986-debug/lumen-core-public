# LumenCore Source-Native Prospective Forecast Custody V3

Status: `SEALED_AWAITING_FUTURE_OBSERVATIONS_AND_EXTERNAL_TIMESTAMP`

The first V3 local batch contains 15 predictions, 0 settlements, and 0 eligible
future observations. Its prediction terminal SHA-256 is
`14d0d386cc1de6b6389826cbc4b0cd7c49f6becea600842ceac2e1cc234dd6d4`.
No verified independent timestamp has been ingested, so every row remains
unscoreable. No performance, trading-alpha, field-savings, valuation,
universal-superiority, or deployment claim is authorized.

## V2 Is a Nonconfirmatory Pilot

V2 is preserved and classified as `NONCONFIRMATORY_PILOT`:

- predictions: 15;
- settlements: 0;
- eligible observations: 0;
- prediction terminal SHA-256:
  `9548569419d41cc4c6e8b2b06299d9ecfd2ed2bee92989acfdbbde02570d8081`;
- protocol payload SHA-256:
  `2f82f02cc3fb4f70f2ab51e6f896f559af1f6b03bb415ba6eaf29344fc45c2fc`.

No V2 row is admissible to V3. V2 supplies engineering evidence about local
sealing, not confirmatory performance evidence.

## Why V3 Exists

V3 freezes repairs while there are still zero settled or eligible V2 outcomes.
It closes four validity gaps: production provenance, independent timestamp
verification, fully specified inference, and joint handling of cross-series
dependence. The candidate remains the retrospectively selected
`fractal_brownian_surface` heuristic. V3 is a prospective test of that fixed
selection, not a claim that the earlier search was confirmatory.

The implementation and protocol are frozen before the first V3 target period:

- collector SHA-256:
  `991f83b8352ffe5f5e5bc4ed4955eb189f9fab468ae36d89fe9a73e0777d3d5d`;
- confirmatory analysis SHA-256:
  `8d52abeff72d990ed05a553644e80c2c54638bf8da224c1b1b181322e0fd116f`;
- protocol payload SHA-256:
  `8477ca6f94cfbf9233b9a7ec1cb68a8d8736862384540b4a0166a552fd8b55c3`.

The first pending anchor request SHA-256 is
`9ff12930dd5ddfbb390cb449c0d06ea60cbe40cdc41eeff70ff03716b0af2940`.
Its RFC 3161 query is locally verified but has not been sent to a timestamp
authority. The query itself is not independent time proof.

## Fixed Periods

Period assignment uses the immutable source-native target period, never the
forecast creation date or settlement date.

| Period | Inclusive target-period start | Inclusive target-period end |
| --- | --- | --- |
| `V3_CONFIRMATORY_P1` | 2026-08-03 | 2031-08-31 |
| `V3_REPLICATION_P2` | 2031-09-01 | 2036-08-31 |

For monthly FRED series, the first period contains observation months
2026-09-01 through 2031-08-01, and replication contains 2031-09-01 through
2036-08-01. A target cannot move between periods, appear in both, or be carried
past a boundary. There is no early analysis, period extension, or optional
stopping.

## Direct-Provider Production Custody

Production collection is direct-provider-only. The only production mode is:

```text
python code/time_series_source_native_prospective_collector_v3.py cycle --source FRED --source TWELVE_DATA
```

Production rejects local snapshots, normalized inputs, raw-file inputs,
fixtures, and replay arguments. Test and replay runs must use a physically
separate output namespace. A caller-supplied `custody_mode` is never trusted.

The collector must retain the exact provider response bytes before parsing.
Normalized observations must then be reconstructed from those retained bytes,
not accepted from caller-supplied structures. Every normalized snapshot binds
all raw-response hashes and the parser artifact hash. Reparse is required
before both prediction and settlement. Any mismatch invalidates the affected
arm; an unparseable or changed provider schema leaves it inconclusive.

## RFC 3161 Independent-Time Gate

Every covered pre-release prediction terminal requires a verified RFC 3161
timestamp receipt. The timestamped subject is the SHA-256 of canonical JSON
binding:

1. V3 protocol identifier;
2. V3 protocol payload SHA-256;
3. prediction terminal SHA-256; and
4. prediction count covered by that terminal.

Canonical JSON is UTF-8 with sorted keys, no insignificant whitespace, and no
trailing newline. Code must ingest and verify the DER token, SHA-256 message
imprint, CMS signature, TSA certificate chain to the frozen trust bundle,
certificate validity at `genTime`, exact bound fields, and a `genTime` strictly
before the applicable target-release boundary. A request, local clock, local
hash, unverified token, or file timestamp is insufficient. A missing or failed
receipt is `INVALID_NOT_SCOREABLE`.

## Frozen Question

Within each source arm, does the fixed candidate improve absolute forecast
error by at least five percent against each of eight registered baselines on
horizons 1, 3, and 5, under the complete V3 custody and inference rules?

There are exactly 16 contrasts: two source arms multiplied by eight baselines.
Holm correction covers all 16 together. No best-looking subset may be selected.

## Endpoint

For cell `c = source-series-horizon` and baseline `b`:

```text
MAE_C(c)   = mean(abs(candidate - actual))
MAE_B(c,b) = mean(abs(baseline_b - actual))
rMAE(c,b)  = MAE_C(c) / MAE_B(c,b)
theta_hat(source,b) = equal-weight mean_c(log(rMAE(c,b)))
```

FRED has 12 fixed cells and Twelve Data has 3. Every cell receives equal
weight. If any `MAE_B(c,b) <= 1e-12`, the source arm and period are invalid;
no epsilon is substituted.

The boundary null and alternative for every contrast are:

```text
H0: theta >= log(0.95)
H1: theta <  log(0.95)
```

For the tail guard, pool the fully paired absolute errors across the source arm.
Compute NumPy p95 candidate absolute error divided by p95 baseline absolute
error with `method="linear"`. A baseline p95 at or below `1e-12` invalidates
the arm.

## Joint Circular Moving-Block Bootstrap

Use 20,000 replications and NumPy PCG64 seed `2026072901`.

- FRED uses ordered UTC calendar-month clusters, circular blocks of 6 months,
  and at least 60 clusters. Every FRED series and horizon is resampled jointly.
- Twelve Data uses America/New_York exchange-week clusters from Monday through
  Sunday, circular blocks of 8 weeks, and at least 104 clusters. Every horizon
  is resampled jointly.

For each source arm and replication, draw one sequence of block starts uniformly
with replacement, wrap at the final cluster, concatenate, and truncate to the
original cluster count. Reuse that exact sampled sequence for the candidate and
all eight baselines. Recompute cell MAEs, cell rMAEs, and all eight arm-level
statistics from the sampled rows. Block length cannot be retuned.

Let `delta_r = theta_star_r - theta_hat` and `theta_0 = log(0.95)`. The exact
one-sided centered-bootstrap p-value is:

```text
p = (1 + sum_r I(theta_0 + delta_r <= theta_hat)) / 20001
```

Let `q_0.05` be NumPy
`quantile(delta, 0.05, method="linear")`. The one-sided 95 percent
basic-bootstrap upper bound is:

```text
U_0.95 = theta_hat - q_0.05
```

Raw one-sided p-values are ordered ascending, with ties broken by source arm
then registered baseline order. Holm compares rank `i` to `0.05/(17-i)` and
stops at the first non-rejection.

## Completeness And Decision Rule

No partial cell or complete-case subset is analyzed. A cell is partial when any
preregistered eligible target lacks a verified pre-release RFC 3161 receipt,
retained and reparsable raw response, immutable actual, candidate forecast, or
one of the eight baseline forecasts. A partial cell leaves the entire source
arm and period `INCONCLUSIVE`.

Each contrast must satisfy all of the following:

1. Holm rejection across the 16-contrast family;
2. `exp(theta_hat) <= 0.95`;
3. `U_0.95 < log(0.95)`;
4. every cell `rMAE <= 1.05`; and
5. arm-level candidate/baseline p95 absolute-error ratio `<= 1.10`.

A source arm passes only if all eight contrasts pass. The first-period result
requires both complete arms. A replicated result requires an independent pass
in `V3_REPLICATION_P2` under the unchanged implementation and rules, excluding
all first-period rows. Missing custody, insufficient clusters, or any incomplete
arm cannot be converted into a win.

## No Outcome-Dependent Choices

The candidate, sources, series, horizons, baselines, periods, target identity,
cluster units, block lengths, seed, replication count, formulas, denominator
rule, quantile method, multiplicity family, thresholds, and missingness rules
are fixed. No interim leaderboard, fallback, row compression, backfill,
replacement, sample-gate reduction, parameter override, or post-outcome method
choice is allowed.

## Claim Boundary

A future complete first-period pass would support only a bounded result for the
named sources, series, horizons, period, and custody rules. A broader promotion
claim requires the independent replication period. Neither result would by
itself establish trading alpha, field performance, realized savings, enterprise
value, universal superiority, government approval, or deployment authority.
