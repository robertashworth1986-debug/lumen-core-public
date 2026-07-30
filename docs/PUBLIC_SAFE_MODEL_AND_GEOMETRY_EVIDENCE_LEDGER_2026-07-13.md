# Public-Safe Model and Geometry Evidence Ledger

Generated: 2026-07-13

Purpose: give reviewers a single, conservative map of what LumenCore has tested, what won, what lost, and what remains unvalidated.

This ledger is an evidence boundary, not a claim of universal model superiority, field validation, realized savings, agency approval, investment performance, or scientific consensus.

## Evidence Levels

| Level | Meaning | Public posture |
| --- | --- | --- |
| `E0_EXPLORATORY` | Broad search or single-holdout comparison used to discover candidates. | May describe scope and conditional results with limitations. |
| `E1_LOCKED_REPLAY` | Candidate and baseline replay over frozen, hashed source routes. | May report route-level comparisons and named metrics; not field validation. |
| `E2_PREREGISTERED_HOLDOUT` | Protocol committed before results and evaluated on a frozen official holdout. | May report wins and losses exactly as observed. |
| `E3_INDEPENDENT_REPLICATION` | External party reproduces the protocol on independently held data. | May describe replication within the tested lane only. |
| `E4_FIELD_VALIDATION` | Operational owner validates performance and economics in a real workflow. | May describe bounded field outcomes under the signed protocol. |

## Verified Model Evidence

| Evidence | Level | Verified result | Safe interpretation |
| --- | --- | --- | --- |
| Broad frozen holdout benchmark, run `20260613T021546Z` | `E0_EXPLORATORY` | 2,172 of 2,312 series completed. Harmonic models were best on 304 series (14.0%); neural models on 480; naive/linear baselines on 447; tree models on 411; SARIMA on 530. Where a harmonic model won, its median RMSE reduction versus the runner-up family was 5.9%. | Harmonic models were useful on a material minority of heterogeneous series. They were not the overall winner and did not universally beat XGBoost, LightGBM, neural models, SARIMA, or naive baselines. |
| Locked source-conditioned replay | `E1_LOCKED_REPLAY` | 500 manifest rows, 349 ready routes, 2,303 candidate-baseline comparisons, and 7,154,095 per-baseline row exposures. | This is broad replay evidence. Row exposure is not a count of unique observations and must not be converted into a field or dollar claim. |
| XGBoost coverage | `E1_LOCKED_REPLAY` | 97 route comparisons, 50 candidate wins, 2,274,740 row exposures. | XGBoost was executed as a named baseline, not omitted. |
| LightGBM coverage | `E1_LOCKED_REPLAY` | 97 route comparisons, 51 candidate wins, 2,274,740 row exposures. | LightGBM is the other gradient-boosting baseline that must appear beside XGBoost. |
| Random Forest coverage | `E1_LOCKED_REPLAY` | 97 route comparisons, 48 candidate wins, 2,274,740 row exposures. | Random Forest was also executed in the locked replay. |
| Official EIA grid-wave benchmark | `E2_PREREGISTERED_HOLDOUT` | 14,704 official EIA panel rows. Holdout MASE: AR ridge p14 `0.479459`; EIA official day-ahead forecast `0.569405`; Lissajous `1.253218`; Kuramoto `1.253509`; Firefly `1.253944`. | Every wave/geometry candidate lost to both official baselines in this lane. The result falsifies promotion of the earlier synthetic Kuramoto winner to an EIA forecasting claim. |
| Official EIA residual mixture benchmark | `E2_PREREGISTERED_HOLDOUT` | XGBoost residual was selected on development only. Holdout mean MASE: XGBoost residual `0.212112`; direct LightGBM `0.235871`; direct XGBoost `0.264246`; AR ridge `0.491378`; EIA official forecast `0.579383`; seasonal naive `1.066175`. | Residual correction produced a strong aggregate result and beat all six baselines on mean MASE. It did not pass the full preregistered champion gate because its worst-authority regression versus AR ridge was `-0.079973`, beyond the `-0.05` guardrail. This supports prospective conditional routing, not a universal claim. |
| Frozen authority-specific EIA router | `E0_EXPLORATORY` with prospective collection pending | Historical routed mean MASE `0.196873` versus best fixed XGBoost residual `0.212112`, a `7.184%` relative improvement. The route map was frozen in commit `3130a9b` before targets dated on or after 2026-07-14. A live preflight read 14,711 rows and correctly sealed zero already-observed targets. | The historical routing delta is design evidence, not confirmation, because the historical window informed the route map. The implementation must accumulate future sealed predictions before the result can be promoted. |

