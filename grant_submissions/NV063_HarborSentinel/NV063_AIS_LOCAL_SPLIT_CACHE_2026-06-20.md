# HarborSentinel AIS Local Split Cache

Generated UTC: 2026-06-20T21:35:01.622085+00:00

Posture: `PUBLIC_AIS_LOCAL_SPLIT_CACHE_READY`

## Summary

- Required split files OK: 2/2
- Any timeout: False
- Cached split manifest: `out/ops/harbor_ais_cached_split_manifest_latest.json`

## Entries

### development

- status: `cached`
- ok: True
- cache: `out/private_data/harbor_ais_split_cache/development_128c42e103e7.csv`
- expected bytes: 5598389
- actual bytes: 5598389
- SHA-256 matches: True
- elapsed seconds: 0.016

### validation

- status: `cached`
- ok: True
- cache: `out/private_data/harbor_ais_split_cache/validation_050f062ce913.csv`
- expected bytes: 5595298
- actual bytes: 5595298
- SHA-256 matches: True
- elapsed seconds: 0.015

## Next Gate

Run AIS I/O preflight and the HarborSentinel controlled-injection benchmark against the cached split manifest only after the cache is ready.

## Claim Boundary

This cache proves only that local private copies of the frozen public AIS split files match the recorded SHA-256 hashes. It does not establish HarborSentinel detection performance, multi-source fusion, ADS-B or radar validation, Navy/SSDS integration, field performance, or operational suitability.
