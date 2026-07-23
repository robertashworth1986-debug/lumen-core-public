# Post-Merge Evidence Reconciliation — 2026-07-23

## Purpose

PRs #66 and #67 are merged on `main`, but `config/evidence_graph_v1.json` was generated before those merge events and still records PR #66 as held/unmerged while omitting PR #67.

This document and the accompanying machine overlay record that mismatch without pretending the canonical human and machine evidence surfaces have already been reconciled.

## Verified corrections

- PR #66 is now a merged capability on the default branch.
- PR #67 is now a merged capability on the default branch.
- PR #67 supports confirmed receipt indexing, duplicate-outreach locking, founder-only action preservation, and operating-state refresh.
- PR #67 does not establish proposal submission, selection, award, funding, contract, or external validation.

## Machine correction record

- Overlay: `config/evidence_graph_post_merge_overlay_v1.json`
- Verifier: `code/ops/VERIFY_EVIDENCE_GRAPH_OVERLAY.py`
- Tests: `tests/test_evidence_graph_overlay.py`

The verifier binds the overlay to the exact Git blob of the current base graph, checks the expected stale values before applying corrections in memory, and then runs the canonical evidence-graph verifier against the effective graph.

## Why this remains noncanonical

The overlay intentionally reports `canonical_ready=false` because the following human reviewer documents still require coordinated updates:

- `EVIDENCE_INDEX.md`
- `docs/PR_CONSOLIDATION_MAP_2026-07-22.md`

The overlay must not be treated as permission to leave the base graph stale indefinitely. Its purpose is to make the drift explicit and testable while the full human/machine update is reviewed.

## Claim boundary

This reconciliation does not establish a submission, selection, award, funding event, contract, sale, valuation, independent validation, field validation, or commercial validation. It does not authorize another merge or any external action.
