# FALCON Independent Reproduction Handoff

Date: 2026-07-15

Status: `UNSIGNED_REVIEWER_TEMPLATE_READY`

## Reviewer Ask

Independently rehash and reproduce the frozen FALCON v3 result. Confirm whether the supplied bytes, pinned model revision and weights, trace chain, `27/30` result, three named failed checks, and null-result status reproduce on a reviewer-controlled runner.

This is a reproducibility request, not a request to endorse model quality. A successful receipt validates the integrity and reproducibility of the failed qualification. It does not convert the result into a pass.

## Frozen Identity

- Protocol SHA-256: `6384d5f9755e70e868052b0887c4a8d981068de85fbd89c968c874c1808521d9`
- Runner SHA-256: `aa4c37b20b5d732ede34ec25f33897b5dc059756455dc1176b3480ba5e74daa9`
- Source manifest SHA-256: `2b6ad75db13396a26ab2600da73e764b33400f815945e3e9f057cf699bfb5bcb`
- Trace terminal SHA-256: `a2b51eb22f287f939909028f06218e0f7077e65b414ac9b8af858b21a83015ec`
- Model revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- Model weights SHA-256: `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`
- Public feed file SHA-256: `8527167a01635085fd67e6a093007679d0dac78b00e4979ef5169332417ce8a8`
- Custody packet manifest SHA-256: `b10f3ff0586e01fa859d5bf49f6466f39033c4022d3e1a1a99a4f1bbcca66598`

## Expected Reproduction

- Status: `FROZEN_NULL_RESULT_PRESERVED`
- Qualification gate: `false`
- Correct decisions: `27/30`
- Overall accuracy: `0.900000`
- Unsupported output rate: `0.000000`
- Mean permutation agreement: `0.822222`
- Minimum permutation agreement: `0.333333`
- Failed checks: `mean_permutation_agreement`, `minimum_permutation_agreement`, `per_context_accuracy`

The prior `30/30` fixture is excluded. It used `fixture-not-an-llm` and exists only to test software-path behavior.

## Reviewer-Controlled Workflow

1. Copy `config/falcon_independent_reproduction_receipt_template_v1.json` into reviewer-controlled custody.
2. Verify the unsigned template before filling it:

```powershell
python code/ops/VERIFY_FALCON_INDEPENDENT_REPRODUCTION_RECEIPT.py --expect-template
```

3. Rehash the custody packet, frozen sources, trace chain, and exact model weights.
4. Execute or independently recompute the result without changing the protocol, prompts, model revision, thresholds, or scoring rules.
5. Fill every reviewer and reproduction field. LumenCore must not fill reviewer-controlled fields.
6. Preserve an independence/authority artifact and a detached signature artifact under reviewer control; place their SHA-256 hashes in the receipt.
7. Compute the signing payload hash before signing:

```powershell
python code/ops/VERIFY_FALCON_INDEPENDENT_REPRODUCTION_RECEIPT.py --receipt <completed-receipt.json> --print-signing-payload-sha256
```

8. Validate the completed receipt and supplied artifacts:

```powershell
python code/ops/VERIFY_FALCON_INDEPENDENT_REPRODUCTION_RECEIPT.py --receipt <completed-receipt.json> --independence-artifact <independence-artifact> --signature-artifact <signature-artifact>
```

## Promotion Boundary

Even a valid independent reproduction receipt leaves `performance_promotion_allowed = false`. Performance validation requires a separate prospectively accepted protocol with evaluator-owned held-out data, incumbent baseline, metric, threshold, and pass/fail result. Field validation and economic claims require an operator-owned pilot and accepted economic conversion.
