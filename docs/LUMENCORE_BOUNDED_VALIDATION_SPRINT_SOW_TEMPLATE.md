# LumenCore Bounded Validation Sprint — Statement of Work Template

**Draft status:** Commercial scoping template only. This is not legal, tax, cybersecurity, export-control, procurement, or accounting advice. Replace every bracketed field and obtain appropriate review before signature.

## 1. Parties and controlling agreement

This Statement of Work (“SOW”) is between:

- **Customer:** `[legal name and address]`
- **Provider:** `[LumenCore legal name and address]`
- **Effective date:** `[YYYY-MM-DD]`
- **Controlling agreement / purchase instrument:** `[agreement name and date]`
- **Customer decision owner:** `[name and role]`
- **LumenCore delivery owner:** `Robert Ashworth / LumenCore`

If this SOW conflicts with the controlling agreement or government instrument, the controlling agreement or instrument governs.

## 2. Decision to be made

The sprint is intended to answer one bounded question:

> `[Plain-language decision question.]`

Permitted final decisions:

- `promote` — the evidence supports the agreed next gate;
- `rerun` — the evaluation should be repeated under specified conditions;
- `external_review` — a qualified outside reviewer or data owner should perform the next evaluation;
- `hold` — evidence or authority is insufficient;
- `reject` — the candidate does not satisfy the pre-registered contract.

A favorable decision is not promised.

## 3. Scope

### 3.1 Candidate

| Field | Agreed value |
|---|---|
| Candidate name/version | `[value]` |
| Candidate owner | `[value]` |
| Candidate interface | `[file / API / container / report / model / other]` |
| Code/model revision | `[SHA / version / unknown]` |
| Production access required | `No, unless separately authorized in writing` |

### 3.2 Source and rights

| Field | Agreed value |
|---|---|
| Source name | `[value]` |
| Source type | `[dataset / stream / log / sensor / simulation / document]` |
| Rights owner | `[value]` |
| Rights status | `[public / synthetic / buyer-authorized]` |
| Authorized purpose | `[value]` |
| Authorized users | `[value]` |
| Retention/deletion rule | `[value]` |
| Transfer channel | `[approved channel]` |
| Source hash / receipt | `[value]` |

The Customer represents only that it has authority to permit the use stated in this SOW. LumenCore does not independently grant rights in Customer data.

### 3.3 Excluded information

Unless a separate written security and legal schedule is executed, Customer will not provide and LumenCore will not accept:

- classified information;
- controlled unclassified information;
- protected health information;
- payment-card data;
- export-controlled technical data;
- credentials, secrets, private keys, or production tokens;
- data whose transfer violates a contract, privacy duty, law, regulation, or policy;
- direct autonomous control of physical or safety-critical systems.

### 3.4 Baseline

| Field | Agreed value |
|---|---|
| Baseline name/version | `[value]` |
| Baseline type | `[incumbent / naive / historical / named method / synthetic control]` |
| Selected before scoring | `Yes` |
| Baseline owner/reference | `[value]` |
| Baseline hash/version | `[value]` |

### 3.5 Pre-registered evaluation contract

| Field | Agreed value |
|---|---|
| Primary metric | `[value]` |
| Metric definition | `[value]` |
| Acceptance threshold | `[value]` |
| Held-out window / frozen seeds | `[value]` |
| Secondary metrics | `[value]` |
| Failure rules | `[value]` |
| Incomplete-run rules | `[value]` |
| Exclusions | `[value]` |
| Allowed tuning before holdout | `[value]` |
| Prohibited post-outcome tuning | `[value]` |
| Human adjudication owner | `[value]` |
| Economic translation rule, if any | `[separate approved rule or none]` |

The primary metric, threshold, holdout, and failure rules must be approved before the scored run begins. Changes require a written change record and may require a new holdout.

## 4. Work plan

### Phase 1 — Intake and authorization

- confirm the decision owner and authorized source;
- verify the source receipt and data-handling boundary;
- inventory candidate and baseline dependencies;
- stop and report if the evaluation cannot be run lawfully or fairly.

### Phase 2 — Contract freeze

- freeze the source, baseline, metric, threshold, holdout, exclusions, and failure rules;
- record code, model, configuration, and dependency versions;
- create a pre-run evaluation receipt.

### Phase 3 — Matched evaluation

- execute candidate and baseline under the same agreed conditions;
- preserve logs, exceptions, timeouts, missing data, constraint violations, and adverse findings;
- block promotion when a required integrity, rights, or authority gate fails.

### Phase 4 — Verification and challenge

- generate input/output SHA-256 manifests;
- provide offline verification instructions;
- conduct `[number]` included controlled reviewer rerun(s), if applicable;
- record discrepancies between original and rerun results.

### Phase 5 — Decision packet

- issue the Proof Capsule and failure register;
- separate measured, replay, synthetic, modeled, estimated, and externally validated statements;
- brief the Customer decision owner;
- record one bounded decision and the evidence required for the next gate.

## 5. Deliverables and acceptance

