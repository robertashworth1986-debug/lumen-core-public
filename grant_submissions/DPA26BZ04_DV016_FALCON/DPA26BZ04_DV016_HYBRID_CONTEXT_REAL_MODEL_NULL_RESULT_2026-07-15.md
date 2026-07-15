# DPA26BZ04-DV016 Hybrid Context Real-Model Null Result

## Evidence identity

- Run UTC: `2026-07-15T14:45:22.607246+00:00`
- Frozen protocol: `falcon_hybrid_context_protocol.v1`
- Protocol SHA-256: `4442c63743a419eeb3d2c090e340f6d875c4096e711679171ebea48439abcd77`
- Code SHA-256: `8c70ab92c98e9ca917530667f3b30496bbe17b4fc393d45faded31158136d8e5`
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Resolved model revision: `7ae557604adf67be50417f59c2c2f167def9a775`
- Model mode: local CPU inference with no paid API
- Model calls: `126`
- Total model-generation time: `1614.617368` seconds

## Result

The predeclared promotion gate did not pass. The null result is preserved and must not be presented as a hybrid-routing win.

| Strategy | Macro slice balanced accuracy | Macro slice F1 |
|---|---:|---:|
| Fixed ML only | 0.944444 | 0.941026 |
| LLM only | 0.407407 | 0.292460 |
| LLM-routed hybrid | 0.944444 | 0.941636 |
| Deterministic context router | 0.944444 | 0.942247 |

- Hybrid delta over fixed ML: `0.000000`
- Hybrid delta over LLM only: `0.537037`
- Route accuracy: `0.055556` (`1/18` correct route calls)
- Unsupported route-output rate: `0.833333` (`15/18` route calls)
- Unsupported label-output rate: `0.000000`
- Per-domain hybrid regression against fixed ML: `0.000000` in both domains

## Failure analysis

The model copied the prompt's literal pipe-delimited option string in most route calls. Strict allowlist validation correctly rejected those outputs and converted them to abstentions. The hybrid consequently fell back to the fixed expert and tied, rather than beat, the fixed-ML baseline. This is an output-control and routing-quality failure, not evidence of superiority.

Any follow-on constrained-choice router must use a new protocol identity, preserve the original thresholds, and be evaluated prospectively. This result must remain available beside any later improvement.

## Integrity receipt

- Output manifest SHA-256: `854dc5918c1e01345c60702c269798cef97da634ab50225a3cbdb80887d362c4`
- Output files, byte counts, source hashes, and manifest hash: independently verified
- Trace records: `126/126` independently verified
- Trace terminal hash: independently matched to the benchmark result
- Trace-chain verification: `true`
- Focused test receipt: `4 passed in 2.16s`
- External vault package ID: `FALCON_HYBRID_CONTEXT_20260715T144522Z`
- External vault manifest: canonical self-hash stored in `vault_manifest.sha256.json`
- Initial source-to-vault hash matches: `19/19`; the final manifest also covers this receipt

## Claim boundary

A future gate pass would support bounded internal feasibility only. This failed gate does not establish external validation, enterprise scale, agency acceptance, patent scope, operational performance, field savings, or universal superiority.
