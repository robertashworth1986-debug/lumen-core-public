# Grant Evidence Card — Navy_TrackCast

Generated UTC: 2026-06-16T02:01:05.053191+00:00

## Status

- Evidence status: YELLOW
- Existing scripts: 4
- Scripts ran: 4
- Passed: 2
- Failed: 2
- Timed out: 0

## Claim Type

signal tracking, forecasting, and early warning

## Reviewer-Safe Claim

Reviewer-safe claim: this lane has partial passing preliminary benchmark evidence, but one or more scripts require cleanup before it should be presented as complete.

## Evidence Table

| Script | Exists | Ran | Return Code | Timeout | SHA-256 |
|---|---:|---:|---:|---:|---|
| code/trackcast/trackcast_existing_stack_benchmark.py | True | True | 0 | False | 3a092e0bec0872a2bb5d34b83961b4e552f5151a476479cfa78a0993d7169f1b |
| code/regime_shift_scanner.py | True | True | 0 | False | 68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f |
| code/anomaly_scanner.py | True | True | 1 | False | f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d |
| code/forecast_api.py | True | True | 1 | False | 1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e |

## Use In Grant Narrative

- Use this lane carefully as partial evidence.
- Put failures/timeouts in risk mitigation or next-work section.
- Fix the failing script before submission when possible.

## Next Action

- Fix TrackCast failing scripts first; this is the only detected benchmark lane blocker.