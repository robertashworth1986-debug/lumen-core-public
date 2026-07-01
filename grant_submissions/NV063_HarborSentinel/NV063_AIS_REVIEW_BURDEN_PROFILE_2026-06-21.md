# HarborSentinel AIS Review-Burden Profile

Generated UTC: 2026-06-21T05:57:18.767340+00:00

Posture: `PUBLIC_AIS_REVIEW_BURDEN_PROFILE_READY`

## Boundary

This is an unlabeled public AIS review-burden profile. It estimates natural candidate queues, density context, and capped analyst-review workload from held-out validation traffic. It does not measure precision, false positives, real threat detection, multi-source fusion, ADS-B/radar performance, Navy/SSDS integration, field validation, or operational suitability.

## Region And Inputs

- Region: New Orleans / Mississippi River Delta (`new_orleans_delta`)
- Development segments: 48624
- Validation segments: 48616
- Development CSV SHA-256: `128c42e103e722f8343af85e18c7b392953d2e48f46261705cf3e6f509149a46`
- Validation CSV SHA-256: `050f062ce913bc98b63573ba649c6022061e44dd9773dce48f520dd9006849e6`

## Natural Review Queue

- Validation hours: 12
- Validation candidate rate: 0.0358
- Mean candidates/hour: 145.167
- P95 candidates/hour: 158.700
- Max candidates/hour: 162
- Hours with candidates: 12

## Capped Review Queues

| Cap/hour | Retained candidate fraction | Mean retained/hour |
|---:|---:|---:|
| 5 | 0.0344 | 5.000 |
| 10 | 0.0689 | 10.000 |
| 20 | 0.1378 | 20.000 |

## Density Context

| Density tier | Segments | Candidates | Candidate rate | Mean density count |
|---|---:|---:|---:|---:|
| sparse | 3997 | 476 | 0.1191 | 3.133 |
| normal | 18615 | 670 | 0.0360 | 23.658 |
| dense | 26004 | 596 | 0.0229 | 109.466 |

## Claim Gate

- ready_for_portal_upload: false
- ready_for_submit: false
- measures_false_positive_rate: false
- proves_field_performance: false
- proves_operational_suitability: false
