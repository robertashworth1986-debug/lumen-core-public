# DICE Safety Boundary Memo v0.1

**Project:** LumenCore / DARPA DICE full-submission working packet  
**Abstract ID:** HR001126S0010-DICE-PA-052  
**Abstract Title:** Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives  
**Status:** Internal working draft only. Not a submission. Not legal advice. Not an export-control determination. Not a cybersecurity certification. Not a government representation or certification.

---

## 0. Purpose and Control Boundary

This memo defines the proposed research, safety, data, autonomy, evidence, and claim boundaries for the Coherence-Bounded Peer Mesh (CBPM) effort. Its purpose is to keep the technical volume, budget narrative, benchmark packet, transition plan, and portal package internally consistent and reviewer-auditable.

The final solicitation, official amendments, BAAT instructions, award instrument, security guidance, data-rights clauses, export-control requirements, cybersecurity requirements, and contracting officer direction control any final submission or performance obligation.

No proposal, certification, representation, data-rights assertion, security claim, export-control statement, or official filing may be submitted without explicit approval from Robert Ashworth / LumenCore and verification against the controlling government documents.

---

## 1. Safety Thesis

CBPM is proposed as a **bounded coordination, local-control, and evidence layer for controlled research evaluation of heterogeneous AI collectives**.

The effort is not proposed as unrestricted autonomy. Its safety thesis is:

> Decentralized AI collectives should not receive operational trust merely because they complete tasks. They should earn trust through explicit role boundaries, local uncertainty checks, limited tool permissions, challenge and abstention paths, failure containment, reproducible replay, and human approval gates for consequential actions.

The proposed system is designed to measure and constrain behavior before field deployment is considered.

---

## 2. Intended Research Scope

The initial effort is limited to controlled, reproducible, non-actuating research activities, including:

1. deterministic and stochastic simulation;
2. replay of synthetic, public, or properly authorized datasets;
3. software-only agent and policy evaluation;
4. sparse peer task-market experiments;
5. local inference-time role and uncertainty controls;
6. modeled failure, drift, compromise, collusion, and monitor-shift scenarios;
7. communication-cost and scalability analysis;
8. abstention, challenge, re-auction, isolation, and recovery experiments;
9. generation of logs, metrics, negative-result registers, and SHA-256 manifests;
10. controlled demonstrations in sandboxed environments with no authority over real-world systems.

The research objective is to identify capability limits, failure envelopes, and measurable tradeoffs. It is not to manufacture an all-win result.

---

## 3. Explicitly Out-of-Scope Activities

Unless later authorized through a separately reviewed scope, compliant environment, and explicit written approval, CBPM will not be used for:

- autonomous weapons, targeting, engagement, or fire-control decisions;
- physical actuation of aircraft, vehicles, robots, industrial equipment, energy systems, medical devices, or critical infrastructure;
- autonomous cyber operations against external systems;
- unsupervised access to production government networks;
- processing classified information;
- processing CUI or FCI in an environment not confirmed appropriate for that data;
- autonomous financial trading or movement of funds;
- biometric identification, surveillance, or tracking of real individuals;
- law-enforcement, detention, sentencing, immigration, benefits, employment, housing, medical, or other high-impact eligibility decisions;
- self-modifying deployment that expands permissions without human authorization;
- concealment of agent identity, action provenance, limitations, or known failures;
- claims of certification, operational readiness, adversarial security, or guaranteed mission improvement based only on simulation.

These exclusions are proposal-development boundaries, not statements about what a future government-directed program may or may not authorize.

---

## 4. Non-Actuating Default

The default CBPM implementation mode shall be **observe, score, recommend, log, and abstain**.

A research node may:

- receive a simulated task;
- advertise bounded capabilities;
- bid or abstain;
- produce a recommendation or simulated action;
- challenge a peer commitment;
- request clarification;
- reduce its own simulated authority;
- trigger re-auction;
- isolate or discount a simulated peer;
- route a case to human review;
- record evidence.

A research node shall not directly execute consequential external actions under the proposed initial scope.

---

## 5. Human Authority and Approval Gates

Human review is required whenever a proposed action crosses a defined consequence, uncertainty, permission, or data boundary.

### 5.1 Approval Ladder

