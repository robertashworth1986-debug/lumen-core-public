# LumenCore Canonical Operating State

**State date:** 2026-08-08 UTC
**Owner:** Robert Ashworth  
**Canonical product:** Proof-to-pilot AI infrastructure validation architecture  
**Work-in-progress limit:** Three founder outcomes

## One commercial sentence

LumenCore helps a buyer or technical reviewer compare an AI, forecasting, routing, or infrastructure candidate against an accepted baseline under predeclared rules, then packages the result, failures, provenance, and claim boundary into a hash-verifiable decision record.

## Active outcomes

### 1. EPRI / Open Power AI Consortium onboarding

**State:** Consortium onboarding is active under a private controlling agreement. Exact agreement status, dates, named-party terms, IP terms, and publicity terms remain in the private legal record. This lane is not funding, an award, an endorsement, independent validation, or permission to make broader public claims.

**Existing asset:** The private agreement and existing Gmail thread are the controlling records. One bounded reply supplied the two requested logo variants with permission limited to the described consortium-material use. On August 4, EPRI/OPAI replied that no extra contribution packet is required and that Robert's presence and contributions to Member Representative Committee and Work Group meetings are enough; optional thoughts or suggestions can be shared during those calls.

**Next allowed action:** Attend the recurring Member Representative Committee and selected Work Group meetings, review public/non-proprietary materials, and share bounded thoughts during those calls when useful. Keep IP and publicity actions separately agreement-gated; do not send another onboarding acknowledgment or contribution-path follow-up.

### 2. One external validation or paid-pilot conversion

**Reviewer doorway:** PR #66 was merged on July 23 at `aed61134407426114148e3201cd357099d155864`. It is the canonical human-and-machine evidence-navigation layer. PR #74 is the current merged CODECHECK/reviewer package. Route a qualified non-author evaluator through those existing surfaces; do not create another platform or validation package.

**Private external-review follow-up:** After a private technical review, a prospective collaborator shared private product documentation, requested LumenCore's thoughts, and proposed another discussion. Keep the counterparty identity and materials out of the public repository. This is not a partnership, customer, paid pilot, endorsement, validation, or permission to publish the material. Reduce any follow-up to one buyer-owned workflow, baseline, metric, data-rights boundary, and go/no-go decision.

**Agent Arena sub-harness:** PR #94 merged the single canonical V5 adversarial multi-agent synthetic/replay harness into `main`. It tests seven specialist roles under corrupted telemetry, hidden faults, role dropout, Byzantine proposals, predeclared selection-versus-holdout separation, deterministic robustness statistics, and hash-bound custody. The frozen reference scenario uses six selection floors, two holdout bosses, eight selection seeds, eight disjoint holdout seeds, and a no-red-team ablation. It is a secondary stress/holdout harness inside the proof-to-pilot architecture, not a separate product or a replacement for the PR #74 independent-execution target. Positive results remain synthetic/model evidence until a qualified non-author independently executes the frozen harness or a buyer supplies an accepted dataset or simulator, baseline, metric, threshold, and failure rules.

**LANL VISION:** A bounded non-proprietary follow-up package was sent after the July 16 meeting connection was not completed. Wait for a reschedule, a specific information request, an agreement-path owner, or a no-fit decision.

**EVTit / Vynetic:** Two near-duplicate follow-ups were sent in the same thread. The lane is locked. Wait for a substantive reply; do not send another update, deck, or scope packet.

**Selection rule:** The first qualified party that agrees to a controlled dataset, incumbent baseline, prelocked metric and threshold, reporting format, failure rules, and one go/no-go decision becomes the single active external-validation lane. All other pilot outreach pauses.

### Public runtime incident and recovery boundary

On August 8, read-only current-state probes established that DNS, TLS, nginx,
the static reviewer surface, VPS storage, and filesystem inodes were available,
while the dynamic gateway returned HTTP 502 and had no listener on loopback port
8787. The storage diagnostic recorded about 109 GiB free and no inode pressure,
so capacity was ruled out as the cause.

PRs #114, #115, and #116 progressively hardened the existing read-only VPS
diagnostic. The post-merge runs `31246089227`, `31246224480`, and
`31246373528` established a restart storm, a dead-PID singleton lock, and the
allowlisted failure signature `ModuleNotFoundError: No module named
'booth_public_contract'`. The deployed gateway source was a stale monolithic
file; the reviewed `main` entrypoint is a fail-closed facade whose local import
closure was not deployed. This is deployment drift and an incomplete runtime
bundle, not evidence of a storage failure or a defect in nginx routing.

