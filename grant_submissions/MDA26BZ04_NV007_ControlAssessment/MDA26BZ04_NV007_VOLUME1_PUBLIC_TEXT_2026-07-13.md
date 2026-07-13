# MDA26BZ04-NV007 Volume 1 Public Text

Prepared: 2026-07-13

Status: `PUBLIC_SAFE_DRAFT_PORTAL_REVIEW_REQUIRED`

## Proposed Title

Evidence-First Assessment Orchestration for Hybrid and Disconnected Environments

## Technical Abstract

Cybersecurity assessors must correlate vulnerability findings and configuration checks to security controls across cloud, on-premise, and disconnected environments. Manual correlation is difficult to reproduce, slows review, and can separate a conclusion from the source evidence and reference version that support it. LumenCore proposes a six-month Phase I feasibility effort for an evidence-first assessment orchestration framework that preserves human authority while automating bounded parts of this workflow.

The research will address four objectives. First, it will prototype schema-validated ingestion and normalization of representative ACAS/Nessus and SCAP artifacts into a versioned finding record with source hashes and parser receipts. Second, it will compare a static crosswalk baseline, a lexical retrieval baseline, and a hybrid correlation approach for proposing NIST SP 800-53 control mappings with confidence and explicit abstention. Third, it will define and test a modular core packaged for cloud, local-server, and standalone-laptop profiles using identical frozen test vectors. Fourth, it will prototype an assessor workflow that preserves the original recommendation and records accept, correct, reject, defer, rationale, reviewer, and time.

Evaluation will use development, validation, blind-holdout, and independent-replay partitions. Metrics will include exact and control-family precision, recall, and F1; coverage; abstention; calibration; unsupported-mapping rate; analyst correction burden; provenance completeness; and cross-profile output conformance. Phase I will report negative and inconclusive results and will not make an autonomous compliance determination. Existing LumenCore assets supply reusable provenance, replay, and evidence-receipt patterns; cyber-specific parsers, mappings, deployment profiles, and operational validation are proposed R&D.

## Anticipated Benefits and Commercial Applications

The anticipated Government benefit is a feasibility-tested method for reducing repetitive assessment administration while improving traceability from a technical finding to the reference, rule or model, confidence, and human decision that produced a control-validation record. A successful Phase I would provide MDA with evidence needed to decide whether an end-to-end Phase II prototype is justified; it would not require MDA to accept an unbounded artificial-intelligence claim or transfer risk authority to software.

Potential Phase II benefits include portable ingestion, control-correlation assistance, assessor adjudication, longitudinal trend analysis, and synchronization of signed evidence records between disconnected and connected environments. The same evidence contract could support an assess-once, report-many workflow while retaining the configuration and reference versions used for each result. The approach is designed to complement existing scanners, governance tools, and Defensive Cyber Operations workflows rather than replace their authoritative functions.

Potential dual-use applications include Defense Industrial Base assessment support and regulated commercial environments such as energy, healthcare, finance, and operational technology, where organizations must reconcile technical findings with versioned control frameworks and preserve reviewer accountability. Commercialization would initially target a bounded validation and evidence module delivered with qualified cybersecurity, governance, and integration partners. No current MDA deployment, CMMC assessor status, customer commitment, operational accuracy, labor savings, or production readiness is claimed. Phase I will measure feasibility, failure modes, and effect size against predeclared baselines before any transition claim is made.

## Keywords

Assessment orchestration; cybersecurity; NIST SP 800-53; Risk Management Framework; control validation; evidence provenance; human-machine teaming; disconnected operations; confidence and abstention; portable software

## Portal Gate

The live DSIP fields control character counting and accepted formatting. Recount both public fields after paste, inspect for truncation, and obtain authorized-human approval before saving certifications or submitting.
