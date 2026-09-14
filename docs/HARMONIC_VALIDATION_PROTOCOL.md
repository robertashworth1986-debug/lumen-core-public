# Harmonic Validation Protocol

## Current Evidence Status

The March 18, 2026 `Harmonic vs backprop script.txt` is an exploratory V6
benchmark, not submission-grade evidence.

The script creates a final 20% holdout, but lines 389-395 refit each model on
the complete series and then score that same final segment. The holdout is
therefore visible during training. Harmonic win rates, gains, R-squared values,
confidence scores, and opportunity rankings produced by V6 must not be cited
as out-of-sample performance.

## V7 Required Design

1. Preserve chronological order and prohibit random train/test shuffling.
2. Fit every transform, scaler, period selector, and model on training data
   only.
3. Use expanding or rolling walk-forward folds with untouched test windows.
4. Compare harmonic Ridge against at least:
   - seasonal naive;
   - linear trend;
   - regularized autoregression;
   - MLP/backprop with training-only scaling.
5. Report MAE, RMSE, MASE, directional accuracy, and inference cost per fold.
6. Aggregate paired per-fold error differences, not only global averages.
7. Keep every random seed, dependency version, input hash, and fold boundary
   in the frozen run manifest.

## Monte Carlo Evidence

More simulations help only when they test a defined null hypothesis. A larger
run count cannot repair leakage or turn an in-sample fit into proof.

Each candidate series should receive:

- Moving-block bootstrap confidence intervals for the paired error difference.
- Phase-randomized Fourier surrogates that preserve the spectrum while
  destroying the original phase relationships.
- Circular-shift timing nulls for claimed phase-lock or entry-time effects.
- Regime-stratified resampling across volatility and trend states.
- Multiple-comparison control across datasets, symbols, horizons, and models.
- Sensitivity runs over fold size, harmonic count, regularization, and seed.

Default claim gate:

- at least 5 untouched walk-forward folds;
- at least 100 test observations in aggregate;
- 95% bootstrap interval for improvement entirely above zero;
- surrogate-test adjusted `p < 0.05`;
- positive effect in at least 70% of folds;
- no single fold contributing more than 40% of total measured gain;
- reproducible rerun from a frozen manifest.

Results below the gate remain research leads and must be labeled exploratory.

## Frozen Delta Unit

A sellable or grant-ready frozen delta is not merely a chart or model score.
It is a reproducible evidence unit containing:

- problem and baseline definition;
- immutable input manifest and SHA-256 hashes;
- exact code commit and dependency lock;
- train/test boundaries and leakage audit;
- before/after metric with confidence interval;
- operational cost, latency, and failure modes;
- attributable economic-impact calculation;
- signed result manifest and machine-readable output;
- plain-language limitations and deployment decision.

There is no reliable fixed government price of `$10,000` per frozen delta.
Its value depends on whether it satisfies a funded milestone, reduces a
documented cost, supports procurement acceptance, or protects a decision.

For scale claims, use:

`gross annual impact = measured efficiency gain * attributable annual cost base`

For example, `0.01%` applied to a verified `$10 billion` annual cost base is
`$1 million` of gross annual impact before implementation cost, attribution,
risk, and realization discounts.

## Simulation Storage

Use `E:\GLYPH_DRIVE\simulation_lake` for large Monte Carlo and surrogate
artifacts. The F drive is too small for this role.

Recommended layout:

```text
simulation_lake/
  inputs/<dataset_sha256>/
  runs/<run_id>/manifest.json
  runs/<run_id>/folds/
  runs/<run_id>/surrogates/
  runs/<run_id>/summary.json
  frozen_deltas/<delta_id>/
```

Git should contain code, compact summaries, schemas, and hashes. Large samples,
plots, and intermediate arrays stay on E and must not contain credentials.

## Production Boundary

Validation output may rank paper or shadow candidates. It must not authorize
live orders. Promotion to live execution requires a separate reviewed runtime
change, stable paper evidence, reconciliation, risk limits, and an explicit
operator decision.

## Existing offline ensemble evaluator: corrected research contract

The existing `dashboard/run_ensemble_meta_strategy.py` now implements the
versioned `lumencore.ensemble_past_only_research.v2` diagnostic. This repair
advances the existing external-validation or paid-pilot outcome by making one
supporting research evaluator inspectable. It does not satisfy the V7 claim
gate above or create a separate commercial product.

