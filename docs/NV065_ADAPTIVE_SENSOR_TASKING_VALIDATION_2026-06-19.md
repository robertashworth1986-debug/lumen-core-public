# NV065 Adaptive Sensor-Tasking Synthetic Validation

Date: June 19, 2026

## Evidence Boundary

This is a generated software benchmark only. Tracks, sensors, covariance,
hostility changes, sensor feedback, and tasking costs are synthetic. Results
do not establish SSDS integration, fire-control performance, sensor physics,
classified-environment performance, cybersecurity, adversarial robustness, or
field readiness.

## Design

Frozen run `20260619T_NV065_SENSOR_TASKING_V2_SENSOR_PROFILE` used 12 development scenarios
across nominal, dense-raid, and hostility-shift conditions to select one
adaptive sensor-management policy from four candidates. The selected
`critical_release` policy was then held fixed for 24 disjoint validation
scenarios in each condition:

- nominal generated track load;
- dense raid load with capacity pressure;
- generated sensor degradation;
- hostility-shift behavior; and
- combined dense raid, degradation, maneuver, clutter, and capacity stress.

Each paired seed used identical generated tracks for:

- fixed-priority sensor tasking;
- greedy uncertainty tasking; and
- adaptive sensor management using marginal contribution, source quality,
  recent confirmation, and generated fire-control-quality need.

The v2 packet also emits `sensor_resource_profile.json`, which documents the
generated SPS-48, SPQ-9B, MK-9, and SPY-6(V)3 archetypes used in the
experiment. These are topic-aligned unclassified assumptions only, not
Navy-approved radar physics, SSDS interface data, or fire-control evidence.

## Results

| Condition | Greedy critical FCQ | Adaptive critical FCQ | Mean delta | Paired 95% bootstrap interval | Sensor-task delta | Low-value fraction delta |
|---|---:|---:|---:|---:|---:|---:|
| Nominal | 0.993 | 0.998 | +0.005 | [+0.005, +0.006] | -12.28 | +0.008 |
| Dense raid | 0.491 | 0.655 | +0.164 | [+0.151, +0.177] | +0.00 | +0.000 |
| Sensor degradation | 0.986 | 0.995 | +0.009 | [+0.008, +0.010] | -7.24 | +0.132 |
| Hostility shift | 0.990 | 0.997 | +0.007 | [+0.006, +0.008] | -4.26 | +0.039 |
| Combined stress | 0.003 | 0.104 | +0.101 | [+0.092, +0.112] | +0.00 | +0.000 |

Negative sensor-task deltas mean fewer generated sensor updates per time step.
The low-value fraction was mixed and worsened under generated sensor
degradation and hostility shift because the adaptive policy used fewer total
updates while concentrating more of the remaining updates on already-controlled
critical tracks. This is a diagnostic tradeoff, not a hidden success.

## Generated Sensor-Resource Profile

| Sensor archetype | Generated capacity/step | Generated precision | Generated scan cost | Strongest generated suitability |
|---|---:|---:|---:|---|
| SPS-48 | 8 | 0.16 | 1.00 | air |
| SPQ-9B | 7 | 0.18 | 1.00 | surface |
| MK-9 | 3 | 0.36 | 1.80 | missile |
| SPY-6(V)3 | 9 | 0.24 | 1.40 | air |

Not modeled: radar waveforms, electromagnetic propagation, track association
with real sensors, classified sensor performance, SSDS message implementation,
operator workload study, cybersecurity, or adversarial effects.

## Interpretation

The result supports continued investigation of one narrow Phase I hypothesis:
under a generated track and sensor-resource model, marginal contribution
estimation can improve critical-track fire-control-quality coverage over a
greedy uncertainty baseline and can release tasking load in lighter conditions.

The result does not prove operational sensor management. Dense raid and
combined stress remain capacity-pressure regions: the adaptive policy improves
generated critical-FCQ coverage, but absolute coverage remains poor in
combined stress. The next evidence must replace generated parameters with
approved representative models or public unclassified data, add a real
covariance filter and latency budget, and include an SSDS-facing
operator-review concept without claiming integration.

## Reproduction

```powershell
.\.venv\Scripts\python.exe code\nv065_sensor_tasking_benchmark.py `
  --out out\nv065_sensor_tasking\<new-run-name> `
  --development-scenarios 12 `
  --validation-scenarios 24 `
  --horizon 150
```

The suite writes `summary.json`, `sensor_resource_profile.json`,
`scenario_summary.csv`, `SCORECARD.md`, and a SHA-256 manifest.
