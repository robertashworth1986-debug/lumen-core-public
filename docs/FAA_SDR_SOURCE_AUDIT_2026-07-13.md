# FAA SDR Source Audit and 10,000-Scenario Readiness

Generated UTC: `2026-07-14T01:56:50.352805+00:00`

## Decision

- Pulled and hashed reports: `226,124` across `4` yearly files.
- Unique report keys: `226,124`; duplicate-key rows: `0`.
- Report-level 10,000-row holdout feasible: `true`.
- Engine-populated 2026 holdout rows: `869`.
- Rolls-Royce-family 2026 holdout rows: `75`.
- Benchmark executed: `false`.

The defensible next study is a report-level maintenance-triage benchmark. An engine-specific or Rolls-Royce-specific 10,000-row claim is not supported by this public slice.

## Source Receipts

| Year | Rows | Bytes | Columns | Schema match | SHA-256 |
|---:|---:|---:|---:|---|---|
| 2023 | 62,686 | 32,895,116 | 76 | true | `f08d1d62eeb662655240147527f7f532acd76d0122ce2af929d73d5ff1c1e42d` |
| 2024 | 66,073 | 33,743,573 | 76 | true | `0ec88e723365194d01721d0a00842b969bb8f03f62c85ac2708d0c903ac8cb61` |
| 2025 | 67,521 | 33,116,503 | 76 | true | `ab87a6f00092428692dd2f9055984f569c65881ff35fdc25992e2fe80ecb4ba0` |
| 2026 | 29,844 | 14,022,311 | 76 | true | `bfeb7187e85b8cece6aa98dbf8722f9bc1e87478672023faf84a49e458c90a79` |

## Quality Profile

Observed date range: `2023-01-01` through `2026-07-13`.

| Field | Nonempty rows | Completeness |
|---|---:|---:|
| EngineMake | 6,214 | 2.75% |
| EngineModel | 6,291 | 2.78% |
| EngineSerialNumber | 4,008 | 1.77% |
| EngineTotalTime | 3,663 | 1.62% |
| EngineTotalCycles | 3,119 | 1.38% |
| PartMake | 95,839 | 42.38% |
| PartName | 226,118 | 100.00% |
| PartNumber | 124,538 | 55.08% |
| PartCondition | 226,119 | 100.00% |
| ComponentMake | 2,191 | 0.97% |
| ComponentModel | 459 | 0.20% |
| ComponentName | 2,800 | 1.24% |
| Discrepancy | 226,124 | 100.00% |

## Frozen 10,000-Scenario Design

- Development eligible rows (2023-2025): `196,280`.
- 2026 holdout eligible rows: `29,844`.
- Deterministically selected unique holdout rows: `10,000`.
- Selected-ID set SHA-256: `9886c8c168601c47081a51919d19387cbabd899b5a70d7961e1619c1654df71f`.
- Protocol: `config/faa_sdr_aviation_reliability_10k_protocol_v1.json`.
- Protocol SHA-256: `3af7dcfce210600eb83935e2840855e192469a7253d3996e186cda39079a1895`.

The selection is without replacement and report IDs cannot cross development and holdout windows. The protocol forbids outcome-revealing fields and preserves all wins, non-wins, errors, seeds, and package versions.

## Rolls-Royce Boundary

The transparent matching rule identifies `737` exploratory rows across 2023-2026, including `706` rows explicitly coded `RROYCE`. This is useful for taxonomy and data-access planning, not a trusted-engine validation claim.

## Claim Boundary

FAA SDR is report-only observational maintenance data. This audit does not estimate failure rates, establish causality, determine airworthiness, validate an engine-health monitor, authorize operational use, or show FAA, operator, airport, or OEM approval. Rolls-Royce-family rows are an exploratory public-data subgroup only.

Receipt SHA-256: `7612b0057a32cfe25614759617699763d78dd6d87e76526fb7ac0fd8df7d227c`
