# Source Ablation Nonpromotion Diagnostic

Generated UTC: `2026-07-29T07:39:19.881096+00:00`
Diagnostic SHA-256: `88186f78b9e1609e9e2d5430f7c6c7fef4986b0e838e0ef6e5ab60b395ce6da2`

## Truth Line

No performance champion is present. Kuramoto is a negative measured reference: it won 482 of 1,525 paired holdouts against the named Kalman baseline with mean delta -0.508191, and it was not development-selected. Its measured audit uses one source system, so withholding that source leaves no evaluable replay and supports no promotion claim.

## Canonical Evidence Contract

- Performance champion present: `false`
- Direct measured routes: `2`
- Conditioned-synthetic routes: `2`
- Baseline comparisons: `22`
- Performance rows: `32608`
- Direct all-baseline globally Holm-positive promotions: `0`
- Inventory measured sources: `24`
- Inventory measured rows: `17081`
- Inventory is performance evidence: `false`

## Negative Measured Reference

- Family: `kuramoto_phase_coupling`
- Status: `negative_measured_reference_not_development_selected`
- Development-selected: `false`
- Development-selected candidate: `lissajous_phase_paths`
- Wins vs named Kalman baseline: `482/1525`
- Mean delta vs named Kalman baseline: `-0.508191`
- Supports promotion: `false`

## Leave-One-Source-Out Diagnostic

| Withheld Source | Remaining Sources | Remaining Comparisons | Evaluable | Supports Promotion |
|---|---:|---:|---|---|
| `EIA_GRID_VALIDATION` | 0 | 0 | `false` | `false` |

## Boundary

This is a nonpromotion source-ablation diagnostic. It audits source dependence and evidence coverage; it does not identify a performance champion. Direct measured replay, conditioned-synthetic replay, and source inventory are separate evidence classes. Inventory counts are inventory only. No field-validation, realized-savings, fixed-dollar, live-trading, or hardware performance claim is allowed.
