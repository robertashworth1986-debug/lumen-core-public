# HarborSentinel Synthetic Validation

Date: June 13, 2026

## Evidence Boundary

This is a deterministic synthetic software benchmark. Inputs are generated
AIS/ADS-B and radar-like observations, not operational sensor data. Results do
not establish harbor, SSDS, adversarial, cybersecurity,
classified-environment, or field performance. The fixed kinematic comparator
is a simple reference implementation, not a claimed state-of-the-art system.
Runtime measurements are machine-specific observations.

## Design

Run `20260613T_NV063_V4_FRESH_DEV20_VAL20` used 20 development scenarios to
select a threshold, then froze threshold 8.0 for 20 disjoint validation
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

## Results

| Condition | Precision | Recall | F1 | Review false alerts / 10k normal points | Threat-candidate false alerts / 10k |
|---|---:|---:|---:|---:|---:|
| Nominal, 24 tracks | 0.942 | 0.919 | 0.930 | 77.3 | 76.9 |
| Congested, 96 tracks | 0.940 | 0.917 | 0.928 | 79.0 | 78.9 |
| Sensor shift, 1.5x | 0.852 | 0.923 | 0.886 | 217.9 | 182.4 |
| Benign point dropout, 2% | 0.941 | 0.919 | 0.930 | 76.3 | 76.2 |
| Benign burst dropout, 20% | 0.911 | 0.918 | 0.914 | 119.0 | 76.9 |
| Combined stress | 0.823 | 0.924 | 0.871 | 268.1 | 192.4 |
| Severe combined stress | 0.340 | 0.943 | 0.500 | 2468.3 | 1580.9 |

Nominal fixed-rule comparator F1 was 0.608. Nominal event recall was 1.000,
median detection delay was one simulation step, and explanation coverage was
1.000. The counted compact algorithmic state was at most 139 bytes per track;
that count excludes Python, runtime, buffering, networking, and integration
overhead.

All six nominal event classes had event recall 1.000. Median detection delay
was zero steps for route deviation and beacon spoofing-like inconsistency, one
step for loiter, speed burst, and sharp turn, and 11 steps for beacon silence.

## Interpretation

The nominal and congestion-only results support continued Phase I
investigation of compact streaming state and explainable anomaly categories.
Separating source-integrity from behavioral alerts helped under persistent
benign transmitter outage: review false alerts increased, while the
behavior-based threat-candidate false-alert measure remained near nominal.

The same split did not solve sensor-noise shift. False alerts rose materially
at 1.5x noise, and the severe condition is a clear breakdown region. These
negative results narrow the next technical work:

- evaluate on representative public and authorized government data;
- add covariance-aware tracking and explicit source-quality estimation;
- calibrate thresholds by density, sensor, and operating regime;
- detect degraded-sensor conditions and abstain or reduce confidence;
- test the beacon-silence delay versus false-alert tradeoff; and
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
