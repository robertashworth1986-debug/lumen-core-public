# MDA Control-Mapping Open-Set Synthetic Result

Generated UTC: `2026-07-13T22:38:56.019882+00:00`

## Verdict

- Synthetic open-set gate passed: `false`
- Candidate validation constraints feasible: `true`
- Candidate score threshold: `0.3`
- Candidate margin threshold: `0.1`
- Best baseline: `tfidf_lexical_retrieval`
- Candidate micro-F1 delta: `0.020319`
- Preregistration commit: `ff610a147b79350a37f92cfa65853cd402885922`
- Protocol SHA-256: `9a694ed6f194137880c070e73355ef826a51d3fed438ccf65adf6d4726ca80f0`
- Fixture-chain SHA-256: `25f32a2e03157f6f058f1022bec7d0f0ea151991fc4e1c68d0b91fe59b1e278e`

## Blind Holdout

| Strategy | Precision | Recall | Micro F1 | Macro F1 | Supported coverage | Overall coverage | Unsupported mapping |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `static_identifier_crosswalk` | 1.0000 | 0.6786 | 0.8085 | 0.8048 | 0.7083 | 0.4722 | 0.0000 |
| `tfidf_lexical_retrieval` | 1.0000 | 0.8571 | 0.9231 | 0.9155 | 1.0000 | 0.6667 | 0.0000 |
| `hybrid_static_then_open_set_lexical_v2` | 1.0000 | 0.8929 | 0.9434 | 0.9393 | 0.9583 | 0.6389 | 0.0000 |

## Gate Detail

- `parser_conformance`: `true`
- `provenance_completeness`: `true`
- `validation_constraints_feasible`: `true`
- `minimum_holdout_supported_coverage`: `true`
- `maximum_holdout_unsupported_mapping_rate`: `true`
- `minimum_micro_f1_delta_over_best_baseline`: `false`
- `all_baselines_present`: `true`

## Evidence Boundary

A passing result supports independent synthetic open-set routing feasibility only. It does not establish operational ACAS or SCAP parsing, authoritative STIG or CVE mapping, NIST or RMF compliance, CMMC status, MDA validation, field performance, labor savings, production readiness, or authorization to operate.

V1 remains a separate negative result. V2 uses a new seed and new fixtures; neither experiment establishes operational cyber accuracy or Government validation.

## Next Evidence Gate

If v2 passes, rerun a separately preregistered protocol on lawfully obtained representative artifacts with a qualified cyber/RMF reviewer and an independently held blind set.
