# LumenCore Proof Capsule Quick Start

This is the shortest public reviewer path for LumenCore. It verifies one bounded,
public-safe replay capsule without requiring private datasets, credentials, API keys,
or a live service.

## What this checks

The verifier confirms that the capsule contains a named source, a baseline selected
before scoring, a prelocked metric, a labeled run type, preserved negative results,
explicit claim boundaries, a pilot decision, valid SHA-256 file records, and a matching
manifest hash.

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

Expected result:

```json
{
  "valid": true,
  "capsule_id": "DICE-EIA-PUBLIC-SUMMARY-20260621",
  "evidence_type": "replay",
  "verified_hash_records": 1,
  "pilot_decision": "external_review"
}
```

The printed manifest hash is deterministic and may differ only when a referenced
artifact or its declared hash changes.

## Run the focused tests

```bash
python -m unittest discover -s tests -p "test_proof_capsule_verifier.py" -v
```

The tests confirm the valid path and fail-closed behavior for hash tampering, an
unlocked metric, missing negative results, and a path-traversal attempt.

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
