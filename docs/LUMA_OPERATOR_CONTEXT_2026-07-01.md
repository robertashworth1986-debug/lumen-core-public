# Luma Operator Context

Generated UTC: `2026-07-29T08:02:00.102537+00:00`
Context SHA-256: `473e498049dbfdf92e0c069dbc8599c302c9f0dd79a78963102dd5332a6a57d3`

## Current Truth

- Internal performance champion present: `false`
- Current performance champion: `none`
- Measured reference candidate: `kuramoto_phase_coupling`
- Development-selected candidate: `lissajous_phase_paths`
- Reference candidate was protocol-selected: `false`
- Named baseline: `kalman_local_linear_trend`
- Paired-day wins: `482/1525`
- Mean skill delta: `-0.508191`
- Registered baseline mean wins: `0/6`
- All-baseline Holm gate passed: `false`
- Compatible routes: `4`
- Direct measured routes: `2`
- Conditioned-synthetic routes: `2`
- Raw baseline comparison wins: `10/22`
- Direct all-baseline global promotions: `0`
- Performance rows reviewed: `32608`
- Legacy ready rows excluded: `358`
- Numeric fallbacks: `0`
- Geometry source inventory: `24` measured sources / `17081` rows
- Geometry source inventory is performance evidence: `false`
- Buyer field replay request ready: `false`
- Field validation claim allowed: `false`
- Real dollar savings claim allowed: `false`

No current geometry family is an internal performance champion. Kuramoto phase coupling was audited on 1525 paired measured EIA holdout days; it won 482 pairs against kalman_local_linear_trend but had a negative mean skill delta of -0.508191 and did not clear any complete source-specific all-baseline promotion gate. The broader source inventory is research capacity only, not performance evidence. The safe commercial ask is a paid protocol or evidence review, not a performance or savings claim.

No internal performance champion exists. Kuramoto was not development-selected and won 482/1525 paired measured days against kalman_local_linear_trend with mean skill delta -0.508191. Across 2 direct measured and 2 conditioned synthetic routes, the current 22 comparisons contain 0 global Holm positives.

## Live Domain

- State: `LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE`
- Reviewer ready: `false`
- Required feeds matched: `9/14`
- Stale/missing required feeds: `5`

## Source Breadth

- Runtime-bound keys: `22`
- Measured enabled sources: `17/17`
- Measured sectors: `14/14`
- Fresh HTTP measured sources: `25/29`
- Fresh HTTP measured rows: `2580`
- Live-context replay rows: `32608`
- Live-context candidate wins vs named baselines: `1`
- Live-context snapshot chain: `f51dcd96203fda99b0ad55b1d052fefaf7e4157d7cb3ea9686bd62dccc665b80`
- Latest measured providers in safe ping: `13`
- Latest blocked/thin providers in safe ping: `2`

Provider gaps to fix:
- `ALPACA`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.
- `NREL`: `PROBE_FAILED_OR_THIN`; next: Retry DNS/network and use a known NREL developer endpoint; current failure is name resolution.
- `EPA_AQS`: `PROBE_FAILED_OR_THIN`; next: Refresh the EPA AQS email/key pair; the latest probe reports invalid email/key.
- `KRAKEN`: `NO_LATEST_STATUS`; next: Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured.

## Replay Lanes

| Lane | Evidence Mode | Wins | Comparisons | Global Holm Positive | Samples | Mean Delta |
|---|---|---:|---:|---:|---:|---:|
| `wave_resonance_timing` | `direct_measured_replay` | 0 | 6 | 0 | 15250 | -0.52947 |
| `branching_transport` | `source_conditioned_synthetic_stress` | 3 | 5 | 0 | 42 | -0.008167 |
| `thermal_ventilation` | `source_conditioned_synthetic_stress` | 3 | 3 | 0 | 18 | 0.131017 |
| `time_series_model_routing` | `direct_measured_replay` | 4 | 8 | 0 | 17298 | 0.004536 |

## Dollar Gate

- Bounded estimated hourly signal: `$0`
- Bounded estimated annual signal: `$0`
- Blocked context-only annual surface: `$0.0`
- Safe line: The current priceable work is a bounded source-native benchmark and evidence protocol review. Realized savings require a future promoted candidate, buyer-authorized field replay, locked baseline, held-out data, accepted metric, and approved economic conversion.

## Protocol Review Lane

- Recommended buyer: `none`
- Action: Verify one current official channel, reconcile duplicate-send history, select a real recipient, and obtain exact action-time approval before outreach.
- Paid protocol-review scoping allowed: `true`
- Manual reviewed outreach allowed: `false`
- Send gate: No send is authorized. Verify the current official channel, reconcile duplicate-send history, select a real recipient, and obtain exact action-time approval.

## Next 10 Actions

- Run the focused proof tests before every commit.
- Treat the 24-source geometry inventory as research capacity, not performance evidence.
- Keep Kuramoto as measured negative evidence; do not call it a champion.
- Select the next wave-family candidate on development data only.
- Register every source-native baseline before opening the untouched holdout.
- Require every baseline gate to pass after multiplicity correction.
- Keep live-domain hash verification green after every proof feed update.
- Offer only a bounded paid protocol review while no candidate is promoted.
- Do not open new EPRI outreach; that lane remains inbound-only.
- Require exact action-time approval before any external send.

## Long-Arc Operator Prompt

Operate LumenCore as a measurement-first evidence and benchmark platform. The standard is reviewer-safe proof that survives hostile reading. Every comparison must name its source task, native units, registered baselines, chronology, metrics, multiplicity correction, code commit, hashes, negative results, and claim boundary. No current geometry family is a performance champion. Kuramoto is a useful direct measured negative result: it was not development-selected, won 482 of 1,525 paired EIA days against the named Kalman baseline, and had mean skill delta -0.508191. Keep direct measured and conditioned-synthetic routes separate. Treat source breadth as adapter inventory. The commercially honest near-term offer is a bounded source-native protocol review or benchmark implementation, with no candidate-win, field, savings, or live-execution claim. Publish only canonical secret-free proof feeds, preserve failures, and require exact action-time approval for every external send.
