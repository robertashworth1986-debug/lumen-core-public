# DOE FY26 Genesis Mission Phase I Pitch Packet

Generated UTC: `2026-07-29T19:37:29.234983Z`
Decision: **CONDITIONAL_FIT_NOT_YET_SUBMISSION_READY**
Status: `CONDITIONAL_TOPIC_FIT_R_AND_D_PROTOCOL_AND_FOUNDER_GATES_OPEN`

## Official Source Lock

- Opportunity: [DOE FY26 Phase I - Genesis Mission](https://sbir-sttr.connectwerx.org/portfolio-items/fy26genesismission/)
- Topic: `Achieving AI-Driven Autonomous Laboratories`
- Deadline: **September 10, 2026 at 2 PM ET**
- Application portal: `COMING_SOON`
- Route: pitch first; only invited applicants proceed to a full application.
- External action taken by this builder: `0`.

## Submission Constraints

- DOE accepts at most `3` pitches per company and reviews only the last three.
- Topic and prime small business cannot change between pitch and full application.
- Phase I is `6 to 12 months`, with a `$250,000` R&D cap or `$256,500` including maximum TABA.
- The optional references PDF must be print-capable, unencrypted, at most 5 MB, and use no special filename characters.
- Generative-AI use must be truthfully disclosed in the pitch and any invited full application.

## Fit Decision

The current stack supports evidence contracts, provenance, replay, adversarial testing, and fail-closed promotion. It does not yet establish laboratory integration or autonomous-lab performance.

The concept is an assurance layer for an autonomous experiment workflow, not a claim that LumenCore already operates a laboratory or controls physical instruments.

## Bounded Pitch Draft

### Summary, Topic, and Mission Alignment

Word count: `92 / 100`

LumenCore Autonomous Experiment Assurance Plane is proposed middleware between AI experiment planners and laboratory instruments. It would convert experiments into machine-checkable contracts defining authorized actions, parameter bounds, required data and provenance, stopping rules, and human approvals; block noncompliant commands before dispatch; and issue replayable evidence capsules linking plans, inputs, actions, outputs, deviations, and negative results. Phase I would test only instrument simulators and synthetic workflows; no laboratory deployment is claimed. The project addresses Achieving AI-Driven Autonomous Laboratories by targeting repeatability, safer closed-loop automation, and richer auditable datasets without replacing laboratory control systems.

### Technical Promise

Word count: `181 / 200`

Autonomous laboratories can accelerate discovery, but nondeterministic AI planners can change hypotheses, parameters, or stopping criteria mid-run, complicating repeatability and scientific review. Current workflow engines, experiment trackers, and policy tools address parts of this problem. The research question is whether an interoperable assurance layer can bind them into one enforceable experiment contract without unacceptable latency or false blocks. The proposed innovation is a policy-compiled contract that binds the hypothesis, design space, baselines, instrument capabilities, approval points, data schema, and falsification rules before execution. A runtime mediator would validate every action against that contract and generate an evidence capsule linking plans, commands, observations, model versions, deviations, and preserved null results. This is a proposed integration and control method, not a deployed laboratory capability. Within 6 to 12 months, Phase I would implement adapters for three instrument simulators; compare direct-agent, Bluesky/databroker, HELAO-async, and component baselines; and run normal, fault-injection, and adversarial scenarios. Feasibility would require predeclared gates for command containment, provenance completeness, deterministic decision replay, over-blocking, and overhead. Failure of any critical safety or reproducibility gate would be reported as a no-go.

### Commercialization Potential

Word count: `183 / 200`

Target users are autonomous-lab developers, DOE user facilities, and industrial materials or biotechnology R&D teams that need to govern AI-directed experiments without replacing installed orchestration. The proposed entry product is an assurance gateway and adapter kit, sold first through paid evaluations and then annual site or platform licenses. No customer, revenue, laboratory deployment, or procurement commitment is claimed. Alternatives include Bluesky/databroker, HELAO-async, LIMS and ELN systems, MLflow Tracking, Open Policy Agent, and custom safety interlocks. These address orchestration, records, model tracking, policy, or instrument safety. The proposed differentiation is a vendor-neutral, machine-enforced chain from predeclared scientific intent through command authorization to a replayable evidence capsule that retains deviations and null results. Phase I must demonstrate incremental value over named baselines, not merely repackage logging. Customer discovery would test procurement, integration, cybersecurity, data rights, and validation through 20 structured interviews. Phase II readiness targets are two authorized, nonbinding evaluation commitments and one instrument-integration plan. Supply-chain planning centers on signed dependencies, adapter maintenance, and on-premises packages; other barriers are sales cycles, authorization requirements, vendor APIs, liability, and resistance to middleware in safety-relevant paths.

### Team Qualifications

Word count: `184 / 200`

LumenCore's demonstrated starting point is local evidence-governance software: hashed source custody, frozen protocols, named-baseline evaluation, reproducible receipts, retained negative results, and human approval gates. The current repository supports software-pattern and source-conditioned replay claims only; it does not establish autonomous-laboratory experience, independent validation, or field deployment. A credible Phase I team needs four named functions: [PI/software assurance lead], [laboratory automation and controls lead], [scientific-domain experimentalist], and [commercialization/customer-discovery lead]. Before submission, replace every bracket with an authorized person, role, relevant project evidence, availability, and employment status. No partnership should be implied without consent. The plan should add an authorized simulator or equipment-vendor collaborator. A laboratory partner would strengthen the pitch but is not claimed here. SBIR workshare and PI-employment requirements must be checked against the final team, or the project should be structured truthfully as STTR with required research-institution participation. Follow-on funding is contingent: Phase II only after technical gates and DOE approval, followed by paid evaluations, strategic platform partnerships, and non-SBIR revenue. Insert only verified cash, runway, prior awards, commitments, and matching resources; otherwise state that no committed follow-on capital is presently claimed.

## Proposed Phase I Test

Scope: `SIMULATION_AND_FAULT_INJECTION_NO_LAB_DEPLOYMENT_CLAIM`

### Aims

- Compile experiment contracts that bind hypotheses, action bounds, models, approvals, stopping rules, data schemas, and falsification criteria across three simulator families.
- Intercept commands before dispatch and test faults, policy bypasses, stale state, altered plans, and missing observations while remaining subordinate to physical interlocks.
- Validate evidence capsules through blinded replay and compare trace completeness, reproducibility, diagnosis time, and overhead against frozen baseline versions.

### Named Baselines

- direct agent-to-simulator control with native JSON logs
- Bluesky RunEngine with Ophyd and databroker
- HELAO-async with native workflow and provenance handling
- MLflow Tracking plus Open Policy Agent component baseline
- no-assurance pass-through adapter and feature ablations

### Proposed Targets, Not Results

- contract compilation: `>=100 frozen contracts across three simulator families, >=95% valid compilation, and 100% seeded malformed or out-of-range plans rejected before dispatch`
- critical command containment: `0 critical unauthorized commands delivered in >=1,000 seeded trials, with a reported confidence bound and no zero-risk claim`
- valid-command admission: `>=97%, with Wilson 95% lower bound >=95%`
- critical provenance completeness: `100% of critical events bind plan, model, policy, instrument, input, and output identifiers`
- tamper detection: `100% of >=100 seeded record mutations detected`
- decision and trace replay: `100% authorization decisions reproduced from frozen inputs and >=95% complete traces reconstructed`
- runtime overhead: `p95 policy latency <=50 ms and median workflow overhead <=10% on declared non-hard-real-time simulators`
- diagnosis and market evidence: `>=30% lower median deviation-diagnosis time than the strongest baseline, 20 structured interviews, two authorized nonbinding evaluation commitments, and one instrument-integration plan`

Critical gate rule: Any critical containment, tamper-detection, or replay failure is a no-go and cannot be averaged away.

## Independent Red-Team Decision

Reviewer verdict: **BORDERLINE_NOT_INVITE_READY_TODAY**

Truthful position: `PRE_DISPATCH_EXPERIMENT_ASSURANCE_MIDDLEWARE_FOR_SIMULATED_WORKFLOWS`

Novelty hypothesis: A policy-compiled experiment contract can bind scientific intent, command authorization, model and instrument state, falsification rules, and replayable evidence before dispatch with measurable incremental value over established orchestration, tracking, and policy components.

### Rejection Triggers

- generic governance or compliance wrapper rather than experimental-workflow R&D
- post-hoc log inspection without pre-dispatch command mediation
- no measurable advantage over Bluesky, HELAO-async, MLflow plus OPA, or native interlocks
- no specific simulator family, instrument class, experimental domain, or hazard model
- software safety wording that displaces physical interlocks, ES&H controls, or operator authority
- blocking every command to manufacture a perfect containment score
- repository benchmark counts presented as laboratory validation
- invented partnerships, deployments, customers, revenue, capital, or DOE experience
- unresolved PI employment, workshare, ownership, registration, or certification gates
- failure to disclose generative-AI assistance in an eventual submission
- accelerated-discovery claims without direct measurement

### Claims Not Supported Today

- autonomous laboratory operation
- laboratory instrument integration
- physical safety certification
- DOE deployment or endorsement
- independent field validation
- discovery acceleration
- customer adoption, savings, or revenue

## Current Evidence Boundary

- Registered families accounted for: `140`
- Concrete implementations: `35`
- Implementation gaps: `105`
- Current source-native promotion gates passed: `0`
- Prospective protocol: `FROZEN_AWAITING_FUTURE_OBSERVATIONS`
- These are governance and research-readiness facts, not autonomous-lab performance.

| Evidence | Level | Supports |
| --- | --- | --- |
| `build_week/prooflock_console/verify_receipt.py` | `BOUNDED_SOFTWARE_IMPLEMENTATION` | deterministic receipt verification and separation of integrity from promotion |
| `tests/test_prooflock_console.py` | `LOCAL_SOFTWARE_TEST` | adversarial tests for tampering, path traversal, missing evidence, and premature promotion |
| `out/ops/source_native_family_baseline_ledger_latest.json` | `LOCAL_RESEARCH_LEDGER` | source-native baseline accounting and claim suppression |
| `out/ops/time_series_source_native_prospective_protocol_status.json` | `LOCAL_PROTOCOL_RECEIPT` | frozen prospective protocol and wait-for-future-data state |
| `docs/ALPHA_EDGE_EVIDENCE_AUDIT_2026-07-29.md` | `LOCAL_SKEPTICAL_AUDIT` | preservation and classification of negative results |
| `docs/FULL_GEOMETRY_PROTOCOL_FIELD_2026-07-29.md` | `LOCAL_COVERAGE_AUDIT` | implemented-versus-unimplemented family accounting |
| `code/hardware/lumenshell_safety_state_machine.py` | `EXECUTABLE_SOFTWARE_REQUIREMENTS_MODEL` | software-only fail-closed state and fault-lockout patterns; no physical safety case |
| `tests/test_autonomous_agent_manifest_security.py` | `LOCAL_SOFTWARE_TEST` | local tests for authorization, payload filtering, and human-controlled action gates |

## Open Gates

- **small_business_eligibility** - `FOUNDER_CONFIRMATION_REQUIRED`: U.S. for-profit small business, no more than 500 employees, and qualifying 51% ownership and control
- **domestic_research** - `FOUNDER_CONFIRMATION_REQUIRED`: all proposed research and development performed in the U.S.
- **principal_investigator** - `FOUNDER_CONFIRMATION_REQUIRED`: named PI, relevant qualifications, and primary-employment commitment at the small business if awarded
- **registrations** - `DIRECT_PORTAL_EVIDENCE_REQUIRED`: active SAM/UEI, SBA Company Registry, and DOE SBIR/STTR Application Hub registration
- **laboratory_domain_credibility** - `PARTNER_OR_ADVISOR_EVIDENCE_REQUIRED`: direct experimental-workflow expertise or a bounded plan to secure it before a full application
- **commercialization_and_financials** - `FOUNDER_REVIEW_REQUIRED`: truthful customer-discovery plan, pricing hypothesis, follow-on funding plan, and no invented traction
- **generative_ai_disclosure** - `TRUTHFUL_DISCLOSURE_REQUIRED`: state the extent and use of generative AI in developing both the pitch and any invited full application
- **action_time_review** - `HUMAN_REVIEW_REQUIRED`: final portal text, bibliography, company facts, certifications, and submit action reviewed at action time

## Candidate References

- [Bluesky simulated hardware tutorial](https://blueskyproject.io/tutorials/Hello%20Bluesky.html) - candidate simulation and orchestration baseline; no relationship claimed.
- [Bluesky plan simulation documentation](https://blueskyproject.io/bluesky/main/simulation.html) - candidate pre-execution inspection baseline; no relationship claimed.
- [HELAO autonomous laboratory framework](https://pubs.rsc.org/en/content/articlehtml/2023/dd/d3dd00166k) - candidate distributed-instrument orchestration baseline; no relationship claimed.
- [NIST modular and autonomous laboratory ecosystem](https://www.nist.gov/programs-projects/development-standards-support-modular-and-autonomous-laboratory-ecosystem) - standards landscape and prior-system boundary; no relationship claimed.
- [NREL autonomous experimentation](https://www.nrel.gov/materials-science/autonomous-experimentation) - application context and customer-discovery reference; no relationship claimed.

## Claim Boundary

This packet is a source-bound R&D pitch draft. It does not establish DOE eligibility, invitation, laboratory integration, autonomous-lab performance, adoption, savings, field validation, award, or authority to sign in, certify, upload, or submit.

## Safest Next Action

Resolve the company, PI, registration, laboratory-domain, and commercialization facts; then red-team the bounded pitch before the AMP portal opens.

Control SHA-256: `77EB8FB975AF8B32DB830091D1838FDBE380894F0391DA381B4D37ECA91623DA`