## Aggregate Replay Reconciliation Gate

Two generated audit documents currently disagree on aggregate candidate wins:

- `docs/LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md` reports `1549`.
- `docs/BASELINE_GAUNTLET_COVERAGE_2026-07-03.md` reports `1540`.

Until the generator lineage is reconciled, public materials may cite the stable comparison count, per-baseline rows, and named model coverage, but must not cite one aggregate win count as canonical.

## Models Actually Included

The verified evidence stack includes these named model families where the cited artifacts say they executed:

- naive persistence and linear trend
- fixed and searched harmonic models
- multilayer perceptrons
- SARIMA
- XGBoost
- LightGBM
- Random Forest regression
- rolling mean, EWMA, seasonal naive, and Holt-Winters/ETS
- Kalman, extended Kalman, unscented Kalman, and particle filters
- Gaussian process regression
- ARIMA/SARIMAX

LSTM, TCN, small-transformer forecasting, DC power flow, OPF, and IEEE 39/118/300 bus tests remain implementation or dataset gates in the current baseline coverage artifact.

## Reviewer-Safe Claims

Allowed:

- "LumenCore tested harmonic candidates against XGBoost, LightGBM, neural, classical, and naive families across 2,172 completed frozen series in an exploratory broad benchmark."
- "Harmonic models led on 14.0% of those series and therefore appear useful as routed specialists, not universal replacements."
- "A preregistered official EIA holdout rejected the wave candidates in that grid-forecast lane; the negative result is retained in the public evidence record."
- "A separate preregistered residual test selected XGBoost on development data and achieved lower aggregate holdout MASE than the official EIA, AR, seasonal, direct XGBoost, and direct LightGBM baselines, but it did not clear the worst-authority guardrail."
- "A frozen authority-specific router showed a 7.184% exploratory historical improvement over the best fixed specialist; prospective collection begins with targets dated 2026-07-14, so no confirmatory routing claim exists yet."
- "The locked replay includes named XGBoost, LightGBM, and Random Forest comparisons with source-conditioned hashes and claim boundaries."

Blocked:

- "LumenCore beat XGBoost everywhere."
- "Kuramoto beat Kalman on the power grid" based only on synthetic or proxy evidence.
- "Seven million unique live rows prove field performance."
- Any realized-savings, trading-profit, safety, certification, or agency-validation claim without an E3 or E4 receipt.

## Source Artifacts

- `out/master_universe_v2/20260613T021546Z/UNDENIABLE_SCORECARD_V2.md`
- `docs/LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md`
- `docs/BASELINE_GAUNTLET_COVERAGE_2026-07-03.md`
- `docs/EIA_GRID_WAVE_CHAMPION_BENCHMARK_2026-07-13.md`
- `config/eia_grid_wave_champion_protocol_v1.json`
- `docs/EIA_GRID_RESIDUAL_MOE_BENCHMARK_2026-07-13.md`
- `config/eia_grid_residual_moe_protocol_v1.json`
- `docs/EIA_GRID_PROSPECTIVE_HYBRID_ROUTER_2026-07-13.md`
- `config/eia_grid_prospective_hybrid_router_protocol_v1.json`
