# Live-Breadth Provenance Gate Capsule

Generated UTC: 2026-06-21T06:20:00Z

## Purpose

This capsule documents a public-safe evidence-boundary upgrade for LumenCore's
live-breadth and frozen-delta reporting.

The useful change is simple: only rows tied to measured live sources are
promoted as live-breadth evidence. Unmeasured frozen deltas, reference fallback
rows, synthetic controls, and exploratory context stay visible, but they are no
longer allowed to inflate the headline evidence layer.

## Public-Safe Snapshot

| Field | Value |
|---|---:|
| Enabled live sources | 17 |
| Measured live sources | 12 |
| Measured coverage | 70.59% |
| Promoted live-measured source rows | 11 |
| Context-only source rows | 8 |
| Reference fallback used | false |
| Promoted live-measured hourly value signal | $8,435 |
| Promoted live-measured annual value signal | $73,890,600 |

## What Changed

The local evidence router now separates three buckets:

1. `live_measured_delta_rows`: promoted live-breadth evidence.
2. `unmeasured_frozen_delta_rows`: context-only until source measurement is proven.
3. `reference_fallback_only`: calibration/context only.

This means a large unmeasured or reference-derived value surface can remain in
the research file, but it is not treated as primary public evidence.

## Why It Matters

Reviewers can now distinguish:

- what was actually measured through live-source registry evidence;
- what was frozen and hashable but not yet source-measured;
- what remains synthetic, reference, or exploratory context.

That makes the grant posture stronger because the claim surface is smaller,
cleaner, and harder to overstate.

## Boundary

This capsule does not prove actual customer savings, revenue, trading profit,
grant merit, agency acceptance, valuation, field performance, or operational
deployment readiness.

The dollar figures above are value-signal estimates from the provenance-gated
live-breadth evidence layer. They are not revenue, not realized savings, not an
investment claim, and not a guarantee.

## Reviewer Use

Use this capsule as a public evidence-quality control. It supports the statement
that LumenCore separates live-measured evidence from context-only evidence before
using frozen deltas in public or grant-facing materials.

Do not use it as a substitute for portal authority, compliance review, customer
baseline acceptance, field validation, or final human submission approval.
