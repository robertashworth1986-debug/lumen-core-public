# Scientific Contribution and Next Experiments

Snapshot date: 2026-07-26
Status: evidence-first research direction; no promoted champion

## Executive Answer

There is no defensible KurryMotto champion in the tracked repository. No
implementation under that name was found in the current public tree. The
implemented Kuramoto candidate is real code, but on the frozen public EIA-930
benchmark it did not win: autoregressive ridge ranked first at mean seasonal
MASE 0.479459, while the Kuramoto phase-coupling candidate recorded 1.253509.

FlowForm is also not presently a validated physical or operational champion.
The tracked geometry registry classifies the hybrid FlowForm lane as exploratory
and says that no leakage-resistant, lane-specific promotion run has passed.
Archived transforms, scoring heuristics, simulations, and dashboards are not a
substitute for prospective or field validation.

The strongest measured algorithmic candidate in the bounded public replay is
the XGBoost residual model at MASE 0.211206. That result is useful for selecting
the next prospective experiment, but its promotion, coverage, external, and
field-validation gates remain false.

## What Is Real Today

### 1. A reproducible evidence-assurance method

The public repository can make a defensible software and research-method
contribution:

- bind each claim to an authorized source, accepted baseline, locked metric,
  frozen split, code state, environment, and artifact hash;
- preserve negative and null findings rather than promoting a preferred story;
- separate deterministic tests from AI-assisted summaries and routing;
- make missing rights, missing coverage, failed gates, and human decision
  authority explicit;
- package a bounded workflow so an independent executor can reproduce it.

The current CODECHECK reviewer capsule recreated 31 of 31 declared assertions
across 3 of 3 suites in its packaged clean-run workflow. That is first-party
executable reproducibility. It is not independent scientific validation,
agency approval, field performance, realized savings, or certification.

### 2. A measured negative Kuramoto result

The public EIA benchmark is scientifically valuable because it falsifies a
preferred idea under a locked comparison:

- 14,704 panel rows;
- 1,525 frozen holdout rows across eight authorities;
- official EIA, naive, seasonal-naive, Kalman, autoregressive ridge, FFT, and
  wave-family comparisons;
- autoregressive ridge ranked first;
- Kuramoto phase coupling ranked below the accepted baseline;
- promotion and field-validation gates stayed false.

The contribution is not "Kuramoto wins." The contribution is a replayable test
that shows where this implementation did not win and prevents that negative
result from being marketed as a success.

### 3. A candidate for prospective testing

The residual-model replay used 14,704 panel rows and 1,176 frozen holdout rows
across eight authorities. XGBoost residual ranked first at MASE 0.211206, with
six point-improvement comparisons surviving the recorded Holm procedure. The
coverage, promotion, and field gates remained false.

This is the most credible near-term candidate for a prospective study. It is
not yet a champion, savings claim, or production recommendation.

## Ranked Experiment Program

### Experiment 1: Prospective multi-authority router and residual study

**Question:** Can a frozen router or residual candidate improve forecast error
without violating authority-level guardrails after the preregistration date?

**Data:** EIA-930 hourly demand, ingested prospectively after the protocol and
code hashes are frozen.

**Baselines:** official EIA forecast where available, seasonal naive,
autoregressive ridge with 14 lags, Kalman, equal-weight ensemble, and an online
Hedge ensemble.

**Primary endpoint:** authority-level seasonal MASE, aggregated under a locked
rule. Track cumulative regret and worst-authority degradation as guardrails.

**Success rule:** the paired lower confidence bound for the candidate's
improvement over the strongest accepted baseline is positive, and no locked
authority-level guardrail fails.

**Failure rule:** the lower bound is non-positive, a guardrail fails, coverage
is inadequate, or any post-freeze tuning changes the candidate.

**Required artifacts:** preregistration, source authorization, immutable code
and environment hashes, sealed predictions, settlement receipts, authority-level
rows, attrition accounting, and an independent evaluator handoff.

### Experiment 2: Strictly causal FlowForm ablation

**Question:** Does any FlowForm transform add forecast information beyond an
identity transform when preprocessing, tuning budget, and model class are held
constant?

**Design:** evaluate each transform one at a time on pre-declared rolling
origins. Fit every transform using only information available before each
origin. Compare identity, seasonal-naive, and accepted autoregressive baselines.

