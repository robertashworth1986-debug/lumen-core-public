# ERDC SDC Internal Red-Team Receipt

**Classification:** INTERNAL MODEL REVIEW - NOT INDEPENDENT VALIDATION

**Reviewed UTC:** `2026-07-29T21:14:27Z`

**Reviewer:** Codex read-only subagent `Dirac`

**Agent ID:** `019fafa5-a831-78e1-af85-e2ebba5f432c`

**Disposition:** `BLOCKED_NOT_SUBMISSION_READY`

## Reviewed Scope

- `code/ops/BUILD_ERDC_SDC_EVIDENCE_ABLATION.py`
- `out/ops/erdc_sdc_evidence_ablation_latest.json`
- `docs/ERDC_SDC_EVIDENCE_ABLATION_2026-07-29.md`
- `code/ops/BUILD_ERDC_SDC_SOLUTION_BRIEF.py`
- `output/pdf/LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf`
- `grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json`
- Official CSO and July 20 FAQ source set for `W912HZ26SC005`

## Findings

1. The version-one receipt could be adaptively re-chained and re-sealed because its verifier trusted mutable expected counts and roots inside the same packet.
2. OpenTelemetry and SLSA were scored asymmetrically against LumenCore even though they are interoperability and provenance formats with different purposes.
3. The exact July 29 evidence was not reproducible from the public repository because the current files had not been reviewed, committed, and pushed.
4. The acronym list omitted terms used in the brief, including AI, CLI, CPU, HTTP, SAM, and SLSA.
5. The compliance gate called local format and marker checks "technical" and used a status that overstated hardening.
6. Mission scope was too broad. Unified Service Layer and Vendor Lock-In Prevention should be primary; AI-Powered Orchestration and Secure Data Fabric should be integration boundaries.
7. Several phrases outran the evidence, including detection, OpenAPI schema, append-only chain, digest verification, and comparative timing language.
8. Source custody lacked extracted text, a requirement crosswalk, and a locally hashed live-page snapshot.
9. There was no controlled private-final artifact path binding the approved ROM, SAM/contact facts, exact final PDF, and portal review.

## Remediation State

- The evidence ablation protocol was revised to version two with seven declared attacks, full synthetic artifact-byte rehashing, and a separately supplied local anchor.
- OpenTelemetry and SLSA are now context-only and are not ranked.
- Proposal scope, claim wording, acronyms, source custody, and gate names were revised.
- Public reproducibility, external trust anchoring, an HPCMP-representative workload and Government comparator, committed delivery resources, independent review, private ROM/SAM/contact finalization, and portal review remain open.

## Claim Boundary

This receipt records an internal model-assisted review and remediation queue. It is not an independent assessment, Government review, security authorization, software certification, field validation, or evidence of performance or award readiness.
