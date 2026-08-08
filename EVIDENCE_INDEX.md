# LumenCore Canonical Evidence Index

This page is the shortest reliable path through the public repository. It separates merged capability, deployed demonstrations, first-party reproducibility, external-review readiness, and commercial packaging. A passing hash or CI check proves only the property named by that check.

## Reviewer decision in five minutes

LumenCore is a proof-to-pilot assurance platform. Its current public strengths are artifact custody, deterministic replay, fail-closed claim governance, reviewer handoff packaging, and bounded pilot design.

The repository does **not** currently establish independent scientific validation, field-validated savings, agency endorsement, certified safety, audited revenue, or customer adoption unless a separately identified external record says so.

## Human and machine entrypoints

- Reviewer start page: [`docs/REVIEWER_START_HERE.md`](docs/REVIEWER_START_HERE.md)
- Human evidence index: `EVIDENCE_INDEX.md`
- Machine graph: [`config/evidence_graph_v1.json`](config/evidence_graph_v1.json)
- Fail-closed verifier: [`code/ops/VERIFY_EVIDENCE_GRAPH.py`](code/ops/VERIFY_EVIDENCE_GRAPH.py)
- Graph protocol: [`docs/MACHINE_EVIDENCE_GRAPH.md`](docs/MACHINE_EVIDENCE_GRAPH.md)
- Current buyer offer: [`docs/STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md`](docs/STRATEGIC_TRANSACTION_BRIEF_2026-08-08.md)
- Institutional readiness dossier: [`docs/INSTITUTIONAL_READINESS_DOSSIER.md`](docs/INSTITUTIONAL_READINESS_DOSSIER.md)
- Machine readiness register: [`config/institutional_readiness_register_v1.json`](config/institutional_readiness_register_v1.json)
- Fail-closed readiness verifier: [`code/ops/VERIFY_INSTITUTIONAL_READINESS.py`](code/ops/VERIFY_INSTITUTIONAL_READINESS.py)
- Machine-sealed offer packet: [`config/strategic_transaction_packet_v2.json`](config/strategic_transaction_packet_v2.json)
- Governed portfolio audit: [`docs/LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md`](docs/LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md)
- Machine-readable portfolio receipt: [`dashboard/data/lumencore_engine_portfolio_audit.json`](dashboard/data/lumencore_engine_portfolio_audit.json)
- PR disposition map: [`docs/PR_CONSOLIDATION_MAP_2026-07-22.md`](docs/PR_CONSOLIDATION_MAP_2026-07-22.md)
- Geometry protocol: [`docs/GEOMETRY_EVALUATION_PROTOCOL_V1.md`](docs/GEOMETRY_EVALUATION_PROTOCOL_V1.md)
- Geometry protocol registry: [`config/geometry_evaluation_protocol_v1.json`](config/geometry_evaluation_protocol_v1.json)
- Geometry protocol verifier: [`code/ops/VERIFY_GEOMETRY_EVALUATION_PROTOCOL.py`](code/ops/VERIFY_GEOMETRY_EVALUATION_PROTOCOL.py)

The machine graph is an index over detailed source records, not a replacement for them. CI verifies that upper evidence states retain their required support markers and that the reviewer-facing documents do not silently omit indexed pull requests.

## Evidence-state legend

| State | Meaning |
|---|---|
| **MERGED** | Present on the default branch. |
| **DEPLOYED DEMO** | A bounded public demonstration is live; deployment is not external validation. |
| **FIRST-PARTY REPRODUCED** | The author/operator reproduced the named computation from pinned source and environment. |
| **EXTERNALLY EXECUTABLE** | A bounded package exists for a non-author evaluator; no outside result is implied. |
| **EXTERNAL COMPLETE** | A qualified outside evaluator executed the agreed protocol and produced an accepted receipt. |
| **FIELD VALIDATED** | A data owner or operational partner validated the result under agreed field conditions. |
| **COMMERCIALLY VALIDATED** | A signed scope or purchase record, delivery record, and payment or contract evidence support the named commercial result. |
| **HELD** | The item is intentionally blocked from promotion until its named evidence or authority gate is satisfied. |
| **HISTORICAL** | The item is preserved as lineage or prior work and is not the current canonical implementation or claim. |

## 1. Canonical merged assurance foundation

### Proof Capsule verifier v3 — **MERGED**

