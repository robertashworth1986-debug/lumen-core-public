# Hybrid Echo Routing — End-to-End Lineage V1

## Purpose

This lane operationalizes the founder thesis that useful energy behavior can be shaped by combining:

1. passive geometry,
2. bounded adaptive control,
3. deterministic disturbance testing,
4. lineage-preserving evolution,
5. proof-capsule reporting.

It is simulation-first. It does **not** control a physical grid, aircraft, reactor, vehicle, or critical facility.

## Evolution lineage

The run begins with a zero-control straight-path ancestor. Every generation stores:

- candidate parameters,
- parent identifier,
- training metrics,
- disjoint validation metrics,
- generation number,
- final manifest hash.

The geometry search space is straight, spiral, helix, branching, gyroid, and phyllotactic.

The controller parameters are phase gain, damping, reroute gain, and thermal gain.

## Locked objective

The composite objective is locked before evolution and rewards transmission efficiency while charging peak load, thermal concentration, instability, recovery burden, and control cost. This prevents a candidate from winning merely by adding more control action.

## Run

```bash
python code/hybrid_echo_routing.py \
  --seed 1986 \
  --generations 24 \
  --population 36 \
  --output artifacts/hybrid_echo_lineage.json
```

## Acceptance gate

A candidate is not promoted solely because its composite score is higher. Promotion requires:

1. deterministic reproduction,
2. improvement on disjoint validation seeds,
3. no material instability regression,
4. explicit control-cost accounting,
5. failure notes and claim boundary,
6. external bench or field validation before operational claims.

## Claim boundary

Safe statement:

> LumenCore has a synthetic, lineage-preserving benchmark for comparing geometry-only, control-only, and hybrid routing candidates under a locked multi-objective score.

Unsafe statements include field-validated savings, certified resilience, grid control, aircraft performance, or universal superiority.
