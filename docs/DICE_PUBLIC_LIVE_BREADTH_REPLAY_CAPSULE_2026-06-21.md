# DICE Public Live-Breadth Replay Capsule

Generated UTC: 2026-06-21T00:15:00Z

## Purpose

This public capsule summarizes a private, hash-manifested DICE evidence upgrade
without publishing private portal materials, entity identifiers, upload files,
API keys, account screenshots, or submission-only artifacts.

The useful point is narrow: LumenCore now has a path that starts with synthetic
controls and then tests the same coordination/control logic against frozen
live-pulled time-series stress windows.

## What Was Added

- Evidence lane: frozen live-breadth replay
- Source families: Kraken market time-series and EIA power-grid time-series
- Source files: 6
- Deterministic replay windows: 14
- Agents per replay scenario: 180
- Roles per replay scenario: 8
- Task multiplier per live row: 3

## Public-Safe Result Snapshot

| Metric | Mean Delta | Favorable Fraction | Scenario Count | Boundary |
|---|---:|---:|---:|---|
| Safe completion | +0.0437 | 0.857 | 14 | Stress-replay signal, not DICE metric proof. |
| Constraint violation | -0.1216 | 0.929 | 14 | Supports a constraint-check validation lane. |
| Messages per safe completion | -2.8157 | 1.000 | 14 | Shows modeled coordination-cost behavior on frozen live windows. |
| False rejection | +0.0514 | 0.000 | 14 | Known cost to reduce in Phase I. |

## Why It Matters

Synthetic tests are necessary because they provide controlled ground truth.
They are not enough by themselves. The live-breadth replay lane gives reviewers
a second proof surface: real pulled time-series behavior converted into frozen,
deterministic stress scenarios after the synthetic controls.

That makes the grant posture stronger because the proposal can now say:

1. We can run controlled synthetic baselines.
2. We can run constraint-contract ablations.
3. We can freeze live-pulled time-series windows into replay stress scenarios.
4. We can report gains and costs without turning them into field-performance
   claims.

## Boundary

This capsule does not prove DICE program metric attainment, field validation,
operational DoD performance, semantic correctness, adversarial security,
trading profit, award likelihood, or portal readiness.

The live rows are stress signals. The replay labels are deterministic derived
labels, not native DICE task labels.

## Reviewer Use

Use this as public evidence that LumenCore is moving from synthetic-only claims
toward a reproducible evidence ladder. Do not use it as a substitute for BAAT
portal authority, final cost review, compliance review, team review, upload
preview, or fresh action-time approval.
