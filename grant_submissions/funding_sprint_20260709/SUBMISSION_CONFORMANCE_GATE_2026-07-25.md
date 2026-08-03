# Submission Conformance Gate

As of UTC: `2026-07-29T21:24:51.841554Z`

Require a source-bound objective, novelty, baseline, metric, experiment, evidence-applicability, execution, and independent-red-team trace before any technical submission can be called reviewer-ready.

No technical submission is reviewer-ready unless every required criterion passes against cited source artifacts and a separate red-team receipt also passes. File presence, hashes, formatting, and self-authored reviewer notes cannot substitute for this argument gate. Human action-time approval remains mandatory after a technical pass.

## Status

- Status: `SUBMISSION_CONFORMANCE_BLOCKED`
- Current lane universe: `22`
- Current traction federal/IP lanes: `15`
- Registry lanes: `22`
- Missing current lanes: `0`
- Active submission candidates: `3`
- Active argument passes: `0`
- Active argument blocks: `3`
- Closed official decisions: `1`
- Expired without verified submission: `1`
- Technical no-go lanes: `1`
- Final submission without human: `false`
- Gate SHA-256: `0bb3a4bf1895565613410b3cbe5f479aaca6db958bbe8d9f3eb4320ddaa0c8c5`

## Lane Gates

### sam_registration_external_validation_watch

- Name: SAM.gov registration external validation watch
- Disposition: `NO_SUBMISSION_ROUTE`
- Status: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Keep registration state separate from technical proposal readiness.
- Boundary: Submitted or locally recorded registration data does not establish active award eligibility.

### lanl_vision_licensing_followup

- Name: LANL VISION licensing opportunity follow-up
- Disposition: `MONITOR_ONLY_ALREADY_SENT`
- Status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: At action time, recheck the complete package thread. If no reply remains, obtain exact single-use approval for the hash-bound zero-attachment follow-up; otherwise monitor and do not duplicate.
- Boundary: No LANL license, partnership, endorsement, or technical validation is established.

### uspto_georgia_patents_route

- Name: USPTO and Georgia PATENTS pro bono routing
- Disposition: `NO_SUBMISSION_ROUTE`
- Status: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Use a current counsel or official patent-services route only when new evidence exists.
- Boundary: Routing history does not establish representation, filing status, patentability, ownership, scope, or freedom to operate.

### darpa_dice_full_submission

