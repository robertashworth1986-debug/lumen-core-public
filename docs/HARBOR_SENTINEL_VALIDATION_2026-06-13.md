# HarborSentinel Synthetic Validation

Updated: June 19, 2026

## Evidence Boundary

This is a deterministic synthetic software benchmark. Inputs are generated
AIS/ADS-B and radar-like observations, not operational sensor data. Results do
not establish harbor, SSDS, adversarial, cybersecurity,
classified-environment, or field performance. The fixed kinematic comparator
is a simple reference implementation, not a claimed state-of-the-art system.
Runtime measurements are machine-specific observations.

## Design

Run `20260619T_NV063_V5_SOURCE_QUALITY_GATE` used 20 development scenarios to
select a threshold, then froze threshold 10.0 for 20 disjoint validation
scenarios in each of seven conditions:

- nominal, 24 tracks;
- congested, 96 tracks;
- 1.5x post-warmup sensor-noise shift;
- 2% benign point transmitter dropout;
- 20% benign burst transmitter dropout;
- combined congestion, noise shift, and dropout; and
- severe combined stress at 192 tracks, 2.5x noise, 5% point dropout, and 35%
  burst dropout.

The six injected event classes were route deviation, loiter, speed burst,
sharp turn, beacon silence, and beacon spoofing-like inconsistency. Alerts
were categorized as source-integrity, behavioral, or combined. Source-only
alerts were retained for review but were not automatically treated as threat
candidates.

The v5 scoring stream adds two guardrails that are computed from observations
only, not from ground-truth labels:

- a scene-wide source-quality gate based on median normalized radar/beacon
  disagreement, which reduces behavioral confidence during detected
  sensor-noise shift; and
- a five-observation beacon-loss review gate, which sends persistent
  cooperative-source loss to operator review without treating loss alone as a
  behavior-based threat candidate.

## Results

| Condition | Precision | Recall | F1 | Review false alerts / 10k normal points | Threat-candidate false alerts / 10k |
|---|---:|---:|---:|---:|---:|
| Nominal, 24 tracks | 0.948 | 0.957 | 0.953 | 71.4 | 71.4 |
| Congested, 96 tracks | 0.947 | 0.957 | 0.952 | 71.5 | 71.5 |
| Sensor shift, 1.5x | 0.944 | 0.956 | 0.950 | 76.5 | 76.5 |
| Benign point dropout, 2% | 0.948 | 0.958 | 0.953 | 71.2 | 71.2 |
| Benign burst dropout, 20% | 0.905 | 0.956 | 0.930 | 134.5 | 71.1 |
| Combined stress | 0.899 | 0.956 | 0.927 | 144.6 | 76.8 |
| Severe combined stress | 0.866 | 0.913 | 0.889 | 190.7 | 78.0 |

Nominal fixed-rule comparator F1 was 0.566. Nominal event recall was 1.000,
median detection delay was one simulation step, and explanation coverage was
1.000. The counted compact algorithmic state remains a software metric, not a
deployed system footprint; it excludes Python, runtime, buffering, networking,
and integration overhead.

All six nominal event classes had event recall 1.000. Median detection delay
was zero steps for route deviation and beacon spoofing-like inconsistency, one
step for loiter, speed burst, and sharp turn, and four steps for beacon
silence.

The measured source-degradation factor stayed near 1.0 under nominal and
congested runs, increased to about 1.27 under 1.5x sensor-noise shift and
combined stress, and capped at 2.25 under the severe breakdown test. This is a
useful diagnostic signal for degraded-source handling; it is not yet an
operational sensor-health claim.

## Interpretation

The nominal and congestion-only results support continued Phase I
investigation of compact streaming state and explainable anomaly categories.
Separating source-integrity from behavioral alerts helped under persistent
benign transmitter outage: review false alerts increased, while the
behavior-based threat-candidate false-alert measure remained near nominal.

The v5 source-quality gate materially improved the v4 breakdown region in
synthetic tests. The 1.5x sensor-shift review false-alert rate fell from 217.9
to 76.5 per 10,000 normal points; combined-stress review false alerts fell
from 268.1 to 144.6; and severe-stress review false alerts fell from 2,468.3 to
190.7. The severe condition is still a stress case, not an operating envelope:
source-integrity review volume rises, and threat-candidate recall drops as the
system avoids converting sensor/source failure into unsupported hostile-intent
claims.

These results narrow the next technical work:

- evaluate on representative public and authorized government data;
- add covariance-aware tracking and independent source-quality estimation;
- calibrate thresholds by density, sensor, and operating regime;
- detect degraded-sensor conditions and abstain, reduce confidence, or route
  to source-integrity review;
- test the beacon-silence delay versus false-alert tradeoff on representative
  observation gaps; and
- repeat frozen evaluation with independent reproducibility review.

## Reproduction

Run:

```powershell
.\.venv\Scripts\python.exe code\harbor_sentinel_validation_suite.py `
  --out out\harbor_sentinel_validation\<new-run-name> `
  --development-scenarios 20 `
  --validation-scenarios 20
```

The suite writes `summary.json`, `scenario_summary.csv`, `SCORECARD.md`, and a
SHA-256 manifest. The run directory should be preserved with the proposal
evidence record.
