# Live-Breadth Provenance Gate Capsule

Generated UTC: 2026-06-21T07:50:23.657357+00:00

## Purpose

Document the public-safe evidence-boundary upgrade for LumenCore live-breadth and frozen-delta reporting.

The useful change is simple: only rows tied to measured live sources are promoted as live-breadth evidence. Unmeasured frozen deltas, reference fallback rows, synthetic controls, and exploratory context stay visible, but they are not allowed to inflate the headline evidence layer.

## Public-Safe Snapshot

| Field | Value |
|---|---:|
| Enabled live sources | 17 |
| Measured live sources | 12 |
| Measured coverage | 70.59% |
| Promoted live-measured source rows | 11 |
| Context-only source rows | 8 |
| Reference fallback used | false |
| Promoted live-measured hourly value signal | $8,435 |
| Promoted live-measured annual value signal | $73,890,600 |
| Context-only annual surface | $52,257,442,740 |
| Top live-measured sector | power_grid |
| Top live-measured sector hourly value signal | $5,562 |

## Evidence Buckets

### `live_measured_delta_rows`

- Public use: Promoted live-breadth evidence.
- Boundary: Still not proof of customer savings, grant merit, field performance, or trading profit.

### `unmeasured_frozen_delta_rows`

- Public use: Context-only until source measurement is proven.
- Boundary: May remain visible for research prioritization but cannot inflate headline evidence.

### `reference_fallback_only`

- Public use: Calibration/context only.
- Boundary: Not live evidence and not a substitute for measured source rows.

## Truth-Chain Interpretation

- Promoted annual value signal: $73,890,600
- Context-only annual surface retained as context: $52,257,442,740
- Interpretation: The public annual value signal should be read as the promoted live-measured measurement surface only. The larger context-only surface is retained for research prioritization and must not be described as live proof.

## Grant Packet Use

- DICE: Useful as proof of measurement discipline and replay realism after synthetic controls; not native DICE ground truth or DICE metric attainment.
- HarborSentinel: Useful as cross-stack provenance discipline; HarborSentinel merit still rests on bounded public AIS evidence, controlled injections, review-burden profile, and future authorized lanes.

## Boundary

This public-safe capsule does not prove actual customer savings, revenue, trading profit, grant merit, agency acceptance, valuation, field performance, operational deployment readiness, or portal readiness. Dollar figures are value-signal estimates from a provenance-gated measurement layer, not realized savings, not revenue, not an investment claim, and not a guarantee.

## Reviewer Use

Use this capsule as public evidence-quality control showing that LumenCore separates live-measured evidence from context-only evidence before using frozen deltas in public or grant-facing materials.

## Claim Gate

- ready_for_portal_upload: `false`
- ready_for_submit: `false`
- grant_merit_proven: `false`
- field_performance_proven: `false`
- trading_profit_proven: `false`
- context_only_promoted_as_live_proof: `false`
