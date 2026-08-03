# CS Dislocation MR Momentum-Gate Paper Protocol V1

## Status and authority

Protocol ID: `CS_DISLOCATION_MR_MOM_GATE_PAPER_V1`

Status: `PRECOLLECTION_LOCKED_PAPER_ONLY`

Normative machine-readable protocol:
`config/cs_dislocation_mr_mom_gate_paper_v1.json`

Normative validator:
`code/ops/VERIFY_CS_DISLOCATION_MR_MOM_GATE_PROTOCOL.py`

This document is a human-readable map. The JSON and its validator are
authoritative. The protocol is based on the sealed review in
`out/ops/alpha_edge_scientific_audit_20260719/ALPHA_EDGE_SCIENTIFIC_AUDIT_20260719.md`.
It declares no result. Its current result label is `NO_PROSPECTIVE_RESULT`.

`T0` is `2026-08-01T00:00:00Z`. A nonreplaceable, append-only receipt outside
this repository is required before confirmatory collection. A local mutable
file is not sufficient. Any code, parameter, schema, exclusion, fee, seed, or
timestamp change requires `CS_DISLOCATION_MR_MOM_GATE_PAPER_V2` and a new
prospective sample. Results cannot bridge versions.

## Immutable bindings

The protocol uses SHA-256 and canonical JSON with sorted keys, compact
separators, ASCII escaping, and UTF-8 encoding. Its self-hash is computed with
`immutable_bindings.protocol_payload_sha256` set to JSON `null`.

| Binding | SHA-256 |
|---|---|
| Canonical protocol payload | `d1d60a2311c5b6958e4682de1f4f8a0b110a42ec944dfc7c075b8374b3567370` |
| Sealed scientific audit | `c8f928811514dd9fd703fc68dbd103243c75bebafa928e0974fdd7b6a0367e35` |
| Validator implementation | `0d11be70b3f737ea4ee53eecd089b2803f683be40f3e16c544fe0eb395ecfac8` |
| Reviewer dependency lock | `e2f514c3c1c10a0278d4ef1147fee1cdd5b1126e5d34d8ee88bba1c4e1d14b18` |
| Symbol exclusions payload | `f6729a0031b3cc23df198168b741e40bc6a2fea6547dbe2fccb488d1248f6c53` |
| Fee schedule payload | `532a024b4db84fd47ff50f8ea696630bcc2c23498408e810294b80298842e765` |
| Raw-data schema payload | `75ff9360830efe7a2d4f957a3c3c826d4bb52c1fca3849121016ffed510375cf` |
| Candidate-family payload | `7345f0e0fb406ec4b66917cfeb9b7516316f99e1d6af10b8c0d070bd323520f0` |
| Random-seed payload | `02fc2e9a18dee6ef7fc31154b059c691a2a87b073d2533510ad5100aa4b172ae` |
| Start-timestamp payload | `7b4462783e0bef1ec11560168b5f5d1df701a8555a1be016eaa487515b960a60` |

The validator also contains independent hashes for every semantic JSON
section. Recomputing the visible protocol and inline hashes after a mutation
does not make a changed V1 valid.

## Absolute boundaries

The lane is long/flat USD spot, paper only, at nominal NAV of $100,000. The
validator has no collector, network, paper-fill, credential, order, or trading
capability. Any collector must be separately approved, public, unauthenticated,
and read-only.

V1 prohibits all of the following:

- authenticated or private APIs;
- order endpoints and exchange sandbox orders;
- live orders or capital exposure;
- margin, leverage, shorting, borrow, or funding;
- network contact or paper-fill generation by the validator;
- optional stopping, early promotion, and unregistered subgroup promotion;
- cross-version result bridging.

## Point-in-time universe and clock

At 00:00 UTC on day one of each month, freeze every USD spot pair in the raw
public instrument snapshot and apply the hashed stablecoin, fiat, and leveraged
token exclusions. Eligibility uses only information available before the
freeze and requires:

- listing age at least 180 days;
- prior 30-day hourly-bar completeness at least 95%;
- prior 30-day median daily notional at least $5 million;
- prior 7-day median quoted spread no more than 25 bps.

