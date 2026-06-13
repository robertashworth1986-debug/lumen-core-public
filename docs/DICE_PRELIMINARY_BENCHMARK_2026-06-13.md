# DICE Preliminary Synthetic Benchmark

Updated: June 13, 2026

## Evidence Boundary

This is a synthetic discrete-event software benchmark. Agents are stochastic
task executors, not language models. The results do not establish DARPA DICE
program metric attainment, operational defense performance, foundation-model
inference at scale, or adversarial security.

## Research Question

Can a bounded-neighborhood peer task market with local reputation and
role-coherence repair reduce coordination and recovery messages relative to a
centralized assignment baseline without materially reducing mission
completion?

The benchmark compares:

1. A centralized assignment baseline with global status collection and
   periodic refresh.
2. A cached-capability peer auction with local challenge, reputation updates,
   task re-auction, and role repair.

Both approaches receive the same tasks, roles, failures, compromised agents,
and random seeds.

## Frozen Results

| Agents | Tasks | Paired trials | Peer messages | Message reduction | Recovery-message reduction | Mission-success delta | Role-coherence delta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 500 | 1,200 | 200 | 3,539 mean | 31.5% | 40.1% | +0.008 points | +6.45 points |
| 5,000 | 15,000 | 50 | 43,119 mean | 31.8% | 33.4% | +0.002 points | +6.57 points |
| 100,000 | 250,000 | 5 | 734,102 mean | 30.1% | 38.3% | +0.001 points | +6.53 points |

At 5,000 and 100,000 agents, the bootstrap confidence intervals for the
mission-success difference crossed zero. The current evidence therefore
supports message-efficiency and harness-scalability hypotheses, not a claim of
improved mission success.

## Failure Found And Corrected

The first scale attempt exposed a benchmark implementation defect: the
centralized baseline rescanned an entire role population for every task. This
measured Python search overhead rather than the intended coordination policy.
The baseline was corrected to use a cached role index while preserving its
assignment rule. The 500-agent frozen comparison was rerun after the repair and
reproduced the prior aggregate metrics.

## Reproducibility

Implementation:

- `code/dice_preliminary_benchmark.py`
- `tests/test_dice_preliminary_benchmark.py`

Each run writes:

- `trials.csv`
- `summary.json`
- `SCORECARD.md`
- `manifest.sha256.json`

Current local run identifiers:

- `20260613T_DICE_V1_500A_200PAIRS_OPT`
- `20260613T_DICE_V1_5000A_50PAIRS`
- `20260613T_DICE_V1_100KA_5PAIRS`

## Required Next Evidence

- Replace stochastic executors with heterogeneous open-weight and black-box
  agentic AI systems.
- Compare against current centralized and decentralized multi-agent
  frameworks.
- Preregister adversarial behaviors, collusion topologies, and breakdown
  thresholds.
- Measure false isolation, course-of-action diversity, latency, inference
  cost, and model-token use.
- Integrate through a TA3-compatible adaptor and obtain independent
  evaluation.
