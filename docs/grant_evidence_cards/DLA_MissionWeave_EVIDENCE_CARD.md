# Grant Evidence Card — DLA_MissionWeave

Generated UTC: 2026-06-16T02:01:05.052587+00:00

## Status

- Evidence status: YELLOW
- Existing scripts: 2
- Scripts ran: 2
- Passed: 1
- Failed: 1
- Timed out: 0

## Claim Type

workflow orchestration and mission support automation

## Reviewer-Safe Claim

Reviewer-safe claim: this lane has partial passing preliminary benchmark evidence, but one or more scripts require cleanup before it should be presented as complete.

## Evidence Table

| Script | Exists | Ran | Return Code | Timeout | SHA-256 |
|---|---:|---:|---:|---:|---|
| code/missionweave_benchmark.py | True | True | 1 | False | ecff9ead66347b48aff093ffd7affe8958f355bf93273be8820dc5326331e39d |
| tests/test_missionweave_benchmark.py | True | True | 0 | False | c5e1ed552e100db9e13690b3c7ac561a59a89031208aea4ea0583836313ad178 |

## Use In Grant Narrative

- Use this lane carefully as partial evidence.
- Put failures/timeouts in risk mitigation or next-work section.
- Fix the failing script before submission when possible.

## Next Action

- Review the failing or timeout script and rerun the benchmark lab.