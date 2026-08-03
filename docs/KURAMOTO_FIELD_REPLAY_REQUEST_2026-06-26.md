# Kuramoto Nonpromotion and Protocol Redesign Brief

Generated UTC: `2026-07-29T06:17:51.902760+00:00`

The filename is retained for downstream compatibility. This artifact blocks the request and is not an outreach packet.

Record the direct measured Kuramoto nonpromotion result, close the legacy field-replay narrative, and define the gates for a future source-specific wave-family benchmark.

## Measured Result

- Candidate: `kuramoto_phase_coupling`
- Development-selected candidate: `lissajous_phase_paths`
- Candidate was protocol-selected: `false`
- Status: `field_replay_request_blocked_source_specific_baseline_gate_failed`
- Direct measured wins vs Kalman: `482/1525`
- Losses or ties vs Kalman: `1043`
- Mean skill delta vs Kalman: `-0.508190706`
- Best registered baseline: `autoregressive_ridge_p14`
- Registered baseline mean wins: `0/6`
- Registered baseline gate passes: `0/6`
- All-baseline Holm gate passed: `false`
- Panel rows: `14704`
- Holdout chain SHA-256: `ffb3e4448ad393027791e3c582b2c8d0dde1e6cf0685fafd630727bb2477a9cb`

## Request Gate

- Request type: `not_a_field_replay_request`
- Current status: `blocked`
- Field-replay request allowed: `false`
- Manual outreach allowed: `false`
- Paid protocol-review scoping allowed: `true`

Do not ask an external owner to replay Kuramoto as a promoted candidate; preserve its direct measured nonpromotion result and redesign the next source-native wave benchmark.

Unlock conditions:

- select the future candidate using development data only
- freeze source-native baselines before opening the holdout
- beat every registered baseline on the untouched holdout
- pass multiplicity correction and independent frozen repeats
- obtain exact action-time approval before any external request

## Claim Boundary

Kuramoto was measured directly on the frozen EIA panel, was not selected by the development protocol, and lost on mean skill to the named Kalman baseline and every registered baseline. This is useful negative evidence, not a promoted candidate or field-performance result.

- Field-validation claim allowed: `false`
- Realized savings claim allowed: `false`
- Live execution allowed: `false`

## Next Actions

1. Keep the negative result and its chain hash in the reviewer room.
2. Do not send the legacy field-replay request.
3. Map each future wave family to the exact source task it can represent.
4. Select the future candidate on development data only.
5. Freeze all source-native baselines before opening the holdout.
6. Require all-baseline success after multiplicity correction.
7. Require independent frozen repeats before a field-replay request.
8. Offer only a bounded protocol review while those gates remain closed.

Packet SHA-256: `02ab6e066178fadd3bae69605da258cb1c4e55a318e8ebea914de087423e47a6`
