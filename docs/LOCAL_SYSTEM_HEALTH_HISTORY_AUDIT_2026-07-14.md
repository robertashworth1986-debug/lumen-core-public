# Local System Health History Audit

Generated UTC: `2026-07-14T10:13:25.915582Z`

## Decision

- Valid point snapshots: `1,250`.
- Observed UTC range: `2026-01-13T17:00:09Z` through `2026-07-14T10:00:02Z`.
- Active UTC dates: `155`.
- UTC-hour bucket coverage: `28.61%`.
- Integrity status: `defects_present` with `13` recorded defects.
- Hardware degradation claim allowed: `false`.

The history contains useful local pressure and free-space observations, but its CPU values are sparse one-second point samples. It is not a continuous hardware-health or degradation study.

## Source Manifest Receipts

| Source alias | Records | Logical bytes | SHA-256 |
|---|---:|---:|---|
| legacy_health_snapshot_set | 1,252 | 857,556 | `2a19f4feb74537507dcdc5f2b8a3752429a05502d1f73b983ef98bfd0c06365c` |
| legacy_health_snapshot_sidecar_set | 1,249 | 82,434 | `45701659595002fabbc79eb2ffde82b065de938404b3c9963eb50b7446484e2c` |
| legacy_health_proof_set | 1,249 | 726,509 | `dec53d12f8b5d803f30b638ce45899a1df61dfce187b5244d4e7b1141ae2a5ca` |
| legacy_health_custody_ledger | 3,749 | 1,068,315 | `3183d5e98766fcfa2d749b91852b7a1bd1fb5ddd73230e77c3414f7167934c48` |
| legacy_health_collector | 1 | 4,784 | `bb57e55ea5b096db84045c4f37283c2e6b9fa9242ba7644e63ec9e5c716b5c4f` |

Source-manifest SHA-256: `01ab6f1b45499d375c25f72e960f9ad9df2c84dc68626a587d1e6a5ac4f17a74`

## Exact Trailing Windows

| Window | Snapshots | Active dates | Observed / expected UTC-hour buckets | CPU median / p95 | Memory-free median / p10 |
|---:|---:|---:|---:|---:|---:|
| 30 days | 177 | 28 | 177 / 721 | 35.09% / 59.93% | 33.98% / 5.61% |
| 90 days | 699 | 87 | 699 / 2,161 | 30.74% / 61.54% | 30.76% / 8.56% |
| 180 days | 1,233 | 153 | 1,233 / 4,321 | 24.94% / 56.15% | 33.16% / 12.18% |

## Integrity Defects

| Code | Count |
|---|---:|
| proof_unledgered | 1 |
| proof_zero_bytes | 1 |
| snapshot_json_invalid | 2 |
| snapshot_sidecar_missing | 3 |
| snapshot_unledgered | 4 |
| snapshot_zero_bytes | 2 |

## Claim Boundary

This audit summarizes local, unevenly spaced point observations. Each legacy CPU value is a single one-second sample, not continuous utilization. Sparse point samples and free-space deltas can identify observed pressure and capacity change, but they cannot establish hardware degradation, root cause, prevented failure, field validation, independent validation, or a medical or safety diagnosis. The legacy collector does not measure temperature, SMART or NVMe wear, battery health or cycles, fan speed, GPU state, power state, network health, or per-process attribution.

Audit receipt SHA-256: `917ca393dcde64c63909a0049cf431d8dbb257999f514acdea6b1d1e44cb372a`
