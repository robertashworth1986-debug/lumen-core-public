# LumenCore Canonical Operating State

**State date:** 2026-08-12 UTC
**Owner:** Robert Ashworth  
**Canonical product:** Proof-to-pilot AI infrastructure validation architecture  
**Work-in-progress limit:** Three founder outcomes

## Execution policy update — September 5, 2026

Codex is no longer categorically draft-only. Codex and ChatGPT / Luma may execute
an exact founder-approved outreach message after the same campaign, existing-thread,
mailbox and duplicate checks. The current `AGENTS.md` and `code/ops/outreach_gate.py`
govern this role parity. Approval is action-specific, not blanket authority, and
the existing single-use dispatch/consumption controls remain in place. The gate
does not send email or authenticate an approval; a CLI flag is not a consent source.
Unknown, closed and waiting campaigns remain blocked. No trading, transfer,
signature, certification, account-consent or final-submission authority is added.

Implementation work should be finished, tested and committed/pushed when that
publication is authorized, without mixing unrelated dirty files or exposing private
records. Git uncommitted files, unmerged PRs, unpublished commits and undeployed
releases are different states; count and reconcile them separately. Existing
dated evidence and outreach observations below remain historical, not renewed
authorizations or current portal status.

## One commercial sentence

LumenCore helps a buyer or technical reviewer compare an AI, forecasting, routing, or infrastructure candidate against an accepted baseline under predeclared rules, then packages the result, failures, provenance, and claim boundary into a hash-verifiable decision record.

## Active outcomes

### 1. EPRI / Open Power AI Consortium onboarding

**State:** Consortium onboarding is active under a private controlling agreement. Exact agreement status, dates, named-party terms, IP terms, and publicity terms remain in the private legal record. This lane is not funding, an award, an endorsement, independent validation, or permission to make broader public claims.

**Existing asset:** The private agreement and existing Gmail thread are the controlling records. The July 29 reply supplied two harmonic-ring files that the founder identified on August 8 as the wrong consortium mark. The founder-confirmed replacement is `assets/brand/lumaarc_arc_seal_v1.png`, SHA-256 `1ed1c9b00e273aa9e781bd7fd0a4fcc3fc542257c6d294c8e8fbfada500701af`. LumenCore remains the member and company name; LumaArc is the seal name, not a company rename. On August 8, one corrective reply was sent in the existing thread with that exact asset attached and instructions to disregard the two July 29 files; Gmail sent-message ID `19fe0959c4875700` is the transmission receipt. On August 4, EPRI/OPAI replied that no extra contribution packet is required and that Robert's presence and contributions to Member Representative Committee and Work Group meetings are enough; optional thoughts or suggestions can be shared during those calls.

**Next allowed action:** Return to the no-duplicate hold. Attend the recurring Member Representative Committee and selected Work Group meetings, review public/non-proprietary materials, and share bounded thoughts during those calls when useful. Keep IP and publicity actions separately agreement-gated; do not send another logo correction, onboarding acknowledgment, or contribution-path follow-up unless EPRI/OPAI asks.

### 2. One external validation or paid-pilot conversion

**Reviewer doorway:** PR #66 was merged on July 23 at `aed61134407426114148e3201cd357099d155864`. It is the canonical human-and-machine evidence-navigation layer. PR #74 is the current merged CODECHECK/reviewer package. Route a qualified non-author evaluator through those existing surfaces; do not create another platform or validation package.

**Private external-review follow-up:** After a private technical review, a prospective collaborator shared private product documentation, requested LumenCore's thoughts, and proposed another discussion. Keep the counterparty identity and materials out of the public repository. This is not a partnership, customer, paid pilot, endorsement, validation, or permission to publish the material. Reduce any follow-up to one buyer-owned workflow, baseline, metric, data-rights boundary, and go/no-go decision.

