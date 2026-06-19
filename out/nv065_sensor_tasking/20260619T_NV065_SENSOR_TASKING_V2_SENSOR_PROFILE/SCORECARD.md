# NV065 Adaptive Sensor-Tasking Scorecard

Evidence boundary: Generated software benchmark only. Tracks, sensors, covariance, hostility changes, sensor feedback, and tasking costs are synthetic. Results do not establish SSDS integration, fire-control performance, sensor physics, classified-environment performance, cybersecurity, adversarial robustness, or field readiness.

## Development Gate

- Development scenarios: 12
- Selected policy: critical_release
- Development conditions: nominal, dense raid, hostility shift.
- Baselines: fixed priority and greedy uncertainty tasking.
- Sensor-resource profile: generated SPS-48, SPQ-9B, MK-9, and SPY-6(V)3 archetypes; not Navy-approved radar physics or SSDS data.

## Frozen Validation

| Condition | Greedy critical FCQ | ASM critical FCQ | Critical FCQ delta [95% CI] | Sensor-task delta | Low-value fraction delta | Shift-delay delta |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 0.993 | 0.998 | +0.005 [+0.005, +0.006] | -12.28 | +0.008 | +0.00 |
| dense_raid | 0.491 | 0.655 | +0.164 [+0.151, +0.177] | +0.00 | +0.000 | -0.02 |
| sensor_degradation | 0.986 | 0.995 | +0.009 [+0.008, +0.010] | -7.24 | +0.132 | +0.00 |
| hostility_shift | 0.990 | 0.997 | +0.007 [+0.006, +0.008] | -4.26 | +0.039 | +0.00 |
| combined_stress | 0.003 | 0.104 | +0.101 [+0.092, +0.112] | +0.00 | +0.000 | -33.06 |

Negative sensor-task and shift-delay deltas favor the adaptive sensor manager. Low-value fraction is a diagnostic and may worsen when fewer total updates are concentrated on already-controlled critical tracks. All comparisons use identical generated tracks per paired seed.

## Generated Sensor-Resource Profile

Boundary: Topic-aligned unclassified archetypes only. Parameters are generated software assumptions for task-allocation experiments, not radar physics, Navy-approved values, SSDS interface data, or fire-control evidence.

| Sensor archetype | Generated capacity/step | Generated precision | Generated scan cost | Strongest generated suitability |
|---|---:|---:|---:|---|
| SPS-48 | 8 | 0.16 | 1.00 | air |
| SPQ-9B | 7 | 0.18 | 1.00 | surface |
| MK-9 | 3 | 0.36 | 1.80 | missile |
| SPY-6(V)3 | 9 | 0.24 | 1.40 | air |

## Interpretation

The benchmark tests a narrow allocation hypothesis: marginal contribution estimates can release generated sensor resources from well-characterized tracks and reallocate them to tracks with greater expected fire-control-quality benefit. Stress conditions are generated feasibility checks, not operating envelopes. Any condition with weak or negative critical-FCQ delta remains a preserved failure region for the proposal.
