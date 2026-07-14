# Contributing To LumenCore Quant Hub

LumenCore Quant Hub is a public research and engineering record for reproducible benchmarking, evidence provenance, hybrid routing experiments, reviewer context, and human-gated operational preparation.

Start with `docs/REVIEWER_START_HERE.md` and preserve the claim boundaries in `README.md`.

## Useful Contributions

- Reproduce a benchmark and report the exact environment and artifact hashes.
- Add a protocol-compliant baseline, ablation, leakage check, or failure case.
- Improve deterministic tests, schemas, accessibility, or reviewer navigation.
- Report data-quality defects or unsupported claims with file and line references.
- Propose an external held-out evaluation with a named data owner, preregistered metric, and acceptance threshold.

## Ground Rules

1. Never include credentials, private records, counsel communications, meeting credentials, or proprietary source data.
2. Do not rewrite historical evidence. Add a dated correction or explicit supersession record.
3. Preserve negative results, non-wins, exclusions, and uncertainty.
4. Do not label synthetic, replay, paper, or self-evaluated results as field validation.
5. Do not add code that sends, submits, publishes, trades, spends, or changes an external account without a separate authenticated HumanUnlock boundary.
6. Keep each pull request focused and explain its claim impact.

## Development

```bash
git clone https://github.com/robertashworth1986-debug/lumen-core-public.git
cd lumen-core-public
python -m pytest -q tests/test_quant_hub_reviewer_context.py
```

Run targeted tests for every changed builder or control. For dashboard changes, verify the relevant page at desktop and mobile sizes and confirm that missing data produces a truthful empty or unavailable state.

## Evidence-Bearing Pull Requests

Describe:

- source identity and authorization;
- protocol and split version;
- baselines and acceptance gate;
- commands run and tests passed;
- output paths and SHA-256 receipts;
- wins, non-wins, failures, and known limitations;
- whether any public claim changes.

Generated state from recurring monitors should be attached to workflow runs or published through a deliberate release process. It should not create recurring commits to `main`.

## Language Support

The repository does not claim universal language expertise. A new language or toolchain is accepted only with a detected runtime or compiler, a minimal reproducible test, and a reviewer-visible receipt. See `config/hybrid_agent_capability_registry_v1.json`.

## License

Contributions are licensed under the repository's MIT License.
