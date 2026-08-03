# Product Lane Evidence Audit

Date: 2026-07-29

Scope: bounded, read-only audit of the top three lanes in
`config/product_lane_priority_v1.json`. This audit evaluates repository evidence,
focused tests, current claim gates, and readiness for a paid design-partner pilot.
It does not establish external validation, forecast superiority, realized savings,
award probability, production readiness, or independent scientific validation.

No outreach, portal action, submission, deployment, or existing-file modification
was performed.

## Executive Finding

All 12 evidence paths declared for the three lanes exist. Path existence is not
the same as evidence sufficiency:

| Priority | Lane | Current bounded readiness | Main blocker |
|---|---|---|---|
| 1 | ProofLock Opportunity Operations | Suitable for a paid workflow-baseline/design-partner pilot now; full live monitoring remains gated | Current opportunity board is freshness-blocked, and the SAM credential alias consistency gate fails |
| 2 | ProofLock Evidence Router API | Suitable only for a paid technical co-design/research sprint | The current router uses full-series features, lacks deterministic abstention, and is not an API service |
| 3 | Energy Forecast Validation Service | Suitable for a paid protocol and independent-reproduction setup engagement | Prospective sample gates and independent reproduction remain incomplete; no operator economic case is present |

The strongest near-term lane remains ProofLock Opportunity Operations. The
honest first offer is workflow measurement and evidence-controlled preparation,
not autonomous opportunity discovery, eligibility determination, submission, or
award optimization. Pilot scoping can begin now; continuous live-source
monitoring should remain gated until freshness and credential controls pass.

## Audit Method

The audit:

1. Read the lane definitions, offers, evidence paths, blocked claims, and first
   external-validation requirements in
   `config/product_lane_priority_v1.json`.
2. Verified every declared evidence path on disk.
3. Inspected the most relevant current generated artifacts and claim-control
   documents.
4. Ran focused, read-only tests covering lane configuration, grant readiness,
   near-deadline command routing, proof-to-revenue controls, EIA reproduction,
   and outage economic-value packet integrity.
5. Treated generated counts and historical evaluations as dated observations,
   not current performance claims.

Focused test command:

```powershell
python -m pytest -q tests/test_product_lane_priority_engine.py tests/test_grant_submission_readiness_audit.py tests/test_near_deadline_submission_command_board.py tests/test_proof_to_revenue_engine.py tests/test_eia_grid_hourly_independent_reproduction_packet.py tests/test_outage_second_economic_value_packet.py
```

Current rerun result after claim-chain repairs: **55 passed in 4.91 seconds**.
The passing command-board test now preserves the actual fail-closed state:
SAM credential aliases are inconsistent and live verification is absent. No
credential values or secret material were inspected or reproduced in this
audit.

## 1. ProofLock Opportunity Operations

### Verified Assets

Every evidence path declared for this lane exists:

- `code/ops/run_healthcare_grants_engine.py`
- `code/ops/build_healthcare_website_feed.py`
- `code/ops/BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py`
- `code/ops/BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py`
- `dashboard/embed/mindwise_premium_flow_demo.html`

Additional relevant assets:

- `out/ops/healthcare_grants_engine/healthcare_grants_engine_latest.json`
  records a dated July 18 run that scanned 496 records and selected 30. These
  are historical run counts, not a current opportunity inventory or a measure
  of qualification accuracy.
- `out/ops/grant_submission_readiness_audit_latest.json` records
  `LOCAL_READY_PORTAL_BLOCKED` on July 17, with five packages, no reported
  local blockers, and 25 portal/user blockers. Its claim boundary correctly
  leaves portal authority, certifications, partner commitments, costs, field
  validation, and submission actions under human control.
- `out/ops/near_deadline_submission_command_board_latest.json` records a July
  19 fail-closed freshness state. It identifies 13 freshness-blocked lanes and
  six freshness blockers. A zero-row SAM discovery result is treated as
  inconclusive rather than proof that no opportunities exist.
