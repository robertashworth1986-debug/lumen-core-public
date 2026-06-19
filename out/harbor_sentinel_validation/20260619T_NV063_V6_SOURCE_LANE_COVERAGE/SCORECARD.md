# HarborSentinel Validation and Stress Scorecard

Evidence boundary: Synthetic software benchmark only. Inputs are generated AIS/ADS-B and radar-like observations, not operational sensor data. Results do not establish harbor, SSDS, adversarial, classified-environment, or field performance. Runtime measurements are machine-specific observations.

## Development Gate

- Development scenarios: 20
- Frozen threshold: 10.0
- Selection rule: maximize development F1 subject to no more than 100 false alerts per 10,000 normal points.
- Source-quality calibration: scene-wide median radar/beacon disagreement gates behavior confidence under detected sensor-noise shift.
- Beacon-loss review gate: five consecutive missing cooperative observations generate source-integrity review without automatically creating a threat candidate.
- Source lanes represented in this generated run: AIS-like surface cooperative beacon, ADS-B-like air cooperative beacon, and notional radar-like contacts.

## Disjoint Nominal Validation

- Precision: 0.948
- Recall: 0.957
- F1: 0.952
- Fixed kinematic comparator F1: 0.566
- False alerts per 10,000 normal points: 71.5
- Behavior-based threat-candidate false alerts per 10,000 normal points: 71.5
- Event recall: 1.000
- Median detection delay: 1.0 steps

## Nominal Class Detection

- route_deviation: event recall 1.000; median delay 0.0
- loiter: event recall 1.000; median delay 1.0
- speed_burst: event recall 1.000; median delay 1.0
- sharp_turn: event recall 1.000; median delay 1.0
- beacon_silence: event recall 1.000; median delay 4.0
- beacon_spoof: event recall 1.000; median delay 0.0

## Combined Congestion/Noise/Dropout Stress

- Tracks per scenario: 96
- Precision: 0.899
- Recall: 0.956
- F1: 0.927
- False alerts per 10,000 normal points: 144.9
- Behavior-based threat-candidate false alerts per 10,000 normal points: 76.5
- Event recall: 1.000
- Median source-degradation factor: 1.27

## Severe Breakdown Test

- Tracks per scenario: 192
- Review-alert precision: 0.865
- Review-alert F1: 0.888
- Review false alerts per 10,000 normal points: 191.9
- Behavior-based threat-candidate false alerts per 10,000 normal points: 77.0
- Median source-degradation factor: 2.25

## Generated Source-Lane Coverage

- Boundary: generated feasibility inputs only; no NOAA AIS, OpenSky ADS-B, Navy radar, SSDS, or government-furnished operational data are included.
- Nominal AIS-like availability: 0.960
- Nominal ADS-B-like availability: 1.000
- Nominal radar-like contact availability: 1.000
- Severe-stress AIS-like availability: 0.904
- Severe-stress ADS-B-like availability: 0.945

## Interpretation

These results test threshold separation and software behavior under generated congestion, noise, and benign transmitter dropout. Source-integrity alerts are separated from behavior-based threat candidates because transmitter loss or sensor disagreement alone does not identify hostile intent. The v2 source-quality gate is a synthetic feasibility result, not an operational degraded-sensor claim, and must be repeated on representative public and authorized government data.
