# DICE Constraint-Carrying Commitment Scorecard

Evidence boundary: Generated discrete-event software benchmark only. Agents are stochastic executors, not language models. Contract fields and attacks are modeled assumptions. Results do not establish DICE metric attainment, semantic correctness, operational defense performance, or adversarial security.

## Development Gate

- Frozen coherence-horizon margin: 0
- Development scenarios per condition: 12
- Development conditions: benign and independent 10% compromise.

## Disjoint Validation

| Condition | Peer safe completion | Contract safe completion | Safe-completion delta [95% CI] | Violation delta | Message-cost delta | False rejection |
|---|---:|---:|---:|---:|---:|---:|
| benign | 0.908 | 0.949 | +0.042 [+0.038, +0.045] | -0.066 | -1.75 | 0.024 |
| independent_compromise_10pct | 0.900 | 0.936 | +0.035 [+0.030, +0.040] | -0.072 | -1.81 | 0.058 |
| collusion_10pct | 0.901 | 0.936 | +0.035 [+0.030, +0.040] | -0.065 | -1.61 | 0.057 |
| monitor_shift | 0.902 | 0.923 | +0.021 [+0.017, +0.025] | -0.059 | -1.43 | 0.114 |
| high_collusion_25pct | 0.890 | 0.903 | +0.013 [+0.010, +0.018] | -0.057 | -1.07 | 0.109 |

Negative violation and message-cost deltas favor the contract method. False rejection is measured only for generated honest agents whose true horizon satisfies the task.

## Interpretation

The contract carries six modeled fields in each existing bid message; the field count is reported separately and is not a byte or latency claim. Deterministic checks reject malformed or stale contracts, but locally consistent collusive forgeries can pass. High-collusion and monitor-shift conditions therefore test a known boundary rather than assume certificates solve semantic deception.
