# Machine Evidence Graph Protocol

The LumenCore evidence graph preserves complexity while making it traversable by reviewers, agents, and automated assurance tools.

Canonical machine file:

- `config/evidence_graph_v1.json`

Verifier:

- `code/ops/VERIFY_EVIDENCE_GRAPH.py`

Regression tests:

- `tests/test_evidence_graph.py`

Human navigation surfaces:

- `README.md`
- `EVIDENCE_INDEX.md`
- `docs/PR_CONSOLIDATION_MAP_2026-07-22.md`

## Design principle

The graph is not a simplified replacement for the repository. It is an index over the detailed implementation, receipts, tests, pull requests, evidence packages, and claim boundaries.

A node records:

- identity and type;
- current evidence state;
- canonical role;
- supported properties;
- explicitly unsupported properties;
- important files or missing promotion evidence.

An edge records relationships such as:

- stacked ancestry;
- consolidation;
- proposed succession;
- deployment;
- packaging;
- commercial use;
- reviewer indexing.

## Evidence states

The graph distinguishes:

1. `merged_capability`
2. `deployed_demo`
3. `first_party_reproduced`
4. `externally_executable`
5. `external_complete`
6. `field_validated`
7. `commercially_validated`
8. `held`
9. `historical`

These states are not interchangeable. A deterministic author replay cannot silently become an independent reproduction. A deployed demo cannot silently become field validation. A proposed commercial package cannot silently become customer traction.

## Promotion contract

The verifier owns the canonical transition registry. The JSON graph must contain the same transitions and exact required evidence markers.

- `first_party_reproduced` → `externally_executable`
- `externally_executable` → `external_complete`
- `external_complete` → `field_validated`
- `field_validated` → `commercially_validated`

A node assigned to `external_complete`, `field_validated`, or `commercially_validated` must carry the required support markers for that state. Merely changing a state label does not promote the evidence.

## Current machine conclusions

The indexed public state currently supports:

- merged Proof Capsule artifact-integrity controls through PR #34;
- a deployed bounded ProofLock demonstration through PR #36;
- first-party reproducibility for the pinned EIA package developed through PR #55;
- an externally executable clean-mainline package through PR #64;
- an external evaluation contract candidate through PR #49;
- a commercial validation-sprint package candidate through PR #35.

The indexed public state does not currently contain a node promoted to:

- `external_complete`;
- `field_validated`;
- `commercially_validated`.

The EchoLock pilot remains held because a discoverable public report path, baseline, locked metric, result state, limitations, and artifact manifest have not yet been linked into the graph.

## Verification

Run the graph and repository-navigation contract:

```bash
python code/ops/VERIFY_EVIDENCE_GRAPH.py --json
python -m unittest discover -s tests -p "test_evidence_graph.py" -v
```

To inspect a standalone graph file without the repository navigation surfaces:

```bash
python code/ops/VERIFY_EVIDENCE_GRAPH.py path/to/graph.json \
  --skip-repository-contract \
  --json
```

The verifier fails closed on:

- oversized, invalid UTF-8, duplicate-key, or non-finite JSON;
- repository identity or timestamp-format mismatch;
- duplicate evidence-state declarations;
- malformed node identity, type, title, PR number, or merged-state metadata;
- duplicate node IDs or PR numbers;
- unknown, duplicate, or self-referential edges;
- unsupported evidence states or relationship types;
- contradictory support boundaries;
- missing evidence required by upper promotion states;
- promotion-transition or requirement drift;
- silent reclassification of PR #64 beyond `externally_executable`;
- unsupported EchoLock pilot promotion;
- human navigation that omits an indexed pull request;
- loss of the canonical README-to-index entrypoint;
- loss of the machine graph, verifier, or protocol links from the evidence index.

The path-scoped GitHub Actions workflow compiles the verifier, validates the graph and reviewer-navigation contract, runs 19 adversarial regression tests, and uploads a machine-readable verification receipt for 30 days.

## Extension rule

Do not delete detail to make the graph smaller. Add typed nodes and edges when new evidence is created.

A new pilot should add at minimum:

- authorized source;
- baseline;
- locked metric;
- protocol or run identity;
- manifest;
- result state;
- negative or incomplete outcomes;
- limitations;
- evaluator or data-owner authority;
- promotion decision.

The graph should make the depth queryable without weakening it.
