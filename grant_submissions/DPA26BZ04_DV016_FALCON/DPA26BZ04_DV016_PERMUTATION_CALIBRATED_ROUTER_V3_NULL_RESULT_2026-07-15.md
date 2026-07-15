# DPA26BZ04-DV016 FALCON Permutation-Calibrated Router v3 Null Result

Run UTC: `2026-07-15T17:33:57.139986+00:00`
Status: `FROZEN_NULL_RESULT_PRESERVED`
Qualification gate passed: `false`

## Decision

The frozen v3 qualification gate failed. The run is retained as a null result and must not be described as a qualified router, hybrid lift, field validation, or agency acceptance.

## Observed Result

- Correct decisions: `27/30`
- Overall accuracy: `0.900000`
- Unsupported output rate: `0.000000`
- Mean permutation agreement: `0.822222`
- Minimum permutation agreement: `0.333333`
- Failed checks: `mean_permutation_agreement, minimum_permutation_agreement, per_context_accuracy`

### Per Context

| Context | Accuracy |
| --- | ---: |
| `dropout` | `1.000000` |
| `noise` | `1.000000` |
| `nominal` | `0.700000` |

### Error Receipt

| Dataset | Note | Expected | Selected | Agreement | Margin |
| --- | ---: | --- | --- | ---: | ---: |
| `breast_cancer_diagnostic` | `0` | `nominal` | `noise` | `0.333333` | `0.291667` |
| `breast_cancer_diagnostic` | `3` | `nominal` | `noise` | `0.500000` | `0.632812` |
| `wine_chemistry` | `3` | `nominal` | `noise` | `0.500000` | `0.684896` |

## Integrity

- Source manifest SHA-256: `2b6ad75db13396a26ab2600da73e764b33400f815945e3e9f057cf699bfb5bcb`
- Protocol SHA-256: `6384d5f9755e70e868052b0887c4a8d981068de85fbd89c968c874c1808521d9`
- Runner SHA-256: `aa4c37b20b5d732ede34ec25f33897b5dc059756455dc1176b3480ba5e74daa9`
- Trace records: `30`
- Trace terminal SHA-256: `a2b51eb22f287f939909028f06218e0f7077e65b414ac9b8af858b21a83015ec`
- Model weights SHA-256: `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`
- Raw prompts and model outputs are retained in the source packet, not this public projection.

## Requirement Impact

This attempt adds bounded real-model, CUDA, single-token, prior-calibrated routing evidence. It does not close the FALCON requirement for a same-row ML-only, LLM-only, and hybrid comparison.

## Next Allowed Step

Freeze a new same-row comparative protocol for ML-only, LLM-only, and hybrid systems on a reserved holdout. Preserve v1-v3 unchanged and test lift, calibration, abstention, latency, and failure modes against named baselines.

## Claim Boundary

A qualification pass would support only bounded internal evidence that the frozen local model and permutation-calibrated single-token scoring method classify these frozen note templates across two named domains. It would not establish hybrid performance lift, external validation, field readiness, agency acceptance, patent scope, safety, savings, enterprise scale, or universal superiority.

Reviewer feed SHA-256: `8938e4e3ea0d1f62786f8bc4ab508aa7060dc8c66d80a3ca48a261743917f98e`