- Name: DARPA DICE abstract and full-proposal route
- Disposition: `CLOSED_OFFICIAL_DECISION`
- Status: `CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `2`, partial `3`, fail `5`, unassessed `0`
- Separate red-team receipt pass: `false`
- Next action: Do not reply or prepare a full proposal under this route. Reuse only generalized lessons in future opportunity screening.
- Boundary: The postmortem explains process weaknesses and does not claim access to unstated reviewer reasoning.

Criteria:
- `official_source_current` state=`PASS` passed=`true` - The controlling BAA and required abstract template were retained locally before submission.
- `mandatory_format_and_route` state=`PASS` passed=`true` - The package followed the required section structure and received a BAAT receipt; the official decision did not identify it as nonconforming.
- `program_objective_trace` state=`FAIL` passed=`false` - The abstract discussed TA1 and TA2 topics but no submission-blocking crosswalk proved complete answers to every research question and program objective.
- `foundational_leap` state=`FAIL` passed=`false` - The coupling of sparse task markets, reputation, and local control was not differentiated as a new scientific principle strongly enough to survive comprehensive review.
- `named_sota_baseline` state=`FAIL` passed=`false` - The abstract used a generic centralized assignment baseline rather than a named current state-of-the-art multi-agent orchestration implementation matched to the proposed mission.
- `program_metric_trace` state=`PARTIAL` passed=`false` - Agent scale, message counts, recovery, and role-coherence proxies were named, but formal role-coherence, cognitive-agility, long-horizon, and TA1-usable guarantee metrics were incomplete.
- `mission_specific_experiment` state=`FAIL` passed=`false` - The experiment used generic stochastic tasks instead of one concrete contested mission with distributed evidence, role dependencies, mission success criteria, and a matched SOTA baseline.
- `evidence_applicability` state=`PARTIAL` passed=`false` - The abstract honestly bounded its synthetic task-executor evidence, but that evidence did not exercise inference-time control of heterogeneous foundation-model agents.
- `team_compute_execution` state=`FAIL` passed=`false` - The package disclosed a one-person organization, unnamed future collaborators, and insufficient local compute without binding commitments that demonstrated execution capacity.
- `risk_transition_and_falsifier` state=`PARTIAL` passed=`false` - Important risks and phase tests were named, but the package did not bind each core claim to a quantitative falsifier and transition owner.

### fhwa_tsmo_data_initiative

- Name: FHWA TSMO Data Initiative
- Disposition: `NO_SUBMISSION_ROUTE`
- Status: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Do not revive or duplicate the closed Cambridge route. Reopen only after a different qualified organization provides a written role and current official scope.
- Boundary: The closed referral is not a contract route, teaming commitment, agency endorsement, technical selection, or permission to submit.

### nasa_data_center_rfi

- Name: NASA Data Center Infrastructure RFI
- Disposition: `MONITOR_ONLY_ALREADY_SENT`
- Status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Monitor for a specific clarification or replacement request; apply the full gate before any revised package.
- Boundary: A sent RFI response is market-research participation, not an award, endorsement, or validated capability.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### cdc_ai_acquisition_rfi

- Name: CDC AI for Acquisition Support RFI
- Disposition: `MONITOR_ONLY_ALREADY_SENT`
- Status: `MONITOR_ONLY_NO_DUPLICATE_SUBMISSION`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Monitor for a specific clarification, replacement request, or scheduling message and do not resend the packet.
- Boundary: A receipt acknowledgment is not an award, endorsement, technical validation, or agency selection.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### dla_missionweave_sbir

- Name: DLA MissionWeave DSIP SBIR
- Disposition: `EXPIRED_NO_VERIFIED_SUBMISSION`
- Status: `EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Archive this route as expired without verified submission. Reuse only generalized, non-sensitive material after a fresh solicitation and full conformance audit.
- Boundary: Local packet work does not establish a DSIP submission, receipt, eligibility, JCP status, CMMC status, technical merit, award, or agency consideration.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### nsf_project_pitch

- Name: NSF SBIR and STTR Project Pitch
- Disposition: `ACTIVE_SUBMISSION_CANDIDATE`
- Status: `BLOCKED_UNASSESSED_CRITERIA`
- Active candidate: `true`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Refresh the official NSF source and build a criterion crosswalk before calling the pitch reviewer-ready.
- Boundary: A local pitch draft does not establish current eligibility, invitation, submission availability, or selection.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### erdc_sovereign_cloud_cso

- Name: ERDC Sovereign Defense Cloud CSO
- Disposition: `ACTIVE_SUBMISSION_CANDIDATE`
- Status: `BLOCKED_CRITERION_FAILURE`
- Active candidate: `true`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `3`, partial `7`, fail `0`, unassessed `0`
- Separate red-team receipt pass: `false`
- Next action: Publish the reviewed exact evidence files, bind a trust root outside the mutable receipt, have ERDC or an approved reviewer select the integrated comparator and HPCMP-representative workflow, lock mission and overhead thresholds, bind team, compute, integration, support, evaluator, and transition commitments, obtain independent execution, then separately complete the private ROM, SAM all-awards, contact, Submittable, and final portal gates.
- Boundary: Current-source custody, format and marker checks, a local synthetic ablation, and an explicit objective crosswalk do not establish applicant eligibility, reviewer readiness, public reproducibility, pricing, SAM readiness, technical merit, independent validation, selection, award, deployment, savings, or Government validation.

