# Independent Replication and Negative Results Protocol

Generated: 2026-07-13

## Scientific Contribution Target

LumenCore's most credible contribution is not a claim that one geometry always wins. It is a reproducible protocol for routing many candidate mechanisms through authoritative data, strong baselines, preregistered holdouts, falsification receipts, and independent replication.

Recognition cannot be promised. The contribution becomes scientifically meaningful only when outside reviewers can reproduce both positive and negative results without relying on private judgment or hidden tuning.

## Protocol

1. State one lane, one decision, and one primary metric before running the holdout.
2. Freeze authoritative source identifiers, retrieval timestamps, content hashes, schema, and inclusion rules.
3. Separate development, validation, and final holdout by time, entity, geography, or operating regime as appropriate.
4. Lock every candidate, baseline, hyperparameter range, tie rule, missing-data rule, failure rule, and exclusion rule before final evaluation.
5. Include a naive baseline, an accepted domain baseline, and the strongest feasible modern baseline.
6. Record all attempted candidates, failures, timeouts, and losses. Do not publish only winners.
7. Report effect size and uncertainty, not only win counts. Correct for multiple comparisons when many geometries compete.
8. Preserve executable code, environment lock, source manifest, result tables, logs, and an artifact-chain hash.
9. Ask an independent party to rerun the locked protocol on data withheld from LumenCore.
10. Promote a result to a field or economic claim only after the operational owner signs the metric, baseline, acceptance threshold, and conversion method.

## Minimum Replication Bundle

- human-readable protocol
- machine-readable protocol
- source manifest with hashes and licenses
- deterministic split manifest
- candidate and baseline registry
- environment and dependency lock
- one-command runner
- full result table, including failed runs
- uncertainty and multiplicity analysis
- claim-boundary statement
- artifact-chain receipt

## Falsification Receipt

Each benchmark must emit a receipt with:

- preregistration commit and timestamp
- protocol SHA-256
- source hashes
- selected candidate and selection basis
- untouched holdout metrics for every candidate and baseline
- winner, ties, and losses
- deviations from protocol
- allowed claim
- prohibited claims
- result artifact-chain SHA-256

## First Reference Case

The official EIA grid-wave benchmark is the first reference falsification case:

- protocol committed before results: `5b4ddbaef438e8f1d7c7d294a451d59280175b35`
- protocol SHA-256: `273eb823b0be4b2d403d0aaa591673c2e470e3d7f30abb166a43fe6e311a1c3d`
- official panel rows: `14704`
- development-selected candidate: `lissajous_phase_paths`
- holdout result: both official baselines beat every wave candidate
- result artifact chain: `83b4292005a199113df57acceda53c344eb8523869abe1e65a5847a8142d55c2`

This negative result is valuable because it proves the process can reject a favored geometry. It prevents a synthetic Kuramoto result from becoming an unsupported grid-performance claim.

## Next External Validation Design

The next partner-facing protocol should use a buyer- or agency-owned holdout and answer four questions:

1. Does the routed candidate improve the predeclared operational metric against the incumbent?
2. Does the improvement persist across regimes and uncertainty intervals?
3. How often does the system abstain or fail safely?
4. What measured workflow or economic consequence follows from the delta?

No public claim should move beyond the evidence level actually earned.
