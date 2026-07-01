# DICE Constraint-Carrying Commitment Benchmark - June 18, 2026

## Evidence Boundary

This is a generated discrete-event software benchmark. Agents are stochastic
task executors, not language models. Role, horizon, evidence, attack, and
monitor behavior are modeled assumptions. The result does not establish DICE
metric attainment, semantic correctness, operational defense performance, or
adversarial security.

## Hypothesis

The narrow hypothesis is that bids carrying locally verifiable role,
coherence-horizon, evidence-lineage, expiration, and risk fields can improve
safe task assignment relative to peer reputation alone. Six modeled fields are
piggybacked on existing bid messages.

## Design

- Development: 12 scenarios per condition under benign and 10% independent
  compromise.
- Frozen development choice: coherence-horizon margin 0.
- Validation: 30 disjoint scenarios for each of five conditions.
- Scale per scenario: 500 agents, 1,200 tasks, and 12 roles.
- Comparison: peer reputation versus constraint-carrying commitment.
- Statistics: paired scenario differences with deterministic bootstrap 95%
  intervals.

## Validation Results

| Condition | Peer safe completion | Contract safe completion | Safe-completion delta [95% CI] | Violation delta | Messages/safe delta |
|---|---:|---:|---:|---:|---:|
| Benign | 0.908 | 0.949 | +0.0416 [0.0384, 0.0446] | -0.0663 | -1.750 |
| Independent compromise 10% | 0.900 | 0.936 | +0.0352 [0.0304, 0.0398] | -0.0724 | -1.813 |
| Collusion 10% | 0.902 | 0.937 | +0.0350 [0.0305, 0.0396] | -0.0654 | -1.615 |
| Monitor shift | 0.902 | 0.923 | +0.0210 [0.0169, 0.0249] | -0.0590 | -1.431 |
| High collusion 25% | 0.890 | 0.903 | +0.0135 [0.0095, 0.0175] | -0.0566 | -1.073 |

Safe completion improved in all five generated conditions, while modeled
constraint violations and messages per safe completion declined. The effect
contracted as collusion and monitor error increased.

## Tradeoffs And Failure Modes

- Raw completion fell by approximately 2.5-4.5 percentage points because
  deterministic field checks reject assignments.
- False rejection was 2.36% in the benign condition, 5.76% under independent
  compromise, 5.66% under 10% collusion, 11.38% under monitor shift, and 10.87%
  under high collusion.
- Under 25% high collusion, compromised assignment increased by 0.96 percentage
  points [0.73, 1.18]. Locally consistent collusive forgeries can pass the
  deterministic checks.
- Strategy-entropy changes were small and are only a generated proxy, not
  cognitive-agility evidence.
- Contract fields were counted, but serialized bytes, cryptographic compute,
  and end-to-end latency were not measured.

These results support a Phase I experiment on constraint-carrying commitments.
They do not support a claim that certificates or deterministic fields solve
semantic deception.

## Reproduction

```powershell
.venv\Scripts\python.exe code\dice_constraint_contract_benchmark.py `
  --out out\dice_constraint_contract\<new-run-tag> `
  --development-scenarios 12 `
  --validation-scenarios 30 `
  --agents 500 `
  --tasks 1200
```

Canonical frozen run:
`out/dice_constraint_contract/20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE/`.
The run contains `summary.json`, `trials.csv`, `SCORECARD.md`, and a
verified SHA-256 manifest.