- Pull request: [#34 — Harden the Proof Capsule verifier and CI receipt gate](https://github.com/robertashworth1986-debug/lumen-core-public/pull/34)
- Successor pull request: [#101 — Proof Capsule v3 and assurance integration](https://github.com/robertashworth1986-debug/lumen-core-public/pull/101)
- Current public role: strict schema v3, exact-byte and canonical-JSON custody, role-sensitive manifests, path/link defenses, aggregate resource budgets, declared external-report provenance, and machine-readable receipts.
- Recorded verification: 51 focused adversarial/valid-path tests; full current-main regression; Windows/Linux portability on Python 3.11 and 3.13; aggregate public-assurance integration.
- Does not prove: the underlying experiment, evaluator identity or independence, an outside report's conclusion, release authorization, field performance, or commercial value.

PR #34 remains the merged v2 foundation. Draft PR [#52](https://github.com/robertashworth1986-debug/lumen-core-public/pull/52) is closed as the historical ancestor superseded by #101.

## 2. ProofLock demonstration

### ProofLock Console — **DEPLOYED DEMO / MERGED RELEASE PATH**

- Pull request: [#36 — ProofLock Build Week judge console](https://github.com/robertashworth1986-debug/lumen-core-public/pull/36)
- Current release foundation: [#98 — ProofLock bounded validation buyer path](https://github.com/robertashworth1986-debug/lumen-core-public/pull/98)
- Current buyer-owned offer contract: [#131 — Buyer-owned validation offer](https://github.com/robertashworth1986-debug/lumen-core-public/pull/131)
- Public demo: <https://lumen-core.ai/build_week/prooflock_console/>
- Demonstrates: canonical receipt verification, browser/Python parity, an authority-escalation attack, refusal to promote while required gates remain open, and restoration of the canonical receipt.
- Recorded branch verification: focused tests and green current-head workflows are documented in the PR.
- Submission evidence: the PR records a Devpost submission confirmation. Submission is not an award, endorsement, or technical validation.

Reviewer boundary: ProofLock proves declared artifact integrity and gate policy. It does not authenticate a self-authored issuer or certify the engineering conclusion contained in a receipt.

## 3. Reproducible EIA benchmark and reviewer handoff

### Frozen EIA replay — **FIRST-PARTY REPRODUCED**

The development chain is preserved across the following drafts and its merged consolidation:

1. [#54 — CODECHECK EIA readiness packet](https://github.com/robertashworth1986-debug/lumen-core-public/pull/54)
2. [#55 — Current EIA independent-reproduction handoff](https://github.com/robertashworth1986-debug/lumen-core-public/pull/55)
3. [#61 — Windows text custody](https://github.com/robertashworth1986-debug/lumen-core-public/pull/61)
4. [#62 — Independent reviewer entrypoint](https://github.com/robertashworth1986-debug/lumen-core-public/pull/62)
5. [#64 — Historical clean-mainline consolidation branch](https://github.com/robertashworth1986-debug/lumen-core-public/pull/64)
6. [#74 — Merged current-main CODECHECK reviewer package](https://github.com/robertashworth1986-debug/lumen-core-public/pull/74)

The strongest bounded result recorded by this chain is:

- pinned source and dependency identities;
- exact Ubuntu/CPython runtime checks;
- deterministic source bundles and repeat-build parity;
- network-disabled container replay;
- 3/3 replay suites and 31/31 assertions;
- manifest and output reconciliation;
- fail-closed independent-executor receipt verification;
- explicit preservation of negative and incomplete gates.

Current claim state:

- first-party reproducibility: **supported for the named pinned package**;
- externally executable package: **prepared**;
- independent execution receipt: **not yet present**;
- CODECHECK certificate: **not present**;
- external validation: **false**;
- field validation: **false**.

The EIA lane preserves an important adverse fact: the frozen eight-authority protocol has zero common settled hours across all eight required authorities. Six-authority coverage is diagnostic progress and is not substituted for the locked protocol.

## 4. External replication contract

### External replication docket — **MERGED / EXTERNALLY EXECUTABLE**

- Historical ancestor: [#49 — External replication docket and public assurance receipt](https://github.com/robertashworth1986-debug/lumen-core-public/pull/49)
- Current merged implementation: [#99 — External replication reviewer path](https://github.com/robertashworth1986-debug/lumen-core-public/pull/99)
- Purpose: preregister source rights, holdout separation, frozen code/environment, sample adequacy, uncertainty, deviations, negative results, evaluator independence, and bounded decisions.
- Current state: unassigned `HOLD` template with strict source-custody and independence-contract checks; a passing internal receipt does not create outside validation.

### Public assurance integration — **MERGED**

- Pull request: [#101 — Proof Capsule v3 and assurance integration](https://github.com/robertashworth1986-debug/lumen-core-public/pull/101)
- Purpose: make the external-replication and strict public-assurance paths consume the current v3 receipt contract instead of silently accepting v2 expectations.
- Current state: merged and cross-platform verified; external validation remains `not_established`.

## 5. Commercial pilot package

### Bounded Validation Sprint — **MERGED OFFER / NOT COMMERCIALLY VALIDATED**

- Historical offer ancestor: [#35 — Bounded Validation Sprint](https://github.com/robertashworth1986-debug/lumen-core-public/pull/35)
- Release and offer foundation: [#98 — ProofLock bounded validation buyer path](https://github.com/robertashworth1986-debug/lumen-core-public/pull/98)
- Current machine-sealed offer: [#131 — Buyer-owned validation offer](https://github.com/robertashworth1986-debug/lumen-core-public/pull/131)
- Non-confidential fit intake: [`docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md`](docs/LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md)
- Canonical offer: [`docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md`](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md)
- Buyer-specific SOW template: [`docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md`](docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md)
- Buyer supplies: authorized source, accepted baseline, locked metric and threshold, holdout, failure rules, and decision owner.
- LumenCore supplies: bounded replay/assessment, negative-result retention, Proof Capsule, technical report, and one promote/rerun/external-review/hold/reject recommendation.
- Public price bands remain hypotheses, not booked revenue or market validation; a buyer-specific price belongs in a signed statement of work.
- Founder approval, legal review, and a signed paid scope remain separate gates.

## 6. Canonical market position and governed portfolio

### One platform, one offer, one first validation lane — **MERGED / NOT MARKET VALIDATED**

- Current buyer offer specification: [#131 — Buyer-owned validation offer](https://github.com/robertashworth1986-debug/lumen-core-public/pull/131)
- Current portfolio audit: [#132 — Governed 15-lane engine portfolio audit](https://github.com/robertashworth1986-debug/lumen-core-public/pull/132)
- Platform: **LumenCore**.
- Evidence and claim-governance layer: **ProofLock**.
- Primary paid offer: **Buyer-Owned Baseline Validation Sprint**.
- First sector validation lane: **Lumen Infrastructure Sentinel**.
- The 15 tracked lanes are internal delivery, research, and concept lanes; they are not 15 separately saleable products.
- The sealed offer packet is bound to the canonical evidence graph, and the portfolio receipt is bound to both artifacts plus tracked repository blobs.
- Current portfolio receipt records zero subscription-ready lanes. It does not establish a buyer commitment, signed paid scope, executed pilot, revenue, external validation, or transaction valuation.

## 7. Public website and security lanes

- [#38 — Conversion-ready public website](https://github.com/robertashworth1986-debug/lumen-core-public/pull/38): bounded public offer and immutable release design; draft, not a current default-branch claim.
- [#40 — Repository trust and contribution hardening](https://github.com/robertashworth1986-debug/lumen-core-public/pull/40): removes unsupported production/security language; draft.
- [#57 — Reviewer-facing repository copy cleanup](https://github.com/robertashworth1986-debug/lumen-core-public/pull/57): merged public-copy correction; not technical validation.
- [#60 — Historical operator-boundary draft](https://github.com/robertashworth1986-debug/lumen-core-public/pull/60): closed after consolidation.
- [#100 — Protect operator gateway APIs by default](https://github.com/robertashworth1986-debug/lumen-core-public/pull/100): merged fail-closed `/api`, `/ws`, and `/ws/live` source boundary. Runtime token injection and gateway restart remain governed production actions; merge is not production security certification.
- [#66 — Canonical evidence index](https://github.com/robertashworth1986-debug/lumen-core-public/pull/66): merged human/machine navigation foundation.
- [#67 — Agency receipt reconciliation](https://github.com/robertashworth1986-debug/lumen-core-public/pull/67): merged receipt-index and duplicate-outreach locks; not a proposal, award, contract, or validation event.

## 8. Pilot and external-engagement register

### Geometry evaluation protocol — **ADOPTED PROTOCOL / NO RESULT PROMOTION**

The geometry protocol admits Euclidean, curved, graph, topology-aware, parametric, biological-network, collective-motion, and field-line inspirations only as task-specific candidates. Candidate names—including mycelium, flocking, magnetic-field paths, circle packing, and brachistochrone paths—receive zero evidentiary credit until they beat matched baselines under frozen conditions. Frobenius series are treated as an analysis method, not a geometry or stability result.

The adopted registry records zero task-specific experiments, zero experimentally validated results, and no universal champion. Its CI verifier fails if those counts or claim boundaries are silently promoted.

A pilot or external engagement must be listed here only when the repository contains a discoverable objective, parties/roles, authorized source, baseline, locked metric, result state, limitations, and supporting artifact path.

| Lane | Publicly discoverable state | Evidence treatment |
|---|---|---|
| Bounded Validation Sprint | Proposed product/SOW package | Not a signed customer pilot. |
| LANL VISION | Follow-up packet after missed connection | Not a meeting outcome, partnership, license, or pilot. |
| EPRI / Open Power AI | Completed MOU and bounded onboarding/participation correspondence tracked; EPRI/OPAI replied August 4 that no extra contribution packet is required and that presence and contributions to MRC and Work Group meetings are enough | Not endorsement, independent validation, an award, funding, broader licensing, utility adoption, approval of a specific claim, or performance. |
| ProofLock Build Week | Deployed demo and submission confirmation | Not an award or outside technical validation. |
| EchoLock | **Not yet indexed in this public reviewer path** | Do not claim a completed pilot here until its report and evidence capsule are linked. |

## 9. Canonical PR disposition map

This map prevents reviewers from treating every open draft as an independent product or authoritative state.

| PR | Role | Recommended disposition |
|---:|---|---|
| 34 | Merged Proof Capsule v2 foundation | Preserve as predecessor provenance; #101 is current. |
| 35 | Historical validation-sprint offer | Closed after bounded consolidation into #98. |
| 36 | ProofLock deployed demonstration and submission record | Preserve unique history/media; current bounded release path is #98. |
| 38 | Public website release | Rebase onto current main and merge only after exact-head verification. |
| 40 | Trust/contribution wording | Rebase and merge unless superseded. |
| 42 | Control-plane snapshot | Refresh or retire; do not let a dated snapshot drive current truth. |
| 49 | Historical external replication contract | Closed after consolidation into #99. |
| 50 | Windows evidence-route portability fix | Merge before refreshing the overlapping evidence-route PR. |
| 52 | Historical Proof Capsule v3 branch | Closed after consolidation into #101. |
| 54–62 | Stacked EIA/CODECHECK development history | Preserve history; merged implementation is #74. |
| 57 | Merged reviewer-copy cleanup | Keep as merged provenance; do not treat wording cleanup as validation. |
| 60 | Historical operator API security draft | Closed after consolidation into #100. |
| 64 | Historical CODECHECK consolidation branch | Close as superseded by merged #74 after final file-parity review. |
| 65 | Deadline-specific JCP support escalation | Closed; preserve only as historical operations lineage. |
| 66–67 | Evidence navigation and receipt-state controls | Merged; keep bounded claim labels. |
| 74 | Current-main CODECHECK package | Merged canonical implementation; still awaiting non-author execution. |
| 98 | ProofLock release and bounded buyer path | Merged; not a signed sale or customer validation. |
| 99 | External replication reviewer path | Merged; template remains unassigned and held. |
| 100 | Operator API source boundary | Merged; production activation remains HumanUnlock-gated. |
| 101 | Proof Capsule v3 standard | Merged current standard with aggregate assurance integration. |
| 131 | Buyer-owned validation offer and sealed strategic packet | Merged current commercial offer specification; not a buyer commitment, signed scope, pilot, revenue, or valuation. |
| 132 | Governed 15-lane engine portfolio audit | Merged current one-platform/one-offer map; tracked lanes are not independently validated products. |

## 10. Reviewer scoring boundary

A fair current evaluation is:

- evidence-integrity engineering: strong;
- deterministic first-party reproducibility: strong for the named package;
- external-review preparation: strong but incomplete;
- independent validation: not yet established by the indexed public evidence;
- field validation and commercial traction: must be supported by separately linked external records;
- repository discoverability: synchronized across the evidence graph, current offer packet, portfolio receipt, and reviewer entrypoints.

## 11. Next promotion gates

The fastest credible commercial event is a qualified buyer accepting one authorized dataset or replay window, one incumbent baseline, one locked metric and threshold, and a signed paid validation scope. No performance result should be promised.

The highest-value scientific event is one non-author evaluator executing the pinned EIA/CODECHECK package and returning a completed receipt. That receipt must preserve evaluator identity/disclosure, reviewer-controlled execution, exact source/runtime/dependency bindings, ordered output hashes, deviations, negative results, and timestamp order.

Only after that event may the state move from **EXTERNALLY EXECUTABLE** to **EXTERNAL COMPLETE**. Field or commercial claims require additional evidence.

---

**Operating principle:** bounded light speed — move quickly without outrunning evidence, rights, reversibility, or human authority.
