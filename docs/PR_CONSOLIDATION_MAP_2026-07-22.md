# Pull Request Consolidation Map — 2026-07-22

This document records the recommended repository cleanup order after reviewing PRs #34 through #65. It is an information-architecture control, not a merge authorization.

## Canonical product spine

1. **Proof Capsule / ProofLock assurance**
   - merged foundation: PR #34
   - deployed demonstration and historical submission record: PR #36
   - proposed strict verifier successor: PR #52

2. **Reproducible benchmark / outside-review lane**
   - protocol and author-readiness origin: PR #54
   - accumulated EIA handoff history: PR #55
   - cross-platform custody and reviewer entrypoint: PRs #61 and #62
   - preferred clean-mainline consolidation target: PR #64

3. **External replication governance**
   - canonical draft contract: PR #49

4. **Commercial conversion**
   - canonical proposed offer: PR #35
   - public buyer-facing website: PR #38

## Recommended review and merge order

### Stage 1 — Reviewer entrypoint

- Merge the evidence-index branch after link and wording review.
- Do not promote draft PR claims into default-branch truth merely by linking them.

### Stage 2 — Small bounded fixes

- Review PR #50 as the canonical Windows portability correction for the evidence-route test.
- Rebase or close PR #16 after retaining only non-duplicated bounded route logic.
- Review PR #40 for trust and contribution wording.

### Stage 3 — Evidence protocol

- Review PR #49 independently for evaluator-independence and fail-closed semantics.
- Decide whether PR #52 becomes the new default Proof Capsule standard.
  - If adopted: rebase, run the full named verifier suite, merge, and update the evidence index from v2 to v3.
  - If not adopted: close it with a clear note that v2 remains canonical.

### Stage 4 — EIA/CODECHECK consolidation

- Treat PRs #54, #55, #61, and #62 as preserved development ancestry.
- Use PR #64 as the preferred mainline consolidation candidate.
- Before merge, verify that #64 contains every required final capability without importing stale generated-state or deadline-lane artifacts.
- After #64 is merged, close or retarget ancestors with explicit links to the merged implementation.

### Stage 5 — ProofLock release cleanup

- Split PR #36's durable implementation/release record from its long historical execution log.
- Preserve the exact deployed runtime identity and bounded claim text.
- Keep contest submission confirmation separate from technical validation.
- Merge only the canonical product and release surfaces after current-main conflict review.

### Stage 6 — Commercial and public presentation

- Founder-review the offer, scope, pricing hypotheses, deposit terms, excluded data, IP, and legal gates in PR #35.
- Rebase PR #38 after the evidence/protocol spine is stable.
- Ensure the public site points to the canonical evidence index and does not expose operator-only surfaces.

## PRs requiring refresh or retirement

- **#42:** dated control-plane snapshot; refresh against current state or retire it as historical.
- **#53, #56, #58, #59, #63, #65:** deadline/outreach/proposal operations; keep separate from the technical product and retire when their action windows close.
- **#60:** security-significant operator API boundary; retain as a separate focused security review and deployment lane.

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

The next evidence promotion should be a non-author execution of the pinned EIA/CODECHECK package with a completed independent-executor receipt. Until that occurs, external validation remains false.
