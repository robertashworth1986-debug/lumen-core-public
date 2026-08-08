# Live-Breadth Governance Protocol

## Purpose

Convert a private source registry into a reviewer-auditable governance sidecar
without publishing provider names, credential field names, or unsupported
performance/economic claims.

## Separation of Duties

The software can collect observations, calculate hashes, identify missing
fields, and enforce claim gates. It cannot invent these source-owner decisions:

- whether the organization has the right to use a source for the proposed review,
- which named decision the source is relevant to,
- the minimum row depth required for that decision,
- the maximum acceptable observation age,
- which exact dataset snapshot is being reviewed, and
- which accountable role approved the completed worklist.

## Workflow

1. Build a private worklist from an explicit registry snapshot.
2. Record rights evidence from provider terms, a license, a contract, or a
   written data-owner decision.
3. Define relevance and thresholds from the intended decision before scoring.
4. Hash the exact underlying dataset snapshot.
5. Set the protocol review fields only after the source items have no blockers.
6. Promote the integrity-valid worklist into a sealed governance sidecar.
7. Rebuild the public pseudonymous manifest from the same registry hash and the
   sealed sidecar.

## Commands

```text
python code/ops/build_live_breadth_governance_worklist.py build --registry <private-registry.json> --output <private-worklist.json>
python code/ops/build_live_breadth_governance_worklist.py promote --worklist <approved-private-worklist.json> --output <private-governance.json>
python code/ops/build_public_live_breadth_manifest.py --registry <private-registry.json> --governance <private-governance.json> --output dashboard/data/public_live_breadth_manifest.json --markdown docs/PUBLIC_LIVE_BREADTH_MANIFEST_2026-08-08.md
```

## Fail-Closed Rules

- The registry path is always explicit.
- The private worklist is marked `PRIVATE_DO_NOT_PUBLISH`.
- Credential field names and economic translations are not copied into it.
- An incomplete or tampered worklist cannot be promoted.
- A governance sidecar is invalid when its registry hash does not match the
  manifest input.
- A governance sidecar is invalid without protocol approval, reviewer role,
  review time, worklist hash, and its own valid SHA-256 receipt.
- Public source rows remain pseudonymous and use a strict field allowlist.
- No manifest permits claims of alpha, savings, independent validation,
  current runtime state, or live-capital readiness.

## Current State

The August 6 registry is frozen in a public-safe manifest with 17
configured/enabled sources, 14 explicit probe successes, and 0 review-ready
sources. The next evidence task is completing the private worklist with
source-backed decisions; it is not increasing the public count by assertion.
