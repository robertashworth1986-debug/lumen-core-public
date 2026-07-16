# HarborSentinel Volume 2 Technical Volume

Topic: DON26BZ03-NV063, Anomalous Behavior Detection and Alerting for Congested Maritime Environments

Program: Department of the Navy SBIR 2026 Release 3 Phase I

Proposal title: HarborSentinel: Explainable Low-Storage Pattern-of-Life Analysis for Congested Maritime Environments

Status: Review candidate. Remove the draft control only after the DSIP cover sheet, cost volume, firm forms, compliance representations, and final portal preview are complete.

## 1.0 Description of Proposed Phase I Technical Effort

### Navy need and technical objective

Ship Self-Defense System watch teams may need to review dense surface and air traffic across changing maritime operating areas. Cooperative Automatic Identification System (AIS) and Automatic Dependent Surveillance-Broadcast (ADS-B) observations can help establish context, but cooperative transmissions may be incomplete, delayed, inconsistent, or intentionally disabled. Notional radar and composite-track observations add coverage but introduce different uncertainty and source-quality conditions. The Navy topic therefore calls for an automated pattern-of-life method that examines traffic around a notional ship, identifies anomalous contacts or conditions, explains its reasoning and confidence, limits historical-storage demand, and provides a path toward Ship Self-Defense System (SSDS) integration.

HarborSentinel will assess whether compact, source-aware state can support this mission without retaining a massive region-specific archive. The concept maintains bounded statistics for each track and local traffic regime at multiple time scales. It evaluates route deviation, speed and acceleration changes, turn behavior, stop or loiter behavior, air-track climb, descent, or orbit behavior, source loss, and disagreement among cooperative and notional radar-like observations. Fast references identify abrupt changes; slower references characterize persistent local behavior; operator-pinned constraints prevent an adaptive baseline from silently normalizing selected behavior.

The system is advisory. It does not autonomously determine hostile intent or authorize an operational action. A disabled AIS or ADS-B transmitter is recorded as source-integrity evidence for review and is not treated as a behavior-based threat by itself. Each candidate alert will identify the track, anomaly category, supporting observations, source freshness, source disagreement, machine reasoning, confidence, uncertainty, plausible benign explanations, and the evidence identifiers needed to reconstruct the result.

### Technical innovation

The proposed innovation is the combination of:

- bounded per-track and local-regime state that supports low-storage operation across changing regions;
- explicit separation of source-integrity review from behavior-based threat candidates;
- source-aware consistency checks across AIS, ADS-B, notional radar, and composite-track interfaces;
- adaptive multi-timescale references with operator-pinned constraints and poison-resistance tests;
- density-aware calibration, abstention, and review-queue limits; and
- audit-ready alert records that can be replayed from frozen inputs, thresholds, source metadata, code versions, and SHA-256 manifests.

This approach is different from treating transmitter silence as a threat label, retaining a large location-specific archive, or collapsing all sensor disagreement into one fused answer. HarborSentinel preserves disagreement and uncertainty so the operator can see why the system raised, withheld, or downgraded an alert.

### Architecture and data boundary

Phase I will define an unclassified input and output contract for AIS observations, ADS-B observations used under documented rights, generated or Government-authorized notional air and surface radar contacts, composite tracks, ship position, local traffic context, and operator-pinned watch conditions. Adapters will normalize time, position, speed, heading, altitude where applicable, identity fields, observation quality or covariance, source freshness, and original observation identifiers.

The processing path contains five bounded stages:

1. Source adapters validate schema, time order, freshness, and use rights.
2. Track-state logic maintains compact multi-timescale features and source-health state.
3. Candidate detectors evaluate route, kinematic, loiter, silence, disagreement, and density-regime conditions.
4. A decision layer calibrates confidence, preserves competing explanations, and abstains or reduces confidence outside the validated envelope.
5. An evidence layer emits the operator alert object, replay inputs, configuration, software version, result, limitation, and artifact-chain hash.

Phase I does not claim access to Navy radar, classified sensor data, tactical SSDS software, operational watch-floor data, or Government-furnished interfaces. The deliverable is an unclassified prototype, message and interface-control concept, representative-data evaluation, storage and latency profile, and Phase II transition plan.

