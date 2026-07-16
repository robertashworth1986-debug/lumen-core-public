# LumaJet Flight Assurance Evidence

Generated UTC: `2026-07-16T00:58:25.017960+00:00`
Packet SHA-256: `c2f9f24b874fbd271ed138dedb06123585b0baf22022d6ffd330cf3f3234af37`

## Evidence Boundary

Internal generated software-simulation evidence only. The packet preserves both an adverse v1 result and a tiny-effect v2 internal gate pass. It is not flight control, airworthiness evidence, field validation, independent reproduction, FAA or DoD approval, economic proof, or authorization for operational use.

## Reviewer Answer

The first frozen policy failed. That failure was retained and used only as design evidence. A guarded successor was then frozen and tested on entirely new seeds. It passed the internal generated-software gate, but its effect is tiny and it remains neither external validation nor airworthiness evidence.

## Run Ledger

| Run | Validation Scenarios | Decision | Score Delta | CI95 | Energy Regression | Risk Regression |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| v1 adverse | 1120 | `NOT_PROMOTED_ASSURANCE_GATE_FAILED` | -0.00201305 | `[-0.0047998, 0.0007737]` | 0.01237646 | -0.02363863 |
| v2 guarded | 1400 | `INTERNAL_GENERATED_ASSURANCE_PASS_NOT_AIRWORTHINESS` | 4.771e-05 | `[1.361e-05, 8.181e-05]` | -8.299e-05 | 9.698e-05 |

## V2 Practical Effect

- Classification: `TINY_EFFECT_INTERNAL_GUARD_PASS`.
- Guarded selections: `1382` of `1400`.
- Non-guard specialist selections: `18`.
- Collision rate: `0`.
- Endpoint-failure rate: `0`.
- Reserve-breach rate: `0`.
- Planner expansion multiplier: `5.08332433`.

The v2 score improvement is statistically positive inside the frozen simulator, but the absolute effect is too small to support an aircraft-performance or economic claim. The useful result is the evidence discipline: adverse-result retention, fresh-seed lineage, hard safety vetoes, bounded spectral stress, and deterministic verification.

## Next Gate

1. Give an external runner the frozen v2 protocol, source snapshot, and verification command without the expected leaderboard.
1. Require the runner to publish raw checkpoints, environment package versions, terminal hashes, and all null or adverse rows.
1. Repeat on an accepted representative flight-dynamics environment or partner-approved historical data before any aerospace performance claim.
1. Obtain qualified aerospace software-assurance review before mapping any artifact toward certification objectives.

## Claim Gate

External reproduction, field validation, airworthiness, operational authorization, FAA/DoD approval, and economic claims remain false.
