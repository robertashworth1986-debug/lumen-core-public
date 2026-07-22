# CODECHECK Independent Executor Handoff

Status: `READY_FOR_UNSENT_THIRD_PARTY_EXECUTION`

This handoff lets one independent reviewer execute the frozen public capsule and
return a hash-reconciled receipt without waiting for a CODECHECK identifier. The
template and verifier are administrative adjuncts carried by the current
integration packet; they do not modify the frozen computational source. It does
not bypass the formal CODECHECK workflow and does not authorize contact, packet
transfer, publication, or claim promotion.

## Frozen Target

- Source commit: `1c0eb51754beffac6f4df484914e35efc21c253f`
- Public source: https://github.com/robertashworth1986-debug/lumen-core-public/commit/1c0eb51754beffac6f4df484914e35efc21c253f
- Public preprint SHA-256: `96e744c613d2ae9ae1fcefc82f4e066edc1aac437939c8653a81407ed2157497`
- Declared outputs: `6`
- Bounded suites and assertions: `3` and `31`

## Reviewer Procedure

1. Acquire the immutable source without using an author-controlled checkout.
2. Use Ubuntu 24.04 x86-64, CPython 3.11.9, and the committed hash-locked
   `requirements-reviewer-ubuntu-py311.lock`.
3. Verify the environment before executing:

```bash
python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only
```

4. Run the declared capsule in the reviewer-controlled environment:

```bash
python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia
```

5. From the separately custody-bound integration packet, copy
   `config/codecheck_independent_execution_receipt_template_v1.json` outside the
   frozen checkout. Fill only observed facts, preserve all claim fields as
   `false`, and hash all six files declared in `codecheck.yml`.
6. Verify the completed receipt against the actual output directory:

```bash
python code/ops/VERIFY_CODECHECK_INDEPENDENT_EXECUTION_RECEIPT.py \
  --receipt /path/to/completed-independent-receipt.json \
  --artifact-root /path/to/reviewer-checkout
```

The verifier accepts a documented `PASS`, `FAIL`, or `PARTIAL` outcome only when
the reviewer identity reference, conflict disclosure, immutable source,
environment, timestamps, attestation, six artifact hashes, nested capsule facts,
and preserved negative gates reconcile.

## Interpretation

`DOCUMENTED_INDEPENDENT_REPRODUCTION_PASS` supports one bounded independent
execution claim for this exact frozen source. A non-pass remains useful evidence
and must not be discarded or rewritten. Neither result creates a CODECHECK
certificate or establishes scientific validity, field performance, realized
savings, agency approval, trading performance, patent scope, or valuation.

The verifier does not cryptographically prove the reviewer's real-world identity.
The identity reference and evidence URL must therefore remain available for human
or institutional reconciliation. Formal CODECHECK assignment and certification
remain separate external gates.

## HumanUnlock

Before sending this handoff to any reviewer, reconcile all prior outreach and
obtain fresh action-time approval for exactly one named destination. Do not send
parallel requests or treat an unanswered request as validation.
