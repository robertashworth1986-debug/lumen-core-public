# Reviewer Start Here

This page is the shortest defensible path through the LumenCore technical record.

## Bottom Line

The repository supports an implemented, tested evidence and benchmarking platform with source-conditioned replay and preserved negative results. Its current repository-wide supported evidence maturity is **Level 3**. It does not yet establish independent field validation, universal model superiority, realized savings, profitable live trading, regulatory approval, or patent scope.

## Read In This Order

1. `README.md` for claim boundaries and the maturity scale.
2. `docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md` for the machine-generated evidence snapshot.
3. `evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260716.json` for the dated, public-safe successor snapshot and terminal-chain receipts.
4. `docs/EXTERNAL_VALIDATION_AUTHORITY_DOCKET_2026-07-14.md` for the predecessor-lane evaluator decision, archived clean-runner receipt, and exact Level 4/5 gates.
5. `docs/EXTERNAL_EVALUATOR_ACCEPTANCE_HANDOFF_2026-07-14.md` for the evaluator-owned receipt and fail-closed acceptance procedure; it must be explicitly amended before it governs the hourly successor.
6. `docs/LOCKED_SOURCE_BASELINE_REPLAY_SWEEP_2026-06-30.md` for route-level wins and non-wins.
7. `docs/FAA_SDR_SOURCE_AUDIT_2026-07-13.md` for the aviation source audit and its raw-data custody boundary.
8. `docs/FAA_SDR_10K_BENCHMARK_2026-07-13.md` for the frozen holdout result and failed promotion gate.
9. `docs/HYBRID_AGENT_OPERATING_MODEL_2026-07-13.md` for agent capabilities and HumanUnlock controls.

## Independent Review Roles

| Review role | Decision owned by reviewer | Evidence or receipt |
|---|---|---|
| Reproducibility reviewer | Can the bounded public result be replayed from pinned inputs on an independent runner? | Reviewer capsule receipt, logs, SBOM, and checksum manifest |
| Domain and data owner | Are the source, eligible population, exclusions, baselines, and operational metric suitable for the stated use? | Dated protocol acceptance and authority artifact |
| Security and privacy reviewer | Are custody, access, dependency, secret-scanning, privacy, and HumanUnlock controls adequate for the bounded evaluation? | Scoped findings, disposition record, and artifact hashes |
| Independent technical evaluator | Did the frozen prospective experiment meet its predeclared gate without operator substitution or backfill? | Completed evaluator-owned acceptance and result receipts |

Each role is independent of the operator. A reviewer may accept one bounded decision without endorsing the platform, a patent, an agency use, or a commercial claim.

## Fast Verification

```powershell
python code/ops/BUILD_QUANT_HUB_REVIEWER_CONTEXT.py
python code/ops/BUILD_EIA_HOURLY_RUNTIME_PROJECTION.py --check
python code/ops/BUILD_EXTERNAL_VALIDATION_AUTHORITY_DOCKET.py --check-only
python code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py --expect-template
python -m pytest -q tests/test_quant_hub_reviewer_context.py
python -m pytest -q tests/test_external_validation_authority_docket.py
python -m pytest -q tests/test_external_evaluator_acceptance.py
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

An acceptable Level 5 evaluation must name the evaluator, dataset owner, frozen eligible population, held-out period, baselines, metrics, acceptance threshold, exclusions, and receipt date before outcomes are observed. The current authority record and handoff are scoped to the preserved daily predecessor; they do not silently transfer to the hourly successor. The successor needs an explicit protocol-specific amendment or replacement acceptance record. Commercial value should be estimated only after the external owner accepts both the technical metric and the economic assumptions.

## Citation

Use `CITATION.cff` for the software record. Cite a dated evidence artifact separately when making a result-specific statement.
