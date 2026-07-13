# IEEE AC Optimal-Flow Routing Readiness

Date: 2026-07-13

Status: baseline engine verified; candidate execution not started

Protocol: `config/ieee_acopf_routing_protocol_v1.json`

## Decision

LumenCore has a legitimate optimal-power-flow validation lane available now. The local environment already includes `pandapower 3.4.0`, which provides reproducible IEEE reference networks and a full nonlinear AC OPF implementation. No replacement office package or new solver download is required to begin the benchmark.

The defensible target is not to claim that a geometry or heuristic "beats optimal." Under identical objectives and constraints, an accepted optimum is the reference. The useful research questions are whether a preregistered router can:

1. reach an equivalent feasible objective faster;
2. improve convergence under stressed loads and connected N-1 outages;
3. screen constraints with high recall before the full solve; or
4. improve robust or stochastic decisions under declared uncertainty.

## Baseline Smoke Test

The unmodified `pandapower.runopp` AC OPF completed on four local IEEE-style cases:

| Network | Buses | Lines | Converged | Reported objective |
|---|---:|---:|---|---:|
| case14 | 14 | 15 | yes | 8081.5266 |
| case30 | 30 | 41 | yes | 578.4863 |
| case39 | 39 | 35 | yes | 41872.3026 |
| case118 | 118 | 173 | yes | 129704.7402 |

The objective values are not comparable across networks. They verify only that the local AC OPF baseline executes and converges on these fixtures.

## Locked Evaluation Shape

The v1 protocol freezes five networks, two stress families, a deterministic scenario split, the baseline routes, allowed pre-solve features, end-to-end timing rules, feasibility checks, statistics, and worst-network guardrails before a LumenCore routing candidate is run.

The candidate cannot change the OPF objective or constraints. Its time includes preprocessing, failed attempts, and retries. A full champion label requires objective equivalence, feasibility, no material worst-network convergence regression, and a statistically supported aggregate speed improvement.

## What This Can Support

- Reproducible solver-routing research on public reference networks.
- A concrete bridge from the EIA forecasting evidence into grid operations research.
- A reviewer-auditable negative result when a route does not generalize.
- A foundation for later evaluation with a utility, laboratory, or authorized system owner.

## What This Cannot Support Yet

- Utility field validation or operating approval.
- Realized cost, reliability, or emissions savings.
- A claim that LumenCore replaces an independent system operator's production tools.
- A claim that any geometry universally improves AC OPF.

## Next Gates

1. Commit the protocol before candidate execution.
2. Implement the canonical scenario generator and independent feasibility checks.
3. Freeze development results and the `lumaroute_v1` decision rule.
4. Execute the locked holdout once and publish every network result.
5. Require a fresh prospective or partner-held dataset before making an external generalization claim.
