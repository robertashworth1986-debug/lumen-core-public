# Aerospace Baseline Matrix

## Important boundary

Compliance baselines are not performance opponents. You do not "beat" DO-178C, NASA systems engineering practice, or verification discipline. You satisfy, map to, or prepare evidence against them.

LumaJet can attempt to beat performance baselines only inside simulation, such as:

- straight-line routing baseline,
- random routing baseline,
- uniform honeycomb baseline,
- no-flowform thermal routing baseline.

## Reviewer-safe baseline categories

| Category | LumaJet Phase I target | Status |
|---|---|---|
| Requirements traceability | Each claim maps to an artifact and test | generated |
| Verification and validation | Simulation tests and repeatable outputs | generated |
| Software assurance posture | No flight control; no actuation; evidence-only | generated |
| Tool evidence | Hashes, manifests, reproducibility script | generated |
| Risk register | Safety, claim, export, and autonomy boundaries | generated |
| Performance baseline | Champion vs straight/random synthetic baselines | generated |
| External validation path | Mentor/lab review requested before hardware | required next |

## What LumaJet is allowed to claim after this run

- Simulation-only comparison results.
- Generated evidence package.
- Baseline matrix.
- Hash-frozen artifacts.
- Reviewer-safe SBIR Phase I scope.

## What LumaJet is not allowed to claim

- Certified aircraft capability.
- Airworthiness.
- Flight safety.
- Autonomous flight.
- Drone swarm control.
- Propulsion performance.
- Field validation.
