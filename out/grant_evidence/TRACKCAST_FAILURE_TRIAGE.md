# Navy TrackCast Failure Triage

Generated UTC: 2026-06-16T01:52:27.072651+00:00

## Summary

- Existing scripts: 3
- Ran: 3
- Passed: 0
- Failed: 3
- Timed out: 0

## Failed Scripts

### code/regime_shift_scanner.py

- Return code: 1
- Timeout: False
- SHA-256: 68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f

Error tail:
```text
Traceback (most recent call last):
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 259, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 157, in main
    utc = _resolve_run_utc()
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 65, in _resolve_run_utc
    runs = sorted([p.name for p in V2_RUNS.iterdir() if p.is_dir()])
                                   ~~~~~~~~~~~~~~~^^
  File "C:\Python314\Lib\pathlib\__init__.py", line 836, in iterdir
    with os.scandir(root_dir) as scandir_it:
         ~~~~~~~~~~^^^^^^^^^^
FileNotFoundError: [WinError 3] The system cannot find the path specified: 'C:\\LumenCore_GitHub\\lumen-core-public\\out\\master_universe_v2'

```

### code/anomaly_scanner.py

- Return code: 1
- Timeout: False
- SHA-256: f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d

Output tail:
```text
FATAL: no ANOM_UTC and no latest.txt

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