The repository now contains a deterministic gateway-closure repair path. It is
inspect-only by default, binds twenty explicit local Python files to one bundle
SHA-256 and a full current-main commit, validates the staged entrypoint and live
order block before installation, refuses symbolic targets, removes only a
verified dead-PID gateway lock, restarts only `luma-gateway`, validates minimal
public health/status contracts, and rolls back every affected file on failure.
The corresponding workflow is manual-only and requires both the exact phrase
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE` and the private HumanUnlock secret.
It has not been dispatched in this recorded state. The separate public-static-
site release gate remains unchanged and cannot authorize gateway repair.

The public health contract is intentionally minimal: it reports liveness,
service identity, the operator-access boundary, and a UTC timestamp, but no
process IDs, internal artifact freshness, service inventory, or operator data.
Detailed health remains available only at the token-protected
`/api/operator/health` route.
The daily health workflow classifies the static reviewer surface and dynamic
gateway independently; a healthy static page can no longer conceal a failed
control plane.

### Receipt reconciliation

| Lane | Verified state | Next action |
|---|---|---|
| Army AIDP Draft CfS 2 | ACC-APG confirmed receipt on July 14. | Wait for a substantive request; do not ask for another receipt. |
| Air Force `SAF-AQ-RFI-26-0001` | The Air Force confirmed receipt on July 13. | Wait for a substantive request; do not ask for another receipt. |
| CDC `75D301-26-RFI-73483` | CDC confirmed receipt and said it would follow up. | Wait. |
| DARPA DICE proposal abstract | The IPTO submission-finalization confirmation establishes receipt. | Inspect BAAT or new inbound status; do not send the stray Gmail draft or a duplicate abstract. |
| DARPA `SN-26-97` | The package was sent after DARPA confirmed that compliant submissions were welcome. | Wait for substantive contact; do not send the existing reply draft. |
| DLA MissionWeave `DLA26BZ03-NV011` | DLA SBIR/STTR Program Operations confirmed on July 28 that DSIP showed the proposal as `In Progress`, so it was not formally submitted. The July 22 noon ET deadline passed. | Preserve the packet. Do not claim submission or send another status request without a new official ask. |
| Navy HarborSentinel `DON26BZ03-NV063` | No final-submission receipt was found. The July 22 noon ET deadline passed. | Preserve the packet. Do not claim submission or start late-submission outreach. |
| HHS Project Argos `ONC-ARGOS-SSN-2026-OS351107` | Exactly one response email was transmitted before the July 30 deadline. An automatic out-of-office reply proves mailbox-system reach only; formal receipt and agency review are not confirmed. | Do not resend. Wait for a substantive HHS request; do not claim receipt, review, selection, award, funding, or validation. |
| EPRI / Open Power AI Consortium | The MOU was completed by all parties; LumenCore provided its primary contact, initial Work Group representatives, and requested logo variants, and received the recurring Member Representative Committee invitation. EPRI/OPAI replied August 4 that no extra contribution packet is required and that presence and contributions to MRC and Work Group meetings are enough. | Attend meetings and share bounded thoughts during calls when useful; do not follow up again or start another thread. These records support onboarding and bounded meeting participation only, not endorsement, independent validation, an award, funding, broader licensing, utility adoption, approval of a specific claim, or performance. |
| Nashville EC Fall 2026 TakeOff | EC confirmed receipt of the authorization, electronic signature, and onboarding responses; confirmed everything was received on time; and said the materials would be included with the onboarding submission. EC said Robert is all set for now unless it needs something further. | Do not resend or send another acknowledgment. This confirms timely onboarding-material receipt only. It does not establish payment, a secured spot, program completion, a contract, endorsement, or validation. The separate $125 deposit remains founder-controlled and is due August 14. |
| Launch Tennessee SBIR/STTR support | Exactly one request for no-cost application support and information about the consultant microgrant was sent July 30. No reply was found. | Wait. Do not treat the request as funding, an award, eligibility confirmation, acceptance, or validation, and do not create a duplicate campaign. |

A receipt proves delivery only. It does not prove selection, technical validation, award, contract, deployment, or government endorsement.

### 3. Patent official-record protection

**Keep:** The Patent Examination Review Matrix, customer-number association draft, reviewer handoff, hash-verified patent vault, and official-record retrieval checklist.

**Do next:** Retrieve and review every official Patent Center notice, filing receipt, application document, missing-parts notice, and deadline for application 19/281,546.

**Do not do:** Create more public patent narratives, solicit broad technical endorsements, sign or submit the association form, pay a fee, or infer that outside review can cure missing as-filed support.

## Curated Codex package inventory

### Canonical and active

| Package | Decision |
|---|---|
| `QUICKSTART.md`, Proof Capsule verifier, public EIA/DICE capsule, and focused CI | **Canonical product surface. Keep and maintain.** |
| External evaluator acceptance handoff and portable validation docket | **Keep as the controlled outside-review protocol.** |
| Agent Arena adversarial multi-agent harness | **Keep as a bounded synthetic/replay sub-harness for agentic validation; V5 is the single canonical Arena configuration; do not promote it as a separate platform or as external proof.** |
| Patent Examination Review Matrix and customer-number association draft | **Keep in the protected patent lane. No public expansion.** |
| CDC AI Acquisition RFI package and artifact manifest | **Submitted; receipt confirmed. Freeze and wait.** |
| LANL VISION follow-up package | **Sent; freeze and wait.** |
| Live Funding Portal Handoff | **Use only as a deadline queue. Update existing rows; do not create parallel trackers.** |

### Preserved research, not active product scope

| Package or PR | Decision |
|---|---|
| OPAI crawlers and consortium intelligence engines | Preserve branch history; extract only the outreach lock and public facts needed for onboarding. |
| Alpha Intelligence Champion | Freeze as research. |
| Hybrid Echo Routing evolution lineage | Freeze as research. |
| QMPL and adaptive swarm sweep | Freeze as research. |
| Architecture discovery and validation engine | Freeze; it inventories scope but does not become another product. |
| Geometry publication packet, DICE/geometry audit, HarborSentinel, NV065 sensor tasking | Preserve as bounded research evidence; keep outside v1.0. |
| Trading engines and live execution surfaces | Safety-maintenance only; no product promotion and no live orders. |

## Pull-request curation

- **PR #34** — merged Proof Capsule v2 assurance foundation.
- **PR #57** — merged public-copy correction; wording cleanup is not technical validation.
- **PR #66** — merged canonical reviewer and agent doorway; exact-head evidence-graph and order-safety gates passed.
- **PR #74** — merged externally executable EIA/CODECHECK reviewer package; no independent execution receipt is present.
- **PR #94** — merged Agent Arena V5 synthetic/replay stress and holdout harness; it does not establish field or external validation.
- **PR #64** — superseded by PR #74 and remains conflicted; do not promote it as the current reviewer target.
- **PR #49** — focused external-evaluation protocol candidate.
- **PR #35** — bounded commercial validation-sprint candidate; pricing and traction remain unvalidated.

Use `EVIDENCE_INDEX.md` and `docs/PR_CONSOLIDATION_MAP_2026-07-22.md` for the disposition of the remaining PRs. Preserve superseded branches as lineage unless Robert explicitly authorizes deletion.

## Artifact creation gate

A new artifact is allowed only when all answers are yes:

1. Does it advance one active outcome?
2. Is there no existing canonical artifact that can be updated?
3. Is the audience and decision named?
4. Is the evidence boundary explicit?
5. Will it reduce, rather than expand, the reviewer path?

Otherwise, update the backlog note and stop.

## Clean-checkout protocol gate

The repository-wide test harness distinguishes ordinary clean-checkout checks
from four explicitly named publication or retained-artifact checks. Missing
generated evidence is never treated as a passing validation result: those four
checks are marked artifact-dependent only until their declared files exist.
The authoritative reviewer workflow generates its publications and then runs
the same checks without skips. The frozen CODECHECK source identity remains
byte-identical to its reviewed commit.

## Immediate decision

The next founder-facing actions are to attend the **EPRI / Open Power AI** Member Representative Committee and selected Work Group meetings, make the separate founder-controlled EC deposit decision due August 14, and privately review the active external-review material to define one measurable evaluation decision. The EPRI / OPAI contribution-path follow-up is complete and closed to further email; EC has confirmed the onboarding materials were received on time, so neither lane authorizes another acknowledgment or follow-up. The next runtime action is a separately approved execution of the exact current-main gateway dependency-closure repair followed by read-only public verification; until that occurs, the dynamic gateway remains degraded and must continue to be reported as HTTP 502. The next product action is bounded independent execution through the existing PR #74 reviewer surface, not another dashboard or platform. Agent Arena V5 is only a secondary synthetic fault-injection harness: its locked reference run improves on the weak baseline but fails the absolute zero-violation gate and does not demonstrate Byzantine tolerance. PR #67's duplicate locks and claim boundaries must remain intact. The urgent patent action remains retrieval of the official application record through the USPTO-directed authenticated or Document Services path. No other outbound message is currently authorized; in particular, no duplicate or unsolicited message is authorized.
