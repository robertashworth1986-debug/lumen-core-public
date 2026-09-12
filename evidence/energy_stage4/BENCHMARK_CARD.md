# LumenCore Energy Benchmark — Stage 4

Status: internal research implementation and reproducible evaluation, not production approval.

## What exists

An exact-time replay benchmark for two new delayed-feedback model-routing candidates over seven standard base forecasters. Parameters were registered before 2025 source acquisition. Ridge training and baseline selection use 2023; candidates may adapt during 2025 only after earlier forecast labels mature. No live equipment controls, trading, dispatch or operating setpoints are involved.

Protocol commit: `80bac1f947122c7c4753f7116d42163e07d3b9d2`.
Execution commit: `3373c339033fcf6e6d2505aad0d8997bf3e65f66`.
GitHub run: `33970218198`.
Findings: `evidence/energy_stage4/FINDINGS_20260905.json`.

## Evidence tiers

**Software integrity:** 24 new and 12 inherited tests pass. Source hashes, exact timestamp pairs, target availability, training-only fitting, negative results and shared comparator samples are checked. Internal replay agrees within floating-point tolerance; this is not independent validation.

**Forecast performance:** 90 of 108 predeclared comparisons scored. Eighteen remain withheld because station 46042's 2025 source returned 404. Nine individual comparator screens passed; zero candidate/location/horizon combinations passed against all three required baselines. A green workflow means execution succeeded, not that the candidate outperformed.

**Physical and economic impact:** not established. The response variable is WVHT squared times APD in square-metres-seconds, not electricity, cash savings, device output or a geothermal metric. A forecast-error reduction cannot be multiplied directly by company revenue or energy spending to estimate savings.

## Useful edge cases

Long complete-lag models lose feature availability under scattered sensor missingness. A fixed historical champion can become less competitive than persistence. Nominal 90% forecast intervals covered about 87.2%-89.8% of outcomes across scored cells. Aggregate improvement can coexist with worse quarterly or high-activity behavior.

## Buyer-owned review checklist

Before testing a buyer dataset, name the decision owner, data rights, incumbent implementation, exact issue/availability times, target units, allowed interventions, evaluation period, missing-data policy and false-alarm/latency costs. Freeze a minimum effect appropriate to that buyer; the current research 5% screen is not a universal commercial threshold. Evaluate any smaller effect using verified decision outcomes and costs, not headline forecast percentages.

Maintain separate approvals for data access, computational benchmark acceptance, independent reproduction, shadow deployment, operational intervention and commercial claims. Passing one does not imply passing another.

## Next research ticket

Freeze short-history/missingness-aware experts and revised uncertainty calibration before another evaluation period. Preserve this stage unchanged. Do not rebrand tuned performance on the now-examined 2025 data as an untouched confirmation.
