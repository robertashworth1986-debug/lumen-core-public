# MissionWeave Generated-Workflow Validation

Date: June 13, 2026

## Evidence Boundary

This is a generated-workflow software benchmark. Cases, workers, skills,
deadlines, absences, and outages are synthetic. Results do not establish DLA
readiness, workforce productivity, causal impact, fairness, privacy
compliance, operational integration, or a 10x improvement.

## Design

Frozen run `20260613T_MISSIONWEAVE_V3_DEV16_VAL30` used 16 development seeds
across nominal and surge conditions to choose one routing-weight set from four
candidates. The selected `critical` policy was then held fixed for 30 disjoint
validation seeds in each condition:

- nominal generated demand;
- surge demand;
- targeted absence of two generated workers;
- a generated system outage reducing capacity to 45%; and
- combined surge, absence, and outage stress.

Each paired seed used identical generated cases for:

- fixed-role FIFO;
- cross-trained FIFO; and
- MissionWeave evidence-aware routing.

The stronger cross-trained FIFO policy is the primary comparator below.
MissionWeave scores generated work using criticality, deadline urgency, age,
skill fit, and current-stage congestion.

## Results

| Condition | FIFO on-time | MissionWeave on-time | Mean delta | Paired 95% bootstrap interval | Better / tied / worse seeds |
|---|---:|---:|---:|---:|---:|
| Nominal | 0.935 | 0.993 | +0.058 | [+0.038, +0.081] | 25 / 4 / 1 |
| Surge | 0.249 | 0.365 | +0.116 | [+0.074, +0.161] | 24 / 1 / 5 |
| Targeted absence | 0.751 | 0.869 | +0.118 | [+0.073, +0.164] | 25 / 3 / 2 |
| System outage | 0.665 | 0.791 | +0.127 | [+0.085, +0.176] | 28 / 0 / 2 |
| Combined stress | 0.240 | 0.270 | +0.030 | [+0.017, +0.044] | 23 / 0 / 7 |

Mean critical-case on-time deltas were +0.182, +0.381, +0.296, +0.305,
and +0.158 in the same condition order. Mean cycle-time deltas were -2.29,
-10.60, -3.31, -3.75, and -7.85 generated time steps; negative values favor
MissionWeave.

Under surge, completion rate increased by 0.020 and mean backlog decreased by
2.63 cases. Under combined stress, completion rate increased by 0.069 and
mean backlog decreased by 8.83 cases. Completion and backlog were tied in the
other three conditions after the benchmark's drain period.

## Interpretation

The run supports continued investigation of a narrow claim: under this
generated workflow model, a development-selected routing policy improved
average deadline and cycle-time metrics over cross-trained FIFO on disjoint
seeds.

The run does not support a universal-improvement claim. Some seeds performed
worse, and combined-stress absolute on-time rates were poor for both policies.
That condition is a capacity-breakdown region requiring intervention beyond
routing alone.

Generated workload-concentration values improved under surge, absence, and
combined stress but worsened slightly under nominal and outage conditions.
This metric is not a fairness evaluation and cannot substitute for
process-specific workload, labor, civil-rights, or personnel review.

## Required Next Evidence

- Select one bounded unclassified process and replace generated parameters
  with approved representative observations.
- Preregister mission outcomes, service levels, constraints, comparison
  policies, and holdout periods.
- Test recommendation stability, gaming, missing data, and inequitable burden
  movement.
- Separate routing effects from staffing, automation, policy, and capacity
  interventions.
- Obtain independent domain and reproducibility review.
- Preserve operator approval, uncertainty, assumptions, and rollback
  conditions for every recommended intervention.

## Reproduction

```powershell
.\.venv\Scripts\python.exe code\missionweave_benchmark.py `
  --out out\missionweave_validation\<new-run-name> `
  --development-scenarios 16 `
  --validation-scenarios 30 `
  --horizon 180
```

The suite writes `summary.json`, `scenario_summary.csv`, `SCORECARD.md`, and a
SHA-256 manifest.
