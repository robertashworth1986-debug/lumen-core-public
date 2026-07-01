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

Run `20260619T_NV063_V6_SOURCE_LANE_COVERAGE` used 20 development scenarios to
select a threshold, then froze threshold 10.0 for 30 disjoint validation
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

The v6 scoring stream keeps the source-quality guardrails from v5 and adds
explicit generated source-lane coverage reporting. The guardrails are computed from observations
only, not from ground-truth labels:

- a scene-wide source-quality gate based on median normalized radar/beacon
  disagreement, which reduces behavioral confidence during detected
  sensor-noise shift; and
- a five-observation beacon-loss review gate, which sends persistent
  cooperative-source loss to operator review without treating loss alone as a
  behavior-based threat candidate.

The v6 source-lane report documents generated AIS-like surface cooperative
beacons, generated ADS-B-like air cooperative beacons, and generated
notional radar-like contacts. It does not include NOAA AIS, OpenSky ADS-B,
Navy radar, SSDS, or government-furnished operational data.

## Results

| Condition | Precision | Recall | F1 | Review false alerts / 10k normal points | Threat-candidate false alerts / 10k |
|---|---:|---:|---:|---:|---:|
| Nominal, 24 tracks | 0.948 | 0.957 | 0.952 | 71.5 | 71.5 |
| Congested, 96 tracks | 0.948 | 0.957 | 0.952 | 71.4 | 71.4 |
| Sensor shift, 1.5x | 0.943 | 0.955 | 0.949 | 77.0 | 77.0 |
| Benign point dropout, 2% | 0.947 | 0.957 | 0.952 | 71.1 | 71.1 |
| Benign burst dropout, 20% | 0.908 | 0.957 | 0.932 | 128.7 | 71.2 |
| Combined stress | 0.899 | 0.956 | 0.927 | 144.9 | 76.5 |
| Severe combined stress | 0.865 | 0.913 | 0.888 | 191.9 | 77.0 |

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

Generated source-lane coverage in the v6 run:

| Condition | AIS-like availability | ADS-B-like availability | Radar-like availability |
|---|---:|---:|---:|
| Nominal, 24 tracks | 0.960 | 1.000 | 1.000 |
| Combined stress | 0.936 | 0.975 | 1.000 |
| Severe combined stress | 0.904 | 0.945 | 1.000 |

## Interpretation

The nominal and congestion-only results support continued Phase I
investigation of compact streaming state and explainable anomaly categories.
Separating source-integrity from behavioral alerts helped under persistent
benign transmitter outage: review false alerts increased, while the
behavior-based threat-candidate false-alert measure remained near nominal.

The source-quality gate materially improved the prior breakdown region in
synthetic tests while the v6 source-lane report makes the generated
AIS-like/ADS-B-like/radar-like source coverage explicit. The severe condition
is still a stress case, not an operating envelope: source-integrity review
volume rises, and threat-candidate recall drops as the system avoids
converting sensor/source failure into unsupported hostile-intent claims.

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

The suite writes `summary.json`, `scenario_summary.csv`,
`source_lane_summary.csv`, `SCORECARD.md`, and a SHA-256 manifest. The run
directory should be preserved with the proposal evidence record.