### Existing feasibility evidence and boundary

Existing evidence is internal feasibility work, not field validation. A frozen generated multi-source run selected a threshold on development scenarios and held it fixed across validation and stress conditions modeling AIS-like, ADS-B-like, and notional radar-like observations. It tested route deviation, loitering, speed burst, sharp turn, beacon silence, and beacon-spoofing-like inconsistency. The generated nominal condition reported precision 0.948, recall 0.957, and F1 0.952 against a simple fixed kinematic-rule comparator with F1 0.566. Generated combined and severe stress runs preserved rising review-alert burden and lower precision rather than hiding breakdown behavior.

A separate public-data lane used a frozen NOAA AIS New Orleans and Mississippi River Delta development and validation split. Full-file SHA-256 checks matched the frozen split manifest. A motion-consistency detector selected on development data was compared on 20,000 controlled validation perturbations against reported-speed-only and three single-axis baselines. It achieved recall 1.000 on those controlled perturbations, compared with 0.25835 for reported speed only and 0.5068 for the strongest single-axis comparator. On the unlabeled natural validation stream, the same candidate rule generated a 3.583 percent review queue, averaging 145.167 candidates per hour with a 95th-percentile hourly load of 158.7 before analyst caps.

These results support a Phase I hypothesis and a reproducible test harness. Controlled injections are not real adversary labels. The natural queue is not a false-positive rate. Public AIS does not validate ADS-B, Navy radar, composite tracks, SSDS displays, operational threat identification, cybersecurity, or field suitability. Phase I will test whether useful performance survives representative source conditions, density regimes, frozen acceptance gates, authorized data rights, and independent review.

## 1.1 Phase I Technical Objectives

Objective 1 - Freeze the unclassified architecture and evaluation contract. Define the input and alert schemas, source-rights register, anomaly taxonomy, reference baselines, density regimes, primary and guardrail metrics, acceptance thresholds, abstention rules, failure criteria, and development-validation partitions before final scoring.

Objective 2 - Implement replayable source adapters and compact state. Build AIS, ADS-B, notional radar, and composite-track interfaces that preserve source identity, freshness, uncertainty, and original observation references. Measure memory and storage growth by track count and traffic duration.

Objective 3 - Implement and calibrate explainable detection. Evaluate route, kinematic, loiter, silence, disagreement, and density-aware methods. Test adaptive-baseline poisoning, delayed observations, identity conflict, benign transmitter dropout, noise shift, and operation outside the validated envelope.

Objective 4 - Build the operator alert and SSDS transition concept. Produce an advisory alert object and notional display showing track number, descriptive details, anomaly category, source status, supporting observations, machine reasoning, confidence, uncertainty, competing benign explanations, operator disposition, and linkage to the tactical picture.

Objective 5 - Demonstrate bounded feasibility. Evaluate generated and representative public or authorized lanes with frozen thresholds. Report detection metrics only where labels or controlled cases support them; report review burden separately on unlabeled traffic. Measure delay, calibration, memory, storage, runtime, and latency by source and density regime.

Objective 6 - Deliver a Phase II readiness package. Provide prototype source, test harness, data and interface specifications, frozen manifests, negative-result and failure register, SSDS integration concept, and a bounded plan for CMMC, SPRS, export control, facility and personnel clearances, classified work, and Government-authorized evaluation.

## 1.2 Phase I Base and Option Statement of Work

### Phase I Base, months 1-6, not to exceed $200,000

Task 1 - Requirements and evaluation plan, Month 1. Review topic requirements and freeze the unclassified message boundary, source-rights register, anomaly taxonomy, comparison baselines, metrics, acceptance and abstention rules, failure conditions, and development-validation partitions. Deliver the evaluation protocol and architecture contract.

Task 2 - Source adapters and compact state, Months 1-2. Implement replayable AIS, authorized ADS-B, notional radar, and composite-track interfaces. Implement bounded multi-timescale track state, source freshness, source quality, traffic-density context, and observation identifiers. Deliver adapter tests, schema records, and storage-growth measurements.

Task 3 - Detection, calibration, and degraded-source controls, Months 2-4. Implement route, kinematic, loiter, silence, source-disagreement, and density-regime methods. Test delayed and missing observations, identity conflict, benign dropout, noise shift, and adaptive-reference poisoning. Deliver candidate methods, calibration records, and failure tests.