- `docs/MINDWISE_PAID_DESIGN_PARTNER_PILOT_2026-07-18.md` defines useful pilot
  measurements: qualified-opportunity precision, time to pursue decision, time
  to reviewer-ready draft, preflight defect rate, deadline reliability, and
  provenance completeness.

The code and artifacts demonstrate a credible evidence-controlled workflow:
source ingestion, qualification support, readiness checks, deadline routing,
human-gate labeling, and generated receipts. They do not demonstrate current
source completeness, eligibility, award likelihood, or external buyer value.

### Missing or Broken Paths and Controls

No declared file path is missing, but the operational evidence chain is not
currently clean:

- The latest opportunity and command-board outputs are dated and cannot support
  a current-opportunity claim without a fresh source reconciliation.
- The command board is explicitly freshness-blocked.
- `grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json`
  reports `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`, false alias consistency,
  no live verification, five configured entries, and two distinct secret
  values. This is a configuration/readiness failure, not evidence about entity
  registration status.
- The declared website demo is a presentation surface. It is not direct
  evidence that source connectors, deadlines, portal permissions, or
  submission actions are current.
- Named-program artifacts are mixed with the reusable workflow proposition.
  A buyer pilot needs a buyer-scoped source and acceptance protocol rather than
  reliance on dated internal program snapshots.

### Test Coverage

Focused coverage includes:

- `tests/test_product_lane_priority_engine.py`: lane ordering, required fields,
  claim boundaries, and validation-plan structure.
- `tests/test_grant_submission_readiness_audit.py`: package discovery,
  readiness classification, portal blockers, and fail-closed behavior.
- `tests/test_near_deadline_submission_command_board.py`: command-board
  routing, source freshness, human gates, and credential-control integration.

All focused lane-relevant tests passed. The generated operational control still
reports the present SAM credential alias inconsistency as a live-source blocker.
These tests support bounded software and policy behavior; they do not validate
opportunity recall, qualification precision, buyer time savings, submissions,
or awards.

### Current Claim Gates

Allowed, with dated and buyer-scoped wording:

- Source-bound opportunity triage and owner routing.
- Evidence-controlled drafting and preflight assistance.
- Deadline, provenance, and action-receipt generation.
- Fail-closed escalation when sources, facts, or permissions are missing.

Blocked:

- Guaranteed awards or elevated award probability.
- Automatic eligibility determinations without source and buyer review.
- Autonomous signing, certification, pricing approval, sending, or submission.
- Current-opportunity completeness while source freshness is unresolved.
- Realized time or cost savings before a buyer baseline and completed pilot.

### Strongest Honest Offer

A paid 30-day design-partner pilot that measures the buyer's current opportunity
review workflow, then provides source-bound triage, ownership routing,
reviewer-ready draft assembly, preflight checklists, provenance records, and
action receipts. The buyer retains control of eligibility facts, representations,
certifications, pricing, partner commitments, sends, and final submissions.

The pilot can begin with permitted public sources and synthetic or minimally
sensitive organization data. It should not require protected health information
or uncontrolled portal access.

### First Paid-Pilot Acceptance Criteria

The parties should freeze thresholds before the pilot. A defensible first
acceptance protocol would require:

1. A documented baseline for the buyer's current pursue/no-pursue cycle time,
   draft-preparation time, preflight defects, deadline misses, and provenance
   completeness.
2. A source URL or snapshot, retrieval time, deadline, timezone, and evidence
   reference for every material recommendation.
3. Deterministic abstention when a source is stale, unavailable, zero-row, or
   insufficient to support a recommendation.
4. Human control over 100% of final sends, certifications, signatures, pricing
   approvals, partner commitments, and submissions.
5. Zero duplicate packet or send actions.
6. Buyer adjudication of qualified-opportunity precision and false-positive
   handling against thresholds agreed before the pilot.
