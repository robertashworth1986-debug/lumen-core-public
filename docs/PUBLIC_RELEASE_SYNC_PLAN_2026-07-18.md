# Public Release Sync Plan

As of UTC: `2026-07-29T15:11:53Z`
Plan state: `DRY_RUN_READY_HUMAN_UNLOCK_REQUIRED`
Plan SHA-256: `cc7323f6e65ed60ae8c2d70443580f79e2c6c311f2a875f057ab1e4006cd76cd`

## Decision

The dry-run plan passed local preflight. No files were copied and every network action still requires a human unlock.

## Safety Boundary

- Human gate: `HUMAN_UNLOCK_REQUIRED`
- Files copied: `false`
- Network action performed: `false`
- Registry, credential stores, and API-key sources accessed: `false`
- Allowlisted candidate bytes scanned locally for unsafe patterns: `true`
- Secret or PII values emitted: `false`
- Overwrite behavior: exact-hash targets are no-ops; mismatches are blocked
- Clean-checkout generated artifacts verified: `3`
- Clean-checkout generated artifacts blocked: `0`

## Candidates

| ID | Source | Target | Claim state | Action | Blockers | SHA-256 |
|---|---|---|---|---|---:|---|
| `current_evidence_to_pilot_deck_pdf` | `output/pdf/LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf` | `dashboard/evidence/LumenCore_Evidence_to_Pilot_Deck_2026-07-29_D46096D88E3C.pdf` | `BOUNDED_INTERNAL_EVIDENCE` | `PLAN_NEW_LOCAL_STAGE_COPY` | `none` | `d46096d88e3c2805` |
| `federal_capability_statement_pdf` | `output/pdf/LumenCore_Federal_Capability_Statement_CURRENT.pdf` | `dashboard/evidence/LumenCore_Federal_Capability_Statement_2026-07-29_F7E9ED937196.pdf` | `NO_PERFORMANCE_CLAIM` | `PLAN_NEW_LOCAL_STAGE_COPY` | `none` | `f7e9ed937196aedc` |
| `model_geometry_evidence_ledger` | `docs/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER_2026-07-13.md` | `dashboard/evidence/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER.md` | `PROVENANCE_AND_REPRODUCIBILITY` | `PLAN_NEW_LOCAL_STAGE_COPY` | `none` | `b8af64d9a54ccf37` |
| `quant_hub_reviewer_context_json` | `dashboard/data/quant_hub_reviewer_context.json` | `dashboard/data/quant_hub_reviewer_context.json` | `BOUNDED_INTERNAL_EVIDENCE` | `NOOP_EXACT_MATCH` | `none` | `9dea5125d91c94ea` |
| `quant_hub_reviewer_context_markdown` | `docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md` | `dashboard/evidence/QUANT_HUB_REVIEWER_CONTEXT.md` | `BOUNDED_INTERNAL_EVIDENCE` | `PLAN_NEW_LOCAL_STAGE_COPY` | `none` | `690679b8e4967e86` |
| `source_native_benchmark_whitepaper_pdf` | `output/pdf/LumenCore_Source_Native_Benchmark_Whitepaper_CURRENT.pdf` | `dashboard/evidence/LumenCore_Source_Native_Benchmark_Whitepaper_2026-07-29_2476B88BC8B4.pdf` | `PROVENANCE_AND_REPRODUCIBILITY` | `PLAN_NEW_LOCAL_STAGE_COPY` | `none` | `2476b88bc8b49d14` |

## Public URL Verification

No URL was contacted. After an explicit human unlock and a separate publish action, verify HTTPS status, content type, full body SHA-256, and a cache-bypass repeat hash for each URL.

- `current_evidence_to_pilot_deck_pdf`: https://lumen-core.ai/evidence/LumenCore_Evidence_to_Pilot_Deck_2026-07-29_D46096D88E3C.pdf (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)
- `federal_capability_statement_pdf`: https://lumen-core.ai/evidence/LumenCore_Federal_Capability_Statement_2026-07-29_F7E9ED937196.pdf (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)
- `model_geometry_evidence_ledger`: https://lumen-core.ai/evidence/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER.md (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)
- `quant_hub_reviewer_context_json`: https://lumen-core.ai/data/quant_hub_reviewer_context.json (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)
- `quant_hub_reviewer_context_markdown`: https://lumen-core.ai/evidence/QUANT_HUB_REVIEWER_CONTEXT.md (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)
- `source_native_benchmark_whitepaper_pdf`: https://lumen-core.ai/evidence/LumenCore_Source_Native_Benchmark_Whitepaper_2026-07-29_2476B88BC8B4.pdf (`PENDING_HUMAN_UNLOCK_AND_PUBLICATION`)

## Claim Boundary

This plan is a local safety and provenance preflight. It is not proof that an artifact is public, externally validated, government approved, compliant, deployed, or accepted by a reviewer.