Task 4 - Operator alert prototype, Months 3-4. Build the advisory alert object and notional display concept. Preserve the reason, evidence, source status, confidence, uncertainty, competing explanations, and human disposition. Deliver a message schema, sample alerts, and interface-control concept.

Task 5 - Feasibility evaluation, Months 4-5. Execute frozen generated and representative-data evaluations without changing thresholds after validation is opened. Report class-level detection metrics where supported; review burden on unlabeled traffic; delay; calibration; memory; storage; runtime; latency; and behavior under congestion, source loss, and noise shift. Deliver a hash-manifested result package and negative-result register.

Task 6 - Demonstration and transition package, Month 6. Demonstrate deterministic replay from approved inputs. Deliver prototype source, test harness, source and rights register, architecture, alert schema, evidence manifest, failure register, and Phase II SSDS, data, cyber, export, facility-clearance, personnel-clearance, and classified-work roadmap.

Base success means reproducible evidence that the prototype can process the declared unclassified lanes, maintain bounded state, emit explainable advisory alerts, preserve source uncertainty, and report performance and failure behavior under frozen conditions. It does not mean SSDS integration, classified sensor validation, operational threat classification, field readiness, or CMMC or clearance completion.

### Phase I Option, months 7-12, not to exceed $115,000

Task 7 - Representative-data connector hardening, Months 7-8. Expand lawful representative-data connectors, improve density and source-health calibration, and document data-rights and retention controls.

Task 8 - Composite-track and congestion hardening, Months 8-10. Refine source correlation, disagreement handling, bounded-state scaling, abstention, and analyst-cap policies under larger traffic loads and degraded sources.

Task 9 - Independent reproducibility and red-team review, Months 9-11. Provide a frozen packet to an independent technical reviewer, preserve reproduction failures, and test explicit threat and poisoning assumptions without converting modeled attacks into operational claims.

Task 10 - Phase II design package, Months 10-12. Mature the SSDS-facing message and display specification, latency and storage budgets, Government-data plan, cyber and export boundary, facility and personnel clearance plan, and prototype requirements for Phase II.

Option success means a reviewed Phase II design and evidence package that states what transferred, what failed, and what Government-authorized resources are required. The Option does not claim completion of SSDS integration or an operational prototype.

### Work location and performer

The work will be performed in the United States by Robert Ashworth d/b/a LumenCore. The small business will perform at least two-thirds of the research and analytical work in both the Base and Option as measured by direct and indirect cost. Any consultant or subcontractor will have a written, topic-specific scope and will not receive controlled or export-restricted information unless the applicable authorization and security boundary are in place.

No Phase I task requires human-subject research, animal testing, or recombinant DNA work. Operator-display evaluation will use software requirements and simulated or non-personally-identifiable review workflows unless the Government authorizes a later protocol.

## 1.3 Related Work

LumenCore has implemented source adapters, deterministic replay, baseline-versus-candidate evaluation, holdout controls, anomaly and regime-change methods, evidence manifests, and reviewer-facing proof records across multiple public-data domains. HarborSentinel-specific work includes a generated multi-source pattern-of-life feasibility suite, public NOAA AIS acquisition and frozen development-validation splits, full-file hash verification, controlled kinematic injection tests against named baselines, and an unlabeled review-burden profile.

This work was privately developed by the proposing small business and was not performed for a Navy customer. No Navy endorsement, operational access, classified work, Government-furnished data, SSDS integration, or field result is claimed. The Phase I effort will use this prior work only as a starting implementation and will judge the proposed concept against the official topic, stronger baselines, source-rights controls, representative traffic, declared metrics, and preserved failure cases.

Relevant open technical foundations include robust statistics, cumulative-sum change detection, multi-target tracking, maritime pattern-of-life analysis, uncertainty calibration, and human-machine decision support. Phase I will identify the state of the art and compare HarborSentinel to simple fixed rules, single-axis comparators, density-aware baselines, and other methods appropriate to each authorized lane. Planned outside coordination is limited to written, scoped domain or independent technical review after the reviewer, data rights, export, and information boundaries are approved.

## 2.0 Key Personnel

