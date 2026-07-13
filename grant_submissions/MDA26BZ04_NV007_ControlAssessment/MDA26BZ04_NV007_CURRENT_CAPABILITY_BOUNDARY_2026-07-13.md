# MDA26BZ04-NV007 Current Capability Boundary

Prepared: 2026-07-13

## Safe Current-Capability Statement

LumenCore currently provides reusable software patterns for source hashing, schema-aware ingestion, frozen replay, candidate-versus-baseline evaluation, append-only evidence receipts, portable Python execution, and human review gates. Those patterns are relevant to assessment orchestration because they can preserve where a finding came from, which reference and rule version produced a proposed mapping, what a baseline produced, what failed, and what a reviewer accepted or corrected.

LumenCore does not currently claim operational ACAS, Nessus, SCAP, XCCDF, ARF, STIG, CVE-to-control, NIST SP 800-53, RMF, CMMC, POA&M, Security Assessment Report, DCO, MDA, classified, CUI, or air-gapped deployment capability. Building and validating those cyber-specific adapters, mappings, workflows, and deployment profiles is the proposed Phase I R&D.

## Existing Assets

| Asset | Current evidence | Relevance to Phase I | Boundary |
| --- | --- | --- | --- |
| Source manifests and SHA-256 chains | Executable local tooling and generated receipts | Preserve scanner artifact identity, parser version, reference version, and result lineage | Not a cyber parser or authorization mechanism |
| Frozen benchmark protocols | Preregistered EIA holdout and prospective-routing examples | Freeze corpus splits, baselines, metrics, failure rules, and promotion gates | Grid evidence does not validate cyber performance |
| Candidate-baseline orchestration | Multiple public-data benchmark runners | Compare static crosswalk, lexical retrieval, and candidate mapping routes | Operational cyber mapping remains proposed work |
| Synthetic control-mapping feasibility | Two preregistered synthetic experiments with independent seeds, full predictions, failure logs, and hash manifests | V1 exposed forced unsupported mappings; v2 reduced unsupported mappings to zero while retaining 95.8% supported-case coverage | Both experiments remained below their frozen promotion gates; synthetic fixtures do not establish operational accuracy or Government validation |
| Human approval gates | Repository policy and machine-readable status records | Keep assessors responsible for validation and risk adjudication | Not an RMF authority or compliance determination |
| Portable Python execution | Local reproducible runners and environment receipts | Starting point for cloud, server, and laptop packaging | No disconnected cyber deployment has been demonstrated |
| Reviewer manifests and dashboards | Source, baseline, candidate, metric, status, and caveat records | Starting point for assessor evidence and correction workflow | Not an MDA-approved user interface |

## Proposed Phase I Outputs

1. Schema-validated ACAS/Nessus and SCAP ingestion feasibility prototypes.
2. Versioned finding schema with source and parser provenance.
3. Static-crosswalk, lexical-retrieval, and candidate mapping baselines.
4. Confidence, abstention, and human correction workflow.
5. Identical frozen-vector conformance runs across three packaging profiles.
6. Blind-holdout metrics, failure log, and independent replay bundle.

## Current Synthetic Evidence Boundary

The current software can generate deterministic synthetic finding records, compare static and lexical routes, enforce validation-selected abstention rules, score a blind holdout, preserve failures, and emit separate fixture, split, threshold, prediction, result, and artifact-chain receipts. V1 failed its unsupported-mapping and baseline-delta gates. A separately seeded v2 passed its synthetic unsupported-mapping and supported-coverage checks but missed its minimum baseline-delta gate. This is useful technical-risk evidence, not a promoted cyber capability.

Proposal-safe details are recorded in `MDA26BZ04_NV007_SYNTHETIC_FEASIBILITY_EVIDENCE_2026-07-13.md`.

## Prohibited Proposal Claims

- current MDA customer, access, validation, endorsement, or past performance
- current CMMC assessor status or compliance certification
- current production-ready ACAS/SCAP ingestion or NIST control mapping
- autonomous compliance or risk determination
- classified, CUI, or air-gapped operational readiness
- measured labor savings or mapping-accuracy percentage before Phase I testing
- partner, consultant, data access, or letter of support that is not documented