7. A signed pilot receipt reporting pass, fail, or inconclusive for every
   metric. Null or negative results remain reportable outcomes.

### Prioritized Minimal Fixes

1. Scope the workflow-baseline pilot without promising current source
   completeness.
2. Repair the SAM credential alias inconsistency, obtain non-secret live
   connector verification, and refresh opportunity sources before enabling
   continuous live monitoring.
3. Add a freshness service-level rule and a focused health test that proves
   stale or zero-row sources abstain.
4. Bind the existing pilot metrics to a versioned buyer-specific protocol and
   acceptance receipt.
5. Separate dated named-program demonstrations from the reusable product
   workflow and its buyer-scoped evidence.

## 2. ProofLock Evidence Router API

### Verified Assets

Every declared evidence path exists:

- `code/meta_router.py`
- `code/ops/BUILD_PROOF_TO_REVENUE_ENGINE.py`
- `dashboard/evidence/runs/20260505T121657Z/router/eval.json`
- `dashboard/evidence/runs/20260505T121657Z/stacker/eval.json`

The repository contains a research router, historical evaluation artifacts, and
commercial claim controls. This is useful prototype evidence, but it is not yet
evidence of a deployable Evidence Router API.

`out/ops/proof_to_revenue_engine_latest.json` is appropriately conservative. Its
July 29 v2 output reports `proof_stack_not_ready_for_outreach`, records the
current 0/6 proven Kuramoto sector-gain result, suppresses model-performance and
dollar claims, and identifies ProofLock Opportunity Operations as the immediate
commercial lane. This artifact is a claim-control and commercialization planning
record, not API behavior evidence.

### Missing or Broken Paths and Controls

- `code/meta_router.py` is a research script, not an HTTP or RPC service. It has
  no stable request/response schema, authentication boundary, rate limits,
  tenant policy interface, or operational service tests.
- Feature extraction is performed from the full raw series while labels are
  derived from test-window performance. Cross-dataset folds do not remove this
  within-series timing leakage. The repository's own product-lane analysis
  identifies the need for a train-only rerun.
- The current router has no explicit deterministic abstention contract.
- No dedicated test directly exercises `code/meta_router.py`.
- The May 5 router and stacker evaluations are historical, self-authored
  cross-validation artifacts. They are not prospective or independent
  validation.
- Ratio summaries can be unstable when an oracle denominator is near zero.
  Those values should not be used as buyer-facing superiority claims.
- No receipt schema currently binds input identity, source time, model version,
  policy version, selected route, abstention reason, and output hash into one
  validated API contract.

### Test Coverage

Relevant passing coverage includes:

- Eight product-lane configuration and claim-control tests in
  `tests/test_product_lane_priority_engine.py`.
- Three proof-to-revenue claim-control tests in
  `tests/test_proof_to_revenue_engine.py`.

There are no direct router unit, property, leakage-timing, abstention,
determinism, receipt-schema, or API contract tests. The passing tests validate
configuration and fail-closed commercialization rules, not router correctness
or performance.

### Current Claim Gates

Allowed:

- A research prototype for comparing bounded route families.
- A design sprint to define a buyer-specific route decision and receipt
  contract.
- Historical evaluation described with its exact date, method, and
  limitations.

Blocked:

- Leakage-free performance until features are rebuilt from train-only or
  decision-time-available information.
- Prospective or independent validation.
- Universal superiority, oracle-equivalent performance, or patentability.
- Production API readiness, deterministic abstention, or tamper-evident
  receipts until directly implemented and tested.

### Strongest Honest Offer

A paid technical co-design sprint that freezes a buyer's route family, available
decision-time inputs, fixed comparator, metric, abstention rules, and receipt
schema. The sprint then implements train-only/source-available features and
evaluates deterministic selection or abstention prospectively.

This is an instrumentation and evaluation offer, not a promise that the router
will outperform the buyer's incumbent route.

### First Paid-Pilot Acceptance Criteria

