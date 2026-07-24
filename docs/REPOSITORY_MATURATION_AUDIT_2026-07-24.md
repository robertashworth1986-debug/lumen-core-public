# LumenCore Repository Maturation Audit — 2026-07-24

## Executive decision

LumenCore should not try to become a general-purpose model company. Its defensible lane is narrower and more valuable:

> **Proof-to-pilot technical-claim assurance:** turn a technical or AI claim into a bounded, reproducible, machine-readable decision package that preserves adverse results and prevents evidence from being promoted beyond its authority.

The canonical product spine is:

`Proof Capsule -> ProofLock -> external-replication contract -> independent-executor package -> bounded paid pilot -> buyer or transaction packet`

This audit classifies every pull request returned by the connected GitHub PR census through PR #69. Every observed PR is accounted for in `config/repository_maturation_audit_v1.json`.

The earlier connector limitation is now closed by a Git-native CI census. The audit workflow fetches `refs/heads/*` directly, enumerates every remote branch and exact tip SHA, checks every open PR head, tests ancestry against `main`, and fails if a branch without an observed PR is not classified. The current exact-head receipt records:

- **75 remote branches**;
- **59 observed PR head branches**, including this audit branch;
- **16 branch-only lines** absent from the PR census;
- **0 missing open-PR heads**;
- **0 unclassified branch-only lines**;
- one deleted historical PR head, `geometry-coverage-audit-20260623`.

The 16 branch-only lines are assigned exactly once in `config/repository_branch_disposition_v1.json`: five are already merged aliases or ancestors, five are selective-port sources, and six are preserved historical branches that must not be merged wholesale.

## Highest-severity findings

### P0 — the public evidence route is operationally broken

The current `data/site_health.json` receipt records five of six monitored endpoints healthy and `https://lumen-core.ai/evidence/` at HTTP 502. The repository already contains a bounded route-repair utility, rollback wrapper, deployment workflow, and smoke tests. The remaining defect is therefore a production execution or runtime-state problem, not proof that another competing repair implementation is needed.

Closure requires a production run receipt showing:

- `/evidence/` returns HTTP 200;
- the bounded `proof-to-pilot-evidence-v1` marker is present;
- Nginx validation succeeds;
- no DNS, credential, unrelated service, or claim-state change occurs.

A code-only CI pass does not close this operational defect.

### P0 — independent execution is still the main evidence gap

The repository has strong first-party reproducibility and an externally executable package, but no completed named non-author execution receipt. The highest-value technical event remains one independent evaluator executing the pinned package and returning the bounded receipt with deviations, ordered output hashes, negative results, and timestamp order.

### P1 — active PR overhang obscures the product

Open work currently mixes canonical product candidates, stacked ancestry, expired proposal operations, live external lanes, and historical research. This increases reviewer cost and makes a mature repository look less settled than the underlying engineering deserves.

## Branch-only disposition

### Already merged aliases or ancestors

- `agent/proof-capsule-validator`
- `agent/prooflock-cinematic-build-week`
- `deploy/retry-after-safe-capacity-recovery-20260717`
- `fix/vps-staging-directory-preflight-20260717`
- `research/architecture-discovery-validation-engine`

These require no merge. Their exact tips are already ancestors of `main`.

### Preserve and selectively port

- `agent/public-site-conversion-v1`
- `agent/whitehole-blackhole-evidence-core`
- `codex/bounded-deadline-evidence-20260719`
- `codex/live-domain-proof-feed-bundle`
- `codex/public-safe-compat-20260619`

These contain branch-only handoffs, compatibility code, evidence packaging, or economic-value controls. They are not merge candidates as branches. Any recovery requires one current owner, exact selected paths, current tests, and current claim/privacy review.

### Preserve historically; never merge wholesale

- `codex/deadline-receipts-20260718`
- `codex/harborsentinel-deadline-reconcile-20260719`
- `codex/kraken-validate-safety-20260619`
- `codex/live-data-no-orders-gate`
- `codex/mindwise-product-lane-20260718`
- `remote-main-backup-20260511-100612`

The two Kraken/no-orders branches are superseded by merged PR #18. The deadline and product-parent branches contain large stale overlap or expired state. The remote-main backup is recovery history, not an active product branch.

