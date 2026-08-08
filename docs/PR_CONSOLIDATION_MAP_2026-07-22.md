# Pull Request Consolidation Map — 2026-07-22

This document records the current repository consolidation state after reviewing the principal product-spine work through PR #132 on 2026-08-08. It is an information-architecture control; merge authority remains separate.

## Canonical product spine

1. **Proof Capsule / ProofLock assurance**
   - merged foundation: PR #34
   - deployed demonstration and historical submission record: PR #36
   - current merged release/offer: PR #98
   - current merged strict verifier and assurance contract: PR #101
   - current buyer-owned offer contract: PR #131

2. **Reproducible benchmark / outside-review lane**
   - protocol and author-readiness origin: PR #54
   - accumulated EIA handoff history: PR #55
   - cross-platform custody and reviewer entrypoint: PRs #61 and #62
   - historical clean-mainline consolidation branch: PR #64
   - merged current-main implementation: PR #74

3. **External replication governance**
   - historical draft contract: PR #49
   - merged current contract and assurance surface: PR #99

4. **Commercial conversion**
   - historical proposed offer: PR #35
   - merged bounded release/offer foundation: PR #98
   - current machine-sealed buyer-owned offer: PR #131
   - public buyer-facing website: PR #38

5. **Reviewer navigation and public-copy governance**
   - merged reviewer-facing copy correction: PR #57
   - canonical evidence index and machine graph: PR #66
   - merged receipt and outreach-state reconciliation: PR #67
   - current one-platform/one-offer portfolio audit: PR #132

## Recommended review and merge order

### Stage 1 — Reviewer entrypoint — completed

- PR #66 is merged; keep graph, evidence index, and consolidation map synchronized atomically.
- PR #67 is merged; retain its no-submission/no-award/no-contract boundaries.
- Preserve PR #57 as merged public-copy provenance; wording cleanup is not technical validation.
- Do not promote draft PR claims into default-branch truth merely by linking them.

### Stage 2 — Small bounded fixes

- Review PR #50 as the canonical Windows portability correction for the evidence-route test.
- Rebase or close PR #16 after retaining only non-duplicated bounded route logic.
- Review PR #40 for trust and contribution wording.

### Stage 3 — Evidence protocol — completed on current main

- PR #49 is closed after its unique protocol work was consolidated into merged PR #99 with strict source-custody assurance and reviewer UI.
- PR #52 is closed after its verifier was consolidated into merged PR #101.
- PR #101 is the current Proof Capsule v3 standard and binds the aggregate public-assurance runner to the v3 receipt contract.

### Stage 4 — EIA/CODECHECK consolidation — implementation merged

- Treat PRs #54, #55, #61, and #62 as preserved development ancestry.
- PR #74 is the merged current-main implementation and contains the same 54-file CODECHECK/reviewer package surface as #64.
- Close #64 and its stacked ancestors only after documenting their historical lineage and confirming no unique current implementation remains.
- The remaining promotion gate is a non-author execution receipt, not more author-side packaging.

### Stage 5 — ProofLock release cleanup — bounded release merged

- PR #98 carries the bounded canonical release and buyer path on current main.
- Preserve PR #36 for unique historical/media/submission lineage; submission remains separate from technical validation.
- The public ProofLock console and proof-to-pilot surface are deployed; deployment is not external or field validation.

### Stage 6 — Commercial and public presentation

- PR #131 is the current buyer-owned validation offer and machine-sealed strategic packet. PR #98 remains its release and offer foundation.
- PR #132 is the current governed portfolio map: LumenCore is the platform, ProofLock is the evidence layer, the Buyer-Owned Baseline Validation Sprint is the primary offer, and Lumen Infrastructure Sentinel is the first sector lane.
- The 15 tracked lanes are not 15 separately saleable products; the current audit records zero subscription-ready lanes.
- Founder-review signed scope, pricing, excluded data, IP, and legal terms at contract time; neither #131 nor #132 is a sale, paid pilot, revenue record, external validation, or valuation.
- Rebase PR #38 after the evidence/protocol spine is stable.
- Ensure the public site points to the canonical evidence index and does not expose operator-only surfaces.

## PRs requiring refresh or retirement

- **#42:** dated control-plane snapshot; retire it as historical unless a new current-state control plane is built.
- **#53, #56, #58, #59, #63, #65:** deadline/outreach/proposal operations; keep separate from the technical product and retire when their action windows close.
- **#60:** closed after consolidation into merged PR #100. Source protection is merged; production token injection/restart remains HumanUnlock-gated.
- **#69:** stale two-PR overlay against an old graph blob; close after this atomic graph/index/map reconciliation merges.

## Merge criteria used in this map

A PR is ready for canonicalization only when:

- its base is current enough for conflict review;
- it has one clear authority and no competing exact-path implementation;
- its claim state matches the evidence state;
- generated receipts are tied to the intended source identity;
- negative results and unresolved gates are preserved;
- CI success is not described as independent or field validation;
- external actions remain separately authorized;
- its documentation identifies whether it is merged, deployed, first-party reproduced, externally executable, externally complete, or field validated.

## Current highest-value external gate

The fastest credible commercial gate is one signed buyer-owned validation scope with an authorized input, accepted baseline, locked metric, and bounded decision contract. The next evidence promotion remains a non-author execution of the pinned EIA/CODECHECK package or the assigned external-replication docket with a completed independent-executor receipt. Until those separate gates occur, revenue and external validation remain false.
