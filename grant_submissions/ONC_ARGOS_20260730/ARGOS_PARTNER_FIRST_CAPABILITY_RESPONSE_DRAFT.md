# Project Argos Partner-First Capability Statement



**Notice:** `ONC-ARGOS-SSN-2026-OS351107`

**Deadline:** July 30, 2026 at 5:00 PM Eastern

**Status:** `DRAFT - HUMAN REVIEW AND ACTION-TIME FACTS REQUIRED`



![Founder-selected LumaArc seal of approval](../../assets/brand/lumaarc_arc_seal_v1.png)



## Required Cover Facts



| Field | Current response |

| --- | --- |

| Company name | LumenCore |

| Responding legal entity | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Seal | LumaArc seal of approval |

| UEI / DUNS if applicable | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Company address | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Authorized point of contact | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Telephone / email | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Small-business designation(s) | ACTION_TIME_PRIVATE_FACT_REQUIRED |

| Public evidence repository | https://github.com/robertashworth1986-debug/lumen-core-public |



## 1. Executive Fit and Recommended Role



LumenCore responds to this Sources Sought as a prospective evidence-assurance and deterministic-validation workstream contributor, not as a presently qualified full-scope health IT prime. The public LumenCore repository demonstrates bounded patterns for authorized-source custody, deterministic replay, rule traceability, hash-locked evidence cases, human decision gates, negative-result retention, and reviewer handoff.

For Project Argos, those patterns align most directly with requirements traceability, public-source ingestion provenance, deterministic validator orchestration, evidence-case generation, corrective-action retest records, and production handoff documentation. A credible team still requires named FHIR R4/CHPL and ONC Certification Program expertise plus an HHS ATO/FIPS 199/security assessment lead. LumenCore recommends participating under, or alongside, a qualified health IT and federal cybersecurity prime.



**Recommended acquisition position:** bounded evidence-assurance workstream participant in a named team. Full-prime readiness is not claimed.



## 2. Understanding of the Requirement



- Argos is a governed monitoring and evidence system, not a general-purpose chatbot. Standards-based and legal pass/fail decisions should remain deterministic wherever possible, with AI limited to bounded support such as summarization, classification, reconciliation, and drafting.

- The evidence chain begins with authoritative public sources and must preserve raw artifacts, request context, timestamps, response metadata, normalized records, lineage decisions, validation outputs, and hashes.

- Suspected non-conformities require human review, rule-level traceability, deduplication, plain-language narratives, controlled corrective-action support, and before/after retesting.

- Real-world endpoint observation must be safe and unauthenticated where appropriate, must avoid patient data and protected health information absent separate written authorization, and must operate within approved rate, scope, security, and hosting boundaries.

- Production readiness includes Government-aligned deployment, operations and rollback runbooks, cost and staffing visibility, and an HHS authorization path; a proof-of-concept result alone is not an Authority to Operate.



## 3. Task-by-Task Capability and Teaming Matrix



| Task | Requirement | Proposed position | Bounded contribution |

| --- | --- | --- | --- |

| 1 | Initiation, requirements, and regulatory traceability | Core contribution with partner review | Build a versioned requirements-to-test-to-evidence matrix; define evidence identifiers, severity fields, human checkpoints, decision rights, schedules, and change-control receipts. A health-regulatory lead must approve mappings to 45 CFR and ONC program practice. |

| 2 | Monthly administrative reporting | Core contribution | Produce source-backed status reports with task progress, blockers, expected completion dates, evidence links, decisions, and unresolved gates. |

| 3 | Public-source discovery and ingestion | Core contribution with FHIR partner | Implement source inventory, raw-response custody, timestamps, request metadata, hashes, lineage, precedence rules, data dictionaries, and reproducible normalized projections. Partner validates CHPL, Lantern, NPPES, and FHIR domain mappings. |

| 4 | Agentic architecture and governance | Core contribution with security partner | Separate deterministic validators from AI support; version policies, prompts, rules, retries, rate limits, fallbacks, error handling, and audit logs; require human authorization for compliance determinations. |

| 5 | Publication and FHIR R4 conformance testing | Partner-led | LumenCore can wrap validator outputs in traceable evidence cases and regression receipts. A qualified FHIR/ONC partner must own standards interpretation, test design, and conformance acceptance. |

| 6 | Real-world endpoint observation | Partner-led with evidence support | Contribute safe-observation logging, scope controls, drift records, hashes, and replayable comparison artifacts. Partner owns health-endpoint semantics, Government-approved access boundaries, and PHI avoidance controls. |

| 7 | Evidence case generation and triage | Core contribution | Assemble raw and normalized artifacts, validator output, request/response logs, timestamps, hashes, severity, rule traceability, issue narratives, deduplication keys, and machine/human-readable exports. |

| 8 | Corrective-action workflow support | Core contribution with regulatory approval | Provide controlled draft, review, authorization, retest, and before/after evidence workflows. ONC/ONC-ACB discretion and regulatory interpretation stay with authorized personnel. |

| 9 | HHS Authority to Operate | Security-partner-led | LumenCore can supply component inventories, reproducibility records, change receipts, evidence links, and control-test artifacts. The team requires an experienced HHS ATO/FIPS 199/SSP lead and authorized assessment support. |

| 10 | Production-ready PPC release package | Core contribution with prime | Package code, dependency locks, manifests, runbooks, rollback procedures, limitations, test coverage, operating assumptions, costs, staffing needs, and reviewer receipts. Hosting and production acceptance remain prime/Government decisions. |

