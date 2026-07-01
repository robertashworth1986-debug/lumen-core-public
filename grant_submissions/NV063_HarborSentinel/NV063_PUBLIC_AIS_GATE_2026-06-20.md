# HarborSentinel Public AIS Single-Lane Gate

Generated UTC: 2026-06-20T07:53:43.701511+00:00

Posture: `PUBLIC_AIS_SINGLE_LANE_GATE_READY`

## Selected Region

- Region: New Orleans / Mississippi River Delta (`new_orleans_delta`)

## Split Coverage

- Development rows: 50000; unique MMSI: 1110; core completeness: 1.0000
- Validation rows: 50000; unique MMSI: 1117; core completeness: 1.0000
- MMSI overlap: 1046

## Frozen Validation Diagnostics

- Validation eligible tracks: 1090
- Validation SOG over dev p99 rate: 0.0123
- Validation derived-speed over dev p99 rate: 0.0109
- Boundary: outlier rates are data-quality diagnostics, not threat detection performance.

## Gate Checks

- development_rows_at_least_10000: True
- validation_rows_at_least_10000: True
- core_completeness_at_least_99pct: True
- overlap_mmsi_at_least_100: True
- validation_eligible_tracks_at_least_50: True

## Claim Boundary

This gate establishes public AIS single-lane data readiness, schema coverage, track overlap, and frozen development-to-validation diagnostics. It does not establish HarborSentinel detection performance, multi-source fusion performance, ADS-B licensing, radar validation, Navy/SSDS integration, field performance, or operational suitability.
