# ERDC SDC Solution Brief Compliance Gate - 2026-07-29

The public-safe brief now binds a purpose-bounded comparator, local control ablation, proposed quantitative falsifiers, cost denominators, and honest delivery boundaries. It is not submission-ready until the Phase II price and execution commitments are approved, private SAM/contact facts are inserted and reverified, and the complete authenticated portal form is reviewed.

## Gate Summary

- Status: `CURRENT_PUBLIC_DRAFT_FORMAT_AND_MARKER_CHECKS_PASS_SEMANTIC_EVIDENCE_AND_PRIVATE_FINALIZATION_REQUIRED`
- Submission ready: `false`
- Funding currently available: `false`
- Safest operational deadline: `4:00 PM CT on August 7, 2026`
- Original CSO PDF deadline text: `1700 EST, 07 AUG 2026`
- Current live page deadline text: `4:00 PM CT on August 7, 2026`
- Question submission cutoff: `July 31, 2026`
- PDF pages: `7` physical; `5` counted body pages
- PDF bytes: `108736`
- PDF SHA-256: `f1135e0ce4564335d3d5fcc2a7ec2aa8c20e435e9a9bcae815a2619023ab0690`
- Minimum detected font size: `12.0`
- Times New Roman detected: `true`
- Letter portrait: `true`
- One-inch text margins: `true`
- Body page labels present: `true`
- Format and marker checks pass: `true`
- Semantic review complete: `false`
- Source checks pass: `true`
- Evidence ablation checks pass: `true`
- Evidence ablation SHA-256: `0e17f27d4ea6c049b73e12664a6838c5ac0cb767e9a7a18ac2e1e8b108db2a7f`
- Evidence protocol SHA-256: `61337e3493f63f46a700152748d5a586635dfb9338fb5ba6766e084d6ae5a723`
- Synthetic workflows: `48`
- Full-control attacks detected: `7/7`
- Adverse-outcome recall: `1.0`
- Synthetic artifact byte rehash rate: `1.0`
- Finalization blockers: `8`
- External send without human: `false`
- Final portal submit without human: `false`
- Session-browser navigation performed: `false`
- Gate SHA-256: `ae818a96dd5518308e66fa64660fae6cb8dfc3b70c3268a50fb28ff3fbfcbff8`

## Compliance Matrix