**Primary endpoint:** paired change in seasonal MASE versus identity, corrected
for multiple FlowForm comparisons with a locked Holm procedure.

**Success rule:** at least one transform has a positive corrected lower
confidence bound and passes all leakage, coverage, stability, and authority
guardrails.

**Failure rule:** no corrected lower bound is positive, the effect is confined
to one authority or regime, or any transform uses future information.

**Interpretation:** a pass would support a narrow transform contribution in the
tested lane. It would not establish a universal FlowForm principle.

### Experiment 3: FlowForm topology resilience on NREL SMART-DS

**Question:** At matched line length or capital budget, does a geometry-informed
network augmentation reduce expected unserved energy relative to radial,
minimum-spanning-tree, and conventional augmentation baselines?

**Primary endpoint:** expected unserved energy under a locked outage ensemble.

**Guardrails:** capital/line-length parity, voltage and thermal constraints,
contingency coverage, and sensitivity to load and outage assumptions.

**Contribution if successful:** a bounded topology-design result on a named,
public distribution-system testbed. Independent replication and field
engineering review would still be required.

### Experiment 4: Topology-aware Kuramoto on MATPOWER

**Question:** Does a power-network Kuramoto control or topology intervention
improve transient synchronization at matched control effort?

**Baselines:** unmodified network, conventional damping/control, and
budget-matched topology interventions.

**Endpoints:** basin stability, phase slips, settling time, maximum frequency
deviation, and control effort.

**Reason to run:** the current EIA implementation is a time-series forecast
candidate, not a full network-coupled dynamical model. This experiment tests the
theory in a domain where topology and synchronization are explicit.

### Experiment 5: Thermal FlowForm in DOE reference buildings

**Question:** Can a geometry-informed routing or control candidate reduce HVAC
or fan energy while preserving comfort in EnergyPlus reference buildings?

**Primary endpoint:** energy use with a locked comfort non-inferiority margin.

**Guardrails:** weather-year coverage, building-type coverage, control effort,
peak demand, and reproducibility across independent simulation environments.

## How to Prove Economic Value

"One percent of one billion dollars is ten million dollars" is arithmetic, not
evidence that a model creates ten million dollars of value. A defensible value
case needs all of the following:

1. A buyer or domain owner defines the native operational decision and approved
   cost function before results are opened.
2. The study measures a prospective change in native units under an accepted
   counterfactual, not a percentage imported from a simulation.
3. The effect passes uncertainty, coverage, safety, and operational guardrails.
4. The buyer validates how technical units map to avoidable cost, including
   implementation cost, capacity limits, rebound effects, and failure modes.
5. An independent evaluator reproduces the analysis or the domain owner
   validates it under agreed field conditions.

Until that chain exists, dollar values must be labeled scenarios or sensitivity
analyses, not savings.

## Literature and Prior-Art Boundary

The repository audit can identify tests not yet run here. It cannot establish
that no one has ever tested an idea. Any novelty statement requires a
documented literature and prior-art search covering:

- Kuramoto methods in power-system stability and forecasting;
- graph and topology optimization for grid resilience;
- causal and learned transforms for time-series forecasting;
- HVAC topology, airflow, and EnergyPlus control research;
- relevant patents, standards, and public implementations.

Use "not yet tested in this repository under this protocol" until that search
is complete.

## Immediate Research Gates

1. Freeze the prospective EIA protocol, baselines, primary metric, guardrails,
   code hash, and settlement rules.
2. Name an outcome-independent evaluator before spending on tuning or compute.
3. Repair or retire any public surface that implies universal FlowForm,
   Kuramoto, savings, or field superiority.
4. Keep the residual candidate labeled `CANDIDATE_NOT_PROMOTED`.
5. Run the causal FlowForm ablation before any new cross-sector marketing.
6. Use public simulation lanes for topology and thermal work, then seek domain
   partners only with the resulting bounded packet.

## Current Decision

No FlowForm or Kuramoto champion is promoted. The next research priority is the
prospective multi-authority EIA study because it has measured public inputs,
accepted baselines, an existing reproducibility capsule, and a candidate that
can be falsified quickly. The scientific contribution to lead with is rigorous
evidence custody and honest baseline comparison, not an unsupported claim of a
new universal law.
