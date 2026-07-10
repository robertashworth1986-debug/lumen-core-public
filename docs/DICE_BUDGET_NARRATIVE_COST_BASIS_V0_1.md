# DICE Budget Narrative + Cost Basis Draft v0.1

**Project:** LumenCore / DARPA DICE full-submission working packet  
**Abstract ID:** HR001126S0010-DICE-PA-052  
**Abstract Title:** Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives  
**Status:** Internal working draft only. Not a submission. Not legal advice. Not an accounting certification. Not a government certification.  

---

## 0. Budget Control Boundary

This document is a planning asset for a potential DICE full-submission package. The official BAA, BAAT portal instructions, required budget spreadsheet, cost proposal template, organization type, indirect-rate status, allowable-cost rules, representations, certifications, and contracting officer instructions control any final cost submission.

No dollar amount, rate, indirect-cost treatment, subcontract commitment, or government representation should be treated as final until reviewed against the official solicitation package and explicitly approved by Robert Ashworth / LumenCore.

This draft intentionally uses conservative, explainable cost categories. It avoids claims of audited revenue, certified product status, deployed government capability, autonomous physical control, weapons capability, or validated field savings.

---

## 1. Budget Strategy

The budget should present LumenCore as a founder-led, software-heavy research effort with a narrow, defensible cost basis:

1. build and harden the Coherence-Bounded Peer Mesh prototype,
2. implement local inference-time control and sparse task-market protocols,
3. run controlled simulation/replay benchmarks,
4. preserve negative results and failure modes,
5. generate reproducible evidence artifacts and SHA-256 manifests,
6. prepare transition materials for evaluator, lab, and pilot-partner review.

The budget should not look like a broad company-building request. It should map directly to the technical tasks and deliverables in the DICE technical volume.

Recommended posture:

> LumenCore requests support for a bounded research-and-validation effort to determine whether sparse peer task markets plus local inference-time control improve resilience, role coherence, recovery, and auditability in heterogeneous AI collectives under controlled simulation and replay conditions.

---

## 2. Cost Categories

### 2.1 Personnel / Founder Technical Labor

**Purpose:** Core architecture, implementation, evaluation design, benchmark execution, documentation, and evidence packaging.

**Basis of estimate:** Founder technical effort required to design and implement the CBPM prototype, run the evaluation harness, analyze outcomes, and prepare technical reports.

**Likely tasks:**

- define TA1/TA2 work breakdown,
- implement role-state register and local inference controller,
- implement sparse task-market simulator,
- implement peer-reputation and challenge/re-auction logic,
- build benchmark scenarios,
- run benign, compromise, collusion, monitor-shift, and high-compromise conditions,
- generate evidence manifests,
- write technical reports and transition briefs.

**Narrative wording:**

> Personnel funds support founder-led technical execution for architecture, software implementation, benchmark design, controlled replay, result analysis, and evidence packaging. The effort is scoped to prototype and evaluation work, not production deployment or operational fielding.

**Open items before final submission:**

- confirm allowable labor-rate format,
- confirm whether LumenCore submits as an individual founder-led entity or registered small business,
- confirm fringe/benefit treatment,
- confirm whether any uncompensated founder effort should be shown as cost share only if allowed and intended.

---

### 2.2 Software Engineering / Prototype Development

**Purpose:** Build the DICE-specific CBPM prototype and supporting harness.

**Basis of estimate:** Engineering time, test harness work, code review, reproducibility tooling, and documentation.

**Likely components:**

- Python simulation/replay harness,
- configuration schema,
- local inference controller,
- sparse task-market allocator,
- challenge/re-auction module,
- compromise/collusion scenario generator,
- metric collector,
- JSON/CSV report outputs,
- SHA-256 manifest generation,
- reproducible run scripts.

**Narrative wording:**

> Software engineering costs support the DICE-specific implementation of CBPM components and reproducible evaluation tooling. The prototype will be designed for controlled research evaluation and will not be represented as an operational or certified autonomy system.

---

### 2.3 Simulation / Replay Benchmark Development

**Purpose:** Produce evidence that reviewers can inspect rather than broad claims.

**Basis of estimate:** Scenario design, baseline implementation, run management, failure-mode injection, and metric reporting.

**Required scenario families:**

1. benign decentralized coordination,
2. compromised-agent injection,
3. colluding-agent behavior,
4. monitor or evaluator shift,
5. high-compromise stress condition,
6. communication-cost sensitivity,
7. role-drift / coherence-decay condition,
8. recovery-latency condition.

**Baseline comparisons:**

- centralized/proxy coordinator,
- naive all-to-all peer coordination,
- non-coherence task allocation,
- static role assignment,
- random or simple confidence baseline.

**Narrative wording:**

