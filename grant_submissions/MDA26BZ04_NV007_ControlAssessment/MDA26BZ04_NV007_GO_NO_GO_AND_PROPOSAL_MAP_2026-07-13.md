# MDA26BZ04-NV007 Go/No-Go and Proposal Map

Generated: 2026-07-13

Status: `CONDITIONAL_GO_BUILD_PHASE_I_PACKAGE`

## Decision

Proceed with a Phase I package because the topic aligns with LumenCore's existing provenance, replay, evidence-manifest, portable orchestration, and reviewer-workflow assets. Do not claim that ACAS, SCAP, STIG, CVE, or NIST 800-53 adapters already exist. Those cyber-specific components are the proposed research and development work.

This is a stronger fit than the currently visible DARPA Direct-to-Phase-II topics, which require prior working capabilities that the present evidence stack does not establish.

## Problem Fit

MDA describes an assessment process dominated by manual correlation of scanner findings and STIG checks to RMF controls. The Phase I objective is feasibility, not production deployment:

1. Parse and normalize ACAS and SCAP outputs.
2. Correlate CVEs and STIGs to NIST SP 800-53 controls with high accuracy.
3. Define a modular architecture that runs in cloud, on-premise, and standalone laptop environments without refactoring.
4. Design an assessor workflow for human validation and risk adjudication.

## Existing Assets That May Be Cited

- source and result SHA-256 manifests
- frozen replay orchestration and baseline comparison runners
- portable Python and container-compatible execution patterns
- machine-readable evidence and reviewer receipts
- human approval and claim-boundary gates
- dashboards that expose source, candidate, baseline, metric, and status records

These are adjacent platform assets. They are not proof of MDA, ACAS, SCAP, RMF, CMMC, or operational cyber validation.

## Required Phase I R&D

- schema-validated ACAS/Nessus and SCAP ARF/XCCDF ingestion adapters
- versioned CVE, CPE, STIG, and NIST SP 800-53 reference ingestion
- traceable many-to-many crosswalk with confidence and abstention
- authoritative mapping test corpus with cyber/RMF subject-matter review
- portable offline bundle and synchronization manifest
- assessor UX for accepting, correcting, rejecting, and annotating mappings
- blind holdout and independent test plan

## Six-Month Work Plan

| Month | Work package | Exit evidence |
| --- | --- | --- |
| 1 | Freeze requirements, schemas, source licenses, threat model, and benchmark protocol. | Approved data dictionary, source manifest, baseline plan, and test corpus split. |
| 1-2 | Build ACAS and SCAP parsers plus normalized finding schema. | Parser conformance tests, malformed-input tests, provenance completeness report. |
| 2-4 | Build versioned CVE/STIG-to-control correlation engine. | Blind-holdout precision, recall, F1, exact-match, calibration, and abstention results. |
| 3-5 | Package the same core engine for cloud, local server, and standalone laptop. | Identical test vectors, container/bundle hashes, disconnected-operation demonstration. |
| 4-6 | Build assessor validation and risk-adjudication workflow. | Human correction log, task-time study, usability findings, and signed evidence manifest. |
| 6 | Independent replay, final technical report, and Phase II transition design. | Reproduction receipt, limitations register, architecture, and Phase II backlog. |

## Evaluation Design

Primary mapping metrics:

- control-ID exact-match precision, recall, and F1
- control-family precision, recall, and F1
- coverage and explicit abstention rate
- calibration error by confidence band
- provenance completeness percentage

Workflow metrics:

- median analyst minutes per finding
- correction rate and correction type
- inter-rater agreement on a double-reviewed subset
- unsupported-mapping rate
- percentage of results traceable to source record, reference version, rule/model version, and reviewer decision

Portability metrics:

- conformance pass rate across cloud, server, and laptop targets
- identical normalized output hash for identical test vectors
- offline installation time and storage footprint
- synchronization conflict and recovery tests

Baselines:

- manual expert mapping on the blind subset
- versioned static crosswalk/rule baseline
- lexical retrieval baseline
- candidate correlation approach with confidence and abstention

The proposal should not prestate an improvement percentage. Phase I will measure feasibility and effect size against these baselines.

## Teaming Gates

The package is not ready for final submission until these roles are covered:

- RMF/NIST 800-53 and STIG subject-matter reviewer
- representative ACAS/SCAP corpus provider with lawful data rights
- independent test or red-team reviewer
- cost-volume reviewer

No partner name, commitment, past performance, or data access may be fabricated.

## Compliance and Portal Gates

- DSIP organization linkage and submitter authority
- current SAM registration and entity data
- CMMC Level 1 and SPRS representations verified by the authorized human
- CCR Volume 4
- Supporting Documents Volume 5
- Fraud, Waste, and Abuse training Volume 6
- Foreign Ownership/Control/Influence or foreign-affiliation webform Volume 7 as required
- cost volume and indirect-rate basis
- final upload, certification, and submit approval

## No-Go Triggers

- inability to obtain lawful representative scanner outputs or an acceptable synthetic/public feasibility corpus
- no qualified cyber/RMF reviewer before the technical volume lock
- unsupported claim that current LumenCore assets already satisfy MDA operational requirements
- unresolved ownership, export, CUI, or cybersecurity representation
- unreviewed cost basis

## Next Package Actions

1. Build the 15-page Technical Volume around the four Phase I objectives.
2. Build a one-page cyber-specific current-capability boundary.
3. Identify and document the lawful Phase I corpus strategy.
4. Create the cost-volume assumptions and staffing table.
5. Create a DSIP field map and stop at the final human submit gate.
