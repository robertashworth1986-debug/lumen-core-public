# HarborSentinel Public AIS Review-Burden Capsule

Generated UTC: 2026-06-21T06:05:00Z

## Purpose

This public capsule summarizes an unlabeled HarborSentinel review-burden profile
without publishing private portal material or implying Navy field validation.

The useful point is narrow: after public AIS acquisition, held-out split
freezing, full-hash I/O preflight, and controlled-injection benchmarking,
HarborSentinel now has a public-safe estimate of the natural candidate queue a
watch team would need to review before labels or adjudication are available.

## Public-Safe Result Snapshot

- Region: New Orleans / Mississippi River Delta
- Development segments: 48,624
- Validation segments: 48,616
- Validation candidate count: 1,742
- Validation candidate rate: 0.0358
- Mean candidates/hour: 145.167
- P95 candidates/hour: 158.7
- Max candidates/hour: 162

## Density Context

| Density tier | Segments | Candidates | Candidate rate |
|---|---:|---:|---:|
| Sparse | 3,997 | 476 | 0.1191 |
| Normal | 18,615 | 670 | 0.0360 |
| Dense | 26,004 | 596 | 0.0229 |

## Capped Review Queue

| Cap/hour | Retained candidate fraction | Mean retained/hour |
|---:|---:|---:|
| 5 | 0.0344 | 5.000 |
| 10 | 0.0689 | 10.000 |
| 20 | 0.1378 | 20.000 |

## Why It Matters

Controlled injections answer whether the detector can catch injected kinematic
perturbations. They do not answer whether a human team can tolerate the natural
review queue. This profile gives reviewers a bounded workload estimate and makes
the next Phase I requirement obvious: add labels or analyst adjudication so
precision, false positives, alert burden, and calibration can be measured
properly.

## Boundary

This capsule does not measure precision, false positives, real threat detection,
multi-source fusion, ADS-B/radar performance, Navy/SSDS integration, field
validation, operational suitability, award likelihood, or portal readiness.

Natural candidate rates are review queues, not false-positive rates.