> Benchmark development funds support controlled simulation and replay tests that compare CBPM against defined baselines. The evaluation will preserve failures, false rejections, communication cost, and negative cases to avoid manufacturing an all-win result.

---

### 2.4 Cloud / Compute / API Resources

**Purpose:** Run repeatable benchmark sweeps and store public-safe artifacts.

**Basis of estimate:** Cloud compute, storage, logging, model/API calls if needed, and controlled benchmark execution.

**Allowable-scope notes:**

- Use only non-sensitive, synthetic, public, or properly authorized data.
- Do not include secrets, API keys, private account identifiers, or controlled government data in public artifacts.
- Maintain fallback mode so benchmark evidence can be reviewed without live API dependence.

**Narrative wording:**

> Compute costs support controlled benchmark runs, result storage, reproducibility checks, and report generation. Live API use, if any, will be isolated behind environment variables and will not expose secrets or sensitive data in proposal artifacts.

**Open items before final submission:**

- identify whether cloud costs belong under materials, ODC, or direct compute,
- confirm whether any provider credits must be disclosed,
- confirm whether API costs are allowable under the solicitation.

---

### 2.5 Independent Technical / Statistical Review

**Purpose:** Improve credibility and reduce overclaim risk.

**Basis of estimate:** Limited-scope review by a qualified technical, statistical, or AI-safety reviewer.

**Possible review tasks:**

- inspect benchmark design,
- verify no temporal/evaluation leakage,
- review baseline fairness,
- review metric definitions,
- inspect negative-result treatment,
- assess whether claims match evidence.

**Narrative wording:**

> Limited independent review costs may support external inspection of benchmark design, baseline fairness, metric definitions, and claim boundaries. Any reviewer role would be scoped in writing before proposal submission and would not imply ownership of pre-existing LumenCore IP.

**Open items before final submission:**

- identify reviewer or subcontractor,
- obtain written scope and estimated cost,
- confirm whether subcontractor/consultant documentation is required,
- confirm conflict, IP, and data-access terms.

---

### 2.6 Security / Safety Boundary Review

**Purpose:** Keep the proposal aligned with non-operational, human-reviewed, simulation-first AI coordination research.

**Basis of estimate:** Review time for safety boundary, misuse boundary, data-rights posture, and controlled-output language.

**Narrative wording:**

> Safety-boundary costs support review of the project’s non-operational, simulation-first posture; data-rights labeling; tool-permission boundaries; and prohibited-claim controls. The work does not include weapons development, operational fielding, autonomous physical control, or certified safety-critical deployment.

**Required memo connection:**

This category should cross-reference the DICE Safety Boundary Memo when drafted.

---

### 2.7 Documentation / Reporting / Evidence Packaging

**Purpose:** Deliver reviewer-readable outputs and reproducibility artifacts.

**Basis of estimate:** Technical writing, report generation, artifact curation, manifest generation, and final package assembly.

**Deliverables:**

- technical report,
- benchmark evidence packet,
- run manifests,
- baseline comparison table,
- negative-result register,
- transition summary,
- public-safe claim boundary table,
- final slide or briefing packet if required.

**Narrative wording:**

> Documentation costs support evidence packaging, reproducibility artifacts, technical reporting, and final briefing material. The deliverables will separate measured, replay, synthetic, modeled, and planned evidence so evaluators can inspect what has been demonstrated and what remains future work.

---

### 2.8 Commercialization / Transition Discovery

**Purpose:** Identify transition paths without overstating market traction or field validation.

**Basis of estimate:** Customer discovery, technical-user interviews, evaluator conversations, and transition-plan writing.

**Likely targets:**

- AI evaluation teams,
- defense research labs,
- industrial autonomy testbeds,
- simulation and test/evaluation partners,
- infrastructure analytics partners,
- technical mentors with decentralized AI or resilience expertise.

**Narrative wording:**

> Transition costs support structured discovery with potential evaluators, labs, and pilot partners to determine where CBPM evidence could be independently reviewed or extended. This activity is market and transition research, not a claim of existing customer deployment or field-validated savings.

---

### 2.9 Travel / Meetings

**Purpose:** Only include if required or strategically necessary.

**Basis of estimate:** Program meetings, technical review, proposer day, evaluator meeting, or transition partner meeting if permitted.

**Narrative wording:**

> Travel, if included, will be limited to required program meetings or high-value technical/evaluator meetings explicitly aligned with the DICE work plan.

**Open items before final submission:**

- confirm whether travel is expected or allowable,
- confirm location, trip count, airfare/lodging/per diem rules,
- avoid adding travel unless it is tied to a required or defensible meeting.

---

### 2.10 Materials / Equipment

**Purpose:** Keep minimal unless necessary.

