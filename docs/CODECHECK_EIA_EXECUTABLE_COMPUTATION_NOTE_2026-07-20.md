# A Bounded Reproducibility Capsule for Public-Data Benchmarking and Preserved Negative Gates

Author: Robert Ashworth

Repository: <https://github.com/robertashworth1986-debug/lumen-core-public>

Prepared (America/Chicago): 2026-07-20

## Companion Public Drafts

- Bounded preprint: [`PDF`](preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf) and [`Markdown source`](preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.md)
- Community request: [`author-side HOLD draft`](CODECHECK_COMMUNITY_REQUEST_DRAFT_2026-07-21.md)
- Immutable release: [`unpublished deterministic candidate plan`](release/CODECHECK_EIA_IMMUTABLE_RELEASE_PLAN_2026-07-21.md)

The request has not been posted. A stable public preprint identifier, immutable public source release, duplicate-request reconciliation, author review, and fresh action-time HumanUnlock remain required before one production request may be opened.

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
python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia
```

The runtime verifier reads `/etc/os-release`, the machine architecture, Python version, libc identity, deterministic environment variables, and dependency-lock hash before the capsule runs. The execution must recreate every path listed in the root `codecheck.yml`. The machine receipt records all observed facts, assertion outcomes, environment controls, source hashes, dependency closure, and privacy scan.

## Existing Internal Execution Evidence

The repository preserves an archived clean GitHub runner bundle at `evidence/reproducibility/github_run_29467557473`. Its six computational artifacts reconcile with the archived `SHA256SUMS`, and the receipt records 3/3 suites and 31/31 assertions passing on the authoritative environment.

That archive is operator-supplied reproducibility evidence. It is not independent execution. The `codechecker`, `report`, `certificate`, and external signature fields are intentionally absent until an external process supplies them.

The separate receipt at `evidence/reproducibility/codecheck_reviewer_runtime_receipt_d60ae723_20260721.json` records 10/10 exact runtime checks passing for Ubuntu 24.04, x86-64, CPython 3.11.9, glibc 2.39, deterministic environment controls, and the dependency-lock hash. It is also first-party evidence and changes no external gate.

## Separation From The Live Prospective Lane

This workflow does not read or report current prospective EIA prediction or settlement counts. It cannot promote the live router, satisfy its sample gates, or replace an evaluator-controlled prospective experiment. Current live status must be cited only from a dated, hash-verified runtime projection created under the frozen prospective protocol.

## Claim Boundary

A successful CODECHECK would confirm that the declared computations were independently executable and that the manifest outputs were recreated. It would not certify the scientific conclusions, establish field or production performance, prove savings, validate a patent, approve a government use, demonstrate profitable trading, or determine a company valuation.