| Deliverable | Format | Acceptance condition |
|---|---|---|
| Evaluation contract | Markdown/PDF/JSON as agreed | Required fields approved before scoring |
| Source and rights receipt | Human- and machine-readable | Rights owner and authorized purpose recorded |
| Input/dependency manifest | JSON | Paths/versions/hashes complete for agreed scope |
| Baseline and candidate outputs | Agreed data format | Both ran under the frozen contract or failure recorded |
| Failure/negative-result register | Markdown/JSON | Adverse, incomplete, and failed outcomes retained |
| SHA-256 manifest | JSON | Declared artifacts verify |
| Offline verifier instructions | Markdown | Customer can execute or inspect the verification path |
| Proof Capsule | JSON plus reviewer summary | Source, baseline, metric, result, limitations, and decision present |
| Decision briefing | Meeting plus written summary | Customer receives one bounded decision and next-gate requirements |

Customer has `[five]` business days after delivery to identify a specific failure to satisfy the written acceptance conditions. New features, additional data, additional baselines, changed metrics, new holdouts, production integration, or stronger claims are out of scope unless added by written change order.

## 6. Schedule

- Start date: `[date]`
- Contract freeze target: `[date]`
- Scored run target: `[date]`
- Review/rerun target: `[date]`
- Final delivery target: `[date, no more than 30 calendar days after start unless amended]`

Customer-caused delay in access, source authorization, baseline availability, review, or decisions moves the schedule by the corresponding period unless otherwise agreed.

## 7. Fees and payment

- Selected tier: `[Launch Replay / Standard Sprint / Institutional Sprint / custom]`
- Fixed fee: `$[amount]`
- Deposit or initial payment: `$[amount]` due `[event/date]`
- Final payment: `$[amount]` due `[event/date]`
- Approved expenses, if any: `[none / written preapproval required]`
- Taxes: `[allocation under controlling agreement]`
- Government invoicing/acceptance: `[controlling instrument]`

No out-of-scope work will begin without written authorization. Pricing does not represent guaranteed savings, ROI, award, certification, deployment, or a favorable result.

## 8. Customer responsibilities

Customer will:

- provide authorized data and an accurate rights statement;
- identify the accepted baseline and decision owner;
- provide timely access to agreed non-production interfaces;
- review and approve the evaluation contract before scoring;
- avoid changing the holdout or acceptance rule after results are known;
- identify required legal, security, privacy, export-control, procurement, or safety review;
- review delivered facts before any external statement.

## 9. LumenCore responsibilities

LumenCore will:

- run only the agreed scope;
- preserve source, configuration, and output custody records;
- retain adverse and incomplete results;
- stop when rights, integrity, authority, or safety gates are not satisfied;
- disclose material limitations and discrepancies;
- avoid external publication or customer identification without written permission;
- keep visual presentation subordinate to verifier output.

## 10. Intellectual property and licenses

### Background IP

Each party retains ownership of its pre-existing code, models, data, documentation, methods, trademarks, names, know-how, inventions, and other intellectual property.

LumenCore background IP includes its proof-to-pilot workflow, Proof Capsule format, verifier architecture, evidence-manifest methods, internal code, module names, lexicon, prior documents, and prior invention disclosures, except where a signed agreement expressly states otherwise.

### Customer materials

Customer materials remain owned or controlled by Customer or the named rights owner. Access is limited to the purpose and period stated in this SOW.

### Sprint outputs

The controlling agreement must state ownership and license rights for buyer-specific reports, configurations, adaptors, code, and derived artifacts. No ownership transfer, joint invention, exclusivity, production license, or right to publish is implied by this template.

## 11. Confidentiality and publicity

Confidentiality follows the controlling agreement. Neither party may identify the other as a customer, partner, validator, endorser, or sponsor; publish the result; use names or logos; or disclose non-public artifacts without written permission.

A technical review, discussion, paid evaluation, or delivered report does not by itself establish partnership, endorsement, field validation, certification, production deployment, or public reference rights.

## 12. Security and system boundary

The standard sprint is non-production and non-actuating. It does not authorize:

- access to production credentials;
- live financial orders;
- autonomous physical control;
- safety-critical recommendations without human review;
- bypassing access controls;
- handling restricted data outside an approved environment;
- security, privacy, regulatory, export-control, or accreditation claims.

Any higher-risk environment requires a separately approved architecture, responsibility matrix, incident process, access boundary, and contracting instrument.

## 13. Claim boundary

The delivered evidence may support only the claim approved in the evaluation contract. It does not automatically establish:

- external or field validation;
- operational approval;
- certified safety or cybersecurity;
- guaranteed performance, savings, or ROI;
- agency endorsement or award likelihood;
- customer deployment or adoption;
- universal superiority;
- patentability, freedom to operate, or ownership beyond the signed agreement.

## 14. Change control and stop conditions

A written change order is required for changes to source, candidate, baseline, metric, threshold, holdout, schedule, deliverables, data handling, or allowed claim.

LumenCore may stop the sprint and issue a bounded `hold` or `reject` record when:

- source rights cannot be confirmed;
- the baseline is unavailable or unfairly defined;
- the metric or threshold changes after scoring;
- artifacts cannot be verified;
- unsafe or unauthorized access is requested;
- Customer requests concealment of material failures;
- applicable law, policy, or the controlling agreement prevents the work.

Commercial consequences of suspension or termination must be stated in the controlling agreement.

## 15. Signatures

**Customer**

Name: `[name]`  
Title: `[title]`  
Signature: `____________________________`  
Date: `[date]`

**LumenCore**

Name: `Robert Ashworth`  
Title: `[authorized title]`  
Signature: `____________________________`  
Date: `[date]`

*Do not sign this template until every bracketed field is completed and the governing legal/commercial terms are reviewed.*
