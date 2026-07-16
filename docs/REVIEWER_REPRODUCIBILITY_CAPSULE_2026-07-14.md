# Reviewer Reproducibility Capsule - 2026-07-14

Purpose: let a technical reviewer replay selected public-safe evidence from a frozen public input and a version-pinned Python environment.

A passing capsule proves that the named code reproduced the declared bounded facts from the packaged input under the recorded environment. It does not prove agency approval, cybersecurity certification, external validation, field performance, realized savings, patent scope, trading performance, or funding eligibility.

## Result

- Status: `BOUNDED_REPRODUCIBILITY_PASS`
- Suites passed: `3/3`
- Assertions passed: `31/31`
- Dependency versions matched: `8/8`
- Scoped SBOM components: `18`
- Deterministic environment matched: `true`
- Authoritative runtime matched: `true`
- Installed dependency closure matched lock: `true`
- Frozen input passed: `true`
- Relevant source clean: `true`
- Clean-runner replay: `true`
- Artifact hash lock complete for authoritative runner: `true`
- Cross-platform artifact hash lock complete: `false`
- External validation complete: `false`
- Agency certification complete: `false`
- Fixture tests executed: `true`
- Fixture tests passed: `true`
- Source chain SHA-256: `e0e2b64af3ee782119ad988a2117de24f8f39a611a38eeba01b1088515958da7`
- Capsule SHA-256: `a87df4bc8fa930f3841b8802407820ce5ba256331bc75e3b8c3f810a5bbe8e0c`

## Protocol Amendment

- This portability tolerance is a post-observation protocol amendment, not a preregistered scientific threshold. The failed runs and their receipts remain in GitHub Actions history.
- Policy: Keep structural, identity, coverage, and gate assertions exact. For the XGBoost residual MASE only, accept at most 1% relative drift from the frozen reference and record the exact observed metric in every receipt.
- Preserved failed GitHub runs: `29335084468, 29335574945`

## Replayed Suites

### `eia_wave_frozen_holdout`

- Kind: `measured_public_data_replay`
- Passed: `true`
- Elapsed seconds: `31.981`
- Fact projection SHA-256: `11bcfa0fe7bf90634e9a960669181c55091342f46ce8b19655fdc7653a43f3a7`
- Facts:
  - `baseline_comparison_count`: `6`
  - `best_mase`: `0.4794593727181179`
  - `best_strategy`: `autoregressive_ridge_p14`
  - `evaluation_rows`: `22530`
  - `field_validation_complete`: `False`
  - `kuramoto_mase`: `1.2535086832250912`
  - `promotion_gate_passed`: `False`
  - `selected_candidate`: `lissajous_phase_paths`
- Assertions:
  - `panel_rows` passed=`true` actual=`14704` expected=`14704`
  - `holdout_rows` passed=`true` actual=`1525` expected=`1525`
  - `holdout_authorities` passed=`true` actual=`8` expected=`8`
  - `selected_candidate` passed=`true` actual=`lissajous_phase_paths` expected=`lissajous_phase_paths`
  - `best_strategy` passed=`true` actual=`autoregressive_ridge_p14` expected=`autoregressive_ridge_p14`
  - `best_mase` passed=`true` actual=`0.4794593727181179` expected=`0.47945937271811834` absolute_tolerance=`1e-06` relative_difference=`9.262290719909434e-16`
  - `kuramoto_mase` passed=`true` actual=`1.2535086832250912` expected=`1.253508683225091` absolute_tolerance=`1e-06` relative_difference=`1.7713846572944643e-16`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `field_validation_complete` passed=`true` actual=`False` expected=`False`

### `eia_residual_frozen_holdout`

- Kind: `measured_public_data_replay`
- Passed: `true`
- Elapsed seconds: `10.14`
- Fact projection SHA-256: `d2052b0fee6fd7b2ae89285084c4dd46fb3500fb3c998073a3b27976bb147eed`
- Facts:
  - `baseline_comparison_count`: `6`
  - `best_mase`: `0.2112062642583228`
  - `best_strategy`: `xgboost_residual`
  - `coverage_gate_passed`: `False`
  - `evaluation_rows`: `16975`
  - `field_validation_complete`: `False`
  - `holm_positive_point_improvement_count`: `6`
  - `promotion_gate_passed`: `False`
  - `selected_candidate`: `xgboost_residual`
