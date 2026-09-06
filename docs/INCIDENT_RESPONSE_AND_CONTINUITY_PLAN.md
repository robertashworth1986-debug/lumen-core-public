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

## Authority and roles

| Role | Responsibility | Authority boundary |
|---|---|---|
| Founder/operator | Accountable incident owner and final release authority | Must personally authorize production mutation and incident closure |
| Automated evidence custodian | Package Git bytes, collect public HTTP evidence, classify bounded drift, retain receipts, and execute the one bounded same-attempt compensation described below | Cannot initiate deployment, perform arbitrary or later rollback/repair, rotate secrets, notify outside parties, delete data, trade, attest, or close an incident |
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

1. packages the 43 allowlisted files from immutable Git blobs;
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
5. if that external gate rejects the candidate or cannot emit a valid receipt
   while the same approved workflow attempt is still running, validate the
   immutable run/attempt/capability-bound authority capsule and all current
   allowlisted targets before restoring the exact captured local state;
6. retain deployment, rollback-authority, live-gate, compensation, and aggregate
   transaction receipts; keep every rejected candidate attempt red even when
   prior-state restoration is verified; and
7. close the static release incident only when `release_verified` is `true` for
   the deployed commit.

The one-attempt capability is masked and ephemeral; only its digest is retained.
It is not a dispatch input or later recovery credential. The pinned runner
runtime, explicit remote Python floor, one fixed root-owned mutation lock, global
preflight, and immediate per-target revalidation protect cooperating writers.
A target that differs from both the candidate and captured prior state stops
before that target is touched, leaves no verified receipt, and is not
overwritten. Earlier targets may already equal prior state; the same authorized
attempt can resume idempotently only after separate reconciliation of the third
state. Uncooperative root mutation is outside the control guarantee.

A malformed or contradictory live-gate file is retained only as explicitly
untrusted evidence. It is not passed to the VPS or treated as rejected-gate
authority; compensation uses the error-or-missing route and the aggregate
receipt records no trusted live-gate hash. Verified compensation establishes only
the prior allowlisted local bytes, numeric ownership, and modes. It does not
establish public recovery through Nginx, a cache or CDN, DNS, or TLS, and it is
not candidate success or incident closure. Cancellation, runner loss, network
loss, or host loss can prevent compensation; later recovery requires a separate
human-reviewed decision.

If apply transport or local receipt parsing is ambiguous, the workflow does not
trust the local command outcome. Live verification and compensation each
rediscover the exact remote authority independently and require its self-hash,
run/attempt/commit/capability bindings, and bound state-file hashes before
continuing. Failure to discover exactly one authority remains red and emits no
success claim.

Gateway repair remains a separate lane. It requires its own literal approval,
private runtime prerequisites, negative-access checks, and retained receipts.
Static deployment does not authorize gateway repair, and gateway repair does
not authorize static deployment.

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
receipt, manual-SEV-1, same-attempt replay/tamper rejection, and transaction-state
boundaries. These are deterministic control exercises,
not evidence of a completed live restoration, backup recovery, customer
notification, disaster-recovery exercise, or independent audit.

A future live exercise must record authorization time, start time, affected
commit, rollback capture, restoration time, all 43 route results, deviations,
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
