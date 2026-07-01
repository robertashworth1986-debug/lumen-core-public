# NSF Project Pitch Portal Fields

Updated: June 19, 2026

Working title: Evidence-Calibrated Model Routing and Abstention for High-Consequence Time-Series Decisions

Primary NSF topic: Artificial Intelligence, with emphasis on trustworthy AI.

Official character limits checked June 19, 2026:

- Technology Innovation: 3,500 characters
- Technical Objectives and Challenges: 3,500 characters
- Market Opportunity: 1,750 characters
- Company and Team: 1,750 characters

Source: https://seedfund.nsf.gov/apply/project-pitch/

Character counts checked locally after drafting:

- Technology Innovation: 2,852 / 3,500 characters (648 spare)
- Technical Objectives and Challenges: 2,419 / 3,500 characters (1,081 spare)
- Market Opportunity: 1,517 / 1,750 characters (233 spare)
- Company and Team: 1,223 / 1,750 characters (527 spare)

## 1. Technology Innovation

Most forecasting and decision-support systems choose a model family, optimize an average error score, and keep returning predictions even after the data-generating process changes. In high-consequence time-series settings, that behavior can create confident failures: the system may look accurate on aggregate while failing on a specific sector, horizon, operating regime, or data-quality condition that an operator must defend.

LumenCore proposes a trustworthy AI architecture that treats model-family routing, uncertainty calibration, regime-change detection, and abstention as one research problem. Instead of asking whether one forecasting method is universally superior, the system asks which method has earned the right to answer this series, at this horizon, under the current evidence. Multiple model families compete only on chronological, past-only validation. A routing layer estimates fit by series, horizon, and regime. Calibration methods quantify uncertainty. A change detector blocks, reroutes, or falls back when data freshness, coverage, or operating conditions leave validated bounds. Each response returns the selected family, uncertainty, abstention state, data freshness, validation identifiers, and a SHA-256 evidence manifest.

This differs from conventional forecasting APIs, AutoML systems, and monitoring dashboards because the product is not merely selecting the lowest recent error model. It is attempting to make model authority auditable: what data were allowed, what validation window justified the answer, what uncertainty was calibrated, what changed, and why the system answered or abstained. That is the technical basis for a durable product advantage in regulated or safety-sensitive operations where an unsupported confident answer can be worse than no answer.

The high-risk technical innovation is an evidence-gated router that can learn when not to decide. The research question is not whether LumenCore can produce another point forecast; it is whether a system can combine leakage-resistant model selection, calibrated uncertainty, and auditable abstention in a way that generalizes across heterogeneous time-series sectors without hidden overfitting or silent subgroup failure.

Existing work establishes engineering feasibility but also shows why the research is needed. LumenCore has run frozen multi-family benchmarks, streaming anomaly and regime-change components, deterministic manifests, and API prototypes. A leakage-resistant V7 validation rejected a universal forecasting-edge claim: median improvement was zero and no series passed every robustness gate. That negative result is central to the proposed innovation. Phase I will convert the current prototype into a validated trustworthy-AI product that knows when to route, when to abstain, and how to prove what evidence supported each response.

## 2. Technical Objectives and Challenges

Objective 1 is a quality-controlled multi-sector benchmark. Candidate time series will be admitted only after provenance, deduplication, minimum-history, missingness, frequency, leakage, and timestamp-order checks. The broader local catalog contains thousands of artifacts, but an artifact will count as a benchmark series only after passing these controls. The challenge is preventing duplicated, stale, or low-quality data from creating false confidence. We will preserve excluded-series records and report benchmark coverage rather than hiding data-quality failures.

Objective 2 is leakage-resistant model routing. Phase I will compare baseline methods, statistical models, machine-learning models, and periodic, regime, and flow-derived feature families under rolling-origin outer folds. Feature and hyperparameter selection will be nested inside past-only folds. The router will be evaluated by sector, horizon, regime, and failure class using paired intervals and multiple-comparison controls. The challenge is router overfitting: a selector can appear intelligent while merely learning test-set artifacts. We will preregister selection rules, freeze holdouts, and require performance to beat simple baselines under repeated folds before promotion.

Objective 3 is uncertainty calibration and abstention under change. We will compare conformal and residual-bootstrap intervals, measure coverage and interval width by horizon and regime, and define abstention gates for stale data, regime change, missing coverage, unsupported horizon, and model disagreement. The challenge is balancing useful coverage with excessive refusal. Phase I will report both false confidence and unnecessary abstention.

Objective 4 is a reproducible API prototype. The prototype will return a forecast distribution or abstention result, selected family, confidence, anomaly/regime indicators, data freshness, and evidence identifiers. Acceptance tests will cover deterministic replay, schema compatibility, latency, stale-data failure, restart recovery, and manifest verification.

The main technical risks are data leakage, duplicated data, distribution shift, hidden subgroup failure, and a router that improves averages while harming important classes. These are the research targets. Phase I will deliver a frozen benchmark, calibrated router, abstention engine, API prototype, and failure register that preserves negative results.

## 3. Market Opportunity

The initial customer is an energy, infrastructure, environmental, supply-chain, or regulated-data operator that already produces forecasts but cannot easily audit model selection, uncertainty, or behavior after a regime change. The pain is not the absence of another prediction. It is the cost of reconciling competing models, investigating false alerts, explaining weak evidence, and defending decisions when the data have shifted.

LumenCore will enter through paid evaluation pilots. On a customer's historical data, the product will run beside the incumbent workflow and be judged on forecast error, interval coverage, alert precision/recall, abstention quality, analyst review time, latency, and deterministic reproducibility. The near-term product is an API and validation service for high-consequence time-series decisions. Longer-term markets include energy operations, environmental forecasting, grid and infrastructure monitoring, supply-chain risk, insurance, and regulated operations analytics.

Competitors include single-family forecasting APIs, AutoML tools, monitoring dashboards, and internal notebooks. LumenCore is differentiated by leakage-resistant per-series routing, shift-aware calibration, explicit abstention, failure reporting, and evidence manifests designed for technical and regulatory review. The broader impact is fewer confident model failures in decisions involving energy reliability, environmental planning, infrastructure risk, and other time-sensitive public-interest operations.

## 4. Company and Team

LumenCore is a U.S.-owned small business led by Robert Ashworth, Founder and Chief Scientist, who will serve as Principal Investigator. He built the current ingestion, multi-family benchmarking, calibration, anomaly/regime detection, API, deployment, and evidence-manifest components. The current stack is a research prototype, not a claim of profitable live trading, universal model superiority, or completed institutional deployment.

The Phase I team plan is intentionally honest about gaps. The company needs domain pilot access, independent statistical review, cybersecurity/compliance review, and product integration support. The budget will reserve scoped consultant or subaward work for these functions, and named commitments will not be claimed until written permission and roles are confirmed.

The founder's advantage is speed of integration across data ingestion, evaluation, software, and audit infrastructure. The execution risk is that the company is currently one person. Phase I is designed to reduce that risk by narrowing the technical scope, freezing evaluation gates, adding external review, and turning the prototype into a reproducible customer-facing API with clear security and evidence boundaries.

## Submission Boundary

This is a working Project Pitch draft. It does not claim an NSF invitation, full-proposal authorization, customer commitment, or award.
