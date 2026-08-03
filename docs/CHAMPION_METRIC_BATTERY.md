# Champion Metric Battery

## Battery Status

No internal performance champion exists. Kuramoto was not development-selected, won 482/1525 paired days against kalman_local_linear_trend, and recorded mean skill delta -0.508191. It cleared 0/6 registered baselines; the full 22-comparison sweep has 0 global Holm positives.

- Internal performance champion: `false`
- Audited candidate: `kuramoto_phase_coupling`
- Development-selected candidate: `lissajous_phase_paths`
- Named baseline: `kalman_local_linear_trend`
- Paired-day wins: `482/1525`
- Mean skill delta: `-0.508191`
- Registered baseline gates: `0/6`
- Global Holm positives: `0/22`
- Performance rows reviewed: `32608`
- Legacy rows excluded: `358`
- Numeric fallbacks: `0`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`

## Metric Categories

| Category | Status | Interpretation |
|---|---|---|
| `development_selection` | `BLOCKED` | Kuramoto is a post-selection audit and cannot inherit the selected candidate's status. |
| `direct_measured_named_baseline` | `MEASURED_NONPROMOTION` | The paired win rate is below one half and mean skill is negative. |
| `source_specific_baseline_gauntlet` | `BLOCKED` | No registered EIA baseline clears the complete candidate promotion gate. |
| `global_holm_promotion` | `BLOCKED` | No comparison is positive after the global Holm correction. |
| `direct_measured_route_coverage` | `PASS_COVERAGE_ONLY` | Route and row depth describe benchmark coverage, not superiority. |
| `conditioned_synthetic_research` | `RESEARCH_ONLY` | Thermal and branching can guide experiments but are not measured performance evidence. |
| `compatibility_hygiene` | `PASS` | Incompatible legacy rows are excluded and numeric fallback profiles are absent. |
| `source_inventory` | `INVENTORY_ONLY` | Source breadth is research inventory, not performance evidence. |
| `external_validation` | `BLOCKED_EXTERNAL` | No independent owner-approved validation is complete. |
| `economic_conversion` | `BLOCKED_EXTERNAL` | No owner-approved cost model or realized-savings evidence exists. |

## Claim Boundary

- Thermal and branching conditioned simulations are research leads only.
- Source breadth is inventory, not performance evidence.
- The safe commercial scope is protocol and evidence review, not performance or savings.

Metric battery SHA-256: `e9cf23a20abc82431a6fc489626aa4de5d46a87f88312aacfc046457c09ff62b`
