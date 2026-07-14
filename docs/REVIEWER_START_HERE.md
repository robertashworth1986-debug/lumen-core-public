# Reviewer Start Here

This page is the shortest defensible path through the LumenCore technical record.

## Bottom Line

The repository supports an implemented, tested evidence and benchmarking platform with source-conditioned replay and preserved negative results. Its current repository-wide supported evidence maturity is **Level 3**. It does not yet establish independent field validation, universal model superiority, realized savings, profitable live trading, regulatory approval, or patent scope.

## Read In This Order

1. `README.md` for claim boundaries and the maturity scale.
2. `docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md` for the machine-generated evidence snapshot.
3. `docs/LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md` for route-level wins and non-wins.
4. `docs/FAA_SDR_SOURCE_AUDIT_2026-07-13.md` for the aviation source audit and its raw-data custody boundary.
5. `docs/FAA_SDR_10K_BENCHMARK_2026-07-13.md` for the frozen holdout result and failed promotion gate.
6. `docs/HYBRID_AGENT_OPERATING_MODEL_2026-07-13.md` for agent capabilities and HumanUnlock controls.

## Fast Verification

```powershell
python code/ops/BUILD_QUANT_HUB_REVIEWER_CONTEXT.py
python -m pytest -q tests/test_quant_hub_reviewer_context.py
python -m pytest -q tests/test_faa_sdr_source_audit.py tests/test_faa_sdr_10k_benchmark.py
python -m pytest -q tests/test_external_proof_vault.py tests/test_funding_sprint_reviewer_gate.py
```

The locked replay is broader and may take several minutes:

```powershell
python -m pytest -q tests/test_locked_source_baseline_replay_sweep.py
```

## Claim Check

| Question | Current answer |
|---|---|
| Is the platform implemented? | Yes, for the bounded workflows represented by code and tests |
| Are source-conditioned comparisons recorded? | Yes, with both wins and non-wins |
| Is prospective performance established? | Not repository-wide; each prospective lane must report its own status |
| Has an independent evaluator validated the platform? | No Level 5 receipt is present |
| May this repository authorize a submission, legal filing, spend, or live order? | No; those actions require HumanUnlock |

## External Validation Target

An acceptable Level 5 evaluation must name the evaluator, dataset owner, frozen eligible population, held-out period, baselines, metrics, acceptance threshold, exclusions, and receipt date before outcomes are observed. Commercial value should be estimated only after the external owner accepts both the technical metric and the economic assumptions.

## Citation

Use `CITATION.cff` for the software record. Cite a dated evidence artifact separately when making a result-specific statement.
