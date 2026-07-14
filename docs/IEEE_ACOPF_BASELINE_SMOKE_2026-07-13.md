# IEEE AC-OPF Baseline Smoke Receipt

Generated UTC: `2026-07-14T10:31:08.091973+00:00`

Verify that the unchanged nonlinear AC-OPF reference engine executes locally before candidate routing.

## Result

- Networks converged: `4/4`
- Candidate execution started: `false`
- Receipt SHA-256: `989cafe22073816df0b7729e47afbd9592328a38266734b534109d730f513bf0`

| Network | Buses | Lines | Converged | Reported objective | Wall seconds |
|---|---:|---:|---|---:|---:|
| case14 | 14 | 15 | true | 8081.526614 | 0.811138 |
| case30 | 30 | 41 | true | 578.486251 | 0.190643 |
| case39 | 39 | 35 | true | 41872.302574 | 0.268826 |
| case118 | 118 | 173 | true | 129704.7402 | 0.375249 |

## Claim Boundary

This is a local baseline-execution receipt on public IEEE-style fixtures. It does not show that LumenCore beats an optimum, improves a utility operation, creates savings, or is field validated.

The reported objectives are fixture-specific and are not compared across networks.