| Lane | Example activity | Default handling |
|---|---|---|
| Green | simulation step, metric calculation, log generation, benchmark replay | may execute automatically inside sandbox |
| Yellow | external API call, use of non-public but authorized data, change to benchmark contract, expanded tool permission | explicit project-level approval required |
| Red | physical actuation, weapons-related use, production network access, CUI/classified handling, financial transfer, legal/government certification | prohibited under initial scope without separate written authorization and compliance review |

### 5.2 Human Override

The research harness should support:

- pause;
- stop;
- deny;
- revoke node permissions;
- quarantine a node;
- preserve current state;
- export a decision trace;
- restart from a known seed or checkpoint.

Human override events must be logged with timestamp, actor, reason, affected node/task, and resulting state.

---

## 6. Local Inference-Control Boundary

Each node should evaluate a proposed action against a local control record containing, at minimum:

- assigned role;
- permitted task classes;
- prohibited task classes;
- tool permissions;
- data-access permissions;
- current confidence or uncertainty;
- context freshness;
- coherence or role-drift score;
- peer-reputation observations;
- consequence class;
- human-review requirement;
- maximum commitment duration;
- recovery and abstention conditions.

The controller does not guarantee correctness or safety. It creates a measurable decision boundary that can be evaluated and audited.

### 6.1 Required Response Options

A node should be able to select among:

1. proceed in sandbox;
2. proceed with reduced authority;
3. request clarification;
4. challenge peer evidence;
5. abstain;
6. re-auction the task;
7. isolate or discount a peer;
8. escalate to human review;
9. terminate the local task.

A forced binary “act or fail” design should be avoided because it hides uncertainty and increases unsafe completion pressure.

---

## 7. Tool-Permission Boundary

Tools should be granted according to least privilege and task necessity.

For every tool or interface, the benchmark configuration should record:

- tool name and version;
- read/write capability;
- permitted inputs;
- prohibited inputs;
- network reachability;
- credential source;
- allowed data classes;
- rate or cost limit;
- timeout;
- human approval requirement;
- revocation condition.

Secrets, passwords, tokens, API keys, account-recovery codes, and private credentials must not be embedded in source files, logs, screenshots, reports, evidence manifests, or public repositories.

---

## 8. Data Handling Boundary

### 8.1 Default Data Classes

The initial benchmark packet should use only:

- synthetic data;
- generated task graphs;
- public datasets with documented provenance and permitted use;
- non-sensitive internal test data explicitly approved for the benchmark.

### 8.2 Restricted Data

The following should not enter the initial public or development evidence pipeline:

- classified data;
- CUI unless the required environment and authorization are confirmed;
- personally identifiable information not necessary for the research;
- protected health information;
- export-controlled technical data without a reviewed authorization path;
- proprietary third-party data without documented permission;
- secrets or credentials;
- live operational data whose release or use could create security, privacy, contractual, or safety risk.

### 8.3 Dataset Record

Each dataset used in a frozen run should have a record containing:

- dataset name and version;
- source and acquisition date;
- license or permission basis;
- sensitivity classification used by the project;
- preprocessing steps;
- excluded fields;
- known limitations;
- checksum;
- approved use within the benchmark.

---

## 9. Security and Environment Boundary

The initial research environment should remain unclassified and non-operational unless official requirements and a compliant environment are confirmed.

Minimum internal controls should include:

- separate development and evidence-output directories;
- no secrets in repositories;
- dependency/version capture;
- deterministic seeds where technically appropriate;
- immutable or append-only run logs where practical;
- SHA-256 manifests for code, config, results, and reports;
- role-based access to non-public artifacts;
- explicit approval before external network access;
- documented backup and restoration procedure;
- incident and anomaly log;
- public/private artifact separation.

This memo does not assert that LumenCore currently satisfies any specific CMMC, NIST, FedRAMP, FISMA, facility-clearance, or information-system authorization level. Any such claim requires separate verification and evidence.

---

## 10. Benchmark Safety Contract

Before a result may be described as frozen evidence, the run contract should define:

1. hypothesis;
2. baseline systems;
3. CBPM variant;
4. scenario families;
5. seed policy;
6. agent count and interaction count;
7. compromise and collusion rates;
8. monitor-shift conditions;
9. metrics;
10. stopping criteria;
11. failure definitions;
12. false-rejection measurement;
13. communication/protocol cost;
14. excluded conditions;
15. claim language permitted by the result.