Robert Ashworth, Founder, Chief Scientist, and Principal Investigator, will provide scientific and technical direction and will perform architecture, implementation, evaluation, evidence packaging, and transition planning. He is a U.S. person and is expected to maintain primary employment with the small business during the effort. His relevant experience includes building heterogeneous data adapters, time-series and anomaly benchmarks, constrained routing and abstention logic, deterministic replay systems, SHA-256 evidence manifests, API and dashboard services, and bounded federal research packages.

No academic degree, publication, award, clearance, certification, customer result, or issued-patent claim is relied upon for evaluation unless separately verified in the final portal record. The proposal instead relies on the inspectable technical plan, existing code and frozen feasibility artifacts, and the Phase I acceptance gates.

The cost plan reserves bounded consultant support for maritime operations or tracking review, independent statistical or reproducibility review, and federal cybersecurity or transition planning. No consultant, subcontractor, letter, commitment, rate, or capability will be named in the final proposal without written permission and a reviewed scope. Foreign-person participation is not planned; the corporate official must confirm the final personnel facts in Volume 5 and Volume 7.

## 3.0 Commercialization and Transition Plan Summary

The Navy transition path is an SSDS-compatible advisory analysis service and operator alert interface evaluated first with unclassified representative data, then with Government-authorized data and integration environments. Phase I will produce the prototype, evidence package, message schema, interface-control concept, storage and latency profile, and security and clearance roadmap needed for a Government decision on Phase II.

Phase II would develop and evaluate a prototype for realistic 360-degree SSDS use cases using architecture information and authorized resources supplied or approved by the acquisition office. It would refine source interfaces, composite-track logic, operator displays, performance limits, and integration behavior. Any classified work would occur only after the required facility, personnel, information-system, export, cybersecurity, and contracting controls are in place. Phase III would focus on integration, qualification, and transition under Navy direction.

Commercial adjacencies include port and terminal security, commercial fleet operations, shipping and logistics, fisheries and environmental monitoring, event and perimeter security, maritime insurance analytics, and critical-infrastructure monitoring. The entry product is an evidence-bounded anomaly-review service or software component evaluated beside an incumbent workflow on customer-authorized historical data. The first commercial engagement would define the source rights, baseline, adjudication method, review-burden limit, latency and storage limits, acceptance rule, and human decision authority before any production claim.

LumenCore's differentiation is not a universal model claim. It is the combination of compact source-aware state, explainable and replayable alerts, explicit abstention and source-integrity handling, frozen candidate-versus-baseline evaluation, and a negative-result register. Commercial progress will be measured by paid evaluation scopes, lawful data access, independent reproduction, integration readiness, and customer acceptance criteria. No current Navy customer, pilot, revenue, field performance, or production deployment is claimed.

## 4.0 Facilities and Equipment

Phase I software development and unclassified evaluation will use company-controlled computing equipment and encrypted local storage located in the United States, plus approved commercial cloud or high-performance computing resources only when the data and solicitation boundary permit their use. Public data and generated data will remain separated from any future controlled Government data. Source files, development and validation partitions, configurations, code versions, logs, and result manifests will be retained under access controls appropriate to their sensitivity.

No specialized hardware purchase is required for the Base concept demonstration. Proposed software, storage, cloud, and small-equipment costs will be itemized in Volume 3 and supported in Volume 5 if required. The current ordinary software-development facility is not represented as a CUI enclave, classified facility, accredited system, or cleared facility. Phase I will produce the plan and cost implications for any future CMMC, SPRS, FCI, CUI, export-controlled, classified, Secret facility-clearance, or personnel-clearance requirement.

The proposed work is software research and does not anticipate airborne emissions, waterborne effluents, external radiation, hazardous-material handling, or unusual solid-waste activity beyond ordinary commercial computing. The corporate official must confirm that the final work locations and equipment comply with applicable Federal, state, and local environmental laws and regulations.

## 5.0 Letters of Support

No letter of support is included in this review candidate. A letter will be included only if it is current, topic-specific, signed by an authorized person, permits its use in this proposal, and fits inside the ten-page Volume 2 limit. The absence of a letter is not replaced with an unsupported partner, customer, Navy sponsor, transition commitment, or validation claim.
