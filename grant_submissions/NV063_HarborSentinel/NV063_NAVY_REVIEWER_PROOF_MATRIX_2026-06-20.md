# NV063 HarborSentinel Navy Reviewer Proof Matrix

Generated: 2026-06-20

Status: local reviewer-control matrix for the HarborSentinel Navy SBIR package.
This document does not authorize DSIP upload, certification, or submission.

## Purpose

This matrix gives the Navy reviewer one grounded answer surface for the current
HarborSentinel package: what the technical bet is, what evidence exists, what
the public AIS benchmark supports, what still needs authorization, and which
claims must remain off-limits until stronger evidence exists.

The strongest current claim is not that HarborSentinel is ready for operational
use. The strongest current claim is that the proposal now has a reproducible
Phase I path from generated multi-source feasibility evidence to public AIS
held-out validation, with explicit gates for ADS-B rights, radar/composite-track
assumptions, SSDS integration, cybersecurity, CMMC/SPRS, and clearance planning.

## Executive Reviewer Spine

| Reviewer question | Current answer | Evidence now | Boundary to preserve |
|---|---|---|---|
| What problem is being solved? | Congested maritime watch teams need explainable, low-storage anomaly review for surface and air contacts without relying on massive port-specific archives. | Volume 2 draft sections 1-3 and representative-data plan. | Not a completed SSDS integration or live watch-floor deployment. |
| What is new? | HarborSentinel keeps compact per-track, source-aware state and separates behavior candidates from source-integrity review instead of turning transmitter loss alone into a threat label. | v6 generated source-lane evidence and Volume 2 approach. | Does not prove real adversary detection or field sensor performance. |
| Why is this Navy-relevant? | The topic asks for anomalous behavior detection in congested maritime environments using AIS, ADS-B, radar-like, and composite-track concepts under low-storage constraints. | Official local Navy instruction copy, Volume 2 topic mapping, and data-lane plan. | Topic fit is not eligibility, submitter authority, or award likelihood. |
| What public data evidence exists? | NOAA AIS was acquired, hashed, split into frozen development/validation sets, full-file SHA-256 verified for both split files, tested with controlled kinematic injections, and profiled for natural review-burden queues. | AIS acquisition, split, local cache, full-hash I/O preflight, controlled-injection artifacts, and review-burden profile. | Public AIS does not validate ADS-B, radar, Navy organic tracks, SSDS displays, field performance, or false-positive rates without labels. |
| What did the controlled benchmark show? | A frozen development-threshold motion-consistency detector caught 20000 injected validation perturbations with recall 1.0 versus 0.25835 for reported-speed-only and 0.5068 for the best single-axis baseline. | `NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md` and public proof packet. | Controlled injections are not real threat labels and natural candidate rates are not false-positive rates. |
| What is the review burden? | On the held-out public AIS validation split, the unlabeled motion-consistency queue flagged 1742 of 48616 segments (3.583%); mean load was 145.167 candidates/hour and p95 load was 158.7 candidates/hour before analyst caps. | `NV063_AIS_REVIEW_BURDEN_PROFILE_2026-06-21.md` and hash-manifested review-burden run. | This is a review-queue estimate, not precision, false-positive rate, real threat detection, or operational suitability. |
| What is the Phase I exam? | Freeze source rights, message schema, baselines, acceptance thresholds, and public/authorized partitions; then report precision, recall, F1, alert burden, delay, calibration, memory, runtime, and latency by data lane. | Volume 2 Month 1-6 plan and deliverables. | Stronger claims require labels, analyst adjudication, or authorized evaluation data. |
| What blocks submission? | DSIP authority, DoD reps, U.S. ownership/operation, FOCI/export, cybersecurity, CMMC/SPRS, cost basis, clearance-transition path, portal preview, and action-time approval. | Readiness file, finalization audit, blocker board, and readiness feed. | Do not hide these gates; they are part of the credibility posture. |

## Evidence Map

| Artifact | Supports | Does not support |
|---|---|---|
| `NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md` and `.docx` | A compact six-page working Volume 2 draft with Base/Option tasks, milestones, success criteria, risks, transition, and submission boundary. | Final DSIP upload approval or portal compliance. |
| `render_qa_20260620_baselines_v1/` | Latest six-page PDF render and page PNGs after adding public AIS full-hash and stronger-baseline controlled-injection evidence. | Independent DSIP portal preview. |
| `NV063_AIS_PILOT_ACQUISITION_2026-06-20.md` | Public NOAA AIS raw file acquired, hashed, and schema-profiled. | HarborSentinel detection performance. |
| `NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md` | Frozen development and validation splits for New Orleans / Mississippi River Delta. | Navy sensor validation or ADS-B/radar coverage. |
| `NV063_AIS_IO_PREFLIGHT_2026-06-20.md` | Frozen split files were reachable, sample-readable, and full-file SHA-256 matched the frozen split manifest. | HarborSentinel detection performance, multi-source fusion, ADS-B/radar validation, or field suitability. |
| `NV063_AIS_LOCAL_SPLIT_CACHE_2026-06-20.md` | Local split cache hash-matched the frozen split manifest. | Field performance or production data operations. |
| `NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md` | Detector-vs-single-axis-baseline comparison on controlled kinematic injections: reported speed, derived trajectory speed, speed-gap consistency, and heading rate. | Real adversary labels, precision, false-positive rates, multi-source fusion, ADS-B/radar validation, or operational suitability. |
| `NV063_AIS_REVIEW_BURDEN_PROFILE_2026-06-21.md` | Natural validation review-queue estimate by hour and density tier; capped-review workload profile for 5/10/20 candidates per hour. | Precision, false-positive rates, real threat detection, field validation, or operational suitability. |
| `NV063_COST_BASIS_WORKING.md` | ROM cost basis for Base/Option planning. | Reviewed cost proposal or certified rates. |
| `LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md` | Cross-stack proof discipline: the evidence system separates promoted live-measured rows from context-only estimates, reports 12/17 measured sources and 11 promoted live-measured rows, and keeps the larger context-only surface fenced off. | HarborSentinel detection merit, Navy sensor validation, public AIS false-positive rate, field performance, trading profit, customer savings, revenue, valuation proof, or award likelihood. |