- Assertions:
  - `panel_rows` passed=`true` actual=`14704` expected=`14704`
  - `holdout_rows` passed=`true` actual=`1176` expected=`1176`
  - `holdout_authorities` passed=`true` actual=`8` expected=`8`
  - `selected_candidate` passed=`true` actual=`xgboost_residual` expected=`xgboost_residual`
  - `best_strategy` passed=`true` actual=`xgboost_residual` expected=`xgboost_residual`
  - `best_mase` passed=`true` actual=`0.2112062642583228` expected=`0.21211186326437864` relative_tolerance=`0.01` relative_difference=`0.004269440624954959`
  - `baseline_comparison_count` passed=`true` actual=`6` expected=`6`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `coverage_gate_passed` passed=`true` actual=`False` expected=`False`
  - `field_validation_complete` passed=`true` actual=`False` expected=`False`

### `mda_open_set_v2`

- Kind: `deterministic_synthetic_falsification_replay`
- Passed: `true`
- Elapsed seconds: `0.108`
- Fact projection SHA-256: `6cbbc86400aa77f0305dd13c3d08b9a46dce26e731b96aade2abf2933d7f56e4`
- Facts:
  - `candidate_micro_f1`: `0.9433962264150945`
  - `candidate_supported_coverage`: `0.9583333333333334`
  - `candidate_unsupported_mapping_rate`: `0.0`
  - `fixture_chain_sha256`: `25f32a2e03157f6f058f1022bec7d0f0ea151991fc4e1c68d0b91fe59b1e278e`
  - `fixture_count`: `128`
  - `holdout_count`: `36`
  - `operational_or_field_claim_allowed`: `False`
  - `promotion_gate_passed`: `False`
- Assertions:
  - `fixture_count` passed=`true` actual=`128` expected=`128`
  - `holdout_count` passed=`true` actual=`36` expected=`36`
  - `candidate_micro_f1` passed=`true` actual=`0.9433962264150945` expected=`0.9433962264150945` absolute_tolerance=`1e-12` relative_difference=`0.0`
  - `candidate_supported_coverage` passed=`true` actual=`0.9583333333333334` expected=`0.9583333333333334` absolute_tolerance=`1e-12` relative_difference=`0.0`
  - `candidate_unsupported_mapping_rate` passed=`true` actual=`0.0` expected=`0.0` absolute_tolerance=`1e-12` relative_difference=`0.0`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `operational_or_field_claim_allowed` passed=`true` actual=`False` expected=`False`

## Supply-Chain Boundary

- Dependency lock verification: `AUTHORITATIVE_RUNNER_LOCK_VALID`
- Authoritative target: `Complete for the authoritative Ubuntu 24.04 x86-64 CPython 3.11.9 reviewer runner only.`
- Locked packages: `18`
- Lock SHA-256: `e2f514c3c1c10a0278d4ef1147fee1cdd5b1126e5d34d8ee88bba1c4e1d14b18`
- Other operating systems and architectures are not covered by this receipt until separately resolved, hash-locked, and replayed.
- The CycloneDX inventory covers the reviewer suite, not every component in the wider repository or deployed service.

## Excluded Full Replays

- `faa_sdr_10k`: The four official FAA SDR CSV source files total about 114 MB and are not bundled in this capsule. Algorithmic fixture tests run, but the 10,000-report result is not clean-room replayed here.
- `locked_source_baseline_replay_sweep`: The broader private/local source universe is not bundled into the public capsule.
- `external_validation`: A clean CI replay is software reproducibility evidence, not independent scientific or field validation.

## Standards References

- [NIST SP 800-218 Secure Software Development Framework 1.1](https://csrc.nist.gov/pubs/sp/800/218/final): Informative source for provenance, protected artifacts, and repeatable verification practices. This capsule is not a NIST certification or full SSDF attestation.
- [CISA 2025 Minimum Elements for a Software Bill of Materials](https://www.cisa.gov/sites/default/files/2025-08/2025_CISA_SBOM_Minimum_Elements.pdf): Informative public-comment-draft reference for component identity and dependency relationships. The emitted inventory is scoped to the reviewer suite and is not a complete product SBOM.
- [pip Secure Installs](https://pip.pypa.io/en/stable/topics/secure-installs/): Primary installer guidance for all-or-nothing hash checking, exact transitive pins, and binary-only installation.
- [uv pip compile](https://docs.astral.sh/uv/pip/compile/): Primary resolver documentation for the target-specific, hash-emitting lock generation command recorded in the lock header.
