# NSF Project Pitch

## Working Title

Evidence-Calibrated Model Routing and Abstention for High-Consequence
Time-Series Decisions

## 1. Technology Innovation

Most forecasting systems select one model class, optimize a single average
error score, and return a prediction even after the data-generating process
changes. This can create confident failures on the exact series, horizon, or
operating regime that matters to an operator.

LumenCore proposes an evidence-calibrated decision architecture that treats
model-family selection, uncertainty calibration, regime change, and
abstention as one research problem. Multiple model families compete on
chronological, past-only evidence. A routing layer estimates which family is
appropriate for the current series and horizon. Calibration methods quantify
forecast uncertainty, while a change detector blocks or reroutes decisions
when data quality, coverage, or operating conditions leave validated bounds.
Every response includes the selected family, uncertainty, abstention state,
data freshness, test identifiers, and a SHA-256 evidence manifest.

The unproven high-impact question is whether routing and abstention can
generalize across heterogeneous sectors without temporal leakage,
overconfidence, or hidden subgroup failure. Existing work establishes
engineering feasibility: a frozen 673-series benchmark across nine models and
five families; a dependency-verified breadth run on 2,172 series; streaming
anomaly and regime-change components; and deterministic evidence packaging.
However, a leakage-resistant V7 validation rejected a universal forecasting
edge: median improvement was zero and no series passed every robustness gate.
That negative result motivates the proposed technology. Phase I will determine
when the system has enough evidence to choose a model and when the correct
product behavior is to abstain.

## 2. Technical Objectives and Challenges

Objective 1 is a quality-controlled multi-sector benchmark. Each candidate
series will receive provenance, deduplication, minimum-history, missingness,
frequency, and leakage checks. The broader local catalog contains 2,586
artifacts and 14,390,128 rows, but an artifact will count as a benchmark series
only after passing those controls.

Objective 2 is leakage-resistant model routing. We will use rolling-origin
outer folds, nested past-only selection for features and hyperparameters,
fixed baselines, paired block-bootstrap intervals, and multiple-comparison
controls. Results will be reported by sector, horizon, regime, and failure
class rather than only as an aggregate win rate.

Objective 3 is uncertainty and abstention under change. We will compare
residual-bootstrap and conformal approaches, measure coverage and interval
width by horizon and regime, and preregister conditions that force abstention
or fallback to a simple baseline.

Objective 4 is a reproducible API prototype. Each response will include the
selected family, forecast distribution, anomaly/regime indicators, confidence,
abstention reason, data freshness, and evidence identifiers. Acceptance tests
will cover deterministic replay, schema compatibility, latency, stale-data
failure, and restart recovery.

The main risks are router overfitting, duplicated or low-quality data,
distribution shift, and apparently strong averages concealing sector
failures. These are the research targets. Phase I will preserve negative
results and deliver a failure register alongside the prototype.

## 3. Market Opportunity

The initial customer is an energy, infrastructure, supply-chain, or regulated
data operator that already produces forecasts but cannot easily audit model
selection, uncertainty, or behavior after a regime change. The pain is not the
absence of another point forecast. It is the cost of reconciling models,
investigating false alerts, and defending decisions made from weak or
poorly-calibrated evidence.

LumenCore will enter through paid evaluation pilots. On a customer's
historical data, the product will run beside the incumbent workflow and be
judged on forecast error, interval coverage, alert precision/recall,
abstention quality, analyst time, latency, and deterministic reproducibility.
The near-term product is an API and deployable validation service. Longer-term
markets include energy operations, environmental forecasting, supply-chain
risk, and regulated financial risk analytics.

Competitors include single-family forecasting APIs, AutoML systems, and
internal notebooks. LumenCore is differentiated by leakage-resistant
per-series routing, shift-aware calibration, explicit abstention and failure
reporting, and evidence manifests designed for high-consequence review.

## 4. Company and Team

Robert Ashworth is a U.S.-owned one-person small business. Robert Ashworth,
Founder and Chief Scientist, built the existing ingestion, multi-family
forecasting, calibration, anomaly/regime detection, API, deployment, and
evidence-manifest systems and will serve as Principal Investigator.

The current stack is a research prototype, not a claim of profitable live
trading, universal model superiority, or completed institutional deployment.
Phase I will convert the reusable evidence and abstention components into a
rigorously validated product with frozen evaluation protocols,
customer-facing APIs, security documentation, and independent reproducibility
review.

The main team gaps are domain-specific pilot access, external statistical
review, cybersecurity/compliance review, and product integration. The Phase I
plan will reserve scoped consultant or subaward work for these functions.
Named personnel and commitments will be finalized before any full proposal
budget or support claim is submitted.

## Submission Boundary

This is a working draft for the NSF Project Pitch gate. It does not claim an
NSF invitation or authorization to submit a full proposal.