Keep the top 30 by prior 30-day median daily notional, breaking ties by symbol.
With fewer than 10 assets, remain in cash. New assets enter only at the next
monthly freeze. Delisted and suspended assets remain in history and are closed
at the last executable bid with an additional 100-bp penalty.

The decision clock uses completed one-hour bars. Features for a bar ending at
`t` must be sealed by `t+60s`. The earliest fill is the first observed executable
public quote at or after `t+90s`. A parallel five-minute delayed-quote path is
mandatory. Source, receipt, bar-end, feature-seal, decision, quote, and paper
fill timestamps and source hashes are required. Missing or revised data never
backfill prior decisions.

## Exact primary signal

For each asset, fit a trailing 60-day hourly OLS model ending strictly before
the decision bar:

`r_i = alpha_i + beta_BTC*r_BTC + beta_EW*r_equal_weight_ex_i + epsilon_i`

At least 1,000 complete training hours are required. Sum the last six residuals
as `D`. Standardize against the trailing 720 values using
`z=(D-median)/(1.4826*MAD)`; zero MAD means no signal.

Primary entry `full_e2p0_m3_h12` requires every condition:

1. `z_t <= -2.0`.
2. `z_t - z_(t-1) >= 0.25`.
3. The last three residuals sum to more than zero.
4. The implied move to `z=-0.5` is at least 2x modeled round-trip cost.
5. Data, spread, capacity, and portfolio gates pass.

Candidates rank by implied edge less modeled round-trip cost. Hold no more than
five positions at 10% NAV each, with gross exposure no more than 50% and no
leverage. Exit on the first of `z >= -0.5`, two consecutive negative three-hour
momentum observations, 12 hours, or a 2.5x trailing 24-hour realized-volatility
adverse move. Entries and exits use the same completed-bar delayed-fill rule.

## All 18 attempts

The 12 full variants are the complete grid entry magnitude
`{1.5, 2.0, 2.5}` x momentum window `{1h, 3h}` x maximum hold `{6h, 12h}`:

`full_e1p5_m1_h6`, `full_e1p5_m1_h12`, `full_e1p5_m3_h6`,
`full_e1p5_m3_h12`, `full_e2p0_m1_h6`, `full_e2p0_m1_h12`,
`full_e2p0_m3_h6`, `full_e2p0_m3_h12`, `full_e2p5_m1_h6`,
`full_e2p5_m1_h12`, `full_e2p5_m3_h6`, and `full_e2p5_m3_h12`.

The six additional registered tests are:

- `ablation_dislocation_only`;
- `ablation_momentum_only`;
- `ablation_no_cost_edge_gate`;
- `ablation_no_spread_capacity_gate`;
- `ablation_rank_enter_non_data_gates_removed`;
- `placebo_time_shift_plus_24h`.

Every attempt counts from the first run, including failed or abandoned attempts.
Only frozen primary `full_e2p0_m3_h12` is promotion-eligible prospectively.
Historical selection is confined to train/validation inside each outer fold;
an outer-test-selected variant cannot be promoted.

## Holdouts and baselines

Historical work requires at least eight disjoint outer folds: 365 days train,
90 validation, 90 test, advancing 90 days, with 24-hour purge and embargo at
each boundary. Betas, scales, liquidity thresholds, empirical slippage, and
variant choice fit on train/validation only. Each outer test is used once.
History is descriptive below 720 OOS calendar days or 250 closed OOS trades.

The six baselines use the same point-in-time universe and clock:

1. Cash at 0%.
2. Monthly equal-weight eligible universe with the same cost model.
3. Volatility-matched BTC buy-and-hold.
4. Top-quintile 24-hour cross-sectional momentum with the same risk/cost limits.
5. Dislocation-only ablation.
6. Event-matched randomized-entry placebo using the preregistered seed.

Cash and equal-weight are the two primary contrasts. Secondary contrasts remain
registered but cannot promote a claim.

## Execution accounting

Per-side fees are the maximum of the public zero-volume taker fee frozen at
`T0` and 40 bps. Buys reference observed ask and sells observed bid, then add
per-side slippage equal to the maximum of 5 bps, the training-only prior-30-day
p75 60-second adverse markout, and square-root impact.

The stress path doubles fees, observed spread, and slippage and uses the
five-minute delayed quote. Entry, resize, exit, stop, suspension, and forced
delisting close all incur costs. Reports must include gross/net P&L, one-way
turnover, cost drag, holding time, and fill delay.

