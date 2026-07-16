# LumenCore Open Power AI Entry and AI for Power 2026 Packet

**Prepared:** July 16, 2026  
**Owner:** Robert Ashworth, Founder / Systems Architect, LumenCore  
**Posture:** Membership interest submitted; acceptance and program eligibility not yet confirmed

## Executive position

LumenCore should enter the Open Power AI Consortium through one narrow contribution: a reviewer-controlled proof-to-pilot protocol for evaluating utility AI and routing claims against a named baseline before deployment.

The protocol freezes the source, comparator, metric, threshold, evaluation window, code revision, dependencies, and output manifest before scoring. It retains positive, neutral, incomplete, and negative results. The deliverable is an offline-verifiable evidence packet and a bounded next-pilot decision, not a broad product claim.

## Current official signals

Public OPAI material currently describes a consortium connecting more than 300 organizations and offering collaboration around benchmarking, domain-specific models, data sharing, implementation, and use cases.

The public AI for Power 2026 page identifies prioritized utility AI use cases and describes paid demonstrations typically completed within 16 weeks. Its timeline lists application and evaluation in May/June 2026, Pitch Day on August 5, 2026, demonstration scoping and execution in Q4 2026 / Q1 2027, and a 2027 showcase.

The same public page still displays a `Submit Application` section. That creates a status ambiguity: the portal surface exists, but the published application window has elapsed. LumenCore must confirm the current technology-provider intake state with the program team instead of assuming that applications are either open or closed.

## Outreach guard

The official membership-interest request is already pending.

Until a response arrives:

- do not send another standalone membership request;
- do not contact working-group leads individually;
- use the existing EPRI/OPAI thread only;
- wait until the configured cooldown expires before one concise follow-up;
- immediately close the follow-up action if acceptance, decline, or onboarding instructions arrive.

The public-safe state is stored in `config/opai_entry_program.json`. The action engine converts it into a deadline-ranked queue and refuses to represent pending interest as accepted membership.

## First four technical entry lanes

### 1. AMI Data Validation

**Why it leads:** The work is fundamentally a validation problem. It fits LumenCore's strongest current capability: pre-registering the source, incumbent method, error metric, data-quality rules, acceptance threshold, run window, and evidence manifest.

**Required external gates:** utility-authorized AMI data or an agreed public proxy; privacy and data-rights boundaries; a named incumbent validator; locked error and review-burden metrics.

### 2. Grid Constraint Forecasting

**Why it fits:** The repository already contains a real-data fair-benchmark harness comparing naive, linear, harmonic, and machine-learning forecasts and generating tamper-evident outputs. That is internal evidence of benchmark mechanics, not proof of utility constraint forecasting.

**Required external gates:** a utility-selected target; held-out evaluation window; incumbent forecast; operationally meaningful threshold; no post-outcome tuning.

### 3. Grid Post-Storm Field Crew Deployment Optimization

**Why it fits:** This is the cleanest route for FlowForm geometry and routing. The first evaluation should be simulation-only and should compare FlowForm against a named dispatch baseline under crew, road, travel, safety, service-priority, and infeasibility constraints.

**Required external gates:** utility-owned or synthetic storm scenario; agreed constraints; baseline dispatcher; locked completion-time, coverage, travel, and violation metrics.

### 4. Grid Model Digital Twin Validation

**Why it fits:** LumenCore can package model-to-source consistency checks and exception reports while keeping human review and authority outside the system.

**Required external gates:** authoritative model and source records; mismatch taxonomy; locked precision, coverage, and review-burden metrics; human adjudication.

## Recommended first ask

> Please confirm whether LumenCore can still enter the AI for Power 2026 technology-provider process at this stage. If that window has closed, please route us to the appropriate OPAI working group or next challenge cycle for a bounded validation use case. Our proposed contribution is a reviewer-controlled replay protocol: named data, incumbent baseline, locked metric and threshold, held-out run, hash manifest, offline verifier, and explicit retention of failed or incomplete results.

This ask should remain in the existing thread. It should not be sent again before the outreach cooldown expires unless the onboarding team requests information.

## Thirty-day validation plan

### Days 0-3 — Route and choose

1. Receive membership/onboarding response.
2. Confirm whether AI for Power 2026 is still accepting technology providers.
3. Select one lane only.
4. Identify the consortium, utility, or working-group owner.
5. Record data-rights, disclosure, and IP boundaries.

### Days 4-7 — Pre-register

1. Name the source or dataset.
2. Name the incumbent or naive baseline.
3. Lock one primary metric and threshold.
4. Freeze the held-out window or simulation seeds.
5. Define failure, incomplete-run, and rejection rules.
6. Freeze the economic conversion rule separately, if one is used.

### Days 8-14 — Build the replay capsule

1. Create input and dependency manifests.
2. Generate SHA-256 hashes.
3. Run the baseline and candidate without post-outcome tuning.
4. Preserve logs, exceptions, constraint violations, and negative results.
5. Produce an offline verifier.

### Days 15-21 — Reviewer challenge

1. Give the reviewer the verifier before conclusions are strengthened.
2. Re-run on reviewer-owned or held-out data.
3. Record discrepancies between internal and reviewer results.
4. Keep measured, replay, synthetic, modeled, and estimated claims separate.

### Days 22-30 — Decision packet

1. Issue the bounded Proof Capsule.
2. State what the result proves and does not prove.
3. Report failure and limitation notes.
4. Record one of five decisions: promote, rerun, external review, hold, or reject.
5. Scope a paid demonstration only when the reviewer owns the acceptance contract.

## Minimum reviewer packet

The first packet should contain only:

- one-page company and founder overview;
- one-page use-case contract;
- source and rights label;
- named baseline;
- locked metric, threshold, window, and failure rules;
- code revision and dependency lock;
- input/output SHA-256 manifest;
- offline verifier instructions;
- positive, neutral, incomplete, and negative results;
- claim boundary and next-gate decision.

Do not send credentials, API keys, UEI/CAGE screenshots, private portal materials, customer identifiers, full private code, bank information, or unbounded patent details through a public or unverified channel.

## Automation included in this branch

`code/ops/build_opai_consortium_intelligence.py` performs the bounded public crawl.

`code/ops/build_opai_action_queue.py` converts the crawl plus the public-safe program state into:

- source-health status;
- membership cooldown status;
- AI for Power timeline urgency;
- ranked use-case fit;
- repository-evidence presence;
- open external gates;
- a hash-addressed action queue.

The action engine does not send emails, submit forms, submit applications, claim membership, or infer acceptance.

## Claim boundary

This packet records public program facts, internal preparation, and proposed evaluation methods. It does not prove accepted consortium membership, challenge eligibility, application acceptance, utility participation, a paid demonstration, funding, endorsement, field validation, savings, deployment, or customer adoption.

*Founder-owned. Evidence before claims. Bounded light speed.*