**Agent Arena sub-harness:** PR #94 merged the single canonical V5 adversarial multi-agent synthetic/replay harness into `main`. It tests seven specialist roles under corrupted telemetry, hidden faults, role dropout, Byzantine proposals, predeclared selection-versus-holdout separation, deterministic robustness statistics, and hash-bound custody. The frozen reference scenario uses six selection floors, two holdout bosses, eight selection seeds, eight disjoint holdout seeds, and a no-red-team ablation. It is a secondary stress/holdout harness inside the proof-to-pilot architecture, not a separate product or a replacement for the PR #74 independent-execution target. Positive results remain synthetic/model evidence until a qualified non-author independently executes the frozen harness or a buyer supplies an accepted dataset or simulator, baseline, metric, threshold, and failure rules.

**LANL VISION:** A bounded non-proprietary follow-up package was sent after the July 16 meeting connection was not completed. Wait for a reschedule, a specific information request, an agreement-path owner, or a no-fit decision.

**EVTit / Vynetic:** Two near-duplicate follow-ups were sent in the same thread. The lane is locked. Wait for a substantive reply; do not send another update, deck, or scope packet.

**Selection rule:** The first qualified party that agrees to a controlled dataset, incumbent baseline, prelocked metric and threshold, reporting format, failure rules, and one go/no-go decision becomes the single active external-validation lane. All other pilot outreach pauses.

### Public runtime incident and recovery boundary

**Latest verified point-in-time observation (August 10):** The committed
`data/site_health.json` snapshot at `2026-08-10T12:33:26Z` recorded all eight
monitored endpoint checks operational: six static HTTP checks and two dynamic
JSON-contract checks. A separate read-only probe beginning at
`2026-08-10T13:50:06Z`
matched the declared content contracts for the five current bounded reviewer
surfaces and the two minimal public gateway endpoints, `/health` and
`/api/public/status`, with HTTP 200 responses. These observations establish
point-in-time public liveness only. They do not establish the recovery cause,
that the guarded dependency-closure repair ran, the deployed gateway commit or
source closure, sustained availability, production approval, or external
validation. Those liveness observations are not exact-byte release parity;
the later separately gated static-release receipts establish that narrower
condition for named release `1ce7c359`.

**Reconciled named static release (August 12):** PR #167 merged the exact
43-file release-control update at commit
`1ce7c35975a4011fa844e8b39ccbc950c8c0f398`. Main-branch supply-chain run
`31548604617`, separately human-gated deployment run `31548829514`, and
read-only post-deployment audit run `31548906293` all completed successfully.
The deployment captured rollback state and the deployment and audit receipts
each recorded 43-of-43 exact live-byte matches with `release_verified: true`.
The audit classified `NO_INCIDENT_OBSERVED`, severity `NONE`, decision
`MONITOR`. PR #168 then merged the append-only receipt history at commit
`5e03e6c98e67d9f8c68ae6816d2c56a9f2cd301d`; the retained verifier
reconstructs both named deployed Git subjects. These are first-party static
release and custody results. They do not establish external validation,
certification, whole-VPS or gateway provenance, scientific validity, customer
acceptance, revenue, savings, or broader platform production authorization.
Neither gateway liveness nor exact-byte deployment constitutes external
validation.
Later commits that do not change the allowlisted static bytes do not replace
the named `1ce7c359` deployment identity.

**Scheduled health-writer integrity receipt (August 12):** PR #171 merged the
exact tested head `600b138f1008022b6c5bb07695eb8c55d3aa3b2b` at merge commit
`f2ea3a3bffbf344b7fa007c222b56f7d7e5bb5c1`. The change requires the daily
health workflow to validate the complete 15-endpoint snapshot and badge
contracts; permits repository mutation only for `data/site_health.json` and
`data/uptime_badge.json` using null-delimited Git path handling; rechecks the
committed path set after rebase; and verifies the exact remote branch head
after publication. The clean local repository suite recorded 798 passed tests,
7 skipped tests, and 48 passed subtests. The PR's gateway-contract, engine,
institutional-readiness, dependency-review, repository-trust, and both
language-specific CodeQL checks passed on that exact head. Manual post-merge
health run `31559056763` then completed successfully, created snapshot commit
`b1fa45003746a9b4b6c3b033034182d97ace3ac0`, and recorded 15-of-15 declared
contracts healthy at `2026-08-12T03:07:11Z`; Pages run `31559066395` deployed
that snapshot successfully. This is first-party software, publication-integrity,
and point-in-time liveness evidence. It does not establish sustained uptime,
gateway source closure, penetration-test or security certification, external
validation, scientific superiority, profitable trading, customer acceptance,
revenue, savings, or broader production authorization.

