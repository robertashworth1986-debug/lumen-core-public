# NSF Project Pitch Portal Fields

Updated: July 29, 2026

Working title: Evidence-Gated Routing and Abstention for High-Consequence Time-Series AI

Primary route: NSF 26-510, general deep technology and trustworthy AI.

Alternate route: NSF 26-511 only if NSF confirms that a software-defined validation platform qualifies under the scientific-instrumentation emphasis.

Public NSF instructions rechecked July 29, 2026:

- Technology Innovation: 3,500 characters
- Technical Objectives and Challenges: 3,500 characters
- Market Opportunity: 1,750 characters
- Company and Team: 1,750 characters

The authenticated MyWork form schema, title limit, applicant eligibility, and account state are not established by the public-source review. Character counts below must be regenerated from this exact file before portal use.

Current exact field counts:

- Technology Innovation: 3,273 / 3,500 characters
- Technical Objectives and Challenges: 3,030 / 3,500 characters
- Market Opportunity: 1,674 / 1,750 characters
- Company and Team: 1,602 / 1,750 characters

## Technology Innovation

Most forecasting and decision-support systems select a model family, optimize an average error score, and continue returning predictions after the data-generating process changes. In high-consequence time-series settings, that behavior can create confident failures: a system may look accurate in aggregate while failing on a specific source, sector, horizon, operating regime, or data-quality condition that an operator must defend.

LumenCore proposes a trustworthy-AI architecture that treats model-family routing, source-specific baseline comparison, uncertainty calibration, regime-change detection, and abstention as one research problem. Instead of asking whether one forecasting method is universally superior, the system asks which method has earned the right to answer this source and series, at this horizon, under the current evidence. Candidate families compete only on chronological, past-only validation against baselines declared for the source. A routing layer estimates fit by source, series, horizon, and regime. Calibration methods quantify uncertainty. A change detector blocks, reroutes, or falls back when freshness, coverage, or operating conditions leave validated bounds. Each response returns the selected family, uncertainty, abstention state, data freshness, validation identifiers, and a SHA-256 evidence receipt.

This differs from conventional forecasting APIs, AutoML systems, and monitoring dashboards because the product is not merely selecting the lowest recent error model. It is designed to make model authority auditable: what source and data were allowed, which source-native baselines were challenged, what validation window justified the answer, how uncertainty was calibrated, what changed, and why the system answered or abstained. That is the technical basis for a durable advantage in regulated or safety-sensitive operations where an unsupported confident answer can be worse than no answer.

The high-risk technical innovation is an evidence-gated router that can learn when not to decide while resisting selection bias across many candidate families. The architecture originated in repeated internal benchmark work where a family that led on one series, horizon, or regime often failed elsewhere and aggregate scores concealed unsupported forecasts. The research question is whether leakage-resistant selection, calibrated uncertainty, change detection, and auditable abstention can generalize across independent source-series clusters without hidden overfitting or subgroup harm.

Current internal evidence establishes engineering feasibility and the unresolved research gap. The registry contains 140 families, of which 35 are implemented. A current source-native ledger records 126 direct comparisons across 23 candidate/source cards, with zero globally corrected positives and zero promoted champions. A market sidecar records 48 source-specific comparisons and 22 descriptive wins, but all 48 are inferentially insufficient because each source currently contributes only one independent series cluster. These are local protocol results, not independent validation or performance claims. Phase I would turn this fail-closed prototype into a statistically qualified system that earns, limits, and records model authority.

## Technical Objectives and Challenges

Objective 1 is a quality-controlled, source-native benchmark. Candidate series will be admitted only after provenance, deduplication, minimum-history, missingness, frequency, leakage, and timestamp-order checks. Each source will have a preregistered baseline set, metric definitions, costs where applicable, minimum independent-series requirement, and frozen train/validation/test chronology. The challenge is preventing duplicated, overlapping, stale, or low-quality series from creating false sample size or false confidence. Exclusions and failed gates will be retained.

Objective 2 is leakage-resistant family routing. Phase I will compare simple persistence and seasonal baselines, source-appropriate statistical and machine-learning baselines, and candidate periodic, regime, flow, and geometry-derived families under rolling-origin outer folds. Feature and hyperparameter selection will remain inside past-only folds. The router will be evaluated by source, series, horizon, regime, and failure class using paired intervals, independent-series clustering, and multiple-comparison controls. The challenge is router overfitting: a selector can appear intelligent while learning test artifacts. Selection rules, holdouts, promotion thresholds, and stopping conditions will be preregistered.

Objective 3 is uncertainty calibration and abstention under change. The research will compare conformal and residual-bootstrap intervals, measure coverage and width by horizon and regime, and define abstention gates for stale data, regime change, missing coverage, unsupported horizon, model disagreement, and insufficient independent evidence. The challenge is balancing useful coverage with excessive refusal. Phase I will report both false confidence and unnecessary abstention, including subgroup failures.

