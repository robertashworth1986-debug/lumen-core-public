# LumenCore Institutional Operations Manual

**Revision:** 1.0.1-draft

**Review date:** October 25, 2026

**Status:** Proposed operating guide; production decision remains `HOLD`

**Audience:** Founder/operator, prospective buyers, and technical reviewers

This guide organizes the existing review and buyer-scoping workflow. It does
not establish an adopted operating policy, executed contract, staffed support
service, or completed production-readiness assessment. The
[readiness dossier](INSTITUTIONAL_READINESS_DOSSIER.md) supports a
non-confidential fit review and buyer-specific scoping conversation. Its
production `HOLD` remains in force until the applicable gates have evidence
and approval.

The [SOW template](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md),
[Security Policy](../SECURITY.md),
[incident plan](INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md), and
[Proof Capsule schema](PROOF_CAPSULE_SCHEMA.md) remain the references for their
respective subjects. Dated observations in those records apply to their named
commits, releases, and observation windows; they are not current-state checks.
Buyer obligations arise from a completed, reviewed, signed agreement and its
controlling instrument, not from this guide.

## 1. Operational authority and responsibility

| Role | Responsibility | Authority boundary |
|---|---|---|
| Founder/operator, Robert Ashworth | Scope, evidence integrity, release review, and commercial decisions | Authorizes the specific consequential action after reviewing its evidence and scope |
| External reviewer | Inspect evidence, reproduce an agreed check, and record findings | Review does not authorize release, buyer acceptance, or stronger claims |
| Buyer decision owner | Approve source rights, baseline, metric, handling, and acceptance criteria | Named and authorized through the buyer-specific scope |
| Automated tools | Prepare artifacts and execute authorized bounded checks | A passing check does not grant contracting, communication, publication, deployment, or live-control authority |

Keep separate records for source verification, human approval, execution, and
the observed outcome. A planned action is not an executed action; a successful
test is not a deployment or acceptance receipt. External messages, submissions,
publication, deployment, credential changes, spend, signatures, and live control
remain subject to the applicable action-time approval gate.

## 2. Customer engagement lifecycle

### 2.1 Non-confidential fit review

Use the [buyer-owned validation intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md)
to identify one decision, one candidate, one accepted incumbent baseline, and
one decision owner. Confirm that the buyer can authorize the source and freeze
the primary metric, threshold, and evaluation window before scoring.

Record missing facts, access restrictions, budget authority, and any additional
security or legal controls. Keep restricted or confidential material out of the
public intake and repository. A fit review may proceed to scoping, request more
facts, require separate controls, or conclude that the proposed work is not a fit.
It does not establish a customer, signed scope, or permission to start execution.

### 2.2 Buyer-specific scope and prerequisites

Complete the existing SOW template rather than creating default contractual
terms in this manual. Resolve:

- parties, controlling agreement, decision owner, and delivery owner;
- source rights, authorized purpose and users, transfer channel, retention,
  disposal, and any separately reviewed confidentiality or restricted-data terms;
- candidate, baseline, versions, matched conditions, held-out window, primary
  metric, direction, threshold, exclusions, failure rules, and change control;
- deliverables, acceptance conditions, review period, dates, and dependencies;
- background and output ownership, licenses, and publicity permissions; and
- fees, deposit, payment events, approved expenses, and termination terms.

The signed agreement determines these terms. This guide sets no default
confidentiality term, non-refundable deposit, payment split, or support SLA.
Delivery, buyer acceptance, invoicing, and cleared payment are distinct events.

Record estimated dates as planning assumptions with their prerequisites. No
measured median delivery time or guaranteed duration is established here.
Before a buyer evaluation begins, retain the executed scope, required approvals,
authorized access, and any prerequisite payment receipt. The standard scope is
non-production and non-actuating; a later integration requires separate scope
and approval.

### 2.3 Evaluation execution

Follow the signed evaluation contract and preserve its pre-run receipt:

1. Freeze source identity, versions, code commit, dependency lock, configuration,
   holdout, metric, threshold, exclusions, and failure rules before scoring.
