# LumenCore Live Breadth & Proof Addendum

**Review date:** September 22, 2026 (US Central).

**Purpose:** Select one buyer-owned validation decision from the existing evidence.

**Status:** First-party review; no independent acceptance, field savings, booked revenue or licensing agreement is established here.

## What is ready for review

Two complete public EIA replay windows retain their inputs, prediction rows, code identities, environments, manifests and original failed gates. Four additional sector cards below identify retained synthetic or negative findings. They are not six independent successes or six operational products.

The strongest next engagement is a scope-matched, timestamped load-forecast shadow comparison. A manufacturing workflow is a separate candidate for owner measurement, not a transfer of the forecasting result into factory energy savings.

| Card / sector | Frozen result | What prevents promotion |
|---|---|---|
| EIA original / electricity forecasting | 1,176 paired authority-days. Candidate MAE 15,979.087 MWh versus 17,874.172 for direct LightGBM with the same features: **10.602% lower error**. Versus archival EIA DF: 36,568.783 to 15,979.087 MWh, 56.304% lower. | Four authorities miss the 150-day minimum; SWPP exceeds the original regression threshold against ridge. The archival DF comparator is not a scope-matched operational incumbent. |
| EIA later / electricity forecasting | Same selected candidate; 285 paired authority-days. MAE 16,107.044 MWh versus direct LightGBM 19,765.544: **18.509% lower error**. Versus archival DF: 35,092.867 to 16,107.044 MWh, 54.102% lower. | 285/464 possible rows survive; SWPP has no eligible rows; available authorities have only 24–58 days; 18 authority-month units fall below the 40-unit gate. |
| Thermal ventilation / building cooling | Retained source-conditioned synthetic stress comparisons are positive against three registered baselines; best score delta +0.148870, straight-duct comparison +0.122835. | Synthetic score units, not metered heat transfer, validated CFD, comfort, kWh or money. Global multiplicity-adjusted positive count is zero. |
| Leaf-vein topology / transport and network design | Three wins in five synthetic comparisons, but **−0.053173** against the named minimum-spanning-tree comparator; route mean −0.008167. | The adverse baseline is retained. No general routing superiority, real traffic, customer topology or operating-cost validation. |
| FAA SDR / maintenance-report triage | 10,000 public reports; hybrid macro-F1 0.142170 versus strongest approved baseline 0.139775. | Multiplicity-adjusted primary improvement failed; candidate remains unpromoted. This is not airworthiness, failure prediction, FAA/OEM validation or maintenance savings. |
| Source-native market forecasting | 22 descriptive mean wins among 48 candidate/source/baseline comparisons. | All 48 are inferentially insufficient under the declared sample rule; zero globally significant positive comparisons. No alpha, profit, trading or capacity claim. |

These numbers were read from retained result objects, not the older prose summaries.
The original and later EIA windows are retrospective and previously inspected.
Historical source records may have been revised. A feature-leakage check does not
prove that each lag was available at its actual decision cutoff. The selected
candidate was not refit or reselected on either reported 2026 window.

**Forecast-error MWh is not electricity saved.** The primary EIA protocol metric
is seasonal MASE; the MAE percentages above are descriptive comparisons. Keep
all authorities, months, exclusions and adverse results in the review.

## Public EIA packet and verification

Start with the [executable EIA review note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md).
It links the original plan, later plan, all comparisons and exact prediction rows.

| Packet | Reviewed manifest SHA-256 |
|---|---|
| [Original](../evidence/reproducibility/eia_constraint_review_20260921/manifest.json) | `d89c5503a5191531b66bedd22d5cda6d316a7fa12e611cff1979eb926b47f92f` |
| [Later](../evidence/reproducibility/eia_constraint_later_window_20260921/manifest.json) | `8d5804c79883236a1ca22bc87428ecb7088e788f47c145d1a2d3a6ca70784295` |

From a trusted reviewed checkout:

```powershell
python code/ops/VERIFY_EIA_CONSTRAINT_REVIEW.py --packet original
python code/ops/VERIFY_EIA_CONSTRAINT_REVIEW.py --packet later
```

Verification checks complete pinned membership, canonical paths, byte counts
and content hashes. It needs no model fitting. Scoped Git attributes preserve
the frozen bytes on Windows; expected hashes and historical results are unchanged.
A matching first-party hash is custody evidence, not independent validation.

The other four cards are selected from three retained result files:

| Retained result identity | Generated UTC | SHA-256 |
|---|---|---|
| `locked_source_baseline_replay_sweep_latest.json` (thermal and topology cards) | 2026-08-01T14:43:48Z | `82d49c764f520efc459d65ab3766fa9c42ef7e30f76b085cf9ddf81a84c2f43e` |
| `faa_sdr_10k_benchmark_latest.json` | 2026-07-14T02:47:47Z | `f5ff18ce8c87749e724ab0f393a56d58fd517144bd84d0ac44186cfcd2756074` |
| `market_signal_source_native_benchmark_latest.json` | 2026-07-29T13:48:55Z | `e2af8f9a4684714dc1243d718af99b77bd2da70d9094cee8086c324c8a3cd0ab` |

Those three retained files support internal diligence and scope selection.
Their complete code/data/dependency closures are not asserted to be public
reproduction packages. Review redistribution rights and the full source chain
before an external transfer. Do not replace them with screenshots or a
favorable-only extract.