Criteria:
- `official_source_current` state=`PASS` passed=`true` - The current-source manifest and custody receipt bind the controlling CSO, July 20 FAQ, extracted text, and a hashed July 29 live-page snapshot. The compliance gate preserves the current commercial-solution deadline plus the original PDF text.
- `mandatory_format_and_route` state=`PASS` passed=`true` - The public draft has five counted body pages plus an excluded cover and acronym list, uses letter portrait format, one-inch margins, 12-point Times New Roman, physical and body page labels, a PDF under 20 MB, and the ERDCWERX portal route.
- `program_objective_trace` state=`PASS` passed=`true` - The brief makes Unified Service Layer and Vendor Lock-In Prevention the primary scope and treats AI-Powered Orchestration evidence and Secure Data Fabric metadata as integration boundaries. The CSO permits a solution to address one or more focus areas.
- `foundational_leap` state=`PARTIAL` passed=`false` - The brief defines a local mechanism and binds no-chain, no-predeclaration, and no-failure-retention ablations. OpenTelemetry 1.59.0 and SLSA 1.2/in-toto v1 are unranked interoperability contexts and are not scored. The result remains a local synthetic full-versus-ablation experiment, not evidence against a current integrated Government or commercial control plane.
- `named_sota_baseline` state=`PARTIAL` passed=`false` - The brief names OpenTelemetry Logs Data Model 1.59.0 and SLSA Build Provenance 1.2 with in-toto Statement v1 as complementary context only. The local protocol does not score or attack them and does not represent either standard as an equivalent evidence-control product or Government-selected incumbent.
- `program_metric_trace` state=`PARTIAL` passed=`false` - The brief now requires complete declared-attack detection, complete adverse-case retention, clean reviewer replay, and fixed-window measurement of bytes per event, capture and verify latency, storage per day, operator-review minutes, and egress bytes. Current baseline values and Government-approved workload and overhead thresholds remain unlocked.
- `mission_specific_experiment` state=`PARTIAL` passed=`false` - The brief proposes a sixteen-week unclassified prototype with two replaceable adapters, two approved environments, shadow replay, Government-run verification, explicit stop rules, and a local 48-workflow precursor. The actual HPCMP workflow, interfaces, data, workload scale, selected comparator, and Government thresholds remain unlocked.
- `evidence_applicability` state=`PARTIAL` passed=`false` - The bound local version-two ablation supports inspectable tamper detection, predeclaration, adverse-result retention, synthetic artifact-byte rehashing, adaptive re-chain attacks, and explicit negative controls relative to a separately supplied local anchor. The exact July 29 evidence is not yet represented as published in the public repository, and it does not exercise an HPCMP environment, SDC integration, classified boundary, Government workload, external trust root, or independent evaluator.
- `team_compute_execution` state=`PARTIAL` passed=`false` - The brief identifies the founder as proposed technical lead and bounds local surrogate development to contractor-furnished commodity CPU, storage, and open software. It explicitly leaves Government or prime integration, evaluator commitment, production HPC or cloud access, staffing, support, transition ownership, and the execution budget uncommitted.
- `risk_transition_and_falsifier` state=`PARTIAL` passed=`false` - The brief now binds the controlled experiment to stop and roll back on any declared attack miss, adverse-case omission, verifier mismatch, or Government-set overhead breach. The Government overhead threshold, transition owner, authorized interface owner, and security-boundary transition remain uncommitted.

### darpa_falcon_dpa26bz04_dv016

- Name: DARPA FALCON Direct to Phase II
- Disposition: `BLOCKED_TECHNICAL_NO_GO`
- Status: `TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Continue only the frozen evidence sprint. Do not assemble or submit a proposal unless the technical, source, DP2 eligibility, IP, team, compute, transition, and independent-review gates all close before the official deadline.
- Boundary: No hybrid superiority, external validation, agency approval, enterprise-scale performance, universal superiority, scholarly impact, or DP2 eligibility is established.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### launchtn_3686_pitch_2026

- Name: Launch Tennessee 3686 Pitch Competition 2026
- Disposition: `ACTIVE_SUBMISSION_CANDIDATE`
- Status: `BLOCKED_UNASSESSED_CRITERIA`
- Active candidate: `true`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Recheck the first-party application source, resolve applicant facts and terms, and complete the full source-bound pitch argument and independent review before portal finalization.
- Boundary: A local application packet does not establish current eligibility, submission, receipt, finalist status, prize eligibility, funding, selection, investment, award, endorsement, or permission to disclose nonpublic information.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### microsoft_for_startups_no_referral_2026

- Name: Microsoft for Startups no-referral path
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `NON_SUBMISSION_ROUTE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Resolve applicant facts and billing guardrails before any founder-only account or application action.
- Boundary: The public route does not establish eligibility, application, approval, credits, partnership, investment, funding, endorsement, or technical validation.

