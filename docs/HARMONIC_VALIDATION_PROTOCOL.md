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