**Current read-only VPS runtime verdict (August 12):** PR #181 merged the
guarded gateway runtime-closure repair at exact merge commit
`40a0463e061e912263a62527fdab2c0fbb92c6d2`. After PR #183 merged the exact
repository-security state, read-only diagnostic run
[`31573034746`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31573034746)
captured a complete bounded receipt against current `main` commit
`6a22b2f748ecb2457d89a0494d0c04f4374a93b9` at `2026-08-12T07:13:07Z`.
The diagnostic workflow completed because the receipt was captured; the
separate commit status correctly reported failure with verdict
`ACTION_REQUIRED`. Its assessment recorded one passing check, six failing
checks, and zero unknown checks. The raw diagnostic SHA-256 is
`340b26868946b02a9516e91c717acff3c46e879b45cf40d7a379c2239a1ab412`.

All seven declared public/loopback endpoint codes passed, including the
expected fail-closed HTTP 503 at the unauthenticated protected snapshot route.
The gateway was active and its lock PID matched the systemd main PID, but the
effective unit still had no explicit `User` or `Group` and the live lock was
`root:root:644`. The approved 20-file current-main gateway closure recorded 19
matches, one mismatch (`grant_application_factory.py`), and zero missing,
symbolic, or unreadable targets. The paper-ticker process was in `activating`
and `auto-restart` with `NRestarts=193976` under `lumencore:lumencore`; its exact
empty ledger remained `opc:opc:644`, was not writable by `lumencore`, and
produced twelve allowlisted `PermissionError` observations during the bounded
five-minute window. The same receipt recorded a successful read-only `nginx -t`.
Capacity was not the cause: about 108 GiB remained available and inode use was
one percent. The retained artifact is `lumencore-vps-runtime-31573034746`,
artifact ID `9132068760`, with GitHub
artifact digest
`sha256:776578b53ed73d95d1fc1e74f7a6335a5cb36bc0edd702fe1add688a6cf3ae2e`
and seven-day retention.

