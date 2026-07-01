# DICE Evidence Synthesis

Generated UTC: `2026-06-24T19:22:40.437295+00:00`

## Reviewer Positioning

Use this as measurable preliminary evidence and a Phase I validation plan, not as a claim that DICE performance has been proven.

## What This Supports

- A live-breadth replay lane maps frozen Kraken and EIA time-series windows into deterministic stress scenarios while keeping replay-label limits explicit.
- A provenance-gated live-breadth annex separates promoted live-measured signals from context-only estimates and anchors the promoted value in the truth chain.
- A reproducible synthetic benchmark harness exists and is hash-manifested.
- Peer/local control reduced message and recovery-message overhead in the preliminary synthetic benchmark.
- Constraint-contract checks improved safe completion and reduced modeled constraint violations across five generated validation conditions.
- The evidence is strong enough to justify a Phase I work plan with stronger agents, independent datasets, and adversarial evaluation.

## What This Does Not Support

- Do not claim DICE performance has been proven.
- Do not claim operational DoD deployment performance.
- Do not claim foundation-model or TA3-scale agent validation.
- Do not claim adversarial security or cryptographic cost measurement.
- Do not claim trading, live-breadth, or frozen-delta results prove DICE merit.
- Do not claim the live-measured economic signal is customer savings, revenue, valuation proof, or grant merit.
- Do not claim live-breadth replay proves field performance; it is a frozen stress replay lane.

## Preliminary Peer-Mesh Benchmark

- Evidence boundary: Synthetic discrete-event software benchmark only. Agents are stochastic task executors, not language models. Results do not establish DICE program metric attainment, operational DoD performance, or adversarial security.
- Configuration: {'seeds': 200, 'agents': 500, 'tasks': 1200, 'roles': 12, 'failed_fraction': 0.1, 'compromised_fraction': 0.05, 'peer_neighborhood': 8}
- Summary: out/dice_preliminary/20260613T_DICE_V1_500A_200PAIRS_OPT/summary.json
- Manifest: out/dice_preliminary/20260613T_DICE_V1_500A_200PAIRS_OPT/manifest.sha256.json

| Metric | Mean | 95% bootstrap interval | Reviewer use |
|---|---:|---:|---|
| Mission success delta | 0.008 points | [0.0004, 0.0146] | Completion preserved in the synthetic setting. |
| Message reduction | 31.523% | [31.3268, 31.7117] | Evidence for measurable coordination-cost reduction. |
| Recovery-message reduction | 40.100% | [39.7442, 40.4710] | Evidence for lower modeled recovery overhead. |
| Role-coherence delta | 6.449 points | [6.2359, 6.6876] | Evidence for a role-consistency measurement lane. |

## Constraint-Contract Stress Benchmark

- Evidence boundary: Generated discrete-event software benchmark only. Agents are stochastic executors, not language models. Contract fields and attacks are modeled assumptions. Results do not establish DICE metric attainment, semantic correctness, operational defense performance, or adversarial security.
- Validation conditions: 5
- Scenarios per condition: 30
- Selected development margin: 0
- Summary: out/dice_constraint_contract/20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE/summary.json
- Manifest: out/dice_constraint_contract/20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE/manifest.sha256.json

| Condition | Safe-completion delta | Violation-rate delta | Message delta | False rejection |
|---|---:|---:|---:|---:|
| benign | 0.0416 [0.0384, 0.0446] | -0.0663 [-0.0700, -0.0623] | -1.7501 [-1.8396, -1.6560] | 0.0236 |
| independent_compromise_10pct | 0.0352 [0.0304, 0.0398] | -0.0724 [-0.0766, -0.0684] | -1.8127 [-1.9225, -1.7050] | 0.0576 |
| collusion_10pct | 0.0350 [0.0305, 0.0396] | -0.0654 [-0.0699, -0.0612] | -1.6150 [-1.7314, -1.5078] | 0.0566 |
| monitor_shift | 0.0210 [0.0169, 0.0249] | -0.0590 [-0.0624, -0.0558] | -1.4312 [-1.5186, -1.3409] | 0.1138 |
| high_collusion_25pct | 0.0135 [0.0095, 0.0175] | -0.0566 [-0.0605, -0.0527] | -1.0727 [-1.1868, -0.9591] | 0.1087 |

## Live-Breadth Replay Lane

