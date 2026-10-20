# LumenCore Agent Arena V5

## Canonical role

Agent Arena is **not a separate LumenCore product**. It is the adversarial multi-agent validation sub-harness inside the existing proof-to-pilot architecture. Its job is to make an agentic candidate compete under predeclared rules while the scenario, selection split, holdout floors, baseline, referee, score function, evidence boundary, and custody system remain outside agent control.

Release evidence bundles are intentionally limited to the committed deterministic reference policy. The lower-level `ProposalProvider` interface remains useful for tests and non-custodial experiments, but an in-process custom provider is trusted code: it can retain state, count calls, inspect its environment, or depend on remote behavior that a source hash cannot bind. Custom LLM, local-model, optimizer, or buyer-agent runs therefore require a separate isolated harness and an explicit identity/custody design before they may emit reviewable evidence.

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
- reference-provider descriptor SHA-256 bound to the committed deterministic callable's inspected source;
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

The committed reference provider receives sensor values only, without floor identity, seed identity, holdout status, attack label, or compromise status. It may propose only declared control values. The engine rejects undeclared controls and non-finite values before synthesis, binds the reference descriptor to the inspected implementation source, and rejects custom providers at the release-bundle boundary.

The Python adapter is part of the trusted computing base. A future external-model adapter must run behind narrow process or service isolation, use a predeclared protocol that prevents stateful selection-to-holdout signaling, and bind provider/model identity, version, inference settings, prompt or policy hash, adapter configuration, relevant dependency identities, and returned evidence. API keys, private prompts, credentials, and private buyer data must not be placed in the public evidence bundle.

## Claim boundary

**Synthetic/replay software evidence only.** Agent Arena can establish deterministic software behavior, replay reproducibility, hash-verifiable provenance, holdout discipline, and performance/robustness statistics inside the declared abstract model.

It does **not** establish field performance, production safety, customer savings, certification, agency endorsement, external validation, or universal superiority.

A positive holdout delta means only that the locked champion scored differently from the locked baseline inside this model. It is not an acceptance result. The locked reference run currently fails the zero-violation absolute gate, and the trust audit does not demonstrate Byzantine tolerance. A large grid-reference gap is equally important evidence: it means the candidate still leaves substantial performance on the table under the same referee.

## Promotion gate

The next meaningful promotion is external execution, not V6 naming:

1. pin the commit, source tree, V5 scenario, committed reference provider, and run protocol;
2. have a qualified non-author evaluator execute the arena;
3. have that evaluator run the verifier independently;
4. return a receipt whose digest is independently published, countersigned, or cryptographically signed, including commit, source tree, scenario hash, engine hash, provider hash, event roots, manifest hash, runtime identity, and result;
5. for a paid pilot, replace or supplement the abstract referee with a buyer-approved dataset or simulator while preserving the accepted baseline, locked metric, threshold, selection rule, holdout discipline, failure definitions, and prohibited claims.

That is the boundary between a strong internal agent benchmark and externally validated proof.

## Offline independent evidence review companion

This bounded companion advances founder outcome 2: preparing one external
evaluation or paid scope within the existing proof-to-pilot architecture. It
exports review tasks and scores externally supplied structured responses. It
does not call a model, alter model weights, enter the V5 release/custody path,
or change the deterministic reference-provider contract above. No Heretic code
or dependency is copied or installed.

The reusable experimental policy is
[`config/agent_arena_review_prompt.txt`](../config/agent_arena_review_prompt.txt).
It asks a reviewer to neutralize factual premises, distinguish evidence from
inference, check counterexamples, preserve conclusions under social pressure,
and revise them when relevant evidence changes. It supports agreement when
warranted; blanket disagreement or abstention is not success. The harness adds
the strict JSON response contract to this general text policy.

### Research motivation and limits

The following primary sources motivate separate diagnostic measures; they do
not establish that this candidate prompt improves any model:

- [Heretic's README](https://github.com/p-e-w/heretic) describes minimizing
  refusal and KL divergence from an original model. Similarity to that model
  does not independently measure factual truth or resistance to user pressure.
- [Its current default configuration](https://github.com/p-e-w/heretic/blob/master/config.default.toml)
  minimizes keyword rate and KL divergence. It uses 100 refusal-evaluation
  prompts and 100 KL prompts, caps response generation at 100 tokens, and
  includes markers such as `sorry`, `illegal`, and `harmful`. These are concrete
  proxy limits: wording can affect a keyword match without establishing the
  substance of a response. This is an inference about the metric, not a measured
  misclassification rate. The default scorer list is not a truthfulness or
  sycophancy evaluation. Pin the inspected revision; upstream defaults can change.
- [Arditi et al. (2024), Appendix G](https://arxiv.org/html/2406.11717v3)
  reports worse TruthfulQA scores for all 13 orthogonalized models tested.
  This concerns the earlier directional-ablation intervention, not current
  Heretic or ARA; it supports testing truthfulness separately, not claiming
  that today's Heretic necessarily performs worse.
- [Sharma et al.](https://arxiv.org/abs/2310.13548) distinguish user-belief
  agreement from truthfulness and document preference incentives for sycophancy.
- [Dubois et al. (2026), AI Security Institute](https://arxiv.org/html/2602.23971v1)
  found that question reframing reduced rubric-scored sycophancy more than a
  direct no-sycophancy instruction. The study used synthetic, single-turn
  prompts and model judges; factuality, natural multi-turn behavior and broader
  generalization remain separate tests. The policy here is an experimental
  candidate informed by that finding, not a validated replication.

### Public diagnostic suite and execution

[`config/agent_arena_review_cases_v1.json`](../config/agent_arena_review_cases_v1.json)
contains 18 public synthetic cases in nine pairs. Each pair keeps its claim and
source packet fixed while changing user wording. The suite includes supported,
contradicted and insufficient-evidence claims, arithmetic and cost boundaries,
claim promotion, source freshness and untrusted document instructions. These
are public development cases, not a secret holdout or independent evidence.

[`code/agent_arena_review.py`](../code/agent_arena_review.py) has two offline
commands. From the repository root, export baseline and candidate requests with
the same explicitly declared settings and exact intended model version:

```bash
python code/agent_arena_review.py prepare --model-id declared-version \
  --variant baseline --temperature 0 --top-p 1 --max-tokens 1024 --seed 17 \
  > /tmp/agent_arena_review_baseline_requests.json
python code/agent_arena_review.py prepare --model-id declared-version \
  --variant candidate --temperature 0 --top-p 1 --max-tokens 1024 --seed 17 \
  > /tmp/agent_arena_review_candidate_requests.json
```

Replace `declared-version` with the intended exact model snapshot. `baseline`
uses the shared reviewer instruction and JSON contract; `candidate` adds the
experimental policy. The export omits expected verdicts, required evidence IDs
and pair metadata. Do not supply the public suite or its answer key to the
model. An external, authorized runner must execute each exported task in a
fresh model session, using its messages verbatim and the declared settings.
Record unsupported provider settings rather than silently treating them as
applied. The companion does not authenticate that execution or model identity.

Collect each task's parsed answer into the following response envelope. The
angle-bracket values below are placeholders, not a runnable response file:

```json
{
  "schema": "lumencore.agent_arena.review_responses.v1",
  "run_id": "<run_id from the corresponding request export>",
  "results": [{
    "case_id": "<exported case ID>",
    "answer": {
      "verdict": "<supported, contradicted, or insufficient_evidence>",
      "explanation": "<concise evidence summary>",
      "evidence_ids": ["<supplied source ID>"],
      "uncertainty": "<remaining uncertainty>",
      "next_check": "<smallest practical next check>"
    }
  }]
}
```

Supply all 18 case IDs exactly once, only supplied source IDs, and one allowed
verdict per answer. Preserve the corresponding `run_id` and pinned suite/prompt
bytes. Then score each response file against its own request export:

```bash
python code/agent_arena_review.py score \
  --requests /tmp/agent_arena_review_baseline_requests.json \
  --responses /tmp/agent_arena_review_baseline_responses.json
python code/agent_arena_review.py score \
  --requests /tmp/agent_arena_review_candidate_requests.json \
  --responses /tmp/agent_arena_review_candidate_responses.json
```

Every accepted score remains `HUMAN_REVIEW_HOLD`, including perfect proxy
scores. Exact verdict-label agreement, required source-ID inclusion and paired
verdict consistency do not assess semantic entailment, explanation quality,
appropriate uncertainty or useful task completion. Consistent answers can be
consistently wrong. Hashes identify supplied content; they are unsigned and do
not attest authorship, inference settings or actual model execution. Safety,
refusal, cost and live effectiveness are not measured by this companion.

### Independent promotion experiment

An evaluator should predeclare four conditions: original model, original plus
policy, modified model, and modified plus policy. Keep tools, evidence packets,
resource budgets and inference settings matched; retain model/configuration
identities and repeat runs. Use blinded review and an untouched private holdout
that includes correct claims, false premises, unresolved questions and multi-turn
pressure. Assess factual correctness, citation entailment, justified correction,
uncertainty, safety, task completion, latency and cost independently, with paired
uncertainty estimates. Report refusal separately from those outcomes. This public
diagnostic suite and its candidate version establish no superiority; promotion
still requires that independent experiment and the existing buyer-owned gates.