| 11 | Public-artifact assessment and FY 2027 strategy | Core contribution with domain partner | Extend the same traceability and evidence-case pattern to approved public documentation checks, prototype scoring only under locked criteria, and retain uncertainty and adverse findings in expansion recommendations. |



## 4. Proposed Evidence-Assurance Workstream



1. **Authorize sources and scope.** Record approved source, purpose, collection boundary, cadence, rate limits, and prohibited data before collection.

2. **Preserve raw observations.** Store source payloads and request context with UTC timestamps, immutable identifiers, and SHA-256 manifests.

3. **Normalize with lineage.** Create common records while retaining source precedence, conflicts, and reversible links to raw artifacts.

4. **Run deterministic checks.** Apply versioned rules and validators; retain rule IDs, inputs, outputs, failures, and environment details.

5. **Use AI only inside policy.** Permit bounded summaries, clustering, reconciliation, and draft narratives; block autonomous compliance determinations.

6. **Assemble an evidence case.** Package artifacts, logs, hashes, timestamps, severity, traceability, narrative, and unresolved questions in human- and machine-readable forms.

7. **Require human disposition.** Route suspected issues to authorized reviewers and record decisions, rationale, corrective-action drafts, and retest outcomes.



## 5. Demonstrated Evidence and Claim Boundaries



| Evidence record | What it supports | What it does not support |

| --- | --- | --- |

| Public reviewer capsule | 31 of 31 declared assertions and 3 of 3 suites reproduced in the packaged clean-run workflow, with dependency and source-state checks. | First-party bounded reproducibility only; not external validation, agency certification, field performance, or health IT past performance. |

| Measured public EIA replay | 14,704 panel rows; frozen multi-authority holdouts; explicit baseline ranking; negative Kuramoto result retained rather than promoted. | Grid-demand benchmark only; it demonstrates evidence discipline, not transfer to FHIR, healthcare, compliance, or operational savings. |

| Residual-model replay | A residual candidate ranked first on the frozen replay while promotion, coverage, and field-validation gates remained false. | Point improvement is not a production or economic claim; prospective and independent gates remain open. |



## 6. Delivery and Security Approach



- Operate in a Government-approved environment with explicit authorization boundaries, least privilege, authenticated administration, dependency locking, secrets separation, immutable audit records, and rollback procedures.

- Treat HHS ATO as a managed authorization program: FIPS 199 categorization, boundary definition, SSP/control implementation, evidence collection, assessment coordination, POA&M handling, and Authorizing Official review.

- Do not collect, request, store, or use patient data or PHI unless separately authorized in writing and supported by approved architecture and controls.

- Keep AI components advisory and inspectable. Every model, prompt, policy, validator, retry, fallback, and rule version must be traceable to the evidence case it influenced.



## 7. Teaming Structure and Missing Qualifications



| Workstream | Accountability | Current gate |

| --- | --- | --- |

| LumenCore evidence-assurance workstream | Source custody, deterministic validation orchestration, traceability, evidence cases, hashes, claim boundaries, reviewer packages, retest receipts. | Public repository evidence supports bounded reproducibility patterns. |

| Health IT/FHIR and ONC program lead | CHPL/Lantern/NPPES semantics, FHIR R4 Endpoint/Organization/Bundle testing, ONC regulatory mapping, corrective-action content review. | Pending named and authorized partner |

| Federal cybersecurity/ATO lead | HHS authorization boundary, FIPS 199, SSP, control implementation, assessment coordination, POA&M and authorization package. | Pending named and authorized partner |

| Prime/program integration lead | Contract performance, staffing, Government coordination, hosting, delivery acceptance, health-domain prior performance, and integrated schedule. | Pending named and authorized partner |



## 8. Illustrative Mobilization Plan



| Period | Illustrative outcome |

| --- | --- |

| 0-30 days | Confirm team, scope, source authorization, regulatory ownership, hosting assumptions, traceability schema, security boundary, and pilot cohort. |

| 31-90 days | Stand up bounded ingestion, lineage, deterministic validator interfaces, evidence-case schema, human work queue, baseline test corpus, and audit logs. |

| 91-180 days | Expand approved endpoint observation, drift tracking, issue clustering, corrective-action draft/retest workflow, security documentation, and operational runbooks. |

| 181 days and beyond | Complete Government-directed hardening, assessment evidence, production handoff, PPC evaluation, cost/staffing analysis, and FY 2027 strategy. |



## 9. Questions and Requested Next Step



1. What proof-of-concept duration, target cohort size, and Government hosting environment should respondents assume for acquisition planning?

2. Which organization owns final interpretation of 45 CFR and ONC Certification Program test outcomes, and what review service levels are expected?

3. Will HHS provide an approved source list, rate-limit policy, synthetic test corpus, and expected evidence-case export schema?

4. Is HHS seeking one full-scope prime, or would it value clearly bounded small-business teaming responses for evidence assurance, FHIR validation, and ATO workstreams?

5. What existing HHS authorization boundary, reusable controls, continuous-monitoring services, or 3PAO arrangements may be available to the PPC?



**Requested next step:** include LumenCore in market-research or teaming discussions where a qualified prime needs an inspectable evidence-assurance workstream.



> This response is for market research only and is not an offer, proposal, certification, or representation that every draft SOW task is presently covered.