1. Every input, source snapshot, model, route family, and policy has an immutable
   identifier and content hash.
2. Identical inputs and policy versions produce a byte-stable selection or
   abstention receipt.
3. Missing, stale, out-of-scope, or insufficient inputs produce a documented
   abstention rather than a forced route.
4. An automated timing test proves that every feature was available at the
   decision cutoff.
5. The buyer approves the fixed comparator, metric, split, sample floor, and
   oracle boundary before evaluation.
6. A prospective holdout meets the buyer's predeclared threshold, or the result
   is recorded as fail or inconclusive without claim promotion.
7. The router performs no unauthorized downstream action.

### Prioritized Minimal Fixes

1. Replace full-series feature extraction with train-only or
   decision-time-available feature construction.
2. Implement a deterministic, reason-coded abstention policy.
3. Define and validate a versioned request, response, and decision-receipt JSON
   schema.
4. Add direct tests for feature timing, determinism, abstention, schema
   validation, receipt tampering, and unstable denominator handling.
5. Run a preregistered prospective comparison against a fixed route family.
6. Add a bounded local service interface only after the research core and claim
   gates pass.

## 3. Energy Forecast Validation Service

### Verified Assets

Every declared evidence path exists:

- `code/ops/BUILD_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py`
- `code/ops/BUILD_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET.py`
- `dashboard/evidence/runs/20260505T121657Z/summary.json`

The declared May 5 summary is a broad benchmark summary, not current evidence
for the EIA hourly prospective lane. Stronger and more relevant current assets
exist:

- `out/eia_grid_prospective_hourly_router/prospective_status_latest.json`
  records `PROSPECTIVE_COLLECTION_ACTIVE` on July 28. It reports 1,119
  predictions, 1,096 settlements, and 40 common settled hours spanning July 23
  through July 29. Preliminary, confirmatory, and durability gates remain
  false, and promotion evaluation is incomplete.
- `out/reviewer_handoffs/EIA_GRID_HOURLY_INDEPENDENT_REPRODUCTION_HANDOFF_LATEST.json`
  records `UNSIGNED_REVIEWER_HANDOFF_READY` on July 21. It explicitly reports
  that independent reproduction and performance promotion are false.
- `docs/EIA_GRID_HOURLY_INDEPENDENT_REPRODUCTION_HANDOFF_2026-07-16.md`
  documents the reviewer process and claim limits, but its frozen snapshot is
  older than the current prospective runtime.
- `config/outage_second_economic_conversion_protocol_v1.json` provides a
  frozen private-entity incremental-cost conversion protocol. It does not
  establish realized savings, social benefit, price, or field validation.

The current prospective counts are collection-state facts only. Because all
sample gates remain false, they do not support a performance or superiority
claim.

### Missing or Broken Paths and Controls

- The lane definition points to the May 5 benchmark summary rather than the
  current prospective status and independent-reproduction handoff.
- The latest reviewer handoff is stale relative to the current runtime: the
  handoff predates the current 40 common settled hours.
- Independent reproduction has not been completed or signed.
- Preliminary, confirmatory, and durability sample gates are not met.
- The default private operator evidence directory
  `evidence/private/outage_second_economic_value_packet_20260716` is absent.
  Builder and protocol code exist, but no external operator case is present.
- No buyer-approved incumbent baseline, holdout, acceptance threshold, economic
  factor, or field receipt is present for a paid outcome claim.
- Economic conversion must remain closed until a technical gate passes and an
  operator supplies and accepts the required private inputs.

### Test Coverage

Focused passing coverage includes:

- Six tests in
  `tests/test_eia_grid_hourly_independent_reproduction_packet.py`.
- Twenty-six tests in
  `tests/test_outage_second_economic_value_packet.py`.

These 32 tests cover packet construction, schema and integrity controls,
fail-closed behavior, signature requirements, private/public separation, and
economic-conversion gating. They do not prove forecast accuracy, superiority,
independent reproduction, field performance, or realized economic value.

