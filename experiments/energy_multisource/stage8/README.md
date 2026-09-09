# LumenCore frozen delta packets — Stage 8

**Three measured domain packets, one replayable evidence bundle, six unmeasured transfer contracts.** This extends the existing proof-to-pilot validation lane and advances the external-validation/paid-pilot outcome. It does not establish a new product or authorize operational control.

Start with `FINDINGS.md`. Inspect each `domain_packets/*/PACKET.json`, then `DESCRIPTIVE_SHORTLIST.json`. All losses and holds remain in `results/metrics/` and `results/metrics.csv`; primitive predictions, timestamps and outcomes are in `results/arrays/`. The domain packets point to their complete evidence within the shared bundle rather than duplicating or quietly omitting failures.

## What is measured

| Packet | Data | Native measures | Horizons |
|---|---|---|---|
| Grid | Eight EIA balancing authorities | Daily demand, MWh | 1, 3, 7 days |
| Marine | Five NOAA NDBC stations | Hourly mean of WVHT² × APD, m²s | 1, 3, 6 hours |
| Geothermal | Four Utah FORGE circulation sensors | Production flow gpm, pressure psi, temperature °F, injection pump rate bpm | 10, 30, 60 minutes |

The marine measure is a resource-activity proxy, not electrical production or calibrated wave power. FORGE timestamps use the source's unspecified local clock. EIA daily labels and revised historical values do not establish real-time publication availability. Sources are never joined across incompatible clocks or units.

The six transfer contracts cover manufacturing, water, telecom, aviation maintenance, healthcare operations and finance operations. They contain field mappings, domain-specific failure cases and explicit missing prerequisites. They have **zero measured rows and no validated uplift**.

## Frozen experiment

Seventeen series × 23 scenarios × three horizons produce 1,173 prediction-array packets. Each has three candidates against two baselines across three slices, yielding 21,114 metric records. These records reuse observations and are not independent trials.

- Baselines: persistence and seasonal repetition. These are reference comparators, not a claim to reproduce a buyer's incumbent or the lane's earlier champions.
- Candidates: five-step median, clipped/damped trend and 50/50 persistence–median blend. No model selection on this evaluation set.
- Scenarios: clean; 10%/30% missingness with two seeds; burst gaps; delays of 1/3/12 steps; positive/negative spikes; stuck sensors; positive/negative bias and drift; two noise seeds; quantization; 110%/90% gain; combined delay/missingness; outage.
- Candidate histories expire after three steps. Seasonal memory follows its declared historical lag, so it can remain available during the early part of an outage. Ground truth is never imputed or corrupted.
- Metrics: identical paired-row MAE, RMSE, 95th-percentile absolute error, signed bias, prediction/pair coverage, native-unit deltas and chronological-quartile stability.
- Slices: all, high-at-issue, ramp-at-issue. Thresholds come only from calibration. Clean issue-time slice labels are privileged offline diagnostics, not model inputs or verified production detectors.
- Candidate-only screen: at least 100 pairs, at least 90% pair coverage, at least 5% MAE improvement, no p95 regression and positive deltas in at least three time quartiles. Slice support thresholds are reporting rules, not effective sample sizes or significance guarantees.

All source histories were previously available to this lane. Local pre-run code/protocol commits are not independent pre-outcome seals. No p-values, confirmatory inference, causality, realized savings or autonomous deployment claims are made.

## Integrity and the retained rejected run

The first run was rejected when its consolidated JSON was truncated during artifact handoff. The format-only revision replaced that file with bounded shards and added an oversized-JSON rejection test. The original protocol/manifest hashes and exposure are retained in `PROTOCOL.json`. Models, sources, thresholds and stress settings did not change; all 21,114 CSV metric records agree between the two runs.

The verifier authenticates the three frozen source files, replays normalization and every prediction array, independently recomputes every paired metric using a separate scalar/statistics implementation, reconciles CSV and JSON, checks coverage of all planned cells, and performs independent scalar prediction spot checks. The cached entry point decodes each NPZ array once and then invokes the unchanged frozen verifier; its own hash is recorded separately in the receipt. Full prediction replay shares the producer; it is not an independent implementation of every transformation. Cryptographic hashes establish content integrity against the pinned digest, not authorship or independent timestamping.

## Reproduce or verify

Use Python 3.11.9 and NumPy 2.3.5. The included institutional lock records the tested dependency environment. Replay and verification require no live APIs once the inputs and dependencies are present. Do not execute unfamiliar bundle code without normal code review.

From the extracted bundle root:

```bash
python source/experiments/energy_multisource/stage8/verify_stage8_cached.py \
  --packet results --inputs inputs \
  --expected-manifest-sha256 73ff9e4ca4fb27eea70b6e74180cf959217a38d2f8a4487f56ae280f99dec370 \
  --receipt reviewer-verification.json

python source/experiments/energy_multisource/stage8/run_stage8.py \
  --inputs inputs --out reviewer-rerun

python -m pytest -q source/experiments/energy_multisource/stage8
```

A new run has a new creation timestamp and manifest; compare its numerical arrays and metric shards, not the whole-run manifest hash. The verifier refuses nonempty run targets and overwritten verification receipts. Preserve `results/` unchanged; put notes and receipts outside it.

In a repository checkout, use the same script paths without the `source/` prefix. Inputs are the pinned `energy-stage4-ci.zip`, `utah-forge-gdr1683.zip` and `eia_grid_validation_panel_20260713.json.gz`; the two ZIPs are from the existing `research-energy-20260905-584e88a0f376` GitHub release.

## Sources and next decision

[EIA grid data documentation](https://www.eia.gov/electricity/gridmonitor/about), [NOAA NDBC wave definitions](https://www.ndbc.noaa.gov/faq/wavecalc.shtml), and [Utah FORGE GDR 1683 circulation dataset](https://gdr.openei.org/submissions/1683) describe the underlying data. Exact archive and extracted-member hashes are retained in the protocol and series metadata.

Take one bounded candidate into a buyer-owned, genuinely fresh replay with an attested incumbent, publication-time records, material-effect threshold, adverse-regime requirements and independent reviewer. Existing Stage 6 prospective-evaluation materials remain drafts. Nothing in these packets turns research error reduction into cash flow, endorsement, plant performance or safety assurance.
