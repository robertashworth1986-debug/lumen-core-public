# FALCON Direct-to-Phase-II Go/No-Go and Gap Map

Assessment date: 2026-07-15

Topic: `DPA26BZ04-DV016`

Decision owner: Robert Ashworth / proposing SBC

## Current Decision

**Final-submission status: NO-GO today.**

The repository contains credible structured-data machine-learning, frozen-baseline, statistical-comparison, prospective-routing, reproducibility, and real-model FALCON development evidence. Three frozen real-model attempts are now preserved: v1 tied the fixed-ML comparator, v2 scored `25/30`, and v3 scored `27/30` while failing its stability and per-context gates. It still does not demonstrate improvement over both justified ML-only and LLM-only state-of-the-art comparators on a reserved two-domain holdout, and it has no documented scholarly impact. Those are material FALCON and Direct-to-Phase-II readiness gaps, not formatting details.

**Build decision: GO for a bounded evidence sprint.** The opportunity closes 2026-08-19, leaving time to generate a truthful feasibility packet if the red gates below are closed without changing the protocol after seeing holdout results.

## Evidence Already Available

| Evidence lane | Current bounded fact | Value to FALCON | Status |
| --- | --- | --- | --- |
| EIA structured forecasting | Frozen untouched holdout selected `xgboost_residual` at mean MASE `0.212112`; direct LightGBM `0.235871`; direct XGBoost `0.264246` | Demonstrates structured-data ML, fixed baselines, native-unit metrics, and preserved null gates | Strong but internal |
| Baseline statistics | Six comparisons were Holm-positive, but one predeclared comparator row failed its full pass condition and the composite protocol gate remained closed | Demonstrates claim discipline and non-cherry-picked reporting | Strong integrity signal |
| Hybrid routing | Historical routed MASE `0.196873` versus fixed specialist `0.212112`; explicitly exploratory | Motivates contextual routing without claiming prospective confirmation | Partial |
| Prospective ledgers | Frozen route maps, pre-target seals, append-only SHA-256 prediction and settlement chains | Directly supports reproducible analytic traces | Strong architecture, results pending |
| Reviewer capsule | 3/3 suites, 31/31 assertions, dependency closure matched; external validation explicitly false | Supports replayability and environment capture | Strong internal reproducibility |
| Multi-domain evidence | EIA, MDA mapping, FAA, NASA and other lanes exist, including preserved failed gates | Supplies candidate datasets and failure-analysis history | Partial; must select representative FALCON datasets |
| FALCON real-model lineage | v1 hybrid tied fixed ML; v2 constrained routing scored `25/30`; v3 pinned Qwen routing scored `27/30`, fixed all noise/dropout rows, and failed nominal/stability gates | Demonstrates real-model execution, output controls, exact model custody, and honest null preservation | Strong method-development evidence; no qualifying lift |

## Red Gates

| Gate | Why it is mandatory | Closure evidence | Owner |
| --- | --- | --- | --- |
| Qualifying real LLM fusion | FALCON requires selected structured-data ML combined with one or more LLMs; v1 executed but did not beat fixed ML | New reserved-holdout protocol, frozen model/revision/license, prompts, raw outputs, validated schemas, executable code, and measured hybrid lift | Technical |
| ML-only and LLM-only comparisons | FAQ requires improvement over both comparator families | Same split, same rows, same ground truth, predeclared metrics, uncertainty, and preserved null outcomes | Technical |
| Two-domain generality | Final demonstrations require at least two datasets from different domains | Two source-backed datasets, domain-specific ground truth, identical evaluation contract, cross-domain summary | Technical |
| Hallucination controls | Topic requires mitigation plus verifiable/reproducible traces | Allowlisted outputs, abstention, unsupported-output rate, prompt/output hashes, replay test | Technical |
| Direct-to-Phase-II equivalence | Feasibility must already satisfy the Phase I work outside prior SBIR/STTR funding | Dated prior-work chronology, reports, test data, prototype evidence, proposer/PI performance statement | PI and counsel |
| Scholarly impact | FAQ strongly prefers reports with data/analysis and demonstrated impact | Public preprint or technical report plus third-party citation, review, reproduction, or documented expert use | PI / external reviewer |
| IP rights | The SBC must own or license the IP used in the feasibility and proposed work before submission | Counsel-reviewed ownership/license memo tied to official filed documents | PI and counsel |
| Enterprise-scale claim | Phase II calls for enterprise-scale interactive analysis | Bounded scale test now; Phase II plan with measurable row, latency, memory, and concurrency targets | Technical |
| Commercial pull | DP2 transition case needs users and a credible path | Non-government advocacy/interest letters only when they substantiate a real claim; named use cases and pilot protocol | Business / PI |

## Human Certification Gates

The following may be prepared but must not be guessed or certified by automation:

- SBC eligibility and ownership representations
- prior federal SBIR/STTR funding relationship to the cited feasibility work
- IP ownership or license rights
- foreign affiliations and foreign-national participation
- organizational conflicts of interest
- company commercialization report
- final labor rates, indirect rates, accounting basis, subcontractor quotes, and cost certifications
- final proposal certification and `Submit Proposal` action

## Evidence Sprint

| Target date | Deliverable | Pass condition |
| --- | --- | --- |
| 2026-07-15 | Real-model qualification lineage v1-v3 frozen | Completed as preserved null evidence; fixture `30/30` explicitly excluded from model-performance claims |
| 2026-07-16 | New same-row comparative protocol frozen | Git commit, protocol SHA-256, reserved holdout, and tests green before execution |
| 2026-07-18 | Full ML-only, LLM-only, and hybrid run on two bounded domains | Model revision recorded; no proxy labeled as an LLM; raw traces and all nulls preserved |
| 2026-07-20 | Comparator and failure report | ML-only, LLM-only, hybrid, deterministic-router control; confidence intervals and nulls |
| 2026-07-23 | DP2 feasibility chronology | Every cited artifact dated, hashed, attributable to SBC/PI, and funding-source tagged |
| 2026-07-27 | External review packet | Reproduction instructions and a narrow, falsifiable reviewer ask |
| 2026-07-31 | Volume 2 alpha | 20-page white-paper budget and 15-slide deck complete without unsupported claims |
| 2026-08-05 | Cost and commercialization alpha | Workbook formulas intact; assumptions and quotes documented |
| 2026-08-10 | Red-team review | Page limits, citations, legal gates, secrets, malware, and DSIP completeness checked |
| 2026-08-14 | Submission candidate frozen | All artifacts hashed; human certifications complete; no open red gate |
| 2026-08-19 before 12:00 PM ET | DSIP receipt preserved | Final user-authorized submission and downloaded confirmation receipt |

## Claim Boundary

Until the red gates close, the defensible claim is:

> LumenCore has internally reproducible structured-data ML and three frozen real-model FALCON development attempts with explicit null preservation. The v1 hybrid tied fixed ML; v2 and v3 routing qualification gates failed. A reserved-holdout, same-row ML-only, LLM-only, and hybrid comparison remains open. No hybrid superiority, external validation, agency approval, enterprise-scale performance, universal superiority, or DP2 eligibility is claimed.
