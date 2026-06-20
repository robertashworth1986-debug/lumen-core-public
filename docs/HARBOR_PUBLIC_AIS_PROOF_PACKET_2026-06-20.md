# HarborSentinel Public AIS Proof Packet

Generated UTC: 2026-06-20T21:42:43Z

## Purpose

This packet summarizes the public-safe HarborSentinel evidence chain. It is
designed for reviewers who need to see exactly what is measured, what is only
data-readiness, and what must not be claimed yet.

The current proof chain is:

1. public NOAA AIS source identified;
2. raw file acquired, hashed, and schema-profiled;
3. New Orleans / Mississippi River Delta development and validation splits
   frozen;
4. split I/O preflight passed with full-file SHA-256 verification;
5. a bounded controlled-injection detector-vs-baseline benchmark ran on the
   validation split.

## Source And Hash

| Field | Value |
|---|---|
| Public source | `https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip` |
| Raw file bytes | 290340871 |
| Raw SHA-256 | `03ed1e16f4445361d3d7cd6e0f0b4175dce4e63b0c5c8c99252728c64de9253c` |
| Schema sample | 10000 rows |
| Core columns | MMSI, BaseDateTime, LAT, LON, SOG, COG, Heading, VesselName, IMO, CallSign, VesselType, Status, Length, Width, Draft, Cargo, TransceiverClass |

Boundary: source acquisition proves public data staging, hashing, and schema
profiling. It does not prove HarborSentinel performance, Navy/SSDS integration,
field validation, ADS-B rights, radar performance, or operational suitability.

## Held-Out Split

| Field | Value |
|---|---|
| Region | New Orleans / Mississippi River Delta |
| Bounds | lat 28.6 to 30.35; lon -90.95 to -88.65 |
| Total region rows | 878938 |
| Development rows before cap | 438050 |
| Validation rows before cap | 440888 |
| Frozen development rows | 50000 |
| Frozen validation rows | 50000 |
| Development SHA-256 | `128c42e103e722f8343af85e18c7b392953d2e48f46261705cf3e6f509149a46` |
| Validation SHA-256 | `050f062ce913bc98b63573ba649c6022061e44dd9773dce48f520dd9006849e6` |

Boundary: the held-out split freezes a public AIS development/validation lane.
It does not establish detection performance, sensor validation, SSDS
integration, ADS-B rights, radar performance, or operational suitability.

## Readiness Gate

| Gate check | Result |
|---|---|
| Development rows at least 10000 | pass |
| Validation rows at least 10000 | pass |
| Core completeness at least 99% | pass |
| Overlap MMSI at least 100 | pass |
| Validation eligible tracks at least 50 | pass |
| Overlap MMSI | 1046 |

Boundary: this gate establishes public AIS single-lane data readiness, schema
coverage, track overlap, and frozen development-to-validation diagnostics. It
does not establish multi-source fusion, ADS-B licensing, radar validation,
Navy/SSDS integration, field performance, or operational suitability.

## I/O Preflight

| Field | Value |
|---|---|
| Posture | `PUBLIC_AIS_SPLIT_IO_READY` |
| Required files OK | 2/2 |
| Timeout | 5.0 seconds |
| Sample bytes per file | 4096 |
| Full hash requested | true |
| Full-hash matches | 2/2 required split files |
| Development file bytes | 5598389 |
| Validation file bytes | 5595298 |

Boundary: the preflight proves the frozen split files are reachable,
sample-readable within the configured timeout, and full-file SHA-256 matched
against the frozen split manifest. It does not establish HarborSentinel
detection performance, multi-source fusion, ADS-B/radar validation,
Navy/SSDS integration, field performance, or operational suitability.

## Controlled-Injection Benchmark

| Field | Value |
|---|---|
| Posture | `PUBLIC_AIS_INJECTION_BENCHMARK_READY` |
| Development segments | 48624 |
| Validation segments | 48616 |
| Injected validation segments | 20000 |
| Motion-consistency recall | 1.0 |
| Speed-only baseline recall | 0.25835 |
| Recall lift vs speed-only | 0.7416499999999999 |

### Family Results

| Injection family | Injected segments | Motion recall | Speed-only baseline recall | Boundary |
|---|---:|---:|---:|---|
| speed_burst | 5000 | 1.0 | 1.0 | Controlled kinematic injection, not a real threat label. |
| position_jump | 5000 | 1.0 | 0.0116 | Controlled kinematic injection, not a real threat label. |
| heading_snap | 5000 | 1.0 | 0.009 | Controlled kinematic injection, not a real threat label. |
| consistency_gap | 5000 | 1.0 | 0.0128 | Controlled kinematic injection, not a real threat label. |

### Natural Candidate Rates

| Candidate rate | Value |
|---|---:|
| Development motion candidate rate | 0.029059723593287266 |
| Validation motion candidate rate | 0.03583182491360869 |
| Development speed-only candidate rate | 0.009912800263244488 |
| Validation speed-only candidate rate | 0.0109428994569689 |

Boundary: natural candidate rates are unlabeled review queues, not false-positive
rates.

## What This Supports

This packet supports the claim that a frozen development-threshold
motion-consistency detector catches controlled kinematic perturbations on
held-out public AIS validation segments better than a speed-only baseline.

This is useful because it moves HarborSentinel from synthetic-only framing into
public-source representative-data evidence with hashes, splits, and a bounded
detector comparison.

## What This Does Not Support

Do not use this packet to claim:

- real adversary detection;
- operational detection performance;
- multi-source fusion;
- ADS-B or radar validation;
- Navy/SSDS integration;
- field performance;
- operational suitability;
- award likelihood, customer adoption, or revenue.

## Next Validation Gates

1. Rehash full development and validation split files during a longer
   reproducibility run.
2. Add labeled or analyst-reviewed anomaly cases if a public or partner-safe
   source becomes available.
3. Add ADS-B and radar only after rights, source quality, and validation
   boundaries are explicit.
4. Compare against stronger baselines beyond speed-only, including trajectory
   smoothness, heading-rate, and track-context models.
5. Report precision, review-queue burden, and false-positive estimates only
   after labels or an analyst adjudication protocol exists.
