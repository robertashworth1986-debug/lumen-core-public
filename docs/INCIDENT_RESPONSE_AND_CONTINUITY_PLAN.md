# LumenCore Incident Response and Continuity Plan

**Version:** 1.0

**Scope:** public review surfaces and the bounded Buyer-Owned Baseline
Validation Sprint

**Machine policy:**
[`config/incident_response_and_continuity_v1.json`](../config/incident_response_and_continuity_v1.json)

## Current assurance state

This is a documented first-party control with deterministic CI exercises and a
live read-only audit integration. It is not a tested live incident-response
program, business-continuity certification, disaster-recovery certification,
enterprise SLA, penetration test, or legal/compliance determination.

The current public-site mismatch is treated as a release-integrity incident,
not hidden as a successful deployment. Repository evidence remains canonical
until a human-authorized exact-snapshot deployment produces a successful
current-commit live receipt.

### October 9, 2026 read-only release reconciliation

Active outcome 2: one external validation or paid-pilot conversion.
The intended source examined was `1fba9f0213ae79c1739fc6f7bca8266e94752b72`.
The unchanged repository verifier completed its full 246-file public HTTP audit
at **2026-10-09T07:44:33.321519Z**: **192 matched, 3 mismatched, and 51 returned HTTP 404**.
The [raw observation](../evidence/public-site-deployments/observations/20261009T073306Z/live-verification.json)
and [classification](../evidence/public-site-deployments/observations/20261009T073306Z/classification.json)
retain `release_verified: false` and `HOLD_PUBLIC_RELEASE_PROMOTION`.
This is a first-party read-only observation, not an independent assessment or
a deployment receipt. No production discrepancy was corrected in this pass.

Separate nonce requests completed at 07:33:59 UTC. All 51 later additions
returned HTTP 404; the three changed existing paths—`operator_home.html`,
`robots.txt`, and `sitemap.xml`—returned hashes matching September 23 source
`dfc45fe2a05102c835dafe05d9b847cd04566086`. The missing additions are 22
Bounded Light files, 23 portfolio files, two rights files, and four art files.
They are in the current allowlist, not intentional current-release exclusions.
The [reconciliation](../evidence/public-site-deployments/observations/20261009T073306Z/reconciliation.json)
enumerates every affected path. Each receipt preserves its own observation time;
the observation directory is anchored to the nonce diagnostic's start time.

The latest successful guarded deployment found was
[run 35907010582](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/35907010582),
which verified all 195 files on September 23. Comparison with intended source
accounts exactly for the 51 added files and three changed files. The 246 release
file paths and hashes are unchanged between October 7 audit source `e5487b6d`
and the October 9 comparison subject. The
[October 8 audit](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37770785899)
also recorded 192 matches, three mismatches, and 51 errors.
This is consistent with the older deployment remaining served. Public requests
do not inspect the origin filesystem or prove every intermediary cache was bypassed.

Local immutable packaging and inventory verification passed for all 246 files.
The reconstructed archive SHA-256 is
`3a10704a9c8f152aa728c0de47e47a9a8d1963f6e1df7d710fe0b20feafb2a87`.
Retained signed provenance and SBOM verification from
[run 37780663244](https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/37780663244)
bind that same archive, source, main ref, signing workflow, GitHub OIDC issuer,
and hosted runner. Those CI receipts were inspected; fresh local cryptographic
verification was not executed because the GitHub CLI was unavailable.

No production files, DNS/email records, Nginx settings, runtime services, or
existing reviewer materials were changed. Exact static-release approval remains
absent, the connected GitHub tools expose no workflow dispatch operation, and no
server deployment session was used. These access and authorization limits prevent
repair in this pass. Public-release promotion and broader production remain HOLD.

## Authority and roles

| Role | Responsibility | Authority boundary |
|---|---|---|
| Founder/operator | Accountable incident owner and final release authority | Must personally authorize production mutation and incident closure |
| Automated evidence custodian | Package Git bytes, collect public HTTP evidence, classify bounded drift, and retain receipts | Cannot deploy, repair, rotate secrets, notify outside parties, delete data, trade, attest, or close an incident |
| Buyer decision owner | Approves buyer source, baseline, metrics, handling, acceptance, and buyer communications | Exists only in a signed buyer-specific scope |
| Legal/security reviewer | Reviews notification, privacy, regulatory, insurance, contractual, and disclosure duties | No such approval is implied by this repository |

## Severity model

| Severity | Machine interpretation | Default decision |
|---|---|---|
| `NONE` | All allowlisted bytes and required MIME contracts match | `MONITOR` |
| `SEV-4` | Advisory observation without confirmed release-integrity impact; manual only | `REVIEW` |
| `SEV-3` | Limited noncritical drift or error below the SEV-2 threshold | `HOLD_AFFECTED_SURFACE_PROMOTION` |
| `SEV-2` | Any critical reviewer surface fails/differs, or at least 20% of the manifest is affected | `HOLD_PUBLIC_RELEASE_PROMOTION` |
| `SEV-1` | Confirmed credential, buyer-data, unauthorized-control, financial, trading, safety, or regulated-system impact | `HUMAN_EMERGENCY_RESPONSE` |

