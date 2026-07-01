# HarborSentinel Public AIS Held-Out Split Manifest

Generated UTC: 2026-06-20T21:34:30.104920+00:00

Posture: `PUBLIC_AIS_HELDOUT_SPLITS_FROZEN`

## Raw Source

- Path: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\raw\noaa_ais\AIS_2024_01_01.zip`
- SHA-256: `03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c`
- Source: https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip

## Selected Pilot Region

- Region: New Orleans / Mississippi River Delta (`new_orleans_delta`)
- Total rows in region: 878938
- Pre-cap split counts: {'development': 438050, 'validation': 440888}

## Frozen Splits

- Development CSV: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\working\noaa_ais\heldout_20260620T213237Z\development.csv`
  - rows: 50000
  - SHA-256: `128c42e103e722f8343af85e18c7b392953d2e48f46261705cf3e6f509149a46`
- Validation CSV: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\working\noaa_ais\heldout_20260620T213237Z\validation.csv`
  - rows: 50000
  - SHA-256: `050f062ce913bc98b63573ba649c6022061e44dd9773dce48f520dd9006849e6`

## Sampling Rule

- development = BaseDateTime hour < 12 UTC; validation = BaseDateTime hour >= 12 UTC
- When a split exceeds max_rows_per_split, keep the rows with the smallest deterministic SHA-256 row keys over the full split.

## Claim Boundary

This artifact freezes public AIS held-out development and validation splits. It does not establish HarborSentinel detection performance, Navy sensor validation, SSDS integration, ADS-B rights, radar performance, or operational suitability.
