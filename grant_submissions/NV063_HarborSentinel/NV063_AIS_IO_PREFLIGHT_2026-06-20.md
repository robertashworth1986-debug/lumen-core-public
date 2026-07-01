# HarborSentinel AIS Split I/O Preflight

Generated UTC: 2026-06-20T22:27:50.028571+00:00

Posture: `PUBLIC_AIS_SPLIT_IO_READY`

## Summary

- Required split files OK: 2/2
- Any timeout: False
- Timeout seconds: 10.0
- Sample bytes: 4096
- Full hash requested: True

## Probes

### development

- status: `ok`
- ok: True
- path: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\working\noaa_ais\heldout_20260620T213237Z\development.csv`
- expected bytes: 5598389
- actual bytes: 5598389
- size matches: True
- SHA-256 matches manifest: True
- actual SHA-256: `128c42e103e722f8343af85e18c7b392953d2e48f46261705cf3e6f509149a46`
- sample bytes read: 4096
- elapsed seconds: 0.0

### validation

- status: `ok`
- ok: True
- path: `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\private_data\HarborSentinel\working\noaa_ais\heldout_20260620T213237Z\validation.csv`
- expected bytes: 5595298
- actual bytes: 5595298
- size matches: True
- SHA-256 matches manifest: True
- actual SHA-256: `050f062ce913bc98b63573ba649c6022061e44dd9773dce48f520dd9006849e6`
- sample bytes read: 4096
- elapsed seconds: 0.0

## Next Gate

Add stronger baselines and labeled or adjudicated validation before claiming precision, false-positive rate, multi-source fusion, ADS-B/radar validation, or field performance.

## Claim Boundary

This preflight proves that the required frozen public AIS split files are reachable, sample-readable within the configured timeout, and full-file SHA-256 matched against the frozen split manifest. It does not establish HarborSentinel detection performance, multi-source fusion, ADS-B or radar validation, Navy/SSDS integration, field performance, or operational suitability.