Every paper order is limited to the minimum of $10,000, 1% of trailing
five-minute median dollar volume, and 10% of visible depth within 25 bps.
Missing depth means no trade. Capacity curves are required at $25,000,
$100,000, and $500,000 NAV, and evidence applies only where every order passes.

## Inference and sample gates

The primary unit is UTC daily net active return. The protocol requires 20,000
stationary-block bootstrap resamples with expected block length seven days,
two-sided 95% intervals, a protocol-hash-derived deterministic seed, and HAC
lag-7 sensitivity.

Family-wise error covers 18 attempts x two primary baselines = 36 contrasts.
Use Romano-Wolf max-t at alpha 0.05. Only if unavailable, use Holm over all 36
and disclose the substitution. Secondary diagnostics may use BH FDR at
`q<=0.05` but cannot promote. Deflated Sharpe uses all 18 attempts and requires
probability of skill at least 0.95.

| Gate | Minimum | Claim effect |
|---|---|---|
| Integrity | 30 days, 50 closes, ledger checks | `PAPER_PIPELINE_OBSERVED` only |
| Preliminary | 90 days, 125 closes, 60 active days | Monitoring only; no alpha claim |
| Confirmatory | 180 days, 250 closes, 120 active days, 20 assets, 30 closes in each of four BTC trend x volatility cells | Statistical evaluation only |
| Durability | 365 days, 500 closes, 50 closes per regime cell, independent reproduction | Bounded wording eligible only if all promotion gates pass |

Short regime cells extend collection to 365 days. Thresholds never relax.

## Eleven promotion gates

All 11 machine-readable gates must pass:

1. Zero future-data, hash, parameter, universe, or replacement violations.
2. At least 99.5% completeness, zero parse/duplicate-ID failures, and lifecycle mismatch no more than 0.1%.
3. Confirmatory sample gate passed.
4. Positive daily net active return versus cash and equal-weight, positive 95% block-bootstrap lower bounds, and adjusted `p<=0.05`.
5. Positive net-Sharpe 95% lower bound and deflated-Sharpe skill probability at least 0.95.
6. Positive cumulative net return under base, 2x-cost, and five-minute latency.
7. Modeled costs below 50% of gross profit and annualized one-way turnover no more than 100x NAV.
8. Drawdown no more than 15%, asset P&L concentration no more than 25%, and regime concentration no more than 60%.
9. Every order passes capacity and p95 decision-seal latency is no more than 60 seconds.
10. Full exceeds dislocation-only, no-cost-gate, and rank-and-enter; a momentum claim additionally needs a positive adjusted 95% lower bound versus dislocation-only.
11. An independent raw-snapshot rerun reproduces decisions exactly and daily net returns within 1 bp/day.

The only success label is `PROSPECTIVE_PAPER_EDGE_SUPPORTED`, bounded to the
tested venue, assets, dates, NAV, and frozen execution assumptions. It is not a
live-alpha, institutional-capacity, large-fund, profitable-live, or universal
claim.

## Kill policy

Immediate invalidation applies to future timestamps, replaced raw data,
non-point-in-time membership, parameter/code/hash drift, omitted variants,
duplicate IDs, authenticated/private API use, order submission, or capital
exposure.

Pause after three consecutive days below 99% observation completeness, p95
decision-seal latency above 90 seconds, or lifecycle mismatch above 1%. Stop
for harm at 15% prospective drawdown.

Exactly one planned harm/futility interim is allowed at the later of 90 days or
125 closes. Stop for futility when conditional power is below 10% or the 95%
upper bound versus cash is no more than zero. There is no early promotion.

Retire V1 if any final promotion gate fails, costs meet or exceed gross profit,
stress cumulative return is non-positive, or a simpler preregistered ablation
materially dominates. A modification requires a new version and sample.

## Validation

Run only the static validator:

```powershell
python code/ops/VERIFY_CS_DISLOCATION_MR_MOM_GATE_PROTOCOL.py
```

Exit code `0` means the static preregistration matches every seal. A nonzero
exit is fail-closed and reports every detected error. Validation does not
collect data, contact an exchange, create paper fills, submit orders, expose
capital, or establish any trading result.