**Basis of estimate:** Software-first project should not need major equipment unless official guidance or a test partner requires it.

**Narrative wording:**

> No major equipment is currently assumed. Any equipment or material cost must be tied directly to the controlled simulation, replay, security, or reporting work and approved before final submission.

---

## 3. Suggested Work Breakdown Structure

| WBS | Task | Budget linkage | Primary output |
|---|---|---|---|
| 1 | Program setup and requirements mapping | Personnel, documentation | compliance checklist, metric plan |
| 2 | CBPM architecture implementation | personnel, software engineering | prototype modules |
| 3 | Local inference control | personnel, software engineering | role/coherence controller |
| 4 | Sparse peer task market | personnel, software engineering | allocator, challenge, re-auction logic |
| 5 | Scenario and baseline development | benchmark development, compute | benchmark suite |
| 6 | Controlled runs and stress tests | compute, personnel | run outputs, logs, metric tables |
| 7 | Evidence packaging | documentation, compute | SHA-256 manifests, evidence packet |
| 8 | Safety and claim-boundary review | safety review, independent review | safety memo, claim table |
| 9 | Transition discovery | commercialization/transition | transition plan and pilot path |
| 10 | Final reporting | documentation, personnel | technical report and submission attachments |

---

## 4. Cost Basis Checklist

Before any final budget is submitted, fill or verify:

- [ ] official cost template or spreadsheet,
- [ ] period of performance,
- [ ] total requested amount,
- [ ] labor categories,
- [ ] labor rates,
- [ ] hours by task,
- [ ] fringe treatment,
- [ ] indirect / overhead / G&A treatment,
- [ ] materials / compute / ODC treatment,
- [ ] consultant or subcontractor quotes,
- [ ] travel assumptions,
- [ ] equipment assumptions,
- [ ] fee/profit rules, if applicable,
- [ ] data rights assertions,
- [ ] IP boundary statement,
- [ ] SAM/CAGE/UEI status,
- [ ] small-business eligibility status,
- [ ] certifications and representations required by the portal,
- [ ] founder approval before submission.

---

## 5. Recommended Conservative Placeholder Budget Shape

Do not submit these percentages as final numbers. Use them as an internal reasonableness check only.

| Category | Internal planning share | Rationale |
|---|---:|---|
| Personnel / founder technical labor | 40-55% | Main work is architecture, implementation, evaluation, and reporting |
| Software engineering / prototype support | 10-20% | Harness and reproducibility work |
| Simulation/replay benchmarks | 10-15% | Scenario design, baselines, failure-mode injection |
| Cloud/API compute | 5-10% | Controlled runs and artifact storage |
| Independent review / advising | 5-10% | Baseline fairness, metrics, claim-boundary review |
| Documentation / reporting | 5-10% | Technical volume, evidence packet, transition materials |
| Transition discovery | 3-7% | Evaluator/lab/pilot discovery |
| Travel | 0-5% | Only if required or defensible |
| Equipment | 0% default | Software-first; avoid unless required |

---

## 6. Claim and Certification Risks to Avoid

Do not put the following into the budget narrative or cost proposal unless independently supported and explicitly approved:

- audited revenue,
- booked government customer revenue,
- production deployment,
- field-validated savings,
- certified autonomy,
- certified aircraft/suit/physical-system capability,
- weapons capability,
- autonomous physical control,
- use of controlled government data,
- guaranteed mission improvement,
- guaranteed model superiority,
- formal subcontract commitment without written authorization,
- indirect-rate assertion not supported by records,
- cost-share commitment not intentionally approved,
- legal/accounting certification not reviewed.

---

## 7. Draft Budget Narrative Paragraph

> The proposed budget supports a bounded software research and validation effort for Coherence-Bounded Peer Mesh, a decentralized AI coordination architecture combining sparse peer task markets, local inference-time control, controlled simulation/replay benchmarks, and reproducible evidence packaging. The requested resources would support founder-led technical labor, DICE-specific prototype implementation, benchmark and baseline development, controlled compute runs, limited independent review, safety-boundary review, documentation, and transition discovery. The effort is scoped to research evaluation and evidence generation. It does not claim operational deployment, certified autonomy, autonomous physical control, weapons capability, field-validated savings, or audited revenue. Final cost treatment, rates, forms, certifications, and attachments must follow the official BAA and BAAT portal instructions.

---

## 8. Next Required Asset

Next asset after this budget narrative:

**DICE Safety Boundary Memo v0.1**

It should define:

- non-operational scope,
- no weapons / no autonomous physical control boundary,
- synthetic/public/authorized data boundary,
- human-review conditions,
- tool-permission limits,
- evidence and claim-class labels,
- misuse-risk language,
- prohibited claims,
- final submission approval gate.
