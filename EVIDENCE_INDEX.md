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
- PR disposition map: [`docs/PR_CONSOLIDATION_MAP_2026-07-22.md`](docs/PR_CONSOLIDATION_MAP_2026-07-22.md)

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

### Proof Capsule verifier v2 — **MERGED**

- Pull request: [#34 — Harden the Proof Capsule verifier and CI receipt gate](https://github.com/robertashworth1986-debug/lumen-core-public/pull/34)
- Current public role: validates capsule structure, source rights, evidence/run compatibility, canonical manifest paths, artifact identity, resource limits, bounded claims, and machine-readable receipts.
- Recorded verification: 26 focused adversarial/valid-path tests, Windows clean-checkout validation, and successful GitHub Actions on the merged head.
- Does not prove: the underlying experiment, external evaluator independence, field performance, or commercial value.

This is the current merged evidence-integrity baseline until a later verifier revision is reviewed and merged.

## 2. ProofLock demonstration

### ProofLock Console — **DEPLOYED DEMO / DRAFT PR**

- Pull request: [#36 — ProofLock Build Week judge console](https://github.com/robertashworth1986-debug/lumen-core-public/pull/36)
- Public demo: <https://lumen-core.ai/build_week/prooflock_console/>
- Demonstrates: canonical receipt verification, browser/Python parity, an authority-escalation attack, refusal to promote while required gates remain open, and restoration of the canonical receipt.
- Recorded branch verification: focused tests and green current-head workflows are documented in the PR.
- Submission evidence: the PR records a Devpost submission confirmation. Submission is not an award, endorsement, or technical validation.

Reviewer boundary: ProofLock proves declared artifact integrity and gate policy. It does not authenticate a self-authored issuer or certify the engineering conclusion contained in a receipt.

## 3. Reproducible EIA benchmark and reviewer handoff

### Frozen EIA replay — **FIRST-PARTY REPRODUCED**

The canonical development chain is documented across the following drafts:

1. [#54 — CODECHECK EIA readiness packet](https://github.com/robertashworth1986-debug/lumen-core-public/pull/54)
2. [#55 — Current EIA independent-reproduction handoff](https://github.com/robertashworth1986-debug/lumen-core-public/pull/55)
3. [#61 — Windows text custody](https://github.com/robertashworth1986-debug/lumen-core-public/pull/61)
4. [#62 — Independent reviewer entrypoint](https://github.com/robertashworth1986-debug/lumen-core-public/pull/62)
5. [#64 — Clean mainline CODECHECK integration](https://github.com/robertashworth1986-debug/lumen-core-public/pull/64)

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

### External replication docket — **DRAFT / REVIEW REQUIRED**

- Pull request: [#49 — External replication docket and public assurance receipt](https://github.com/robertashworth1986-debug/lumen-core-public/pull/49)
- Purpose: preregister source rights, holdout separation, frozen code/environment, sample adequacy, uncertainty, deviations, negative results, evaluator independence, and bounded decisions.
- Current state: unassigned template; a passing internal receipt does not create outside validation.

### Proof Capsule verifier v3 — **DRAFT / REVIEW REQUIRED**

- Pull request: [#52 — Proof Capsule verifier v3 custody hardening](https://github.com/robertashworth1986-debug/lumen-core-public/pull/52)
- Purpose: strict schema v3, exact-byte and canonical-JSON binding, role-sensitive manifests, path/link defenses, artifact budgets, and external-validation provenance requirements.
- Current state: not the merged default-branch standard.

## 5. Commercial pilot package

### 30-Day Bounded Validation Sprint — **PROPOSED / DRAFT**

- Pull request: [#35 — Bounded Validation Sprint](https://github.com/robertashworth1986-debug/lumen-core-public/pull/35)
- Buyer supplies: authorized source, accepted baseline, locked metric and threshold, holdout, failure rules, and decision owner.
- LumenCore supplies: bounded replay/assessment, negative-result retention, Proof Capsule, technical report, and one promote/rerun/external-review/hold/reject recommendation.
- Pricing in the PR is an untested hypothesis, not booked revenue or market validation.
- Founder approval, legal review, and a signed paid scope remain separate gates.

## 6. Public website and security lanes

- [#38 — Conversion-ready public website](https://github.com/robertashworth1986-debug/lumen-core-public/pull/38): bounded public offer and immutable release design; draft, not a current default-branch claim.
- [#40 — Repository trust and contribution hardening](https://github.com/robertashworth1986-debug/lumen-core-public/pull/40): removes unsupported production/security language; draft.
- [#57 — Reviewer-facing repository copy cleanup](https://github.com/robertashworth1986-debug/lumen-core-public/pull/57): merged public-copy correction; not technical validation.
- [#60 — Protect operator gateway APIs by default](https://github.com/robertashworth1986-debug/lumen-core-public/pull/60): fail-closed outer API authentication boundary; draft and not deployed by the PR.

## 7. Pilot and external-engagement register

A pilot or external engagement must be listed here only when the repository contains a discoverable objective, parties/roles, authorized source, baseline, locked metric, result state, limitations, and supporting artifact path.

| Lane | Publicly discoverable state | Evidence treatment |
|---|---|---|
| Bounded Validation Sprint | Proposed product/SOW package | Not a signed customer pilot. |
| LANL VISION | Follow-up packet after missed connection | Not a meeting outcome, partnership, license, or pilot. |
| EPRI / Open Power AI | Completed MOU and bounded onboarding/participation correspondence tracked; EPRI/OPAI replied August 4 that no extra contribution packet is required and that presence and contributions to MRC and Work Group meetings are enough | Not endorsement, independent validation, an award, funding, broader licensing, utility adoption, approval of a specific claim, or performance. |
| ProofLock Build Week | Deployed demo and submission confirmation | Not an award or outside technical validation. |
| EchoLock | **Not yet indexed in this public reviewer path** | Do not claim a completed pilot here until its report and evidence capsule are linked. |

## 8. Canonical PR disposition map

This map prevents reviewers from treating every open draft as an independent product or authoritative state.

| PR | Role | Recommended disposition |
|---:|---|---|
| 34 | Merged Proof Capsule v2 foundation | Keep canonical. |
| 35 | Commercial validation-sprint package | Review, approve boundaries, then merge as commercial documentation. |
| 36 | ProofLock deployed demonstration and submission record | Split historical log from release docs; merge only the bounded canonical release state. |
| 38 | Public website release | Rebase onto current main and merge only after exact-head verification. |
| 40 | Trust/contribution wording | Rebase and merge unless superseded. |
| 42 | Control-plane snapshot | Refresh or retire; do not let a dated snapshot drive current truth. |
| 49 | External replication contract | Focused review, then merge as the canonical external-evaluation protocol. |
| 50 | Windows evidence-route portability fix | Merge before refreshing the overlapping evidence-route PR. |
| 52 | Proof Capsule v3 | Decide explicitly: merge as the new standard or close as an unadopted draft. |
| 54–62 | Stacked EIA/CODECHECK development history | Preserve history; consolidate the final clean implementation through #64. |
| 57 | Merged reviewer-copy cleanup | Keep as merged provenance; do not treat wording cleanup as validation. |
| 60 | Operator API security boundary | Keep as a separate focused security and deployment review. |
| 64 | Clean-mainline reviewer package | Treat as the preferred consolidation target after focused review. |
| 65 | Deadline-specific JCP support escalation | Keep separate from the technical evidence product; close/retire when the deadline lane is complete. |
| 66 | Evidence index and machine navigation | Merge only after conflict reconciliation and current-head graph verification. |

## 9. Reviewer scoring boundary

A fair current evaluation is:

- evidence-integrity engineering: strong;
- deterministic first-party reproducibility: strong for the named package;
- external-review preparation: strong but incomplete;
- independent validation: not yet established by the indexed public evidence;
- field validation and commercial traction: must be supported by separately linked external records;
- repository discoverability: being corrected through this index and subsequent consolidation.

## 10. Next promotion gate

The highest-value next event is one non-author evaluator executing the pinned EIA/CODECHECK package and returning a completed receipt. That receipt must preserve evaluator identity/disclosure, reviewer-controlled execution, exact source/runtime/dependency bindings, ordered output hashes, deviations, negative results, and timestamp order.

Only after that event may the state move from **EXTERNALLY EXECUTABLE** to **EXTERNAL COMPLETE**. Field or commercial claims require additional evidence.

---

**Operating principle:** bounded light speed — move quickly without outrunning evidence, rights, reversibility, or human authority.
