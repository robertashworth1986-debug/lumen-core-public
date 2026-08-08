# LumenCore Proof Capsule Quick Start

This is the shortest public reviewer path for LumenCore. It verifies one bounded,
public-safe replay capsule without requiring private datasets, credentials, API keys,
or a live service.

## What this checks

The verifier confirms that the capsule contains a named source, a resolved data-rights
label, a baseline selected before scoring, a prelocked metric, a compatible run type,
an explicit UTC timestamp, preserved negative results, explicit claim boundaries, a
pilot decision, valid SHA-256 file records, and a matching manifest hash.

Verifier v3 also fails closed on duplicate or unknown JSON fields, non-UTF-8 and
non-standard JSON input, non-canonical or escaping manifest paths, symlink and hardlink
aliases, malformed hashes, unknown public data rights, invalid timestamps,
evidence/run-type conflicts, unbound external-validation labels, oversized inputs,
normalized unsafe promotional claims, and files that change while they are being read.

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
  "receipt_schema": "proof-capsule-receipt-v3",
  "verifier_version": "3.0",
  "verification_scope": "capsule-schema-and-custody",
  "capsule_schema_version": "3.0",
  "capsule_id": "DICE-EIA-PUBLIC-SUMMARY-20260621",
  "capsule_file_custody_complete": true,
  "capsule_file_sha256": "64-character SHA-256 digest",
  "declared_evidence_type": "replay",
  "run_type": "replay",
  "verified_hash_records": 1,
  "declared_external_validation_status": "not_established",
  "external_report_manifest_bound": false,
  "external_validator_identity_evaluated": false,
  "external_validator_independence_evaluated": false,
  "external_validation_conclusion_evaluated": false,
  "pilot_decision": "external_review",
  "release_authorization_evaluated": false,
  "human_unlock_required": true
}
```

The verifier also prints the normalized UTC run timestamp, exact and canonical capsule
digests, verified byte count, and deterministic manifest hash. The manifest hash changes
when a referenced path, declared SHA-256 value, input/output role, or manifest format
changes.

For an unusually large public artifact, the reviewer may raise the explicit size limit:

```bash
python code/proof_capsule_verifier.py \
  examples/proof_capsule/dice_eia_public_capsule.json \
  --root . \
  --max-artifact-bytes 1073741824 \
  --max-total-artifact-bytes 2147483648
```

The defaults are 512 MiB per referenced artifact, 1 GiB across the manifest, and 1 MiB
for the capsule JSON. These are resource-safety limits, not evidence-quality thresholds.

## Run the focused tests

```bash
python -m unittest discover -s tests -p "test_proof_capsule_verifier.py" -v
```

The focused suite confirms the valid path plus fail-closed behavior for exact-schema
violations, hash and role tampering, an unlocked metric, missing negative results, path
traversal, symlink/hardlink aliases, duplicate records, unknown rights, timestamp and
run-type conflicts, malformed JSON/UTF-8, external-validation provenance gaps,
resource-limit violations, hidden Unicode controls, and normalized unsafe public claims.

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

For `evidence_type: externally_validated`, verifier v3 additionally requires the named
validator, organization, scope, completion timestamp, and report digest. The report must
be one of the verified manifest records. The receipt labels the evidence type and status
as declared metadata and reports only that the external report is manifest-bound. It does
not authenticate the validator, establish independence, evaluate the report's conclusion,
or authorize public release; those remain human review gates.