Objective 4 is a reproducible API prototype. The prototype will return a forecast distribution or abstention result, selected family, baseline contract, confidence, anomaly/regime indicators, data freshness, and evidence identifiers. Acceptance tests will cover deterministic replay, schema compatibility, latency, stale-data failure, restart recovery, manifest verification, and refusal when a promotion gate is not met.

Objective 5 is independent evaluation design. A frozen protocol and containerized replay package will be handed to an outcome-independent evaluator. Promotion will require the preregistered minimum number of independent source-series clusters, corrected statistical significance, effect-size and operational guardrails, and successful external reproduction. Negative and null outcomes will remain publishable project outputs.

The main risks are data leakage, pseudo-replication, distribution shift, hidden subgroup failure, baseline mismatch, and a router that improves averages while harming important classes. These are the research targets. Phase I deliverables are a frozen benchmark, calibrated router, abstention engine, reproducible API, independent-evaluation packet, and failure register.

## Market Opportunity

The initial customer is an energy, infrastructure, environmental, supply-chain, or regulated-data operator that already produces forecasts but cannot easily audit model selection, uncertainty, or behavior after a regime change. The pain is not the absence of another prediction. It is the cost of reconciling competing models, investigating false alerts, explaining weak evidence, and defending decisions when sources or operating conditions have shifted.

LumenCore would enter through paid evaluation pilots. On a customer's historical data, the system would run beside the incumbent workflow and be judged on preregistered forecast error, interval coverage, alert precision and recall, abstention quality, analyst review time, latency, and deterministic reproducibility. The near-term product is an API and validation service for high-consequence time-series decisions. Expansion markets include grid and infrastructure monitoring, environmental forecasting, supply-chain risk, insurance, and regulated operations analytics.

Competitors include single-family forecasting APIs, AutoML tools, observability dashboards, and internal notebooks. LumenCore is differentiated by source-specific baseline contracts, leakage-resistant per-series routing, shift-aware calibration, explicit abstention, preserved negative results, and evidence receipts designed for technical and regulatory review. The commercial hypothesis is that operators will pay to reduce unsupported automated decisions and reviewer burden. Phase I must validate that hypothesis through structured discovery and pilot-design evidence; no customer commitment, realized savings, or market adoption is claimed.

## Company and Team

The proposed work is led by Robert Ashworth, founder of LumenCore and builder of the current ingestion, multi-family benchmarking, calibration, anomaly/regime detection, API, deployment, and evidence-receipt components. The stack is a founder-led research prototype. It is not a claim of profitable live trading, universal model superiority, independent validation, or completed institutional deployment.

The intended technical lead combines the data, evaluation, software, and audit work needed to execute a tightly scoped Phase I. Before submission, the authorized company officer must verify the legal business name, small-business and ownership eligibility, U.S. work-performance facts, Principal Investigator employment and effort, and submission authority. This draft does not infer those legal facts from repository artifacts.

The team plan is explicit about current gaps. Phase I would add an outcome-independent statistical evaluator, domain pilot access, cybersecurity and compliance review, and product-integration support. Any consultant, subaward, partner, or customer role will be named only after written permission and scope confirmation.

The founder's advantage is rapid integration across source ingestion, evaluation protocols, software, and audit infrastructure. The execution risk is concentration in one person. Phase I is designed to reduce that risk by narrowing the technical scope, freezing evaluation gates, adding independent review, documenting reproducible operations, and converting the prototype into a customer-facing API with clear security and evidence boundaries.

## Routing Status

- The Project Pitch is the current rolling prerequisite and has no standalone calendar deadline.
- NSF 26-510 was rechecked July 29, 2026. July 27, 2026 is now a past listed full-proposal deadline. The next listed full-proposal deadline is November 4, 2026 at 5:00 PM in the submitting organization's local time.
- No official Project Pitch invitation is verified, so no full-proposal deadline is currently reachable.
- Before any portal action, verify that no Project Pitch is pending and no open invitation or Phase I proposal is active.
- November 4 is an invitation-contingent planning date, not authorization, a Project Pitch deadline, or a guarantee.

## Submission Boundary

This is a current working draft, not an authenticated portal capture. It does not claim applicant eligibility, an NSF invitation, full-proposal authorization, customer commitment, independent validation, or award. Legal company facts, PI eligibility, authenticated portal state, current form prompts, title limit, and final submission require human verification and action-time approval.

It does not claim an NSF invitation.

## Evidence Boundary

The current source-native counts are local reproducibility and protocol evidence only. Hashes, row counts, deterministic replay, descriptive wins, and green software tests do not establish independent scientific validation, model superiority, field performance, commercial savings, or award readiness.

## Official Sources

- Project Pitch overview: https://seedfund.nsf.gov/project-pitch/
- Project Pitch instructions: https://seedfund.nsf.gov/apply/project-pitch/
- NSF 26-510 solicitation: https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation
- NSF 26-511 solicitation: https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology-0/nsf26-511/solicitation
- Current solicitation schedule: https://seedfund.nsf.gov/solicitations/