2. Reproduce the accepted baseline and execute the candidate on matched cases
   under the agreed information-availability and resource conditions.
3. Preserve input and output hashes, environment details, logs, missing data,
   timeouts, exceptions, constraint violations, and incomplete runs.
4. Report the metric delta with its defined sign and direction, denominator,
   uncertainty where applicable, and the agreed decision rule. A raw difference
   is not automatically an improvement or a monetary saving.
5. Record favorable, neutral, and adverse findings. Unresolved rights, integrity,
   comparability, or authority gates require a bounded `hold` or `reject` record
   under the agreed rules. Favorable metrics do not authorize promotion.

Changes after the freeze require a change record and review of whether a new
holdout or run is needed. Preserve the earlier result and reason for the change.
Source-conditioned replay remains replay evidence even when its hashes verify.

### 2.4 Evidence packaging and verifier contract

Use [Proof Capsule v3](PROOF_CAPSULE_SCHEMA.md) and the existing
[public example](../examples/proof_capsule/dice_eia_public_capsule.json).
The table below maps the required JSON objects to their exact field names; the
schema and verifier define types, permitted values, and validation rules.

| Object | Required fields |
|---|---|
| Top level | `schema_version`, `capsule_id`, `title`, `module`, `evidence_type`, `source`, `baseline`, `locked_metric`, `run`, `manifest`, `external_validation`, `result`, `claim_boundary`, `pilot_decision` |
| `source` | `name`, `type`, `rights_status`, `row_count_or_window` |
| `baseline` | `name`, `baseline_type`, `selection_time` |
| `locked_metric` | `name`, `definition`, `locked_before_run` |
| `run` | `run_id`, `run_type`, `timestamp_utc`, `code_commit`, `dependency_lock`, `seed_or_window` |
| `manifest` | `manifest_format`, `input_hashes`, `output_hashes`, `manifest_hash`, `public_safe` |
| Each input/output hash record | `path`, `sha256` |
| `external_validation` | `status`, `validator_name`, `validator_organization`, `scope`, `completed_at_utc`, `report_path`, `report_sha256` |
| `result` | `summary`, `primary_delta`, `secondary_metrics`, `negative_results`, `failure_notes` |
| `claim_boundary` | `proves`, `does_not_prove`, `safe_public_sentence` |
| `pilot_decision` | `status`, `next_gate`, `owner` |

Use `schema_version: "3.0"` and
`manifest_format: "proof-capsule-manifest-v3"`. Do not invent extra JSON keys:
for example, `baseline.version` and `locked_metric.unit`, `direction`, or
`threshold` are not v3 fields. Retain those agreed details in the evaluation
contract and referenced artifacts; describe the metric fully in the defined
fields. Bind the relevant artifacts through the manifest using canonical
repository-relative POSIX paths and SHA-256 digests.

`result.negative_results` and `result.failure_notes` must each be nonempty lists
of distinct, nonblank strings. Report actual adverse findings and exceptions.
When a bounded run observed none, say that truthfully, identify its scope and
remaining limitations, and avoid implying that failure is impossible. Do not
invent a negative outcome to fill a field or suppress an observed failure.

Use `external_validation.status: "not_established"` with null detail fields
unless a qualifying report exists. A declared external report must be
manifest-bound; its identity, independence, scope, and conclusion still require
human authentication. The `public_safe` flag is a declaration checked within
bounded verifier rules, not permission to publish private buyer data.

From the repository root, the runnable public-example command is:

```sh
python code/proof_capsule_verifier.py examples/proof_capsule/dice_eia_public_capsule.json --root .
```

The CLI takes the capsule path as a positional argument; it has no `--verify`
option. For another approved capsule, substitute its path and the correct
artifact root. Keep private artifacts in their approved environment, and do not
label them public-safe merely to satisfy a verifier.

Retain the command, source commit, runtime, exit code, and receipt. A successful
receipt reports `valid: true` within `capsule-schema-and-custody`; it does not
establish scientific correctness, validator independence, buyer acceptance, or
production readiness. `release_authorization_evaluated: false` and
`human_unlock_required: true` preserve the separate publication decision.

