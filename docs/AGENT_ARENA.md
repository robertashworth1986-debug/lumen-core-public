# LumenCore Agent Arena V5

## Canonical role

Agent Arena is **not a separate LumenCore product**. It is the adversarial multi-agent validation sub-harness inside the existing proof-to-pilot architecture. Its job is to make an agentic candidate compete under predeclared rules while the scenario, selection split, holdout floors, baseline, referee, score function, evidence boundary, and custody system remain outside agent control.

The reference implementation is intentionally provider-agnostic: a deterministic policy ships with the repository for reproducibility, while the `ProposalProvider` interface can later wrap a pinned LLM, local model, optimizer, or buyer-supplied agent without granting that provider authority over scoring or evidence.

## V2 → V5 capability chain

### V2 — adversarial multi-agent floor

V2 adds failure modes that are closer to real distributed-agent evaluation than a cooperative demo:

- role-specific noisy telemetry;
- underreported demand, heat, capacity loss, or failures;
- Byzantine control proposals;
- specialist dropout;
- per-role trust scoring based on normalized disagreement;
- trust-threshold filtering and weighted-median synthesis;
- deterministic red-team checks over a robust median observation.

Every attack type, strength, compromised role, and dropout role is frozen in the scenario before execution. This is a deterministic fault-injection model, not proof of a formal Byzantine-tolerance threshold. The scorecard reports when compromised roles survive trust filtering instead of treating a completed run as proof that trust was robust.

### V3 — tournament with leakage control

V3 introduces predeclared candidate profiles. All profiles compete on **selection floors and selection seeds only**. The tournament computes a locked objective from mean score, worst-tail CVaR, and violation rate, then emits a `champion_selected` event with `holdout_results_observed=false`.

Only after that event is written does the harness execute the champion on the disjoint holdout seeds and holdout boss floors. Provider observations omit floor IDs, labels, seed IDs, holdout flags, attack labels, and compromise flags. This blocks direct control flow on holdout metadata and prevents post-hoc champion selection using the final test set. Because the reference scenario is public and sensor patterns can still be recognizable, this is provider-input blinding rather than a claim that the public holdout is secret; credible promotion still requires an independently held scenario.

The reference tournament also includes a `no_red_team_ablation` profile so the contribution of the red-team stage can be compared during selection instead of merely assumed.

### V4 — robustness statistics

V4 makes the result distribution visible instead of promoting one favorable run:

- deterministic bootstrap intervals over holdout-floor clusters;
- median and direction-aware adverse-tail CVaR10 statistics;
- candidate score win rate;
- no-worse constraint-violation rate;
- attack-mode breakdowns;
- separate selection and holdout seed populations.

The default V5 scenario uses eight selection seeds, eight disjoint holdout seeds, six selection floors, and two holdout bosses.

### V5 — evidence and finite-grid reference

V5 binds the run to machine-verifiable identities:

- exact scenario lock SHA-256;
- engine source SHA-256;
- provider descriptor SHA-256 bound to the executing callable's inspected source;
- clean Git commit and source-tree identity, with dirty executions rejected;
- event-by-event predecessor hash chain;
- event Merkle root for the complete ordered event set;
- exact-file manifest with byte counts and SHA-256 values;
- unsigned execution receipt containing runtime identity and manifest binding;
- self-hash over the receipt body;
- fail-closed verifier for current source identity, manifest, event chain, Merkle root, summary custody, and execution-receipt consistency.

V5 also computes a **referee-only finite-grid reference** on each holdout floor. The reference sees ground truth and searches the frozen control grid; candidate agents never see it. It is the best point found on that grid, not a mathematical ceiling on a continuous optimum. The report shows candidate-vs-baseline improvement, the candidate's absolute score and violations, and the gap to the grid reference. The absolute acceptance gate is authoritative: a positive relative delta cannot turn a constraint-violating candidate into a pass.

## Execution sequence

