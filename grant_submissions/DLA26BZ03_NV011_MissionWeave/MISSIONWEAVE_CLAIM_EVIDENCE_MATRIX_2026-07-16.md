# MissionWeave Claim-Evidence Matrix

Updated: July 16, 2026  
Purpose: keep every proposal statement inside the evidence actually available to a reviewer.

| Candidate claim | Evidence available now | Allowed wording | Prohibited escalation |
|---|---|---|---|
| A generated routing policy was developed and tested reproducibly. | Frozen run `out/missionweave_validation/20260613T_MISSIONWEAVE_V3_DEV16_VAL30`; manifest SHA-256 `BD5FB806A6F524DE2E60D48E4D091D916F86B35B2FD73E3889667B2D8B2385DB`; 16 development scenarios; 30 disjoint validation seeds in five conditions. | “Generated-workflow feasibility evidence with a frozen development/validation separation.” | “DLA validated,” “field proven,” “production ready,” or “independently reproduced.” |
| Mean on-time rate improved against cross-trained FIFO in the frozen generated model. | Exact deltas, paired bootstrap intervals, and seed outcomes in `summary.json`. | Report the five exact mean deltas, intervals, and better/tied/worse counts together with limitations. | Universal superiority, causal productivity improvement, 10x improvement, or operational readiness. |
| The approach can preserve negative findings. | 1/30 nominal, 5/30 surge, 2/30 absence, 2/30 outage, and 7/30 combined-stress seeds were worse on on-time rate; combined-stress absolute on-time was 0.240 vs 0.270. | “Negative seeds and low absolute performance regions are retained as design evidence.” | Hiding losses, reporting only averages, or calling the combined-stress case solved. |
| MissionWeave can be adapted to a bounded DLA-relevant process. | Process plan for Critical Supply Exception Triage and Disposition; official topic fit; no DLA approval or data. | “Representative unclassified process assumption, replaceable during Government alignment.” | “Current DLA process,” “DLA-approved workflow,” or “DLA customer use.” |
| Phase I can produce a proof of concept and roadmap. | Existing code, benchmark harness, evidence manifests, task plan, and six-month SOW. | “Proposed Phase I deliverables and acceptance gates.” | Treating proposed work as already delivered or accepted. |
| Results can be made auditable. | SHA-256 manifests, deterministic configuration, source registry design, test harness. | “The POC will bind source, configuration, software, and outputs into reproducibility receipts.” | Blockchain, immutable, tamper-proof, certification-grade, or independent validation unless separately established. |
| Responsible-use controls are designed into the work. | Human approval, minimal data, synthetic labeling, abstention and rollback requirements in the proposal. | “Proposed controls aligned to NIST AI RMF and DoD Responsible AI practices.” | Compliance, certification, fairness validation, privacy-law compliance, or authorization to operate. |
| The project has DLA transition potential. | Official topic calls for DLA Component collaboration and Phase II MVP; no commitment exists. | “Desired transition path through DLA J1/J3/J6/J7 alignment and a Phase II pilot.” | Sponsor, partner, customer, procurement commitment, or letter of support without signed evidence. |
| The applicant can perform the proposed work. | Existing repository implementation, tests, benchmark outputs, documentation, and 640-hour all-prime work plan. | Describe proposal-specific capabilities and artifact evidence. | Unsupported degrees, certifications, security clearances, customers, revenue, awards, publications, or granted patents. |
| The business case can estimate value. | Bottom-up value equation and Phase I data plan; no approved inputs or realized savings. | “Phase I will estimate ROI ranges with approved inputs and sensitivity analysis.” | Realized savings, guaranteed ROI, market dominance, or a dollar valuation of unvalidated technology. |

## Frozen Benchmark Evidence

| Condition | Mean on-time delta vs cross-trained FIFO | Paired 95% bootstrap interval | Better / tied / worse seeds |
|---|---:|---:|---:|
| Nominal | +0.0578 | [0.0378, 0.0806] | 25 / 4 / 1 |
| Surge | +0.1156 | [0.0741, 0.1611] | 24 / 1 / 5 |
| Targeted absence | +0.1175 | [0.0733, 0.1638] | 25 / 3 / 2 |
| System outage | +0.1266 | [0.0852, 0.1761] | 28 / 0 / 2 |
| Combined stress | +0.0302 | [0.0168, 0.0435] | 23 / 0 / 7 |

Evidence boundary: generated cases, workers, skills, deadlines, absences, and outages only. These results do not establish DLA readiness, workforce productivity, causal impact, fairness, privacy compliance, operational integration, or a 10x improvement.
