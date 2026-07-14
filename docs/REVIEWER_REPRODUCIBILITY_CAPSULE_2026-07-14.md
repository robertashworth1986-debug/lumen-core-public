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
- Frozen input passed: `true`
- Relevant source clean: `false`
- Clean-runner replay: `false`
- Artifact hash lock complete: `false`
- External validation complete: `false`
- Agency certification complete: `false`
- Fixture tests executed: `true`
- Fixture tests passed: `true`
- Source chain SHA-256: `6a576ffda2d27d45bb0a4e930468b13f624929f0073f391325f0f938d51434c6`
- Capsule SHA-256: `f5a005759494e71c7da7f45bbbd67e464902b843e44201fe2c7b20bb703352a6`

## Replayed Suites

### `eia_wave_frozen_holdout`

- Kind: `measured_public_data_replay`
- Passed: `true`
- Elapsed seconds: `35.201`
- Fact projection SHA-256: `66f4fde9d3935fb2ea519fc639ec55fd582f0b2f454d33d973ea365e42c98bbf`
- Facts:
  - `evaluation_rows`: `22530`
  - `selected_candidate`: `lissajous_phase_paths`
  - `best_strategy`: `autoregressive_ridge_p14`
  - `best_mase`: `0.47945937271811834`
  - `kuramoto_mase`: `1.253508683225091`
  - `baseline_comparison_count`: `6`
  - `promotion_gate_passed`: `False`
  - `field_validation_complete`: `False`
- Assertions:
  - `panel_rows` passed=`true` actual=`14704` expected=`14704`
  - `holdout_rows` passed=`true` actual=`1525` expected=`1525`
  - `holdout_authorities` passed=`true` actual=`8` expected=`8`
  - `selected_candidate` passed=`true` actual=`lissajous_phase_paths` expected=`lissajous_phase_paths`
  - `best_strategy` passed=`true` actual=`autoregressive_ridge_p14` expected=`autoregressive_ridge_p14`
  - `best_mase` passed=`true` actual=`0.47945937271811834` expected=`0.47945937271811834`
  - `kuramoto_mase` passed=`true` actual=`1.253508683225091` expected=`1.253508683225091`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `field_validation_complete` passed=`true` actual=`False` expected=`False`

### `eia_residual_frozen_holdout`

- Kind: `measured_public_data_replay`
- Passed: `true`
- Elapsed seconds: `11.405`
- Fact projection SHA-256: `c34a50a95474700e60cd1e162ac371f4bb0233c6a1b207d0f11603b3a2320405`
- Facts:
  - `evaluation_rows`: `16975`
  - `selected_candidate`: `xgboost_residual`
  - `best_strategy`: `xgboost_residual`
  - `best_mase`: `0.21211186326437864`
  - `baseline_comparison_count`: `6`
  - `holm_positive_point_improvement_count`: `6`
  - `promotion_gate_passed`: `False`
  - `coverage_gate_passed`: `False`
  - `field_validation_complete`: `False`
- Assertions:
  - `panel_rows` passed=`true` actual=`14704` expected=`14704`
  - `holdout_rows` passed=`true` actual=`1176` expected=`1176`
  - `holdout_authorities` passed=`true` actual=`8` expected=`8`
  - `selected_candidate` passed=`true` actual=`xgboost_residual` expected=`xgboost_residual`
  - `best_strategy` passed=`true` actual=`xgboost_residual` expected=`xgboost_residual`
  - `best_mase` passed=`true` actual=`0.21211186326437864` expected=`0.21211186326437864`
  - `baseline_comparison_count` passed=`true` actual=`6` expected=`6`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `coverage_gate_passed` passed=`true` actual=`False` expected=`False`
  - `field_validation_complete` passed=`true` actual=`False` expected=`False`

### `mda_open_set_v2`

- Kind: `deterministic_synthetic_falsification_replay`
- Passed: `true`
- Elapsed seconds: `0.205`
- Fact projection SHA-256: `6cbbc86400aa77f0305dd13c3d08b9a46dce26e731b96aade2abf2933d7f56e4`
- Facts:
  - `fixture_chain_sha256`: `25f32a2e03157f6f058f1022bec7d0f0ea151991fc4e1c68d0b91fe59b1e278e`
  - `fixture_count`: `128`
  - `holdout_count`: `36`
  - `candidate_micro_f1`: `0.9433962264150945`
  - `candidate_supported_coverage`: `0.9583333333333334`
  - `candidate_unsupported_mapping_rate`: `0.0`
  - `promotion_gate_passed`: `False`
  - `operational_or_field_claim_allowed`: `False`
- Assertions:
  - `fixture_count` passed=`true` actual=`128` expected=`128`
  - `holdout_count` passed=`true` actual=`36` expected=`36`
  - `candidate_micro_f1` passed=`true` actual=`0.9433962264150945` expected=`0.9433962264150945`
  - `candidate_supported_coverage` passed=`true` actual=`0.9583333333333334` expected=`0.9583333333333334`
  - `candidate_unsupported_mapping_rate` passed=`true` actual=`0.0` expected=`0.0`
  - `promotion_gate_passed` passed=`true` actual=`False` expected=`False`
  - `operational_or_field_claim_allowed` passed=`true` actual=`False` expected=`False`

## Supply-Chain Boundary

- Package versions are exact-pinned, but transitive wheel and source-distribution hashes are not yet locked across supported operating systems.
- The CycloneDX inventory covers the reviewer suite, not every component in the wider repository or deployed service.

## Excluded Full Replays

- `faa_sdr_10k`: The four official FAA SDR CSV source files total about 114 MB and are not bundled in this capsule. Algorithmic fixture tests run, but the 10,000-report result is not clean-room replayed here.
- `locked_source_baseline_replay_sweep`: The broader private/local source universe is not bundled into the public capsule.
- `external_validation`: A clean CI replay is software reproducibility evidence, not independent scientific or field validation.

## Standards References

- [NIST SP 800-218 Secure Software Development Framework 1.1](https://csrc.nist.gov/pubs/sp/800/218/final): Informative source for provenance, protected artifacts, and repeatable verification practices. This capsule is not a NIST certification or full SSDF attestation.
- [CISA 2025 Minimum Elements for a Software Bill of Materials](https://www.cisa.gov/sites/default/files/2025-08/2025_CISA_SBOM_Minimum_Elements.pdf): Informative public-comment-draft reference for component identity and dependency relationships. The emitted inventory is scoped to the reviewer suite and is not a complete product SBOM.