```text
                 FROZEN V5 SCENARIO
  controls • constraints • attacks • seed split • weights
                          |
                          v
              SELECTION FLOORS / SEEDS
                          |
       +------------------+------------------+
       |                  |                  |
   profile A          profile B          profile ...
       |                  |                  |
       +-------- adversarial agents ----------+
                          |
                   trust synthesis
                          |
                    red-team gate
                          |
                          v
               deterministic referee
                          |
                  selection objective
                          |
                          v
              CHAMPION LOCKED EVENT
              holdout_observed = false
                          |
                          v
                HOLDOUT BOSS FLOORS
                          |
             +------------+------------+
             |                         |
      locked baseline             champion
             |                         |
             +------------+------------+
                          |
                  deterministic referee
                          |
                          +---- referee-only grid reference
                          |
                          v
       floor-cluster bootstrap / adverse-tail analysis
                          |
                          v
       SHA-256 chain + Merkle + manifest + receipt
```

## Scenario progression

The frozen reference scenario currently contains six selection floors and two holdout bosses:

1. congestion;
2. thermal pressure with heat-blind telemetry;
3. partial capacity loss with underreported loss;
4. specialist dropout plus hidden fault pressure;
5. Byzantine control proposal attack;
6. mixed cascade selection floor;
7. cascading multi-constraint holdout boss;
8. Byzantine + dropout holdout boss.

The point is not to make every candidate win. The point is to make failure measurable, attributable, replayable, and difficult to explain away after the fact.

## Evidence artifacts

Running the arena emits:

- `scenario.lock.json` — exact scenario bytes used by the run;
- `events.jsonl` — ordered, hash-linked selection, champion-lock, holdout, and completion events;
- `summary.json` — tournament state, absolute acceptance gate, holdout statistics, trust audit, attack breakdown, grid-reference comparison, identities, and claim boundary;
- `SCORECARD.md` — compact reviewer-readable result;
- `manifest.sha256.json` — exact byte counts and hashes for the evidence set;
- `execution_receipt.json` — manifest-bound, unsigned runtime receipt with a self-hash over its body. The hash detects accidental alteration only after a digest is independently pinned; it is not a signature.

## Run and verify

From the repository root:

```bash
python code/agent_arena.py run --config config/agent_arena_v5.json --out out/agent_arena
python code/agent_arena.py verify --out out/agent_arena
```

A verifier failure is a failed evidence bundle. The implementation does not silently downgrade a dirty source tree, source-identity mismatch, broken chain, mismatched manifest, inconsistent receipt, unexpected scenario schema, non-finite proposal, or undeclared agent control into a warning. Successful verification is reported as `INTEGRITY_VERIFIED_UNSIGNED`; it establishes internal consistency against the checked-out source, not authorship or external authenticity.

## Provider integration contract

The scoring path accepts a provider callable:

```text
(role, observation, control_bounds) -> proposal mapping
```

The provider receives sensor values only, without floor identity, seed identity, holdout status, attack label, or compromise status. It may propose only declared control values. The engine rejects undeclared controls and non-finite values before synthesis, and binds the provider descriptor to the inspected implementation source. A future external-model adapter should freeze at least provider/model identity, version, inference settings, prompt or policy hash, and relevant adapter hash in its inspectable callable before execution. API keys, private prompts, credentials, and private buyer data must not be placed in the public evidence bundle.

## Claim boundary

**Synthetic/replay software evidence only.** Agent Arena can establish deterministic software behavior, replay reproducibility, hash-verifiable provenance, holdout discipline, and performance/robustness statistics inside the declared abstract model.

It does **not** establish field performance, production safety, customer savings, certification, agency endorsement, external validation, or universal superiority.

A positive holdout delta means only that the locked champion scored differently from the locked baseline inside this model. It is not an acceptance result. The locked reference run currently fails the zero-violation absolute gate, and the trust audit does not demonstrate Byzantine tolerance. A large grid-reference gap is equally important evidence: it means the candidate still leaves substantial performance on the table under the same referee.

## Promotion gate

The next meaningful promotion is external execution, not V6 naming:

1. pin the commit, source tree, V5 scenario, provider implementation, and run protocol;
2. have a qualified non-author evaluator execute the arena;
3. have that evaluator run the verifier independently;
4. return a receipt whose digest is independently published, countersigned, or cryptographically signed, including commit, source tree, scenario hash, engine hash, provider hash, event roots, manifest hash, runtime identity, and result;
5. for a paid pilot, replace or supplement the abstract referee with a buyer-approved dataset or simulator while preserving the accepted baseline, locked metric, threshold, selection rule, holdout discipline, failure definitions, and prohibited claims.

That is the boundary between a strong internal agent benchmark and externally validated proof.