### Current Claim Gates

Allowed:

- Prospective collection status and exact dated counts.
- Reproducible packet construction and integrity verification.
- A reviewer-controlled handoff process.
- A buyer-authorized replay and evaluation protocol.

Blocked:

- Accuracy or superiority promotion while sample gates are false.
- Independent validation until an independent evaluator reproduces the result
  and signs the receipt.
- Realized outage savings or field value without operator evidence.
- Universal harmonic, routing, or forecasting superiority.
- Production or procurement claims based only on local tests and generated
  hash chains.

### Strongest Honest Offer

A paid buyer-authorized forecast evidence and independent-reproduction setup
engagement. The buyer freezes data rights, incumbent forecast, time cutoff,
metric, holdout, missing-data policy, sample floor, and acceptance threshold.
The service then produces traceable predictions, settlements, integrity chains,
and an evaluator handoff.

The offer is to make a forecast comparison inspectable and decision-ready. It
is not a promise to improve the incumbent forecast or create savings.

### First Paid-Pilot Acceptance Criteria

1. The buyer approves data rights, the incumbent baseline, metric, holdout,
   decision cutoff, missing-data policy, and sample floor before scoring.
2. Every included authority or segment reaches its preregistered prospective
   coverage and sample requirement.
3. Prediction, settlement, source, protocol, and terminal chain hashes verify.
4. An independent evaluator reproduces the arithmetic from the frozen packet
   and signs the acceptance receipt.
5. The candidate meets the predeclared metric and effect threshold against the
   incumbent, or the result is recorded as reject, fail, or rerun.
6. Economic conversion remains closed until the operator supplies and approves
   the inputs and the technical acceptance gate passes.
7. The setup engagement creates no field-performance or realized-savings claim
   by itself.

### Prioritized Minimal Fixes

1. Update the lane's canonical evidence mapping to the current prospective
   status and reviewer handoff rather than the May benchmark summary.
2. Refresh the unsigned reviewer handoff from the current runtime without
   promoting performance.
3. Complete the preregistered authority and sample gates, then obtain
   independent reproduction.
4. Secure one buyer-authorized operator case and generate the private outage
   packet from real, approved inputs.
5. Add a buyer-specific, versioned pilot protocol and two-party acceptance
   receipt.
6. Consider subscription or API packaging only after the evaluation contract,
   independent receipt, and operational data boundary are stable.

## Cross-Lane Minimal Integration Order

The smallest defensible sequence is:

1. Repair freshness and credential consistency for Opportunity Operations, then
   run one buyer-scoped workflow-measurement pilot.
2. Rebuild the Evidence Router around decision-time features and deterministic
   abstention before exposing an API surface.
3. Finish the Energy lane's prospective and independent-review gates before
   attaching any performance or economic proposition.
4. Reuse one common receipt vocabulary across lanes: source identity, retrieval
   time, policy version, input hash, action or abstention, human authority,
   output hash, and acceptance status.
5. Keep product revenue claims separate from scientific validation claims.
   Paid design work can be honest and useful even when a performance hypothesis
   fails.

## Audit Conclusion

The repository has meaningful software, policy, packet-integrity, and
fail-closed evidence. The current strongest paid entry point is a bounded
Opportunity Operations workflow-design pilot. Its workflow baseline and design
scope can begin now; continuous live monitoring remains gated by source
freshness and SAM credential consistency. The Evidence Router and Energy
Forecast lanes can support paid co-design or evaluation-setup engagements, but
neither presently supports a performance-based product claim.

The audit found no missing declared evidence files. It did find a fail-closed
SAM credential-control state, stale operational snapshots, a router
timing/leakage defect, incomplete
prospective sample gates, an unsigned independent-review handoff, and no real
operator economic case. Those limits should remain visible in every offer and
reviewer surface until the corresponding evidence is produced.
