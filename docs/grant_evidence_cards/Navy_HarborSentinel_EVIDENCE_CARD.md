# Grant Evidence Card — Navy_HarborSentinel

Generated UTC: 2026-06-16T02:01:05.052254+00:00

## Status

- Evidence status: YELLOW
- Existing scripts: 4
- Scripts ran: 4
- Passed: 3
- Failed: 1
- Timed out: 0

## Claim Type

synthetic validation and anomaly monitoring

## Reviewer-Safe Claim

Reviewer-safe claim: this lane has partial passing preliminary benchmark evidence, but one or more scripts require cleanup before it should be presented as complete.

## Evidence Table

| Script | Exists | Ran | Return Code | Timeout | SHA-256 |
|---|---:|---:|---:|---:|---|
| code/harbor_sentinel_benchmark.py | True | True | 0 | False | 8ec80504efd01d6be6a31f8b50c3d4757fabd233ed7a37640adc698d1b470c3d |
| code/harbor_sentinel_validation_suite.py | True | True | 1 | False | dc9c2586efa5659b8934f02fec37e6afea4afac3780fdff6c566743b10ee14ac |
| tests/test_harbor_sentinel_benchmark.py | True | True | 0 | False | b50141710b3a36bc780f297395a710c15791464615eb6a4900a2f934102080fe |
| tests/test_harbor_sentinel_validation_suite.py | True | True | 0 | False | 5ba5ef9420d9ab603eb529c885a4c86f53c52bc1b19109c8eced2eab6c26dd24 |

## Use In Grant Narrative

- Use this lane carefully as partial evidence.
- Put failures/timeouts in risk mitigation or next-work section.
- Fix the failing script before submission when possible.

## Next Action

- Review the failing or timeout script and rerun the benchmark lab.