### 2.5 Delivery and acceptance

Deliver the agreed evaluation contract, authorized source receipt, manifests,
baseline and candidate outputs or failure records, Proof Capsule, verification
instructions, and decision briefing through the approved channel. Obtain and
retain buyer feedback and acceptance according to the signed agreement.

Record the decision as `promote`, `rerun`, `external_review`, `hold`, or `reject`
with its owner and next gate. `promote` supports only the agreed next gate; it
does not itself authorize deployment. A negative or incomplete result can be a
valid deliverable when it meets the agreed acceptance conditions.

Public release signatures and attestations apply only to the artifacts and
workflow that actually produced them. They are not a required public release of
private buyer data or proof of buyer acceptance. Invoice and payment records
remain separate from technical delivery evidence.

## 3. Incident response and operational security

### 3.1 Detection, classification, and response

Use the existing [incident plan](INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md), its
[machine policy](../config/incident_response_and_continuity_v1.json), and
[Security Policy](../SECURITY.md). Preserve the exact observation, affected
commit or release, timestamps, reproduction, and uncertainty. The public HTTP
classifier cannot establish a credential breach or buyer-data incident.

Hold the affected promotion path while an unresolved material finding is
reviewed. Containment, repair, credential rotation, external notification,
restoration, and closure each need the applicable human authority. Record the
action actually taken and its verification; do not record an intended rollback
as a successful recovery.

Security response times in `SECURITY.md` are best-effort operational targets,
not guarantees. Buyer-specific notification, response, recovery, and service
levels require signed terms and sufficient operating capacity. This guide adds
no competing four-hour, twenty-four-hour, or seventy-two-hour SLA.

### 3.2 Credentials, dependencies, and implementation evidence

Keep production credentials, private keys, buyer records, and sensitive incident
details out of Git, public logs, screenshots, and review artifacts. Use the
approved private environment and least-privilege access for the named purpose.
Do not copy a credential into source or a receipt to prove a control exists.

Inspect the applicable dependency locks, workflow permissions, immutable action
pins, and exact check results. Record scanner coverage and limitations. This
manual does not establish that every dependency is pinned, every secret is
detected, or a periodic security audit has occurred. A proposed control needs
implementation evidence before it is described as operating.

### 3.3 Buyer data custody and disposal

Before intake, agree on classification, rights, authorized users, transfer and
storage locations, access logging, retention, backup handling, and disposal.
Verify the specific environment's controls against that scope; this guide does
not assert that encryption, access auditing, or regulated-data handling is
already implemented everywhere.

Hash authorized source artifacts before transformation and retain source
identity, retrieval time, schema, row count or window, and exclusions. A hash
detects differences against a retained reference; it does not establish source
truth or access rights.

Use an approved disposal method suited to the actual storage and agreed backup
rules. Retain what was removed, when, by whom, the method, verification, and any
remaining copies or limitations. No default thirty-day deletion deadline,
three-pass overwrite procedure, or guaranteed destruction certificate is
established by this guide.

## 4. Release and deployment management

### 4.1 Review and release preparation

Follow the [exact-snapshot protocol](PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md)
and [supply-chain assurance](PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md).
Before any approved release:

1. Identify the exact source commit, changed files, open-PR overlaps, applicable
   checks, and the actual tested merge commit where CI uses one.
2. Retain pass, failure, skip, and unresolved-check results for that source.
   Historical totals and a green unrelated job cannot replace current checks.
3. Review the declared archive, allowlist, manifest, hashes, and any applicable
   signatures, provenance, and SBOM. Their scope must match the named artifact;
   a static-site SBOM is not a complete VPS or runtime inventory.
4. Prepare release notes, target, rollback scope, and verification steps for
   the specific approval. A tag or version number does not establish readiness.

Do not assume a verifier binary, release URL, signature, or reproducible build
exists unless the reviewed workflow and its receipt establish it. Use the
actual release format and immutable identities rather than inventing a parallel
release path in this manual.

### 4.2 Deployment and rollback