### aws_activate_founders_2026

- Name: AWS Activate Founders package
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `NON_SUBMISSION_ROUTE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Resolve applicant facts, prior-credit history, terms, eligible services, expiration, and post-credit spending controls before any founder-only application action.
- Boundary: The public route does not establish eligibility, application, approval, credits, partnership, investment, funding, endorsement, or technical validation.

### nvidia_inception_2026

- Name: NVIDIA Inception
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `NON_SUBMISSION_ROUTE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Resolve applicant facts and review current terms before any founder-only application or disclosure action.
- Boundary: The public route does not establish eligibility, application, membership, benefit availability, cloud credits, investor introduction, funding, endorsement, or technical validation.

### epa_r10_icpoes_route

- Name: EPA Region 10 ICP-OES RFI route
- Disposition: `NO_SUBMISSION_ROUTE`
- Status: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Do not promote to a technical submission without a new official fit signal.
- Boundary: Routing research is not technical fit, eligibility, or an agency request.

### epa_ucmr6_partner_only

- Name: EPA UCMR 6 analytical chemistry lab services
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Require a qualified laboratory lead and a current official scope before any package assembly.
- Boundary: LumenCore does not claim laboratory qualification, analytical certification, or prime eligibility.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### fhwa_infrastructure_baa_call3

- Name: FHWA Infrastructure R&D BAA Call 3.0
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Select and verify a current official topic before drafting or conformance scoring.
- Boundary: Topic similarity does not establish scope fit, eligibility, or submission readiness.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### hhs_ai_power_user_pilot

- Name: HHS AI Power User Advanced Models and Features Pilot
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Require a qualified prime or agency invitation before technical package work.
- Boundary: No prime eligibility, agency invitation, or pilot commitment is established.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### csosa_public_safety_analytics

- Name: CSOSA Public Safety Data Analytics Platform
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Require a qualified prime, controlled-data boundary, and current official request.
- Boundary: No public-safety deployment, controlled-data authority, or prime eligibility is established.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### defense_energy_consortium

- Name: Defense Energy Consortium CMO
- Disposition: `PARTNER_OR_TOPIC_GATE`
- Status: `BLOCKED_BEFORE_SUBMISSION_CANDIDATE`
- Active candidate: `false`
- Argument required: `true`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Wait for a concrete consortium problem statement or teaming request before a technical submission.
- Boundary: Membership or an introduction does not establish a funded project, consortium endorsement, or award route.

Criteria:
- `official_source_current` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mandatory_format_and_route` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_objective_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `foundational_leap` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `named_sota_baseline` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `program_metric_trace` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `mission_specific_experiment` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `evidence_applicability` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `team_compute_execution` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.
- `risk_transition_and_falsifier` state=`UNASSESSED` passed=`false` - No source-bound assessment is registered.

### patent_deadline_counsel

- Name: Patent counsel and IP deadline defense
- Disposition: `NO_SUBMISSION_ROUTE`
- Status: `NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE`
- Active candidate: `false`
- Argument required: `false`
- Argument pass: `false`
- Criteria: pass `0`, partial `0`, fail `0`, unassessed `10`
- Separate red-team receipt pass: `false`
- Next action: Use current official records and licensed counsel before any filing, deadline, ownership, or scope statement.
- Boundary: Repository artifacts do not establish filing status, legal deadlines, patentability, ownership, scope, infringement, or freedom to operate.