The public-site classifier is intentionally capped at `SEV-2`. A public HTTP
audit cannot establish a secret exposure, buyer-data disclosure, unauthorized
control event, financial impact, trading impact, safety event, or regulated
incident. Those conditions require human investigation and classification.

## Detection and evidence

The read-only `Audit exact public-site snapshot` workflow runs on relevant main
changes, daily, and on manual dispatch. It:

1. packages the exact allowlisted files from immutable Git blobs for the audited source commit;
2. binds the commit, Git object IDs, sizes, hashes, archive hash, and target;
3. downloads every canonical live URL without using credentials;
4. checks HTTP status, allowed MIME type, bytes, and SHA-256;
5. emits the raw live-verification receipt even when the audit fails;
6. classifies the result under the machine policy;
7. uploads the package, audit, and incident receipt; and
8. remains red until exact current-commit identity is established.

Hashes establish identity within their declared scope. They do not prove
safety, authorization, scientific validity, customer acceptance, or legal
sufficiency.

## Containment

For any active public-release incident:

1. preserve the immutable package, manifest, live audit, and classification;
2. treat the checked-out Git commit as canonical;
3. treat mismatched live bytes as unverified and hold their promotion;
4. do not repair production from an ad hoc worktree or mutable local folder;
5. separate static-file drift from gateway, secret, DNS, buyer-data, legal, and
   trading lanes; and
6. escalate any suspected `SEV-1` condition without promoting the HTTP audit
   into proof of that condition.

## Recovery

Static-site recovery requires the separately protected exact-snapshot workflow:

1. review the exact commit, full allowlisted manifest, affected routes, and rollback
   scope;
2. provide the literal `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` approval only after
   that review;
3. apply only the allowlisted archive while capturing replaced file identity;
4. rerun every live byte and MIME check declared by the release manifest;
5. retain deployment, rollback, and verification receipts; and
6. close the static release incident only when `release_verified` is `true` for
   the deployed commit.

Gateway repair remains a separate lane. It requires its own literal approval,
private runtime prerequisites, negative-access checks, and retained receipts.
Static deployment does not authorize gateway repair, and gateway repair does
not authorize static deployment.

For the October 9 subject, current-main signed provenance and SBOM verification
are available, but do not authorize deployment. The owner must review the exact
main SHA, select `DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT` in
`deploy-public-site-release.yml`, retain the production-environment gate, and
obtain complete live-byte/MIME verification. If main advances, repin and verify
the new signed subject before any release; this observation is not its approval.

The current apply script restores captured files after an apply failure. Public
HTTP verification is a later, separate workflow step: its failure does not invoke
automatic restoration. Preserve the new timestamped backup and require reviewed
recovery if that gate fails. Existing [PR #208](https://github.com/robertashworth1986-debug/lumen-core-public/pull/208)
proposes same-attempt compensation; it is not current-main behavior and was not
integrated by this observation. The September 23 rollback path is historical
evidence, not a substitute for a fresh pre-release backup.

The art gallery's external Wonder Studio media requires the separate current-main
`repair-public-security-headers.yml` action and `APPLY_PUBLIC_SECURITY_HEADERS`
approval. The observed policy permits same-origin media and lacks the exact
Studio origin. The static release leaves Nginx, DNS/email and runtime data alone.
External Studio bytes are intentionally outside the 246-file release guarantee;
static parity does not prove that gallery media renders successfully.

## Continuity and recovery planning targets

These are non-contractual, unvalidated planning targets—not achieved service
levels or promises:

- public exact-byte audit cadence: within 24 hours through the daily workflow;
- release classification: in the same audit workflow run;
- static public-surface restoration target: within four hours after valid human
  authorization and required production access are available;
- release-byte recovery point: zero loss for the immutable Git-tracked
  allowlisted bytes; and
- buyer-data RTO/RPO: not established and must be negotiated in a signed scope.

No enterprise availability, response, recovery, notification, or support SLA is
currently offered.

## Buyer-data and notification boundary

The first fit review should remain non-confidential. Before receiving buyer
data, the signed scope must define ownership, rights, classification, location,
access, encryption, retention, deletion, backup, restoration, incident contacts,
notification duties, decision authority, and applicable legal or regulatory
requirements.

No automated workflow may notify a buyer, regulator, insurer, partner, or the
public. It also may not delete or disclose evidence or buyer data. Those actions
require human review under the controlling agreement and applicable law.

## Tabletop and live exercise boundary

CI exercises exact, critical-drift, threshold-drift, limited-drift, malformed
receipt, and manual-SEV-1 boundaries. These are deterministic control exercises,
not evidence of a completed live restoration, backup recovery, customer
notification, disaster-recovery exercise, or independent audit.

A future live exercise must record authorization time, start time, affected
commit, rollback capture, restoration time, every route result required by the selected release manifest, deviations,
communications decisions, unresolved gates, and incident-closure authority.

## Machine commands

```bash
python code/ops/VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py
python -m unittest discover -s tests -p "test_public_release_incident_classifier.py" -v
```

The first command verifies the policy, documentation, readiness-register
binding, workflow integration, authority boundaries, and deterministic tabletop
outcomes. The second command runs adversarial classifier tests.

---

**A red live audit is an incident signal, not permission to mutate production.**
