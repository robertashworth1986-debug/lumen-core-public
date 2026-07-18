# LumenCore Proof Capsule Quick Start

This is the shortest public reviewer path for LumenCore. It verifies one bounded,
public-safe replay capsule without requiring private datasets, credentials, API keys,
or a live service.

## What this checks

The verifier confirms that the capsule contains a named source, a resolved data-rights
label, a baseline selected before scoring, a prelocked metric, a compatible run type,
an explicit UTC timestamp, preserved negative results, explicit claim boundaries, a
pilot decision, valid SHA-256 file records, and a matching manifest hash.

Verifier v2 also fails closed on duplicate JSON keys, non-UTF-8 capsule input,
non-canonical or escaping manifest paths, duplicate manifest targets, malformed hashes,
unknown public data rights, invalid timestamps, evidence/run-type conflicts, oversized
inputs, unsafe promotional claims, and files that change while they are being hashed.

It does **not** reproduce the private replay run, independently validate the reported
metrics, establish field performance, confirm consortium participation, or authorize a
pilot. Those require a qualified outside reviewer and an agreed dataset, comparator,
metric, threshold, and test window.

## Run the verifier

From a clean repository checkout with Python 3.10 or newer:

```bash
python code/proof_capsule_verifier.py \
  examples/proof_capsule/dice_eia_public_capsule.json \
  --root .
```

Key fields in the expected result:

```json
{
  "valid": true,
  "verifier_version": "2.0",
  "capsule_id": "DICE-EIA-PUBLIC-SUMMARY-20260621",
  "evidence_type": "replay",
  "run_type": "replay",
  "verified_hash_records": 1,
  "pilot_decision": "external_review"
}
```

The verifier also prints the normalized UTC run timestamp, verified byte count, and
deterministic manifest hash. The manifest hash may differ only when a referenced path
or its declared SHA-256 value changes.

For an unusually large public artifact, the reviewer may raise the explicit size limit:

```bash
python code/proof_capsule_verifier.py \
  examples/proof_capsule/dice_eia_public_capsule.json \
  --root . \
  --max-artifact-bytes 1073741824
```

The default limit is 512 MiB per referenced artifact and 1 MiB for the capsule JSON.
These are resource-safety limits, not evidence-quality thresholds.

## Run the focused tests

```bash
python -m unittest discover -s tests -p "test_proof_capsule_verifier.py" -v
```

The focused suite confirms the valid path plus fail-closed behavior for hash tampering,
an unlocked metric, missing negative results, path traversal, absolute and non-canonical
paths, duplicate records, unknown rights, timestamp and run-type conflicts, duplicate
JSON keys, malformed UTF-8, resource-limit violations, and unsafe public claims.

## Five-minute reviewer sequence

1. Read `examples/proof_capsule/dice_eia_public_capsule.json`.
2. Inspect `examples/proof_capsule/dice_eia_public_summary.txt`.
3. Run the verifier and focused tests.
4. Review `docs/PROOF_CAPSULE_SCHEMA.md` and the claim boundary.
5. Decide whether to reject, request more information, rerun under agreed conditions,
   or scope an external validation.

## External-validation gate

A result becomes externally validated only after a qualified buyer, lab, consortium
working group, mentor, or technical reviewer approves the data rights, baseline,
metric, threshold, test window, reporting format, and allowed claim.