- Evidence mode: primary_live_pulled_source_rows_with_deterministic_replay_labels
- Primary evidence source: frozen_live_pulled_rows
- Synthetic role: secondary_control_labels_ablation_and_failure_injection_only
- Evidence boundary: Frozen live-pulled time-series replay adapter. Source rows are live-pulled or previously live-fetched operational/market signals, but task roles, risk tiers, and adversary knobs are deterministic derived labels for replay. Results do not establish DICE metric attainment, operational DoD performance, field validation, semantic correctness, or adversarial security.
- Source count: 6
- Source types: market_execution, power_grid
- Configuration: {'agents': 180, 'margin': 0, 'max_eia': 2, 'max_kraken': 4, 'roles': 8, 'scenario_count': 14, 'scenarios_per_source': 3, 'task_multiplier': 3, 'window_size': 48}
- Summary: out/ops/dice_live_breadth_replay_latest.json
- Scorecard: grant_submissions/DICE_HR001126S0010/DICE_LIVE_BREADTH_REPLAY_2026-06-20.md
- Boundary to own: Source data do not carry native DICE task labels; replay labels are deterministic derived labels and cannot prove DICE metric attainment.

Claim gate:

- ready_for_portal_upload: false
- ready_for_submit: false
- live_replay_proves_dice_metric_attainment: false
- live_replay_proves_trading_profit: false
- synthetic_primary_evidence: false

| Metric | Mean delta | Favorable fraction | Scenario count | Reviewer use |
|---|---:|---:|---:|---|
| Safe completion | +0.0437 | 0.857 | 14 | Stress-replay signal, not DICE metric proof. |
| Constraint violation | -0.1216 | 0.929 | 14 | Supports a constraint-check validation lane. |
| Messages per safe completion | -2.8157 | 1.000 | 14 | Shows modeled coordination-cost behavior on frozen live windows. |
| False rejection | +0.0514 | 0.000 | 14 | Known cost to reduce in Phase I. |

## Provenance-Gated Live-Breadth Annex

- Primary evidence mode: `live_measured_delta_rows`
- Measured sources: 17/22 (77.27%)
- Promoted live-measured hourly value signal: $4,890.00
- Promoted live-measured annual value signal: $42,836,400.00
- Context-only hourly surface: $5,969,006.50
- Context-only annual surface: $52,288,496,940.00
- Truth-chain entry SHA-256: `cf81edbe23354210b3c9e1c00d68d09506a3b792ad0bb13ca1144220bd9d417a`
- Annex: grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md
- Grant use: Use the promoted live-measured values only as evidence that the measurement system can ingest, separate, hash, and report live evidence with context-only estimates fenced off.
- Boundary to own: Live breadth provides measured source coverage, frozen time-series replay realism, and chain-of-custody evidence after controlled tests. It is not native ground truth for DICE or HarborSentinel.

Claim gate:

- ready_for_portal_upload: false
- ready_for_submit: false
- grant_merit_proven: false
- field_performance_proven: false
- trading_profit_proven: false
- context_only_promoted_as_live_proof: false


## Failure Modes To Own

- False rejection exceeds 10% in: monitor_shift, high_collusion_25pct
- Compromised-assignment rate worsens in: collusion_10pct, high_collusion_25pct
- Locally consistent forged contracts can pass deterministic checks in this generated model.

## Phase I Validation Upgrades

- Replace stochastic task executors with instrumented heterogeneous LLM/tool agents or a TA3-compatible adaptor.
- Measure byte cost, latency, cryptographic overhead, and failure recovery cost instead of only counting logical messages.
- Add preregistered attack sets for role poisoning, collusion, stale evidence, monitor drift, and locally consistent forged contracts.
- Run ablations against centralized, peer-reputation, contract-field, and hybrid variants under identical seeds.
- Expand the live-replay adapter beyond Kraken/EIA into additional live-breadth sectors only after each source has a frozen manifest and replay-label contract.
- Create independent evaluator packets with frozen seeds, manifests, scorecards, and refusal-to-overclaim gates.

## Claim Gate

- ready_for_portal_upload: false
- ready_for_submit: false
- human_action_time_approval_required: true
- boundary: This artifact improves reviewer clarity only. It does not authorize upload, signature, certification, submission, award-likelihood claims, or legal/compliance representations.
