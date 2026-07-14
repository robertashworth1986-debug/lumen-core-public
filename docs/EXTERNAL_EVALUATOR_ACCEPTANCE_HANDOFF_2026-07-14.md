# External Evaluator Acceptance Handoff

This package lets an independent evaluator accept or decline responsibility for the frozen EIA prospective-router experiment without the LumenCore operator filling the evaluator's identity, authority, conflict, or signature fields.

## Files

- Blank evaluator-owned receipt: `config/external_evaluator_acceptance_template_v1.json`
- Fail-closed validator: `code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py`
- Frozen validation docket: `evidence/external_validation/eia_router_validation_authority_docket_20260714.json`

## Evaluator Procedure

1. Copy the blank receipt outside the public repository before adding identity or contact information.
2. Verify the docket and protocol hashes independently.
3. Fill every evaluator, acceptance, and attestation field without operator substitution.
4. Hash an authority artifact that supports the stated review authority and place that SHA-256 value in `authority_evidence_sha256`.
5. Set `method`, then calculate `signed_payload_sha256` over canonical JSON with both signature-hash fields set to `null`.
6. Sign or otherwise preserve that payload in an evaluator-controlled artifact and enter its SHA-256 as `detached_signature_artifact_sha256`.
7. Run the validator with the completed receipt and both supplied artifacts.

```powershell
python code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py `
  --receipt C:\path\to\completed_evaluator_receipt.json `
  --authority-artifact C:\path\to\authority_evidence.pdf `
  --signature-artifact C:\path\to\signed_acceptance.pdf
```

The repository's unsigned template is checked with:

```powershell
python code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py --expect-template
```

## Decision Boundary

A passing completed-receipt validation proves structural completeness, frozen hash agreement, attestation state, and byte identity of the supplied authority and signature artifacts. It does not authenticate the person, establish legal authority or independence, interpret the signature, complete outcome replication, or promote the repository to Level 5. Those decisions remain external and require the complete prospective result record.

Completed identity and contact fields stay evaluator-controlled or in the private proof vault unless the evaluator explicitly authorizes publication. The public repository should receive only a redacted receipt or a hash receipt by default.
