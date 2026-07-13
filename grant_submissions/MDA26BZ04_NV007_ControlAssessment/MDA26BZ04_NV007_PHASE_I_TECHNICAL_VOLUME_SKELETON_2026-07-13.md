# MDA26BZ04-NV007 Phase I Technical Volume Skeleton

Generated: 2026-07-13

Working title: Evidence-First Assessment Orchestration for Hybrid and Disconnected Environments

Status: `STRUCTURE_READY_CONTENT_IN_PROGRESS_WITH_SYNTHETIC_RISK_EVIDENCE`

## Page Budget

| Section | Target pages |
| --- | ---: |
| Title, topic, and required legends | 0.5 |
| Identification and significance of the problem | 1.25 |
| Phase I technical objectives | 0.75 |
| Statement of work, technical approach, experiment, and schedule | 5.0 |
| Related work and current capability boundary | 1.0 |
| Relationship with future R&D | 0.75 |
| Commercialization strategy | 1.25 |
| Key personnel | 1.5 |
| Foreign citizens, facilities, consultants, prior support, and data rights | 1.75 |
| Risks, metrics, and references | 0.5 |
| Planned total | 14.25 |
| Reserved compliance margin | 0.75 |
| Maximum | 15.0 |

The final page allocation must be checked against the live MDA instructions. Required cover content may be excluded or included differently by the official template.

## 1. Identification and Significance of the Problem

MDA assessment teams must correlate scanner findings and configuration checks to RMF controls across cloud, enterprise, and disconnected environments. Manual correlation creates latency, inconsistency, weak provenance, and repeated administrative effort. Phase I will test whether a portable, evidence-first orchestration layer can normalize scanner outputs, generate traceable control candidates, and keep a human assessor responsible for validation and risk adjudication.

Do not claim current MDA access, government data, production deployment, certification, or measured labor savings.

## 2. Technical Objectives

### Objective 1: Universal Data Ingestion

Demonstrate schema-validated parsing and normalization of representative ACAS/Nessus and SCAP artifacts into a unified finding record with source lineage.

### Objective 2: Automated Control Mapping

Develop and evaluate a versioned correlation approach for mapping CVE and STIG evidence to NIST SP 800-53 controls, including confidence, abstention, and human correction.

### Objective 3: Hybrid Architecture

Demonstrate one core engine running without source-code refactoring in cloud, local-server, and standalone-laptop deployment profiles, including disconnected operation.

### Objective 4: Assessor Workflow

Design and test a workflow that lets assessors inspect evidence, accept or reject mappings, add rationale, prioritize risk, and export an audit-ready decision record.

## 3. Phase I Statement of Work and Technical Approach

### 3.1 Normalized Evidence Record

Define a versioned record that preserves source file hash, scanner/tool metadata, asset identifier, finding identifier, CVE/CPE/STIG references, severity, timestamps, raw-record locator, parser version, and validation status. Preserve the original artifact separately from normalized records.

### 3.2 Reference and Crosswalk Layer

Ingest versioned public or authorized references. Every proposed mapping must identify the reference version and rule/model version that produced it. Many-to-many mappings remain candidates until a human or approved rule validates them.

### 3.3 Correlation Engine

Compare a transparent static rule/crosswalk baseline, a lexical retrieval baseline, and a candidate correlation method. The candidate must emit calibrated confidence and abstain when support is insufficient. No autonomous compliance determination is proposed.

### 3.4 Portable Runtime

Use a modular core with deployment-specific configuration and packaging. Run identical frozen test vectors across cloud, server, and laptop profiles; compare normalized outputs by hash. Design synchronization as signed, append-only evidence exchange with explicit conflict handling.

### 3.5 Human Validation UX

Expose the source finding, proposed control, supporting references, confidence, and provenance in one review surface. Capture accept, correct, reject, defer, rationale, reviewer, and timestamp. Preserve the pre-review recommendation and the final human decision.

## 4. Experiment and Analysis Plan

- Freeze a development set, validation set, and blind holdout before final tuning.
- Stratify by scanner source, finding type, control family, and common/rare mapping where feasible.
- Double-review a subset to estimate label ambiguity and inter-rater agreement.
- Report exact-match and family-level precision, recall, F1, coverage, abstention, calibration, and unsupported-mapping rate.
- Measure analyst time and correction burden without assuming a positive result.
- Record all parser failures, unmapped findings, timeouts, and invalid inputs.
- Package code, reference versions, split manifest, results, logs, and hashes for independent replay.

