# LumenCore Agent Arena

## Role in the canonical product

Agent Arena is **not a separate LumenCore product**. It is an adversarial multi-agent validation harness inside the existing proof-to-pilot architecture. Its purpose is to make an agentic system face locked scenarios, constraints, baselines, holdouts, and failure rules while a deterministic referee produces reviewer-readable evidence.

It advances the single active external-validation / paid-pilot outcome by making agent behavior testable without asking a reviewer to trust the agents' own explanations.

## Architecture

The reference arena separates six authorities:

1. **Scenario lock** — freezes floors, seeds, baseline, control bounds, metric thresholds, scoring weights, claim boundary, and the holdout boss before execution.
2. **Specialist agents** — router, thermal, resilience, efficiency, and telemetry-skeptic agents propose bounded controls from the same observation.
3. **Synthesizer** — uses bounded median-style fusion so no single specialist can dominate the plan.
4. **Red team** — challenges obvious under-provisioning and applies deterministic fail-closed mitigations.
5. **Referee / environment** — evaluates both the locked baseline and candidate against ground truth. Agents cannot alter the model, constraints, weights, or result calculation.
6. **Evidence ledger** — writes an event-level SHA-256 chain, summary, scorecard, frozen scenario copy, and manifest.

```text
frozen scenario + seeds
          |
          v
  noisy observation ------------------------------+
          |                                        |
          v                                        |
  specialist proposals                             |
          |                                        |
          v                                        |
 bounded synthesizer                               |
          |                                        |
          v                                        |
     red-team gate                                 |
          |                                        |
          +------------> candidate plan            |
                                                   v
locked baseline ----------------------------> deterministic referee
                                                   |
                                                   v
                                       metrics + violations + score
                                                   |
                                                   v
                              hash-chained events + manifest + scorecard
```

## Dungeon progression

The v1 scenario deliberately escalates instead of using one easy benchmark:

- **F01 — Congestion:** high demand.
- **F02 — Thermal:** demand plus ambient heat pressure.
- **F03 — Capacity loss:** partial infrastructure loss.
- **F04 — Telemetry:** noisy observations plus higher fault pressure.
- **F05 — Cascade holdout boss:** demand, capacity loss, thermal pressure, faults, and telemetry uncertainty combined. This is the only holdout floor.

The holdout label is fixed in the scenario file before the run. It is not used as a post-hoc cherry-picked success case.

## Evidence boundary

**Synthetic/replay software evidence only.** The Arena can support claims about deterministic software behavior, reproducibility, hash-verifiable provenance, and performance inside the declared abstract model. It does **not** establish field performance, production safety, customer savings, external validation, certification, agency endorsement, or universal superiority.

A positive candidate delta is not a field-performance claim. It means only that the reference policy scored differently inside the locked abstract model.

## Run

From the repository root:

```bash
python code/agent_arena.py run --config config/agent_arena_v1.json --out out/agent_arena
python code/agent_arena.py verify --out out/agent_arena
```

Outputs:

- `scenario.lock.json` — exact scenario bytes used for the run.
- `events.jsonl` — event-by-event hash chain with observations, proposals, red-team findings, referee ground truth, baseline result, and candidate result.
- `summary.json` — locked configuration, aggregate metrics, paired deltas, evidence boundary, and next validation gate.
- `SCORECARD.md` — compact reviewer-readable result.
- `manifest.sha256.json` — byte counts and SHA-256 for every evidence artifact plus the event-chain root.

## Model-provider integration

The scoring path is provider agnostic. `run_arena()` accepts a `ProposalProvider` callable with this contract:

```text
(role, observation, control_bounds) -> proposal mapping
```

That provider may later wrap an LLM, local model, rules engine, optimizer, or buyer-supplied agent. The provider controls only proposed controls. It does not control scenario ground truth, bounds, constraints, score weights, hashing, the baseline, or verification.

For an external-model experiment, freeze the provider identity and inference settings in a new scenario revision or an execution receipt before running. Never put API keys or private prompts in the public evidence bundle.

## Promotion path

The high-value next step is **not** adding more dungeon floors. It is independent execution:

1. qualified non-author evaluator checks out the pinned commit;
2. evaluator runs the frozen scenario and `verify` command;
3. evaluator returns an immutable receipt with commit, scenario SHA-256, manifest SHA-256, runtime identity, and result;
4. for a paid pilot, replace or supplement the abstract environment with the buyer's accepted dataset / simulator while keeping the baseline, metric, threshold, holdout rule, failure definitions, and prohibited claims prelocked.

Only that later evidence can promote the claim category beyond internal synthetic/replay evidence.
