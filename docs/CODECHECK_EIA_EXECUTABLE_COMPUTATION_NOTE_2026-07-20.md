# A Bounded Reproducibility Capsule for Public-Data Benchmarking and Preserved Negative Gates

Author: Robert Ashworth

Repository: <https://github.com/robertashworth1986-debug/lumen-core-public>

Prepared (America/Chicago): 2026-07-20

## Companion Public Drafts

- Bounded preprint: [`PDF`](preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf) and [`Markdown source`](preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.md)
- Community request: [`author-side HOLD draft`](CODECHECK_COMMUNITY_REQUEST_DRAFT_2026-07-21.md)
- Immutable source: [`public commit 1c0eb517`](https://github.com/robertashworth1986-debug/lumen-core-public/commit/1c0eb51754beffac6f4df484914e35efc21c253f)

The request has not been posted. The commit-pinned preprint and source satisfy
the author-side stable-reference and immutable-source gates. A fresh
duplicate-request reconciliation, a collision-free Launch Pad identifier,
Robert's review, and fresh action-time HumanUnlock remain required before one
production request may be opened.

## Abstract

This note defines one narrow executable-computation target. The workflow replays two frozen benchmarks derived from public U.S. Energy Information Administration EIA-930 data and one deterministic synthetic falsification suite. It checks a fixed set of facts, emits a machine-readable receipt and scoped software bill of materials, and preserves failed promotion gates.

The question is deliberately limited: can an independent executor recreate the six files named in `codecheck.yml` and reconcile the declared facts under the recorded environment? A successful execution would establish executable reproducibility for this bounded workflow. It would not establish scientific validity, field performance, external validation of the live prospective router, agency approval, realized savings, universal model superiority, patent scope, trading performance, or company valuation.

## Computational Question

Can the named source, frozen input, exact dependency closure, and deterministic controls reproduce all 31 assertions across the following three suites?

1. `eia_wave_frozen_holdout`
2. `eia_residual_frozen_holdout`
3. `mda_open_set_v2`

The frozen protocol is [`reviewer_reproducibility_protocol_v1.json`](../config/reviewer_reproducibility_protocol_v1.json). It is the authority for expected facts, tolerances, exclusions, and claim boundaries.

## Inputs And Environment

- Frozen measured-data input: `evidence/reproducibility/eia_grid_validation_panel_20260713.json.gz`
- Publisher: U.S. Energy Information Administration
- Product: Form EIA-930 daily demand and day-ahead demand forecast by balancing authority
- Frozen row count: 14,704
- Authoritative runtime: Ubuntu 24.04 x86-64, CPython 3.11.9, glibc 2.39
- Dependency closure: 18 exact packages in `requirements-reviewer-ubuntu-py311.lock`
- Installer controls: `--require-hashes` and `--only-binary=:all:`
- Determinism controls: `PYTHONHASHSEED=0`, UTC, and bounded thread settings

The code is MIT licensed. The EIA-derived input remains subject to the EIA Copyrights and Reuse Policy and API Terms of Service described in the repository `LICENSE`; no EIA endorsement is implied.

## Frozen Results To Reproduce

### EIA wave holdout

- Panel rows: 14,704
- Holdout rows: 1,525 across eight balancing authorities
- Selected candidate: `lissajous_phase_paths`
- Best declared strategy: `autoregressive_ridge_p14`
- Best MASE: 0.47945937271811834
- Kuramoto MASE: 1.253508683225091
- Promotion gate: failed
- Field validation complete: false

This suite preserves a loss by the geometry candidate. It is not presented as a champion result.

### EIA residual holdout

- Panel rows: 14,704
- Holdout rows: 1,176 across eight balancing authorities
- Selected candidate and best declared strategy: `xgboost_residual`
- Best MASE reference: 0.21211186326437864
- Baseline comparisons: six
- Promotion gate: failed
- Coverage gate: failed
- Field validation complete: false

The aggregate metric is positive relative to the declared baselines, but the full protocol did not promote the model. Both facts must remain together.

### MDA open-set v2

- Deterministic fixtures: 128
- Holdout fixtures: 36
- Candidate micro-F1: 0.9433962264150945
- Supported coverage: 0.9583333333333334
- Unsupported mapping rate: 0.0
- Promotion gate: failed
- Operational or field claim allowed: false

This is a deterministic synthetic falsification suite, not measured operational evidence.

## Preserved Amendment And Failures

The first clean Ubuntu replay exposed a missing ignored panel path. The second passed 30 of 31 assertions but measured a 0.4269440625% XGBoost CPU histogram MASE drift relative to the Windows reference while preserving selected-model identity, comparison count, coverage state, and every gate outcome.

After observing that failure, the protocol was amended to permit at most 1% relative drift for the XGBoost residual MASE only. Structural, identity, coverage, and decision assertions remain exact. This tolerance is a disclosed post-observation portability amendment, not a preregistered scientific threshold. Failed GitHub run identifiers remain recorded in the protocol.

## Reproduction

From the repository root on the authoritative runtime:

```bash
python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only
python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py
python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --requirement requirements-reviewer-ubuntu-py311.lock
python -m pip check
python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia --publish
```

The runtime verifier reads `/etc/os-release`, the machine architecture, Python version, libc identity, deterministic environment variables, and dependency-lock hash before the capsule runs. The execution must recreate every path listed in the root `codecheck.yml`. The machine receipt records all observed facts, assertion outcomes, environment controls, source hashes, dependency closure, and privacy scan.

## Existing Internal Execution Evidence

The frozen source preserves three first-party receipts under
`evidence/reproducibility/codecheck_reviewer_container_1c0eb517_20260721/`.
The reviewer receipt records 3/3 suites and 31/31 assertions passing. The
runtime receipt records the exact Ubuntu 24.04, x86-64, CPython 3.11.9,
glibc 2.39, deterministic-environment, and dependency-lock checks. The
container receipt records a no-cache operator-controlled rebuild and replay.

These receipts are author-operated reproducibility evidence only. They do not
establish independent execution or external validation. The `codechecker`,
independent report, certificate, and external-signature fields remain absent
until an external process supplies them.

## Separation From The Live Prospective Lane

This workflow does not read or report current prospective EIA prediction or settlement counts. It cannot promote the live router, satisfy its sample gates, or replace an evaluator-controlled prospective experiment. Current live status must be cited only from a dated, hash-verified runtime projection created under the frozen prospective protocol.

## September 21 constraint review: measured improvement, promotion still held

The unchanged July residual protocol was executed again on September 21. The
[pre-run review plan](../config/eia_constraint_replay_review_v1.json) and runner
were committed at `3404bb2` before this replay. Seven development candidates and
six holdout comparators were retained; no parameters, splits, thresholds or
selected-model identity were changed using holdout performance. This supports
active outcome 2: a reviewable external-validation or paid-pilot decision.

This is an **author-operated replay of a previously inspected historical panel**.
It is not a new untouched holdout, a current live-data capture, an as-issued
forecast archive, an independent validation, or a production promotion.

The selected `xgboost_residual` and EIA's archived day-ahead forecast series were scored
on exactly the same 1,176 authority-days from January 1 through July 12, 2026,
across eight balancing authorities. Daily observations and cross-authority
results are correlated; 1,176 rows are not 1,176 independent experiments.

| Metric on identical rows | EIA day-ahead forecast | Selected residual candidate | Descriptive change |
|---|---:|---:|---:|
| Mean absolute forecast error | 36,568.783 MWh | 15,979.087 MWh | 56.304% lower |
| WAPE | 3.53355% | 1.54402% | 1.98953 percentage points lower |
| 95th-percentile absolute error, nearest rank | 99,674.000 MWh | 56,377.064 MWh | 43.439% lower |
| Primary mean seasonal MASE | 0.579383 | 0.211206 | Lower on the measured panel |

The primary metric remains seasonal MASE. The supplemental MAE, WAPE, tail and
subgroup tables diagnose the already selected candidate; they do not add new
superiority tests. The selected candidate has the lowest aggregate MASE among
the six original baselines, including direct LightGBM (0.235871) and direct
XGBoost (0.248338). This is an actual candidate-versus-comparator result, not a
comparison of two baselines presented as LumenCore performance. Against the
strongest aggregate algorithmic baseline, direct LightGBM, the candidate
reduces MAE by 10.602% (17,874.172 to 15,979.087 MWh).

| Authority | Paired days | MAE reduction vs EIA | p95 absolute-error reduction vs EIA |
|---|---:|---:|---:|
| CISO | 164 | 85.282% | 74.355% |
| ERCO | 190 | 6.731% | 19.634% |
| ISNE | 193 | 64.590% | 49.507% |
| MISO | 107 | 53.056% | 39.584% |
| NYIS | 135 | 29.378% | 16.924% |
| PJM | 164 | 42.194% | 40.123% |
| SWPP | 133 | 65.093% | 44.516% |
| TVA | 90 | 22.423% | 27.240% |

Every authority is reported, not just favorable subsets. These descriptive
results are candidates for investigation, not eight independently validated
utility engagements. Across the original 52 authority-month comparisons with
EIA, 45 improve and seven worsen on seasonal MASE. The favorable whole-authority
and whole-month averages do not imply every observation or operating regime wins.

**The original promotion gate still fails.** MISO, NYIS, SWPP and TVA have fewer
than the required 150 common days; the minimum is 90. Against autoregressive
ridge, SWPP's authority-month-weighted seasonal-MASE regression is 0.074058,
exceeding the original maximum tolerated regression of 0.05. The aggregate
winner therefore remains on HOLD. Do not loosen either rule to promote this run.

The [official EIA-930 instructions, page 9](https://www.eia.gov/survey/form/eia_930/instructions.pdf)
allow a balancing authority to report its ordinary business forecast even when
its scope differs from EIA physical demand. The DF series is therefore a
**descriptive archival comparator**, not an established matched operational
incumbent. A scope-adjustment or reporting difference could explain part of the
measured residual; no underlying utility forecast deficiency is established.

The inputs are historical EIA records and may contain revisions. The code's
history-only features pass a target-actual leakage test, but that does not prove
that every lag and target forecast was available at the real decision cutoff.
The next evaluator must verify as-of timestamps, source licensing, reporting
latency, demand/forecast scope, and missingness on fresh prospective records.

**Forecast error in MWh is not electricity saved.** Economic value requires a
buyer-approved action policy and cost function, service-equivalent comparisons,
implementation and integration costs, and actual operating outcomes. Multiplying
this error percentage by utility spending or sector revenue is unsupported.
A small genuine net cost reduction can matter: 0.1% of an illustrative $1 billion
addressable annual cost is $1 million before implementation costs. That arithmetic
is a scenario, not a valuation or savings result from this experiment.

### Retained replay and reproduction

- [Full benchmark and all original gates](../evidence/reproducibility/eia_constraint_review_20260921/benchmark.json)
- [All-authority and all-month diagnostic summary](../evidence/reproducibility/eia_constraint_review_20260921/constraint_summary.json)
- [All development and holdout prediction rows](../evidence/reproducibility/eia_constraint_review_20260921/predictions.csv.gz)
- [Exact runtime versions](../evidence/reproducibility/eia_constraint_review_20260921/environment.json)
- [Input/code/output manifest](../evidence/reproducibility/eia_constraint_review_20260921/manifest.json)

Manifest SHA-256:
`d89c5503a5191531b66bedd22d5cda6d316a7fa12e611cff1979eb926b47f92f`.
The six input identities and four output files verified after execution. Python
3.12.14 and the package versions are recorded. The observed candidate MASE equals
the earlier Ubuntu replay (0.2112062642583228); this supplemental environment is
not the authoritative Python 3.11.9 CODECHECK container and does not replace it.

Verify the committed packet without numerical dependencies:

```bash
python code/ops/REPLAY_EIA_CONSTRAINT_REVIEW.py --verify
```

Replay with the recorded numerical dependencies and bounded thread controls;
choose a new directory so retained evidence cannot be overwritten:

```bash
PYTHONHASHSEED=0 TZ=UTC OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python code/ops/REPLAY_EIA_CONSTRAINT_REVIEW.py --run-dir out/eia_constraint_review
```

Ten targeted tests passed, covering the original candidate registry, target-actual
feature isolation, correction/abstention safety, selection rule, exact pair
alignment, adverse-tail preservation, and rejection of altered evidence.

### Additional temporal test: July 13–September 8 archive

A second [plan](../config/eia_later_window_review_v1.json) and exact later EIA
snapshot were frozen at `8afe493` before scoring. The original model selection,
features, fit parameters and 2024–2025 training/development data remained
unchanged. The selected residual model was evaluated on subsequent July
13–September 8 dates; no 2026 labels entered model fitting. Earlier 2026 values
were permitted as causal lag features under the original protocol.

This is an additional retrospective temporal test. The recovered September 9
archive had already been analyzed with other models, so this work does not
claim untouched data, new live telemetry, prospective issuance or independence.

| Same 285 retained authority-days | MAE | Mean seasonal MASE |
|---|---:|---:|
| Selected XGBoost residual model | 16,107.044 MWh | 0.200574 |
| Direct LightGBM baseline, identical features | 19,765.544 MWh | 0.268516 |
| Direct XGBoost baseline, identical features | 20,956.566 MWh | 0.290483 |
| Archived EIA DF comparator | 35,092.867 MWh | 0.558483 |

The candidate's MAE is **18.509% lower than direct LightGBM**, the strongest
aggregate algorithmic baseline; its original-window reduction was 10.602%.
Versus the scope-unmatched archival DF comparator, MAE is 54.102% lower and
nearest-rank p95 absolute error is 40.702% lower (94,670 to 56,137.113 MWh).
These percentages measure forecast error, not energy or cost savings.

**Coverage and promotion remain HOLD.** Only 285 of 464 possible authority-days
(61.42%) survive the original target and 28-day forecast-history requirements.
Retained counts are CISO 58, ERCO 24, ISNE 58, MISO 25, NYIS 27, PJM 58 and TVA 35;
**SWPP contributes zero eligible rows**. Its original regression against ridge
is not resolved by this absence. Seven authorities and at most 58 days do not
satisfy eight authorities with 150 days each. Only 18 authority-month units are
available, below the 40-unit gate. The favorable aggregate comparisons are
conditional on this missingness pattern and cannot be extended to excluded rows.

The [full later benchmark](../evidence/reproducibility/eia_constraint_later_window_20260921/benchmark.json),
[all predictions](../evidence/reproducibility/eia_constraint_later_window_20260921/predictions.csv.gz),
[manifest](../evidence/reproducibility/eia_constraint_later_window_20260921/manifest.json)
and [exact archived source rows](../evidence/reproducibility/eia_daily_20260713_20260908_selected.json.gz)
retain every comparator and modeled authority. The frozen numerical environment
is the same one recorded for the preceding replay. Verify without model fitting:

```bash
python code/ops/REPLAY_EIA_LATER_WINDOW.py --verify
```

The next useful constraint is now explicit: secure a scope-matched, time-stamped
buyer baseline and complete forecast-history capture, then test this unchanged
candidate prospectively under the buyer's error and cost policy. More repeated
runs of these archives cannot fill those evidence gaps.

## Claim Boundary

A successful CODECHECK would confirm that the declared computations were independently executable and that the manifest outputs were recreated. It would not certify the scientific conclusions, establish field or production performance, prove savings, validate a patent, approve a government use, demonstrate profitable trading, or determine a company valuation.