## Pull-request disposition

### Merge or rebuild into the canonical spine

- **#49:** canonical external-replication contract candidate.
- **#64:** sole clean-mainline CODECHECK and independent-executor consolidation target; rebuild on current `main`.
- **#36:** retain the durable ProofLock implementation, release identity, deployment receipt, and bounded claim contract; keep the long execution history as historical provenance rather than the front door.
- **#60:** default-deny operator API boundary, reviewed independently from deployment and credential provisioning.
- **#35:** bounded validation-sprint commercial package after founder review of scope, pricing, deposit, exclusions, IP, and legal boundaries.
- **#38:** exact buyer-facing public release after the evidence spine stabilizes.
- **#40:** current trust, contribution, and disclosure language, ported without stale operational claims.
- **#68:** strategic transaction optionality after founder review; inquiry authority remains non-binding and no public asking price is asserted.
- **#52:** explicit adopt-or-close decision for Proof Capsule v3. Do not leave two apparent standards indefinitely.

### Preserve as ancestry, then close after the successor is complete

- **#32, #50, #54, #55, #61, #62.** Extract only unique, non-duplicated controls into their named successor. Preserve branches and receipts; do not delete history.

### Retire from the active review queue now

- **#16:** code path superseded by merged deployment work; keep the new P0 runtime defect separate until production is healthy.
- **#42:** dated control-plane snapshot.
- **#53, #56, #58, #59, #63, #65:** expired or superseded Nashville/MissionWeave/deadline/outreach operations.

Closing these drafts does not erase evidence or declare their work invalid. It removes stale action state from the current product queue.

### Keep as active external or deadline lanes

- **#14:** wait for a bounded LANL response, specific information request, rescheduled discussion, or no-fit closure.
- **#37:** keep DICE proposal work separate from the product merge queue and preserve every legal, portal, and certification gate.

### Replace temporary reconciliation

- **#69:** replace the overlay with one atomic update to the machine graph, human evidence index, and PR consolidation map; then close the overlay.

## Scientific geometry policy

Euclidean and non-Euclidean methods are legitimate candidates only when the geometry is mathematically declared and the experiment is task-specific. A spiral, helix, gyroid, manifold, graph, or topological representation is not evidence merely because it is visually complex.

The protocol in `config/geometry_evaluation_protocol_v1.json` requires:

- dimensionality, coordinates or charts, units, metric or distance definition, curvature convention, embedding, initial and boundary conditions;
- solver, discretization, numerical tolerances, seeds, data rights, development/validation/holdout split, one primary metric, threshold, and compute budget;
- incumbent, plain Euclidean, null/randomized, geometry-only, control-only, and hybrid baselines;
- dimensional analysis, transform consistency, invariants where claimed, stability, convergence, causality, constraints, negative controls, stress tests, uncertainty, and retained failures;
- no cross-lane ranking and no universal geometry champion.

A geometry result may progress only through:

`visualization -> geometric optimization -> physics-informed -> physics-constrained -> experimentally validated`

Each transition has distinct evidence requirements. Simulation is not field validation, and visualization is not physics.

## Maturity assessment

The current public evidence supports **Level 3: externally executable** for the named reviewer package.

- Level 1: bounded artifact custody — supported.
- Level 2: deterministic first-party replay — supported for named packages.
- Level 3: externally executable reviewer package — supported.
- Level 4: completed non-author execution — not yet supported.
- Level 5: field validation — not yet supported.
- Level 6: commercial validation — not yet supported.

## Immediate order of operations

1. Restore the public `/evidence/` route and retain the production receipt.
2. Atomically reconcile PRs #66 and #67 into the human and machine evidence surfaces, replacing #69.
3. Port and merge #49 as the canonical external-replication contract.
4. Rebuild #64 on current `main`; close its stacked ancestors after parity is proven.
5. Obtain one completed non-author execution receipt.
6. Stabilize ProofLock, security, commercial, website, and transaction layers in that order.
7. Review the five selective-port branch-only sources under current owners; never merge the six historical branch-only lines wholesale.
8. Use the geometry protocol only for named customer, evaluator, solicitation, or research questions—not as a competing company identity.

**Operating principle:** become unusually trustworthy in one difficult lane rather than vaguely broad in every AI lane.
