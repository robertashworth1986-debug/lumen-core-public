# ProofLock Opportunity Operations

## Buyer-Neutral 30-Day Paid Pilot Protocol

### Objective

Measure whether an evidence-bound opportunity workflow can reduce administrative cycle time and package defects without making unsupported eligibility, award, or savings claims.

### Boundary

Opportunity, workflow, synthetic, sample, and buyer-authorized non-PHI organization data only. No credentials, final certifications, signatures, or autonomous submissions.

### Buyer And Commercial State

- Buyer selected: `false`
- Protocol status: `DRAFT_SCOPE_BUYER_BASELINE_AND_FOUNDER_PRICING_REQUIRED`
- Pricing status: `UNQUOTED_SCOPE_FIRST`
- No fee, subscription price, recipient, or external communication is approved by this document.

### Minimum Sample

- Reviewed opportunities: `30`
- Pursued packages: `5`
- Alternate rule: A lower sample is valid only when the buyer documents the expected source volume before the pilot and both parties approve the alternate denominator.

### Week 1: Lock the Baseline

- Measure current time from opportunity discovery to pursue/no-pursue decision.
- Measure current time from pursue decision to reviewer-ready draft.
- Count eligibility reversals, missing attachments, and missed internal review dates.
- Freeze source permissions, eligibility rules, metric denominators, thresholds, roles, and human gates.

### Weeks 2-4: Run the Pilot

- Refresh permitted opportunity sources and rank candidates with evidence links.
- Generate source-grounded draft structures and an attachment/blocker ledger.
- Route unresolved facts to named owners; abstain instead of guessing.
- Emit a replayable receipt for every shortlist, draft, and preflight decision.

### Acceptance Metrics

- **qualified opportunity precision**: numerator = buyer-confirmed qualified matches; denominator = all candidate matches reviewed by the buyer
- **time to pursue decision**: numerator = sum of elapsed hours from discovery to documented decision; denominator = opportunities receiving a documented pursue or no-pursue decision
- **time to reviewer-ready draft**: numerator = sum of elapsed hours from pursue decision to buyer-defined internal review state; denominator = pursued packages reaching internal review
- **preflight defect rate**: numerator = missing, contradictory, stale, or ownerless required items found at review; denominator = required package items inspected at review
- **deadline reliability**: numerator = pursued packages reaching internal review by the frozen buyer cutoff; denominator = pursued packages with an open verified deadline
- **provenance completeness**: numerator = material claims carrying a traceable reviewed source; denominator = material claims inspected

Threshold rule:

- No metric is called improved or accepted until the buyer approves its baseline, threshold, denominator, exclusions, and cutoff before pilot measurement.

### Permitted Sources

- buyer-approved official public opportunity pages and feeds
- buyer-provided eligibility and workflow rules approved for pilot use
- synthetic or de-identified sample organization records
- buyer-approved internal timestamps and defect labels

### Prohibited Inputs

- protected health information
- account credentials or one-time codes
- controlled unclassified or export-controlled material
- unreleased proposal content unless a written private-data agreement permits it
- payment data

### Deliverables

- signed-off baseline and acceptance memo
- source and eligibility-rule register
- review-only candidate queue with abstention reasons
- attachment, owner, and blocker ledger
- weekly hash-linked workflow receipt
- final metric workbook and claim-bounded decision memo

### Exclusions

- legal or accounting advice
- guaranteed eligibility, award, savings, or revenue
- final certification, signature, upload, send, or submission
- model-superiority or field-performance claims
- production use of protected or controlled data

### RACI

- **buyer_workflow_owner**: accountable for source permissions, eligibility rules, thresholds, and acceptance
- **buyer_authorized_official**: accountable for every certification, signature, send, upload, and final submission
- **lumencore_operator**: responsible for configured monitoring, draft assembly, blocker ledgers, and receipts
- **lumencore_founder**: accountable for scope, pricing, public claims, and any external communication
- **legal_or_security_reviewer**: consulted when data, confidentiality, IP, export, or regulated-domain terms require review

### Retention And Security

- Default post-pilot retention: `30` days
- Deletion: Delete or return buyer data after the approved retention period unless a signed agreement specifies another period.
- Access: Least-privilege named users only; no credentials or protected data in public artifacts.
- Incident response: Stop processing, preserve bounded logs, notify the named buyer owner, and follow the signed incident procedure.

### Support Boundary

- Included: One kickoff, one weekly review, asynchronous blocker triage during agreed business hours, and one final readout.
- Excluded: 24-hour operations, legal representation, portal administration, managed submission, or production SLA unless separately contracted.

### Human Authority Gates

- buyer confirms organizational eligibility and source permissions
- buyer approves claims, representations, thresholds, and package content
- authorized official certifies, signs, uploads, sends, and submits
- LumenCore cannot bypass portal attestations, account controls, or signatures
- founder approves exact scope, price, recipient, and external communication

### Commercial Path

Paid pilot after exact buyer scope, baseline, acceptance thresholds, data terms, price, and recipient are approved.

No value, savings, performance, or price figure is quoted until a selected buyer approves the baseline inputs and prospective thresholds and the pilot produces a traceable measurement.

### Golden Replay

- Verified: `true`
- Synthetic events: `3`
- Replay SHA-256: `2664168a3468bbd59f4e24f8ee787c5b6d686ee2ab89af2067a83ba4079630ff`
- Boundary: This replay proves deterministic decision-state and receipt-chain behavior for synthetic fixtures only. It does not prove eligibility, customer outcomes, awards, savings, or production readiness.
