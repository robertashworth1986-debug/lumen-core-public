# FALCON Hybrid Context Benchmark Protocol

Protocol schema: `falcon_hybrid_context_protocol.v1`

Configuration: `config/falcon_hybrid_context_protocol_v1.json`

Code: `code/falcon_hybrid_context_benchmark.py`

## Question

Can a real, revision-pinned LLM convert unstructured data-quality context into a validated specialist route that improves downstream structured-data classification over a single context-blind ML expert, while preserving an auditable trace and bounded unsupported-output rate?

This is a feasibility benchmark, not an enterprise-scale or operational claim.

## Frozen Design

- Domains: breast-cancer diagnostic measurements and wine chemistry.
- Source: datasets distributed with scikit-learn; dataset content is hashed at run time.
- Contexts: nominal, declared feature dropout, and declared high-noise telemetry.
- Structured experts: full-feature, dropout-robust, and noise-robust logistic pipelines.
- ML-only comparator: one fixed expert selected on validation data and used for every test context.
- LLM-only comparator: the same real LLM predicts the class from a bounded textual row and the context note.
- Hybrid: the LLM selects one allowlisted structured expert from context; that expert predicts the class.
- Deterministic context router: a non-LLM architecture control showing the attainable value of correct routing.
- LLM candidate: `Qwen/Qwen2.5-0.5B-Instruct`, Apache-2.0, with the exact retrieved revision recorded at run time.

## Split and Leakage Controls

1. Use a deterministic stratified train/validation/test split.
2. Select degraded features using training data only.
3. Fit imputers, scalers, feature ranking, and classifiers on training data only.
4. Select the fixed ML-only expert on validation slices only.
5. Freeze protocol and code before the real-model holdout run.
6. Context notes disclose data quality but never the target label.
7. Test labels are used only for final scoring.

## LLM Contract

The route response must be one JSON object containing an allowlisted `route_id`. Unknown routes, malformed output, extra executable instructions, or missing fields are rejected and mapped to `abstain`. The label response must contain one allowlisted class identifier; invalid output is scored as abstention and an incorrect prediction.

Every prompt, raw output, parsed result, validation decision, and source row identifier receives a canonical SHA-256 digest. Credentials, hidden prompts, and private files are not serialized.

## Primary Metrics

- macro-average balanced accuracy across dataset/context slices
- macro-F1 across the same slices
- hybrid delta over fixed ML-only
- hybrid delta over LLM-only
- LLM route accuracy
- unsupported route-output rate
- unsupported label-output rate
- per-call and aggregate latency
- peak resident memory where measurable
- deterministic replay equality for non-model transformations

## Promotion Gate

`promotion_gate_passed` is true only when all conditions pass on the untouched test set:

1. both domains complete with a real model revision
2. hybrid balanced accuracy exceeds fixed ML-only by the configured minimum
3. hybrid balanced accuracy exceeds LLM-only by the configured minimum
4. hybrid is not worse than fixed ML-only in either domain beyond the configured tolerance
5. route accuracy meets threshold
6. unsupported route-output rate is at or below threshold
7. every trace and result hash verifies
8. no training/test leakage audit fails

No threshold may be weakened after observing test results. Failed gates remain in the artifact set.

## Interpretation Boundary

A passing result would support bounded feasibility for LLM-mediated routing of structured-data experts across two small public datasets. It would not establish enterprise scale, operational utility, novel scientific discovery, government acceptance, external validation, patent validity or scope, field savings, or superiority over all state-of-the-art systems.