The previous runner supplied future test rows to vector generators, dropped
the first return at fold boundaries, padded malformed signals, and accepted a
fallback numeric column or filled missing prices. Its historical results and
the old chart's `Cumulative PnL` label must not be cited as validated
out-of-sample performance. Historical files remain retained; the corrected
method requires a new output directory.

### Information set and score

For target row `i`, the signal function receives only rows `[i-window, i)`.
The last returned signal is clipped to `[-1, 1]` and weights the transition
`close[i] / close[i-1] - 1`. Every transition from `window` through the final
input row is scored exactly once. `step` groups the report; it does not reset
positions or change the strategy's information set. A caller must select
`window` on separate development data: the placeholder tuner now refuses to
run. The evaluator does not certify how parameters or input datasets were
selected.

The same fifteen components and their existing formulas are retained. Some
components normalize their full input vector or fill internal warm-up values.
Only a preceding window reaches those components here, and only the final
signal is used. This confines future-row access in this evaluator; it does
not certify those shared vector functions as causal when used elsewhere.
Existing component-internal shifts remain in effect.

Scores are additive unitless weighted returns less assumed turnover costs,
not compounded portfolio returns or realized PnL. Initial weight is zero.
One-way fees and slippage are charged on `abs(weight - previous_weight)`;
the final weight is not liquidated. The buy-and-hold comparator uses the same
transitions with one initial entry cost. Cash scores zero. Same-close decision
and entry timing is an idealization; fills, financing, borrow, market impact,
taxes, and achievable performance are outside this diagnostic.

### Input and custody

Input is bounded to 32 MiB and 10,000 rows. CSV headers must be unique and
nonempty; every record must match the header width. Blank records, NUL bytes,
malformed quoting, nonfinite or nonpositive prices, duplicate or unordered
indices, and malformed signal vectors are rejected. No numeric-column
fallback, interpolation, filling, signal padding, or silent failed-component
substitution is allowed. `window` and `step` are integers from 1 to 10,000.

Select the price column explicitly (default `close`). Optional timestamps
must parse in increasing, unique order; naive timestamps are interpreted as
UTC. Parsed ordering is not independent source-vintage or availability-time
verification. Without timestamps, supplied row order is the only chronology
established.

The runner loads exactly three named canonical files under `code/`, ignoring
legacy `data/code` paths and ordinary module caches. The receipt binds the
executed strategy bytes, evaluator source, raw input bytes, configuration,
Python/NumPy/pandas versions, per-transition CSV, and reporting-block CSV.
Input and loaded-source changes detected during a run prevent a completion
receipt. The receipt is written last; a directory without it is incomplete.
Self-hashes establish internal custody only, not authorship, independent
validation, or scientific truth.

### Reproduce the synthetic software check

Use Python 3.11.9 with NumPy 2.3.5 and pandas 2.3.3, as pinned in
`requirements-institutional.txt`. The optional HTML chart also requires
`plotly==6.3.0`. Test execution uses pytest 9.1.0. These are the directly used
versions; the main institutional Ubuntu dependency lock remains the authority
for the full repository test closure.

From the repository root, using new output destinations:

```text
python dashboard/run_ensemble_meta_strategy.py --input examples/ensemble_research/synthetic_price_fixture.csv --input-kind synthetic --timestamp-column timestamp --window 65 --step 7 --fee-bps 10 --slippage-bps 5 --output-dir out/ensemble_research_check
python dashboard/visualize_ensemble_results.py --run-dir out/ensemble_research_check --output out/ensemble_research_check.html
python -m pytest -q tests/test_ensemble_walkforward_causality.py
```

The 96 synthetic prices use `100 + 0.15*i + 0.25*((i % 9)-4)` for
`i = 0..95`, serialized to two decimal places. Daily synthetic timestamps
begin at 2026-01-01 UTC. They are an explicit software fixture with 31 scored
transitions, not market observations or a source of investment evidence.
`--input-kind` records the operator's declaration. Its default is
`unverified_source`; neither choice independently authenticates the source.

The viewer requires a complete receipt, checks exact file hashes and byte
counts, rejects duplicate JSON members and unsupported evidence claims, and
reconciles row arithmetic, baselines, costs, counts, boundaries, and totals.
Rehashing an inconsistent score does not make it valid. Both CSV artifacts
remain available for reviewer inspection; the HTML presents cumulative
additive scores and the original run identity. The viewer does not re-run the
strategies or establish that the input came from a trusted market source.