## Constraints that matter to the next pilot

| Constraint | Observed evidence or explicit missing fact | Required response |
|---|---|---|
| Source availability at decision time | Historical EIA rows and lag dates exist; as-issued receipt times are not established. | Capture each version with first-seen/issue time and source identity before forecasting. |
| Comparator scope | EIA permits its business forecast to differ in scope from reported physical demand. | Obtain a buyer-accepted incumbent for the same target, cutoff, geography and horizon. |
| Forecast-history coverage | Later replay retains only 61.42% after target and 28-day history requirements. | Measure eligible and excluded rows, missingness and fallback; never count abstention as a win. |
| Authority coverage | Original minimum 90 versus required 150 days; later SWPP contributes zero. | Keep the original coverage gate and gather additional eligible observations. |
| Adverse subgroup | SWPP regression 0.074058 exceeds the maximum 0.05 against ridge. | Retain the baseline; test an unchanged candidate with subgroup/tail gates. |
| Effective inference units | Later EIA has 18 versus required 40 authority-month units; market comparisons lack declared independent-series sufficiency. | Collect the required independent units; rerunning identical rows adds no independent evidence. |
| Operating tails | Seven of 52 original authority-month comparisons against EIA worsen on seasonal MASE. | Report all months, failure regimes, worst cases and effect uncertainty. |
| Physical equivalence | Synthetic topology/thermal scores have no accepted physical energy conversion. | Measure equivalent useful output, quality, ambient/load conditions, failures, auxiliaries and control overhead. |
| Dollar attribution | No buyer-owned action policy, avoidable cost baseline or realized outcome is accepted. | Keep verified savings unknown; use a separately labeled scenario only. |
| Duplicate economic benefit | Several constraints may affect the same job, load or avoided failure. | Define an exclusive accounting boundary; do not sum overlapping opportunities. |
| Evidence transfer integrity | Windows line-ending conversion changed frozen text bytes before verification. | Preserve exact frozen files; do not repair integrity failures by changing expected digests. |
| Legacy producer semantics | Scenario rows, intake flags and reported amounts are not intervention measurements. Missing money is not zero money. | Preserve model/report/measurement classes and signed losses through every export and truth-chain snapshot. |
| Owner fit and adoption | The cohort research contains 207 questions across 69 businesses; operating baselines and accepted pilots remain unknown. | Ask the owner to choose one recurring task and one observable successful outcome. |

The 921-row legacy infrastructure ledger is a scenario inventory. Its 19 latest
source/constraint entries trace to fixed example producers, including repeated
ISO_NE, HHS_FEED and FEDWIRE_OPS scenarios. A recent writer timestamp does not
turn those rows into current measured interventions. Their dollar arithmetic
cannot support buyer savings, government-grade status or permission to scale.

A useful five-level dependency path is: **source receipt → target/scope alignment
→ eligible lag/coverage set → frozen candidate comparison → buyer action and net
cost**. Each arrow is an information requirement. A repair upstream is valuable
only if the downstream equivalent-service result is demonstrated; the chain
itself is not proof of an energy improvement.

## Annual economics without inventing savings

Use buyer-owned quantities with compatible units:

`Annual net cash benefit = attributable avoided cash cost − recurring operating cost`

`First-year net cash benefit = annual net cash benefit − one-time integration/setup cost`

For a scenario based on eligible spend, explicitly identify the affected annual
cash-cost base, the cost-reduction fraction, adoption, attribution, exclusions
and overlap before multiplication. A forecast-error fraction, synthetic score,
processing speedup or source-row count is not a cost-reduction fraction.

Staff capacity is a separate quantity:

`Annual staff-capacity value = avoided hours per month × loaded hourly cost × 12`

For illustration only, 8 hours/month at an assumed $50/hour is $4,800/year;
subtracting an assumed $600 annual tool cost gives $4,200 before setup costs.
Ten hours/month at the same assumed rate is $6,000/year before costs. Neither
example is an observed result, a quote, a cash-saving promise or evidence that a
particular business can remove those hours. Freed time becomes cash savings only
when an actual avoidable cash expense is removed; it may instead increase capacity.
Use uncertainty and downside cases, not only a point estimate.

Physical electricity uses whole-system metered energy per equivalent accepted
output. Include warm-up, failed runs, rework, support equipment and any extra
sensing/compute/control energy. Price only the verified bill-relevant difference
under the buyer's actual tariff; do not assume every saved kWh changes demand charges.

## One reviewable commercial decision

Use the existing [buyer intake](LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md),
[bounded offer](LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md) and
[SOW template](LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md).
The launch offer remains a proposed $7,500, one-source/one-baseline validation
scope; buyer acceptance, budget, rights and terms remain unestablished.

For the next scope, name the owner, accepted incumbent, source permissions,
service definition, primary metric, cutoff, observation period, failure rules,
cost policy and commercial decision before scoring. Return hold or reject when
the gate fails. An internal-use license can be discussed only with the actual
software/data rights and permitted use defined; no license, exclusivity,
endorsement or contract is created by this addendum.

Existing [cohort packages](https://lumen-core.ai/cohort/directory.html) remain free.
The first owner exercise is one work item with a clear next step and acceptance
criteria. A larger tool catalog is not evidence of adoption.

**Our strength is making everyone else stronger.**
