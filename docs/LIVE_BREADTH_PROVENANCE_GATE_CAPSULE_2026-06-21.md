# Live-Breadth Provenance Gate Capsule

Generated UTC: 2026-08-08T09:54:11.201481+00:00
Snapshot observed UTC: 2026-06-21T07:50:23.657357+00:00
Snapshot status: `historical_not_current_runtime_evidence`

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
| Top live-measured sector | power_grid |

## Metric Definitions

- Enabled live sources: Sources configured as enabled in the historical first-party artifact; not proof that each source was healthy, fresh, or usable.
- Measured live sources: Sources marked measured by the historical first-party probe logic; not proof of dataset fitness, material row depth, independent validation, or current availability.
- Measured coverage: Historical measured-source flag count divided by enabled-source flag count.
- Promoted rows: Rows historically classified for the measured bucket; no longer promoted as economic or performance evidence.
- Context-only rows: Rows retained only as historical research context.

## Evidence Buckets

### `live_measured_delta_rows`

- Public use: Historical first-party source-classification evidence only.
- Boundary: A successful or measured flag does not establish freshness, row depth, relevance, data rights, dataset fitness, customer savings, field performance, or trading profit.

### `unmeasured_frozen_delta_rows`

- Public use: Context-only until source measurement is proven.
- Boundary: May remain visible for research prioritization but cannot inflate headline evidence.

### `reference_fallback_only`

- Public use: Calibration/context only.
- Boundary: Not live evidence and not a substitute for measured source rows.

## Truth-Chain Interpretation

- Economic estimates included: `false`
- Interpretation: This artifact reports historical source coverage and provenance buckets only. It does not convert source breadth into economic, performance, or current-runtime claims.

## Grant Packet Use

- DICE: Useful as proof of measurement discipline and replay realism after synthetic controls; not native DICE ground truth or DICE metric attainment.
- HarborSentinel: Useful as cross-stack provenance discipline; HarborSentinel merit still rests on bounded public AIS evidence, controlled injections, review-burden profile, and future authorized lanes.

## Boundary

This historical source-classification snapshot does not prove current feed availability or freshness, customer savings, revenue, trading profit, grant merit, agency acceptance, valuation, field performance, operational deployment readiness, or portal readiness. Economic estimates are intentionally omitted.

## Reviewer Use

Use this capsule as historical claim-quality control showing how LumenCore separated first-party source flags from context-only rows. Do not use it as current live-breadth, dataset-fitness, performance, or economic evidence.

## Claim Gate

- ready_for_portal_upload: `false`
- ready_for_submit: `false`
- grant_merit_proven: `false`
- field_performance_proven: `false`
- trading_profit_proven: `false`
- current_runtime_state_proven: `false`
- economic_value_claim_allowed: `false`
- performance_claim_allowed: `false`
- probe_success_is_dataset_fitness: `false`
- context_only_promoted_as_live_proof: `false`
