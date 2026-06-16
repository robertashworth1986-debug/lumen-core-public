# Navy TrackCast Failure Triage

Generated UTC: 2026-06-16T02:01:05.053812+00:00

## Summary

- Existing scripts: 4
- Ran: 4
- Passed: 2
- Failed: 2
- Timed out: 0

## Failed Scripts

### code/anomaly_scanner.py

- Return code: 1
- Timeout: False
- SHA-256: f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d

Output tail:
```text
FATAL: C:\LumenCore_GitHub\lumen-core-public\out\master_universe_v2\2026-06-15T20:09:00Z\raw does not exist

```

### code/forecast_api.py

- Return code: 1
- Timeout: False
- SHA-256: 1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e

Error tail:
```text
Traceback (most recent call last):
  File "C:\LumenCore_GitHub\lumen-core-public\code\forecast_api.py", line 39, in <module>
    from fastapi import APIRouter, HTTPException, Query
ModuleNotFoundError: No module named 'fastapi'

```

## Repair Plan

1. Identify whether failures are missing dependency, missing data file, import path issue, or actual assertion failure.
2. Add a deterministic synthetic fixture so TrackCast can pass without external APIs.
3. Rerun the grant evidence benchmark lab.
4. Promote TrackCast from RED to GREEN or YELLOW before Navy submission.