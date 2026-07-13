# MDA Control-Mapping Synthetic Feasibility Result

Generated UTC: `2026-07-13T22:30:42.731910+00:00`

## Verdict

- Synthetic feasibility gate passed: `false`
- Selected lexical threshold: `0.3`
- Selected hybrid threshold: `0.3`
- Best baseline: `tfidf_lexical_retrieval`
- Candidate micro-F1 delta: `0.023050`

## Blind Holdout

| Strategy | Precision | Recall | Micro F1 | Macro F1 | Coverage | Unsupported mapping |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `static_identifier_crosswalk` | 1.0000 | 0.7826 | 0.8780 | 0.8530 | 0.7083 | 0.0000 |
| `tfidf_lexical_retrieval` | 0.8750 | 0.9130 | 0.8936 | 0.8905 | 1.0000 | 1.0000 |
| `hybrid_static_then_lexical_v1` | 0.8800 | 0.9565 | 0.9167 | 0.9143 | 1.0000 | 1.0000 |

## Gate Detail

- `parser_conformance`: `true`
- `provenance_completeness`: `true`
- `minimum_holdout_coverage`: `true`
- `maximum_unsupported_mapping_rate`: `false`
- `minimum_micro_f1_delta_over_best_baseline`: `false`
- `all_baselines_present`: `true`

## Evidence Boundary

A passing result supports synthetic software conformance and feasibility only. It does not establish operational ACAS or SCAP parsing, authoritative STIG or CVE mapping, NIST or RMF compliance, CMMC status, MDA validation, field performance, labor savings, production readiness, or authorization to operate.

The fixtures deliberately use synthetic identifiers and text. This result tests software mechanics and cannot be presented as operational cyber accuracy or Government validation.
