# Federal Research Path - June 13, 2026

## Decision

The highest-value near-term path is Navy topic NV063, HarborSentinel:
explainable streaming anomaly detection for congested maritime environments.
NV061 predictive movement is the second-choice topic. The trading stack remains
a research program, not a funding or live-profit claim.

The reason is evidence fit. The stack currently has stronger support for
compact state, anomaly and regime detection, abstention, explanations, APIs,
and immutable evidence than it has for repeatable forecast alpha.

## Current Evidence

| Artifact | Result | Claim boundary |
|---|---|---|
| Master breadth `20260613T021546Z` | 2,172 successful series, 9 models, 5 families | Single chronological holdout; scale evidence only |
| Hybrid V7 development `20260613T040000Z_dev_v71` | 80 series, median MAE gain 0%, 0 robust gates | Development batch |
| Hybrid V7 validation `20260613T041000Z_validation_v71` | 80 untouched series, 11 positive, median MAE gain 0%, 0 robust gates | No repeatable trading or universal forecasting edge |
| HarborSentinel validation `20260613T044500Z_nv063_validation_v1` | Mean precision 0.939, recall 0.919, F1 0.929, baseline F1 0.613 | Synthetic software evidence only |
| HarborSentinel event result | Event recall 1.000, median delay 1 step | 540 injected events across 30 deterministic scenarios |
| HarborSentinel footprint | 139 bytes maximum algorithmic state per track; 100% alert explanation coverage | Does not include Python runtime or integration overhead |

The HarborSentinel validation used disjoint seeds after threshold development.
It covered route deviation, loitering, speed burst, sharp turn, beacon silence,
and beacon spoofing-like inconsistency using AIS/ADS-B and radar-like inputs.
Operational harbor, SSDS, adversarial, cybersecurity, and field claims remain
unproven.

## Legacy Claim Audit

The historical `333/673` meta-router result is not submission-grade. Its
features were calculated from the full series, including the outer test period,
while its labels depended on test RMSE. The downstream hybrid router also used
target-dataset outcome labels. Those numbers remain in the evidence package for
traceability but are explicitly excluded from proposal performance claims.

The leakage-resistant V7 result is negative but valuable: it rejects the
universal-edge story and demonstrates a system that can abstain. The bounded
correction policy removed catastrophic harmonic extrapolations, but it did not
produce a robust median forecasting improvement.

## Geometry And Phase Work

The LumaUniverse family and provenance audit is recorded in
`docs/LUMAUNIVERSE_RESEARCH_EVIDENCE_AUDIT_2026-06-18.md`. Fungus, bee, wolf,
bird, and hibernation paths are currently candidate hypotheses, not completed
findings: no implementation or frozen run under those names was located in the
fetched Git refs or current workspace.


Use the old concepts only when they map to a falsifiable mathematical role:

- Phase locking: spectral phase stability used as a past-only activation gate.
- Brachistochrone: a square-root recency weighting ablation, not a physical
  fastest-path result.
- Frobenius mathematics: matrix norms or regularization when a matrix model
  requires them.
- Non-Euclidean methods: hyperbolic or manifold embeddings only for a defined
  graph or trajectory task and only against Euclidean baselines.
- Vortex, bubble lattice, and flower-of-life language: do not place in a
  proposal or trading claim without equations, a mechanism, preregistered
  tests, and evidence that beats simpler alternatives.

The relevant research tools are surrogate time-series tests, phase-randomized
nulls, walk-forward evaluation, conformal calibration, and explicit
multiple-comparison control. These methods can test a phase hypothesis; they
do not validate it in advance.

## EMP And Nuclear Work

The AIRS material in iCloud is a concept for adaptive EMP mitigation:
sensing, anomaly detection, bounded response, and recovery. No hardware,
electromagnetic simulation, component characterization, chamber testing, or
independent DoD validation was found. Preserve it as a future hardware research
track, but do not make it the immediate funding lead.

To become fundable, AIRS needs a named threat waveform, protected subsystem,
response-time requirement, circuit or field model, component limits, test
article, baseline protection method, and measurable pass/fail protocol.

## Grant Execution

Primary topic: Navy NV063, HarborSentinel.

Secondary topic: Navy NV061, TrackCast.

As of June 13, 2026, Navy Release 3 is in pre-release. It opens June 24, 2026
and closes July 22, 2026 at 12:00 p.m. Eastern Time. The NV063 draft is
generated locally, but submission is correctly blocked until:

1. SAM.gov status, expiration date, and verification timestamp are current.
2. DSIP account and submitter permissions are verified.
3. CMMC Level 2 self-assessment, ITAR/EAR, foreign ownership and foreign
   national review, and topic security requirements are completed.
4. The technical volume is reviewed against the final component instructions.
5. The package is approved by the human submitter after the opportunity opens.

The official Navy instructions set a maximum of $315,000: Phase I Base up to
$200,000 for exactly six months and Phase I Option up to $115,000 for exactly
six months. The option must be included within the ten-page Technical Volume.

## Phase I Research Plan

1. Freeze operational definitions, anomaly taxonomy, baselines, and acceptance
   thresholds before representative-data evaluation.
2. Add public AIS data and notional radar correlation without changing the
   frozen synthetic validation result.
3. Measure class-level precision, recall, false alerts per track-hour, event
   delay, confidence calibration, memory, latency, and congestion scaling.
4. Add adaptive-baseline poisoning and persistent-threat tests.
5. Define an SSDS-facing message and deployment boundary without claiming
   completed integration.
6. Preserve all failures, seeds, manifests, and supersession records.

## Canonical Artifacts

- `out/hybrid_edge_v7/20260613T041000Z_validation_v71/`
- `out/harbor_sentinel/20260613T044500Z_nv063_validation_v1/`
- `out/grants/dod_sbir_26bz_nv063/20260505T121657Z/`

The ledgers preserve superseded runs. `20260613T031912Z` through
`20260613T032053Z` predate the frozen V7.1 governor policy.
`20260613T043000Z_nv063_synthetic_v1` is superseded because of a nominal-track
labeling defect found by the per-class event audit.

## Primary Sources

- Navy Release 3 topics and schedule:
  https://www.navysbir.com/topics26_3.htm
- NV063 official topic record:
  https://www.sbir.gov/topics/12759
- NV061 official topic record:
  https://www.sbir.gov/topics/12757
- Adaptive conformal inference for time series:
  https://arxiv.org/abs/2202.07282
- Sequential predictive conformal inference:
  https://arxiv.org/abs/2212.03463
- Surrogate time-series methodology:
  https://arxiv.org/pdf/chao-dyn/9909037
- IAAFT surrogate caveats:
  https://arxiv.org/pdf/physics/9905021
- Phase-walk analysis:
  https://arxiv.org/pdf/1806.02273
