          # Live-Breadth Provenance Annex

Generated UTC: `2026-06-24T19:22:39.709003+00:00`

## Reviewer-Safe Summary

This annex separates promoted live-measured evidence from context-only estimates so DICE and HarborSentinel packets can use live breadth without overclaiming field performance, grant merit, revenue, or trading profit.

## Promoted Live-Measured Surface

- Primary evidence mode: `live_measured_delta_rows`
- Measured sources: 17/22 (77.27%)
- Live-measured source rows: 13
- Unmeasured/context source rows: 6
- Reference fallback used: `false`
- Promoted live-measured hourly value signal: $4,890.00
- Promoted live-measured annual value signal: $42,836,400.00
- Context-only hourly surface: $5,969,006.50
- Context-only annual surface: $52,288,496,940.00
- Top live-measured sector: `economic_macro` at $1,950.00/h
- Claim boundary: Only rows marked live_measured_source are promoted as live breadth evidence. Unmeasured frozen deltas and reference fallback rows remain calibration or context until the live source registry marks the source measured.

## Multi-Asset Frozen Delta Pack

- Primary evidence mode: `live_measured_delta_rows`
- Live-measured lanes: 10
- Context-only lanes: 6
- Live-measured lanes >= $10k/h: 0
- Live-measured hourly value signal: $4,520.00
- Live-measured annual value signal: $39,595,200.00
 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
## Truth Chain Anchor

- Run tag: `20260621T063554Z`
- Entry SHA-256: `cf81edbe23354210b3c9e1c00d68d09506a3b792ad0bb13ca1144220bd9d417a`
- Annual value signal promoted in truth chain: $73,890,600.00
- Context-total annual value retained as context: $52,331,333,340.00
- Context-only annual value retained as context: $52,257,442,740.00
- Primary evidence mode: `live_measured_delta_rows`

## Grant Packet Use

### DICE_HR001126S0010

- Evidence pack: `out/ops/grant_evidence_packs/DICE_HR001126S0010/EVIDENCE_latest.json`
- Freshness: `fresh`
- Headline source mode: `live_measured_multi_asset_pack`
- Primary evidence mode: `live_measured_delta_rows`
- Live-measured hourly value signal cited by pack: $8,435.00
- Context-only lane count: 8
- Rows promoted: 11
- Claim boundary: Headline values include only rows marked measured_source and primary_live_evidence. Unmeasured frozen deltas, synthetic controls, and reference fallbacks are context-only.

Freshness notes:
- raw infra_frozen_deltas.jsonl age 111.5h > 24h; raw/context lineage is stale but not promoted as headline proof

### NV063_HarborSentinel

- Evidence pack: `out/ops/grant_evidence_packs/NV063_HarborSentinel/EVIDENCE_latest.json`
- Freshness: `fresh`
- Headline source mode: `live_measured_multi_asset_pack`
- Primary evidence mode: `live_measured_delta_rows`
- Live-measured hourly value signal cited by pack: $8,435.00
- Context-only lane count: 8
- Rows promoted: 11
- Claim boundary: Headline values include only rows marked measured_source and primary_live_evidence. Unmeasured frozen deltas, synthetic controls, and reference fallbacks are context-only.

Freshness notes:
- raw infra_frozen_deltas.jsonl age 111.5h > 24h; raw/context lineage is stale but not promoted as headline proof

## Reviewer Use

- Synthetic control role: Synthetic and controlled-injection lanes provide labels, adversary knobs, and repeatable ablations.
- Live breadth role: Live breadth provides measured source coverage, frozen time-series replay realism, and chain-of-custody evidence after controlled tests. It is not native ground truth for DICE or HarborSentinel.
- Economic boundary: The economic signal is a prioritization and preserved-value hypothesis. It is not customer savings, trading profit, revenue, grant merit, field performance, or valuation proof.
- Grant language: Use the promoted live-measured values only as evidence that the measurement system can ingest, separate, hash, and report live evidence with context-only estimates fenced off.

## Claim Gate

- ready_for_portal_upload: `false`
- ready_for_submit: `false`
- grant_merit_proven: `false`
- field_performance_proven: `false`
- trading_profit_proven: `false`
- context_only_promoted_as_live_proof: `false`
- boundary: Only live-measured rows are promoted as live-breadth evidence. Synthetic controls, reference rows, context-only estimates, and valuation proxies remain support material and must not be stated as proof.