## 5. Work Plan and Deliverables

Use the month-by-month tasks in `MDA26BZ04_NV007_GO_NO_GO_AND_PROPOSAL_MAP_2026-07-13.md`.

Expected Phase I deliverables:

- requirements and benchmark protocol
- normalized schema and parser feasibility prototype
- correlation engine feasibility prototype
- portable architecture and deployment demonstration
- assessor UX prototype
- blind-holdout evaluation report
- independent replay bundle
- Phase II architecture, transition, and risk plan

## 6. Related Work and Current Capability Boundary

Existing LumenCore assets provide reusable patterns for hashed source manifests, frozen replay, baseline comparison, portable execution, evidence receipts, and human approval gates. The proposed effort adapts those patterns to cyber assessment.

Two preregistered synthetic experiments now provide bounded evidence about the proposed correlation mechanics. V1 failed because it mapped every unsupported holdout record and did not clear its minimum improvement over the best baseline. A new-seed v2 used explicit open-set score and margin constraints, achieved zero unsupported mappings and 95.8% supported-case coverage on its synthetic blind holdout, but still missed its frozen minimum baseline-delta gate. The negative verdicts are retained. Phase I is therefore framed around the demonstrated unresolved risk: representative-corpus performance, open-set calibration, human correction burden, and independent replay against accepted operational baselines.

Cyber-specific ACAS/SCAP parsers, authoritative STIG/CVE/NIST mappings, MDA integration, CMMC assessment capability, and operational validation are proposed work, not current accomplishments.

## 7. Relationship with Future Research or R&D

Phase II would extend the feasibility work into a deployable assessment workflow with longitudinal trend analysis, portable synchronization, POA&M and Security Assessment Report outputs, and interfaces for validating DCO mandates. This section must explain how each Phase I result reduces Phase II technical risk without promising an award or operational deployment.

## 8. Commercialization Strategy

Phase III paths may include MDA or Defense Industrial Base assessment workflows and regulated commercial environments that require traceable control validation. The final section must distinguish identified market hypotheses from documented customer demand, letters, revenue, or adoption.

## 9. Key Personnel

Insert only verified personnel, roles, availability, education, relevant experience, and commitments. Required gaps currently include a cyber/RMF subject-matter reviewer and independent validation support. Resumes count toward the 15-page limit.

## 10. Foreign Citizens

List only verified foreign-citizen or foreign-national facts required by the official template and live DSIP forms. Do not infer nationality, immigration status, or task assignments.

## 11. Facilities and Equipment

Describe only facilities, computing resources, software, and equipment actually available for Phase I. Identify proposed purchases and justify them consistently with Volume 3. Environmental representations require authorized-human confirmation.

## 12. Subcontractors and Consultants

List only documented roles, scope, hours, rate basis, and commitments. The current open roles are a cyber/RMF reviewer and independent validation support.

## 13. Prior, Current, or Pending Similar Support

Disclose only verified federal or non-federal support and overlapping proposals. The authorized human must confirm completeness.

## 14. Data and Software Rights

Identify any proposed restrictions using the official table and obtain qualified review before submission. Do not mark public references or ordinary commercial software as proprietary without a supportable basis.

## 15. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Ambiguous or many-to-many control mappings | Confidence, abstention, human adjudication, and ambiguity reporting. |
| Insufficient representative data | Obtain authorized corpus access or limit Phase I claims to the lawful corpus actually tested. |
| Reference-version drift | Version pinning, provenance, regression tests, and explicit update receipts. |
| Disconnected deployment differences | Identical test vectors and output-hash conformance across deployment profiles. |
| Automation bias | Present supporting evidence, preserve human authority, and measure correction behavior. |
| Unsupported security/compliance claims | Maintain a proposal claim ledger and authorized-human certification gate. |

## 16. Content Still Required

- final company and principal-investigator fields
- verified cyber/RMF personnel or consultant
- lawful representative corpus plan
- facilities and equipment statement
- verified related-work citations
- cost volume and staffing basis
- commercialization contacts or letters, if obtained
- official DSIP field mapping
- final human review and submission approval
