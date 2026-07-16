# EIA Grid Hourly Independent Reproduction Handoff

Date: 2026-07-16

Status: `UNSIGNED_REVIEWER_HANDOFF_READY`

## Reviewer Ask

Independently rehash and recompute the frozen EIA-930 hourly evidence snapshot on a reviewer-controlled machine. Confirm whether the supplied bytes reproduce:

- the source-cache row chain;
- the prediction, settlement, and operational append-only chains;
- every settlement error and router-regret calculation;
- the frozen protocol and route-map identity;
- authority-level prediction and settlement coverage; and
- the retained zero-prospective-seal result for `SWPP` and `TVA`.

This is a request to reproduce a bounded evidence snapshot, including its unfavorable feasibility result. It is not a request to endorse model quality or LumenCore.

## Frozen Packet Identity

- Public handoff manifest: `evidence/external_validation/eia_grid_hourly_independent_reproduction_handoff_20260716.json`
- Packet source commit: `1c7380eec408222ebfd376e92f657167bad6b8fc`
- Packet ZIP SHA-256: `3eb7a16f739df7aa1eebf637d7d0ba52c7c02c6b695200cd6d6dc8f24ec19f81`
- Packet manifest file SHA-256: `4d7f332df6a80409ea0d256113d4bfdf686139fbef009f5eb4d116dcb1d51924`
- Packet manifest payload SHA-256: `25af10db41899e22261127fff97d8a8a7a1d716d25579a779e8bd6233cbd44cf`
- Protocol SHA-256: `5398f17f57e02bdaadb1cef5b6dae20708146eaa0de534ebbe6ce36ab28952e5`
- Protocol commit: `8fd49772dbeec3664b9c83c1d46f5c8583772946`
- Prediction terminal SHA-256: `daa839587b2dcd53b245ebef587f40f89518de457505c0e20f8e1a4480d7bbad`
- Settlement terminal SHA-256: `2e2d1708ee878e00a53e2330fc6be2917226ef62f5a12372439306babc917dee`
- Operational terminal SHA-256: `6be30e2e30e2f7015710dee3b1d27465e1d52dd8300db8ee6f305d18bb981cad`
- Environment-lock SHA-256: `d69ae015f77309ac652fa8b6fa2efdff31631e18ede437c458748b5d7da8577f`
- Scientific-limitations SHA-256: `4d725457f3b5b8c2aede2f8cc71bb166904f55308caca280cdab1e9617cf012c`

The raw runtime packet is retained outside the public repository. The public handoff manifest binds its ZIP and packet-manifest hashes.

## Frozen Result

- Source rows: `86,716`
- Sealed predictions: `95`
- Settlements: `84`
- Protocol authorities: `8`
- Authorities with at least one valid prospective seal: `6`
- Authorities with zero valid prospective seals: `SWPP`, `TVA`
- Common settled hours across all eight authorities: `0`
- Preliminary sample gate: `false`
- Confirmatory sample gate: `false`
- Durability sample gate: `false`
- Independent reproduction complete: `false`
- Performance promotion allowed: `false`

The frozen protocol is not rewritten after observing outcomes. The missing-authority coverage is preserved as evidence rather than removed from the denominator.

## Reviewer-Controlled Workflow

1. Receive the packet through a reviewer-controlled channel and verify the ZIP SHA-256 against the public handoff manifest.
2. Extract the packet without renaming or editing files.
3. Run the standard-library-only verifier:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir .
```

4. Validate the unsigned receipt template:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt REVIEWER_RECEIPT_TEMPLATE.json --expect-template
```

5. Validate and complete the external-evaluator protocol before scoring:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --evaluator-protocol config/eia_grid_hourly_external_evaluator_protocol_template_v1.json --expect-evaluator-template
```

6. The completed protocol must lock evaluator-owned held-out data, an incumbent baseline, primary metric, effect threshold, authority inclusion, missing-data handling, at least `720` common hours per authority, at least `10,000` paired block-bootstrap replications, authority-day clustering, and Holm correction before scoring.
7. Recompute the packet on a reviewer-controlled machine. LumenCore must not fill reviewer identity, independence, execution, decision, or signature fields.
8. Preserve reviewer-independence evidence and a detached signature artifact under reviewer control.
9. Compute the receipt signing payload and validate the completed receipt:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt completed_receipt.json --print-signing-payload-sha256
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt completed_receipt.json --independence-artifact reviewer_independence.txt --signature-artifact detached_signature.bin
```

## Promotion Boundary

A valid completed receipt can independently reproduce the frozen packet's integrity, settlement arithmetic, and authority coverage. It does not refit the models, convert the incomplete authority panel into a performance pass, establish source-publication timing beyond the sealed records, authenticate reviewer identity or signature semantics by itself, establish field validation, or support agency approval, safety, savings, patent, production, trading, or universal-superiority claims.

The next valid performance protocol must be prospectively accepted by an outside evaluator, with evaluator-owned data, incumbent baseline, metric, threshold, and pass/fail rule fixed before scoring.

## Proof-To-Value Boundary

The commercial sequence is: tag the measurement, lock the protocol, run the test, issue the receipt, obtain independent validation, translate only the accepted effect into the operator's economic unit, and then negotiate a pilot, license, or contract.

The receipt does not create economic value by itself. Economic conversion remains disabled until the technical gate passes and the operator accepts the conversion inputs and unit values.