The benchmark must preserve unfavorable outcomes. Failed runs may be excluded only for documented technical reasons, and the exclusion count and reason must be reported.

---

## 11. Adversarial and Failure-Mode Boundary

The benchmark should treat the following as modeled test conditions, not proof of resistance to real adversaries:

- random node failure;
- stale context;
- role drift;
- contradictory commitments;
- compromised-agent behavior;
- colluding-agent clusters;
- reputation manipulation;
- message loss or delay;
- task-market concentration;
- monitor or evaluator shift;
- malicious or malformed tool output;
- high-compromise collapse conditions.

The proposal may claim only what the specific modeled condition and frozen evidence support.

Example safe wording:

> In controlled simulation under specified compromise and collusion parameters, the tested CBPM configuration produced the reported containment, recovery, completion, and communication-cost measurements relative to the named baselines.

Unsafe wording to avoid:

> CBPM is secure against compromised or colluding agents.

---

## 12. Safety Metrics

The evidence packet should report, at minimum:

- safe completion rate;
- constraint violation rate;
- false rejection rate;
- abstention rate;
- role-coherence length;
- compromised-agent propagation rate;
- collusion success/failure rate;
- recovery latency;
- re-auction frequency;
- isolation and challenge events;
- task-concentration index;
- selected-agent diversity;
- communication and protocol cost;
- human-escalation rate;
- evidence-manifest completeness;
- negative and anomalous run count.

A result should not be called safer solely because completion increased. Safety claims require joint reporting of completion, violations, false rejection, abstention, cost, concentration, and failure behavior.

---

## 13. Claim Boundary Matrix

| Evidence state | Permitted description | Prohibited leap |
|---|---|---|
| concept only | proposed architecture or hypothesis | demonstrated capability |
| implemented component | prototype component exists | integrated system proven |
| synthetic benchmark | measured simulation result under named conditions | operational or field performance |
| public-data replay | replay result on named public data | performance on government mission data |
| adversarial simulation | modeled compromise/collusion response | security against real adversaries |
| scalability test | measured behavior at tested scale | guaranteed scaling beyond tested range |
| hash manifest | artifact integrity record for included files | independent certification or truth guarantee |
| human-reviewed demo | bounded supervised demonstration | autonomous deployment readiness |
| transition discussion | identified potential pathway | customer commitment, contract, or deployment |

All proposal documents should use the same evidence-state vocabulary: **proposed, implemented, simulated, replayed, measured, frozen, independently reviewed, field-tested, certified**. The last three terms must not be used without supporting evidence.

---

## 14. Dual-Use and Misuse Boundary

Decentralized coordination and local inference control are dual-use technologies. Potential misuse includes increasing the scale, resilience, concealment, or autonomy of harmful agent collectives.

The proposed mitigation posture is to:

- keep initial work non-actuating;
- limit tools and permissions;
- preserve identity and provenance of agents;
- log commitments, challenges, and authority changes;
- maintain human review for consequential actions;
- evaluate compromise and collusion rather than assuming benign actors;
- expose collapse conditions and limitations;
- separate public evidence from sensitive implementation details when appropriate;
- require project-level approval for expanded capability or external deployment.

This memo should be revisited before any transition from simulation to a real operational environment.

---

## 15. Intellectual Property and Data-Rights Boundary

The proposal package should distinguish:

1. pre-existing LumenCore background IP;
2. proposed DICE-specific development;
3. third-party and open-source components;
4. government-funded deliverables;
5. public evidence artifacts;
6. non-public source code, data, or know-how.

Before submission, prepare an itemized data-rights assertion table using the official required format, if applicable. Do not promise open-source release, unlimited rights, government-purpose rights, restricted rights, or proprietary treatment until the official clauses and intended deliverables are reviewed.

Repository publication does not automatically resolve ownership, licensing, patent, or government-data-rights questions.

---

## 16. Incident and Anomaly Response

A safety-relevant incident includes:

- unexpected external action;
- tool use outside permission;
- secret or restricted-data exposure;
- unexplained benchmark result change;
- missing or altered evidence artifact;
- agent permission escalation;
- monitor failure;
- unbounded message growth;
- repeated constraint violations;
- unexplained all-win result;
- compromised reproducibility.

Recommended response sequence:

1. stop or isolate the affected run;
2. preserve logs and state;
3. revoke relevant permissions or credentials;
4. record time, actor, configuration, and affected artifacts;
5. reproduce in an isolated environment if safe;
6. determine whether any evidence or claim must be withdrawn;
7. update the failure register and mitigation plan;
8. obtain approval before resuming the affected capability.

---

## 17. Transition Boundary

Transition should proceed in stages:

### Stage 0 — Controlled simulation

Synthetic agents, fixed benchmarks, no external actuation.

### Stage 1 — Authorized replay

Public or approved data, sandboxed tools, reviewer-visible logs.

### Stage 2 — Shadow evaluation

Observe a real workflow without controlling it; compare recommendations with actual or human-approved outcomes.

### Stage 3 — Human-gated pilot

Limited environment, narrow task class, explicit permissions, operator approval for consequential steps.

### Stage 4 — Operational consideration

Only after independent evaluation, security and data review, clearly assigned authority, rollback and incident procedures, and approval by the responsible organization.

The proposed full submission should focus primarily on Stages 0–2 unless the official program scope directs otherwise.

---

## 18. Responsibility Matrix

| Responsibility | Owner before submission | Required evidence |
|---|---|---|
| Technical claims | LumenCore technical lead | frozen result and claim table |
| Benchmark contract | benchmark owner/reviewer | committed config and protocol |
| Data permission | project lead | source/license/authorization record |
| Security posture | designated reviewer | documented environment assessment |
| Export-control statements | qualified reviewer/counsel as needed | written determination or approved language |
| Data-rights assertions | founder plus qualified reviewer | official assertion table and IP inventory |
| Budget/cost assertions | founder plus accounting support as needed | rates, quotes, cost basis |
| Portal certifications | authorized organizational representative | official form review and explicit approval |
| Final submission | authorized submitter | founder approval and complete checklist |

No team member, assistant, script, or automated agent may make a legal/government certification on LumenCore’s behalf without explicit authorization.

---

## 19. Pre-Submission Safety Checklist

- [ ] Abstract ID and title match all volumes.
- [ ] Technical volume describes simulation and replay boundaries consistently.
- [ ] No autonomous weapon, physical actuation, or operational-control claim appears.
- [ ] No claim implies classified/CUI processing capability without verified support.
- [ ] All datasets have provenance and permission records.
- [ ] Secrets and credentials are excluded from all artifacts.
- [ ] Tool permissions and human-review gates are documented.
- [ ] Benchmark conditions and baselines are fixed and named.
- [ ] Failure, false rejection, abstention, cost, and negative results are reported.
- [ ] Claim table maps each claim to an evidence artifact.
- [ ] Public and non-public artifacts are separated.
- [ ] SHA-256 manifest covers the intended evidence packet.
- [ ] IP/background-data inventory is prepared.
- [ ] Official data-rights assertion format is verified.
- [ ] Cybersecurity/CMMC/CUI requirements are checked against the official solicitation and anticipated award.
- [ ] Export-control and foreign-participation language is reviewed if applicable.
- [ ] No customer, deployment, savings, certification, or revenue claim is unsupported.
- [ ] No portal certification or representation has been made without explicit approval.
- [ ] Final safety memo language is reconciled with technical, budget, transition, and evidence volumes.
- [ ] Robert Ashworth / authorized submitter gives explicit final approval.

---

## 20. Recommended Proposal Language

> The proposed Coherence-Bounded Peer Mesh is a non-actuating research architecture for controlled evaluation of decentralized AI coordination and local inference-time control. The effort will use bounded tool permissions, explicit role and uncertainty envelopes, challenge and abstention paths, modeled compromise and failure conditions, human approval gates for consequential actions, and reproducible evidence artifacts. Results will be reported as simulation or replay measurements under specified conditions and will not be represented as operational certification, real-adversary security proof, or unrestricted autonomous capability.

---

## 21. Immediate Follow-On Items

1. Cross-reference this memo from the technical volume and budget narrative.
2. Build the commercialization/transition plan using the staged transition boundary in Section 17.
3. Build the benchmark evidence packet with the metrics and run contract in Sections 10–12.
4. Verify official portal, data-rights, cybersecurity, foreign-participation, and certification requirements.
5. Keep all government submission and certification actions behind explicit founder approval.