## Claim Language To Use

- "bounded public AIS controlled-injection benchmark"
- "detector-vs-baseline evidence on controlled kinematic perturbations"
- "held-out public AIS development and validation splits"
- "unlabeled public AIS review-burden profile"
- "natural candidate rates are review queues, not false-positive rates"
- "representative-data bridge, not field validation"
- "Phase I will test whether the approach transfers to authorized data lanes"
- "source-integrity review is separated from behavior-based threat candidates"

## Claims To Avoid

Do not say or imply:

- HarborSentinel detects real adversaries today.
- Public AIS validates Navy radar, ADS-B, SSDS displays, or composite tracks.
- The system is ready for watch-floor, fleet, or production use.
- The current evidence proves field performance.
- CMMC/SPRS, clearance, export, FOCI, or cybersecurity gates are already solved.
- The $315,000 planning basis is a reviewed cost proposal.
- A Navy reviewer, transition sponsor, customer, or data partner has signed off
  unless a written artifact exists.
- Trading, live-breadth, or frozen-delta artifacts prove HarborSentinel merit.

## Reviewer Objection Handling

| Objection | Grounded answer |
|---|---|
| "Public AIS is not Navy sensor data." | Correct. It is a public representative-data lane for surface cooperative traffic only. The proposal keeps ADS-B, radar, composite tracks, and SSDS claims behind separate authorization gates. |
| "Controlled injections can be too easy." | Correct. They are a first detector-vs-baseline check, not a final metric. The current benchmark now includes four single-axis baselines; Phase I should still add labels or adjudication and density-aware review-burden measurement. |
| "What about false positives?" | Natural candidate rates are review queues, not false-positive rates. The review-burden profile now quantifies the unlabeled queue: 3.583% validation candidate rate, mean 145.167 candidates/hour, p95 158.7 candidates/hour, plus capped-review retention at 5/10/20 candidates per hour. Precision and false-positive estimates still require labels or an analyst adjudication protocol. |
| "Does live breadth prove HarborSentinel value?" | No. The live-breadth provenance annex supports measurement discipline and chain-of-custody only. HarborSentinel merit still rests on the bounded public AIS evidence, controlled-injection baselines, review-burden profile, and Phase I plan for authorized data lanes. |
| "What is the transition path?" | Phase I produces unclassified prototype, alert schema, interface-control concept, frozen evaluation package, failure register, and Phase II SSDS/security/clearance roadmap. |
| "Can this be uploaded now?" | Not yet. Local file readiness is strong, but DSIP authority, DoD representations, cost review, cybersecurity/CMMC/SPRS, FOCI/export, clearance-transition, portal preview, and action-time approval remain. |

## Next Evidence Upgrades

1. Extend beyond the current single-axis baselines and review-burden profile
   into trajectory smoothness, route-distance, track-context, and density-aware
   models.
2. Add a public or partner-authorized labeling/adjudication protocol so
   precision and false-positive estimates are defensible.
3. Add ADS-B only after access rights and data-use terms are documented.
4. Add radar/composite-track evaluation only under generated assumptions or
   government-authorized data with a separate claim boundary.
5. Record CPU/GPU time, memory, latency, and storage footprint for every
   benchmark lane.
6. Create a DSIP upload-preview checklist for exact filename, page count, cover
   fields, and final PDF/DOCX behavior.

## Final Submission Gate

Do not upload or submit until all are true:

- DSIP account, organization linkage, and submitter authority are verified.
- SAM.gov entity status/linkage is verified for the submitting entity.
- DoD ownership/operation, FOCI, export, cybersecurity, and required
  representations are reviewed.
- CMMC/SPRS/Affirming Official status is documented accurately.
- Cost basis is reviewed or clearly retained as ROM planning language.
- Advanced-phase clearance-transition language is credible and bounded.
- Final DSIP upload preview is checked against the latest six-page render.
- The user gives fresh action-time approval for each upload, certification,
  consent, or submit action.