| ID | Status | Requirement | Evidence |
|---|---|---|---|
| `FORMAT_01` | `PASS` | Five-page maximum proposal body | PDF has five numbered body pages plus excluded cover and acronym pages. |
| `FORMAT_02` | `PASS` | Letter, portrait, single-sided, page X of Y | All seven physical pages are 612 by 792 points and carry physical-page X of 7 plus body-page labels where applicable. |
| `FORMAT_03` | `PASS` | Minimum one-inch margins | PDF character-coordinate inspection verifies all non-watermark text remains within a 72-point boundary. |
| `FORMAT_04` | `PASS` | 12-point Times New Roman, including tables and diagrams | Embedded Windows Times New Roman files; PDF inspection requires all substantive text to remain 12 point. |
| `FORMAT_05` | `PASS` | English PDF under 20 MB | Generated PDF is English, Acrobat-readable, and size-checked. |
| `DISCLOSURE_01` | `PASS` | No classified or proprietary information | Public-safe architecture and boundaries only; no private identity, patent claims, credentials, or classified data. |
| `TECH_01` | `PASS` | Describe solution and mission effectiveness | Body pages 1 and 2 define the evidence control plane, mission gap, components, and focus-area alignment. |
| `TECH_02` | `PASS_BOUNDED` | Explain innovation and feasibility | Body pages 1, 3, and 4 distinguish the mechanism, define the prototype, name acceptance checks and falsifiers, and preserve the HPCMP and independent-validation boundary. |
| `TECH_03` | `LOCAL_ONLY_EXTERNAL_REPRODUCIBILITY_REQUIRED` | Provide URL and convincing evidence | Public website and repository are listed, but the exact July 29 builder, receipt, and proposal gate remain local until a reviewed commit is published. Field validation is not claimed. |
| `BASELINE_01` | `PASS_BOUNDED` | Name current purpose-matched interoperability contexts | Body pages 1, 3, and 5 name OpenTelemetry Logs Data Model 1.59.0 and SLSA Build Provenance 1.2 with in-toto Statement v1 as unranked interoperability contexts and reject universal ranking. |
| `ABLATION_01` | `PASS_BOUNDED` | Show the claimed control contribution through ablation | The bound local surrogate covers 48 deterministic workflows and seven declared attacks; the full profile detects 7 of 7 relative to a separately supplied local anchor while each no-chain, no-predeclaration, or no-failure-retention profile loses a declared control. It is not an HPCMP or independent result. |
| `TRUST_01` | `EXTERNAL_TRUST_ROOT_REQUIRED` | Bind the protocol and receipt to a trust root outside the mutable evidence packet | The local experiment supplies an anchor separately from the receipt, but it is not a Government-controlled signature, timestamp, or external trust service. |
| `METRIC_01` | `PASS_BOUNDED` | Define quantitative checks, cost denominators, and falsifiers | Body pages 3 and 4 require complete declared-attack detection, complete adverse-case retention, clean reviewer replay, fixed-window baseline comparison, explicit cost drivers, and stop/rollback on a miss or Government-set overhead breach. |
| `EXEC_01` | `PRIVATE_FINALIZATION_REQUIRED` | Bind delivery roles, compute, support, and transition commitments | Body page 4 identifies the founder as proposed technical lead and bounds commodity surrogate compute; Government or prime integration, evaluator commitment, production compute, staffing, support, and transition ownership remain to be bound in the private Phase II plan and price. |
| `ROM_01` | `PRIVATE_FINALIZATION_REQUIRED` | One estimated price for Phase II prototype only | Body page 5 preserves the required section but intentionally includes no unapproved amount. |
| `SAM_01` | `PRIVATE_FINALIZATION_REQUIRED` | Active SAM all-awards contract registration and matching solution address | Public draft withholds identity and address; live SAM all-awards status, contract eligibility, and exact match must be verified before upload. |
| `CONTACT_01` | `PRIVATE_FINALIZATION_REQUIRED` | Current accurate proposal contact email | Public draft intentionally omits private contact data; insert and verify in the private final copy. |
| `ACCOUNT_01` | `HUMAN_ACCOUNT_ACCESS_REQUIRED` | Working Submittable account and access to the complete live form | The public submission landing page requires a free Submittable account or supported federated sign-in; complete form access has not been verified. |
| `PORTAL_01` | `HUMAN_FINAL_ACTION_REQUIRED` | Submit through ERDCWERX form before the safest current cutoff of 4:00 PM CT August 7, 2026 | The original CSO PDF says 1700 EST while the current live page says 4:00 PM CT; use the current live page's earlier practical cutoff. No portal submission is represented. |
| `FAQ_01` | `PASS` | ROM excludes Phase III and IV | Body page 3 and price gate scope Phase II only. |
| `FAQ_02` | `PASS_BOUNDED` | Consider all classification levels without assuming CAC-only access | Per-enclave architecture and identity-context boundary are described without claiming accreditation or cross-domain transfer. |
| `FAQ_03` | `PASS_BOUNDED` | MOSA and nonproprietary standards prevent vendor lock-in | Body pages 1 and 2 define focused-module MOSA boundaries, replaceable adapters, open contracts, and portable verification. |
| `FAQ_04` | `PASS_BOUNDED` | AI remains human-in-the-loop with manual override | Body page 3 keeps AI advisory and requires explicit parameters, manual override, and retained evidence for bounded administrative automation. |
| `FAQ_05` | `PASS_BOUNDED` | Absolute data separation and cloud-agnostic portability | Body pages 2 and 4 define separate enclave deployment, absolute data separation, replaceable clouds, workload portability, and bounded burst behavior. |
| `FAQ_06` | `PASS_BOUNDED` | Legacy interoperability with phased low-risk migration | Body pages 3 and 4 define shadow-mode prototype work, rollback evidence, legacy transition boundaries, and phased handoff. |
| `FUNDING_01` | `PASS` | Do not imply current funds or guaranteed award | Cover, compliance gate, and claim boundary state funding is not currently available and no award is guaranteed. |

## Required Private Finalization

- Approve one Phase II-only firm-fixed-price Rough Order of Magnitude estimate.
- Bind named Phase II delivery roles, staffing, production compute or cloud access, support, evaluator, integration, and transition ownership without inventing commitments.
- Insert the exact active SAM legal entity name and matching address in a private copy.
- Insert and verify the current proposal contact email in the private copy.
- Reverify active SAM all-awards contract registration and review current ERDCWERX questions and answers.
- Sign in to the required Submittable account and inspect the complete current form.
- Review the final private PDF, portal fields, representations, terms, and submission confirmation.

## Source Integrity

- `grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/CSO_HPCMP_SDC_30April2026_FINAL.pdf`: hash=`true` bytes=`true` pages=`true`
- `grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/HPCMP_SDC_FAQ_20Jul2026.pdf`: hash=`true` bytes=`true` pages=`true`

## Claim Boundary

This is a public-safe technical draft, not a submitted solution brief. It does not include the founder-approved Phase II price, private SAM-matched legal identity and address, a live SAM status verification, signature, certification, or portal confirmation. It does not claim ERDC selection, funding availability, a contract, Department of Defense deployment, an authorization to operate, classified-data handling, field validation, customers, revenue, or realized savings, or technical performance beyond the bounded repository evidence identified here.