Deploy only through the approved, scoped workflow after its prerequisites and
action-time approval. Retain the pre-mutation state, source and artifact
bindings, execution result, and post-deployment evidence. Verify the declared
HTTP, MIME, and exact-byte contracts; an HTTP success or `/health` response alone
does not establish current release identity or production readiness.

Static deployment, gateway repair, and runtime recovery remain distinct scopes.
Use their existing guarded procedures. A rollback must identify the authorized
prior artifact and scope, preserve intervening-state and failure evidence, and
verify the actual restoration outcome. Do not overwrite immutable release tags
or report partial, refused, or unverified recovery as success.

Prepare corrections on a bounded branch and review their exact checks before
promotion. This guide is not a production repair command or permission to
execute one.

## 5. Monitoring and observability

Keep scheduled monitoring read-only. Preserve generated state in workflow
summaries or bounded artifacts according to the existing workflow policy.
Inspect actual trigger definitions and run receipts before claiming a check
runs on every commit or at a particular cadence.

For each review, record the source commit, observation time, workflow and job
links, runtime, passed/failed/skipped counts, and retained artifacts. Keep
overlapping suite counts separate. A historical test total is not a permanent
minimum or evidence that all current checks pass.

Monitor release drift, outstanding findings, evidence freshness, and blocked
buyer prerequisites. `/health` is a bounded liveness observation. It does not
prove source identity, service completeness, safe recovery, or scientific
performance. Report unresolved checks and unobserved periods explicitly.

## 6. Customer support and escalation

Public GitHub issues are suitable for non-sensitive reproducible defects and
feature requests. Route security findings through the private advisory or
contact channel in [SECURITY.md](../SECURITY.md). Keep buyer material and private
incident evidence out of public issues.

Robert Ashworth is the founder/operator contact. An external specialist is a
possible scoped engagement, not an established on-call support tier. Record the
actual responsible person, availability, escalation channel, and approved terms
before offering buyer-specific support. No response-time guarantee is added by
this document.

## 7. Review and assurance

A periodic review may check repository controls, dependencies, access,
documentation, release evidence, and buyer feedback. Assign an owner and dates,
then retain the completed review and unresolved findings. A proposed quarterly
or annual schedule is not evidence that an audit has occurred.

External reviewers should begin with
[REVIEWER_START_HERE.md](REVIEWER_START_HERE.md) and [QUICKSTART.md](../QUICKSTART.md),
record their exact source and environment, run the public-example verifier
command in section 2.4, and distinguish custody checks from substantive
evaluation. Record discrepancies and the next gate. First-party tests and AI
code review are not independent scientific validation or certification.

## 8. Communication and claim boundaries

Follow the [claim boundary register](CLAIM_BOUNDARY_REGISTER.md). State what
the inspected evidence supports, its source and window, limitations, and the
next gate. For example:

> LumenCore packages bounded source, baseline, metric, result, and limitation
> records for reviewer inspection. The public example verifies schema and
> artifact custody; it does not establish buyer acceptance or field savings.

Report test results with their exact commit and job receipt. Do not convert a
passing verifier, dashboard, signed artifact, technical review, or proposed
scope into production readiness, agency endorsement, certification, revenue,
guaranteed performance, or realized savings. Customer identity, logos, results,
and other non-public material need the applicable publication permission.

## 9. Revision and adoption

The October 25, 2026 initial manual introduced a proposed workflow but labeled
it production-ready and binding. This draft corrects those labels, the verifier
command and field mapping, and unsupported contractual or operating claims.
It preserves the existing production `HOLD` and separate action gates.

Before adopting any additional policy, record its owner, exact approved text,
effective date, dependencies, operating evidence, and next review date. Update
the relevant canonical policy instead of maintaining competing requirements.
Document later changes and preserve dated evidence and failed results.

## 10. Contact and authorization

Commercial and technical scoping is founder-led. Use the repository's current
review and intake routes; use [SECURITY.md](../SECURITY.md) for private security
reporting. Record each consequential approval with its specific scope and time.

This document is a proposed operating guide. It does not execute an agreement,
authorize an external action, or change the production decision.