The existing manual gateway repair now treats source and service identity as
one hash-bound runtime closure under the unchanged exact approval phrase
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE`. It validates a deterministic
systemd drop-in, migrates only `/opt/lumencore/run` to
`lumencore:lumencore:750`, requires the live PID lock to become
`lumencore:lumencore:640`, applies the 20 exact source files, and restores the
prior source bytes, service drop-in, run-directory metadata, and active/stopped
service state if any identity, parity, or HTTP contract fails. The distinct
paper control remains `REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP`.

The private `LUMA_HUMAN_UNLOCK_TOKEN` repository secret remains unconfigured,
so neither repair was dispatched and no VPS mutation was attempted. A fresh,
target-specific founder authorization and that private HumanUnlock control are
required before either workflow can change production. These first-party
observations prove only current bounded liveness, runtime identity, source
drift, capacity, and the named paper-worker failure. They do not establish
sustained availability, whole-VPS parity, external validation, profitable
trading, customer acceptance, revenue, savings, or broader production
authorization.

**Repository vulnerability closure (August 12):** Dependabot alert #3,
`GHSA-5239-wwwm-4pmq`, identified a low-severity local-access ReDoS advisory in
the security-header workflow's Pygments dependency. PR #162 upgraded the
hash-locked requirement from 2.19.2 to patched release 2.20.0 and merged at
`d3a6ecd78159c7dd418b1f870bf160c931a77f30`. The dependency-graph update and
security-header receipt workflow passed, and GitHub recorded the alert as
`fixed` at `2026-08-12T00:31:24Z`. This closes that named alert only; it does
not establish a vulnerability-free codebase, penetration test, runtime scan,
or external security certification.

PR #175 separately upgraded the institutional Requests pin and complete
hash-locked closure from 2.32.5 to 2.33.0 for `CVE-2026-25645`, repaired the
pin-drift mutation test so it follows the current manifest rather than a
hard-coded version, and merged at
`8f9fe26d031ff1ad2eed834a2a70fa8aa2015305`. The exact repaired head passed
dependency review, both CodeQL language analyses, the focused institutional
verifier, and the complete repository suite; the same complete and focused
gates passed after merge on `main`. After the dependency graph refreshed,
GitHub reported zero open Dependabot alerts at the point-in-time check. This
closes the named Requests advisory and current GitHub alert queue only; it does
not establish zero vulnerabilities, a penetration test, dependency freshness
outside the tracked manifests, or external security certification.

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
The private value is transferred as an owner-only file and is never expanded
into the remote command line; apply mode refuses any target, service, lock,
runtime, or probe identity outside the exact production contract. Recursive
temporary cleanup is path-bounded, and every workflow dependency is pinned to
an immutable commit. The evidence recorded here does not establish that this
guarded repair was dispatched or that it caused the later point-in-time
recovery. The separate public-static-site release gate remains unchanged and
cannot authorize gateway repair.

The public health contract is intentionally minimal: it reports liveness,
service identity, the operator-access boundary, and a UTC timestamp, but no
process IDs, internal artifact freshness, service inventory, or operator data.
Detailed health remains available only at the token-protected
`/api/operator/health` route.
The daily health workflow classifies the static reviewer surface and dynamic
gateway independently; a healthy static page can no longer conceal a failed
control plane.

The reviewed public browser contract is now separated from the operator
runtime contract. Public pages request only `/health` and
`/api/public/status`, validate the fixed minimal response fields, and display
gateway liveness without probing `/api/snapshot` or inferring execution state.
The canonical homepage no longer links directly into the no-index operator
mission surface. Operator pages retain their separate protected runtime path.
That repository change alone did not establish live gateway health. The August
9 public probes are separate point-in-time liveness evidence, not proof of the
recovery mechanism, the deployed gateway commit, sustained service health, or
static exact-snapshot parity.

Manual gateway-repair run `31248779848` accepted the exact current-main commit
and exact approval phrase, then failed closed before SSH because repository
secret `LUMA_HUMAN_UNLOCK_TOKEN` was not configured. No VPS change was
attempted. The paper-ticker repair was not dispatched because it depends on the
same missing private action-time control. Both workflows now emit a specific
non-secret error for this precondition while retaining the existing gate.

PR #125 corrected the read-only loopback probe so it preserves the public TLS
hostname while pinning the connection to `127.0.0.1`. Post-merge run
[`31251081800`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31251081800)
then established the complete request path without disabling certificate
validation: nginx itself returned HTTP 200 on loopback, the gateway route
through nginx returned HTTP 502, and the direct gateway port refused the
connection. The public root, opportunity-sprint page, and nginx health surface
returned HTTP 200 in the same observation window. This isolates the outage
behind nginx rather than at DNS, TLS, or the static web tier.

PR #126 bound the runtime diagnostic to the exact `main` commit and compared
the deterministic twenty-file gateway source closure with the deployed VPS by
path and SHA-256 without reading or publishing file contents. Post-merge run
[`31251277886`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31251277886)
recorded source commit `4348ff77ef5731221c7116dfa7674b4feda63803`,
approved bundle SHA-256
`af63196219884e7c8d122231dc1aa6e7a919018778082ed0ff4794919ea51c05`,
zero matching files, sixteen mismatched files, and four missing files. The
missing files were `booth_public_contract.py`,
`execution/order_safety_gate.py`, `luma_experience_gateway_legacy.py`, and
`operator_api_access.py`; no symbolic or unreadable targets were found. This
proves whole-closure deployment drift, not a one-file patch condition. It does
not prove that the guarded repair has run or that the live gateway is healthy.

Manual health run `31247095241` recorded the first current-contract snapshot at
commit `0ff614be`: all six static reviewer endpoints passed, while both dynamic
gateway contracts returned HTTP 502, so the public state is explicitly
`degraded`, with `static_surface_state=operational` and
`dynamic_gateway_state=outage`.

Read-only runtime run `31247114240` also showed two worker restart histories
that require diagnosis before any service change: `luma-paper-ticker` was in
`auto-restart` with `NRestarts=179423`, and `luma-symbol-awareness` was running
with `NRestarts=205076`. These counts do not establish a current root cause or
performance defect by themselves. The bounded VPS diagnostic now captures only
allowlisted, redacted failure signatures from five-minute windows for those two
workers, alongside the existing two-minute gateway window. It remains
observation-only: no restart, stop, deletion, log vacuum, or configuration
change is permitted by that workflow.

Post-merge diagnostic run `31247338156` isolated the paper ticker's current
failure signature to `PermissionError` while opening
`/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl`. The
same bounded run found no allowlisted symbol-awareness failure in its five-
minute window. Follow-up read-only run `31247505265` proved that the stack root
was traversable and both output parents were `lumencore:lumencore` mode `755`
and writable, while the exact zero-byte ledger was `opc:opc` mode `644` and not
writable by `lumencore`. No symbolic path was present. This identifies the
current paper-ticker crash cause without reading ledger contents.

The repository now contains a manual-only, rollback-capable repair for that
exact incident. It binds the empty-ledger SHA-256, `opc:opc:644` pre-state, one
repair-script SHA-256, and a full current-main commit; requires both the exact
phrase `REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP` and the private HumanUnlock; stops
and starts only `luma-paper-ticker`; changes only the exact ledger to
`lumencore:lumencore:640`; and installs one bounded restart-policy drop-in. It
refuses symlinks, multiple hard links, path or metadata drift, an unexpected
service identity, or a missing paper-only preflight, and rolls the metadata and
drop-in back if service stability fails. The repair has not been dispatched in
this recorded state. Future full deployments explicitly preserve the ledger,
set least-privilege ownership/mode, and bound both paper-ticker and shadow
symbol-awareness restart storms.

### Institutional full-suite gate receipt — August 12, 2026

PR #174 merged the repository-wide institutional test gate into `main` at
commit `852dd05f7320705e764f0cd488e874248ae57b36`. Every pull request and every
push to `main` now runs the complete first-party pytest collection on Ubuntu
24.04 with exact Python 3.11.9, a hash-locked binary-only dependency closure,
`pip check`, a source-mutation check, and a commit-bound JUnit artifact. The
fast focused readiness verifier remains a separate job.

The first PR attempt was blocked before merge because GitHub dependency review
identified two high-severity malformed-PDF infinite-loop advisories in
`pypdf==6.13.2` (`GHSA-5xf7-4p34-54qr` and
`GHSA-g867-7843-wf8q`). The final reviewed head upgraded the direct pin to
`pypdf==6.15.0`, regenerated the complete lock, and then passed dependency
review. This is evidence that the security gate rejected one vulnerable
dependency change and that the corrected closure passed that bounded review;
it is not a whole-system or future vulnerability-free claim.

Post-merge institutional-readiness run
[`31563059423`](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31563059423)
executed against the exact published `main` commit and recorded:

- dependency-lock status `INSTITUTIONAL_DEPENDENCY_LOCK_VALID`;
- 14 direct pins, 39 resolved packages, and 717 recorded SHA-256 hashes;
- normalized lock SHA-256
  `90cc18300371fcb3a09f3967c15880b97ddad174ec7f10e91d1f8bba5d715229`;
- `pip check`: no broken requirements;
- 802 passed tests, 7 explicit skips, 5 warnings, and 48 passed subtests in
  46.87 seconds; and
- successful source-mutation rejection and artifact upload steps.

The main-bound JUnit artifact is
`institutional-full-suite-852dd05f7320705e764f0cd488e874248ae57b36`,
artifact ID `9128457813`, with GitHub artifact digest
`sha256:de02d797e0c28c5c6f90c877ee43dd0a73053294f6db1450e41b73ff1e079115`.
It expires under the workflow's 30-day retention policy on September 11, 2026.

The seven Ubuntu skips are not counted as passes: four require generated
publication or evidence artifacts absent from a clean source checkout, and
three require Windows PowerShell rather than the Ubuntu runner. A complementary
Windows run on the reviewed head recorded 802 passed, 7 skipped, 5 warnings,
and 48 passed subtests in 411.82 seconds; its three platform skips were the
POSIX-only root-side Bash integrations. Together these runs establish bounded
cross-platform first-party software behavior for the tested source. They do
not establish production readiness, independent or field validation,
certification, zero vulnerabilities, revenue, savings, profitable trading, or
sustained uptime.

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
| EPRI / Open Power AI Consortium | The MOU was completed by all parties; LumenCore provided its primary contact and initial Work Group representatives and received the recurring Member Representative Committee invitation. The founder identified the two July 29 harmonic-ring logo attachments as the wrong consortium mark. One corrective reply was sent August 8 in the existing thread with the founder-confirmed LumaArc seal attached and a statement that the member/company name remains LumenCore; Gmail sent-message ID `19fe0959c4875700` is the transmission receipt. EPRI/OPAI replied August 4 that no extra contribution packet is required and that presence and contributions to MRC and Work Group meetings are enough. | Return to the no-duplicate hold and attend meetings. Do not send another logo correction or onboarding follow-up unless EPRI/OPAI asks. These records support onboarding and bounded meeting participation only, not endorsement, independent validation, an award, funding, broader licensing, utility adoption, approval of a specific claim, or performance. |
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
- **PR #162** — merged the hash-locked Pygments 2.20.0 security update at `d3a6ecd7`; Dependabot alert #3 is fixed, not a whole-system security claim.
- **PR #164** — merged eight noindex HOLD stubs at `f7662d5`; those files are included in named release `1ce7c359` and its 43-of-43 live receipt.
- **PR #167** — merged the 43-file exact public-release controls at `1ce7c359`; the separately gated deployment and read-only audit succeeded.
- **PR #168** — merged append-only deployment receipt history at `5e03e6c9`; the broader platform remains `HOLD`.
- **PR #181** — merged the two guarded VPS repair controls at `40a0463e`; the merge established code and approval boundaries, not execution of either live repair.
- **PR #183** — merged the exact remote repository-security assurance at `6a22b2f7`; the bounded checks passed, while one historical provider-key alert and unenforced `main` protection remain visible `HOLD` gates.
- **PR #184** — merged the newest read-only VPS-runtime receipt into this canonical state at `e4a4aeaa`; the observed runtime verdict remains `ACTION_REQUIRED`, and no VPS mutation was authorized or attempted.
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

The next founder-facing actions are to attend the **EPRI / Open Power AI**
Member Representative Committee and selected Work Group meetings, make the
separate founder-controlled EC deposit decision due August 14, and reduce the
active private-review material to one buyer-owned workflow, baseline, metric,
threshold, and go/no-go decision. EPRI / OPAI and EC remain under no-duplicate
holds unless they make a new substantive request.

The named public static release is reconciled at `1ce7c359`, but broader
production promotion remains `HOLD`. The August 12 read-only runtime receipt
against `6a22b2f7`, now recorded on `main` at `e4a4aeaa`, proves only the exact
point-in-time endpoint, identity, source-parity, worker, ledger, and capacity
observations stated above. Do not describe the gateway as down, repaired,
source-complete, or production-authorized. The only prepared live changes are
`REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE` and
`REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP`; neither may be dispatched until the
private HumanUnlock secret exists and Robert gives fresh target-specific
authorization at action time.

The next product and revenue gate is one paid or independently executed
Buyer-Owned Baseline Validation Sprint through the existing PR #74 reviewer
surface. Do not create another dashboard, platform, or generic evidence pack.
Agent Arena V5 remains a secondary synthetic fault-injection harness and does
not demonstrate Byzantine tolerance or field performance. PR #67's duplicate
locks and claim boundaries remain intact. The urgent patent action remains
retrieval of the official application record through the USPTO-directed
authenticated or Document Services path. No duplicate or unsolicited outbound
message is authorized. No other outbound message is currently authorized.
