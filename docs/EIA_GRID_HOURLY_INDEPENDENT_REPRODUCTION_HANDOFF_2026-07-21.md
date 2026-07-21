# EIA Grid Hourly Independent Reproduction Handoff

Date: 2026-07-21 UTC

Status: `UNSIGNED_REVIEWER_HANDOFF_READY`

## Reviewer Ask

On a reviewer-controlled machine, verify the frozen packet bytes, recompute its append-only chains and settlement arithmetic, and return a reviewer-completed receipt. This is a bounded reproduction request, not a request to endorse LumenCore or promote model performance.

## Frozen Identity

- Public handoff: `evidence/external_validation/eia_grid_hourly_independent_reproduction_handoff_20260721.json`
- Public-safe runtime projection: `evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260721.json`
- Packet source commit: `680e693bc75d19f9bba1f52b9bbebbaeea8a5ff1`
- Byte-exact packet sources: `7 / 7`
- Packet directory: `EIA_GRID_HOURLY_REPRODUCTION_20260721T040212Z`
- Packet ZIP SHA-256: `366039d85014cf509a118400bdc404d748f0eaf77ac3d60c5becc54489ae3cc5`
- Packet manifest file SHA-256: `88333c09741de84caebde14da1bca4cd073bbac06ee1e48f4b28a32b93ef6432`
- Packet manifest payload SHA-256: `9625d8a3265f665c892b22852ee2319f5f20e399c434362b1d2d19d88e57de92`
- Receipt-template SHA-256: `850c3ee9a523a15148635374ba5646e517f8cef63066b0fb3c7ad4f9f8734c0b`
- Protocol SHA-256: `5398f17f57e02bdaadb1cef5b6dae20708146eaa0de534ebbe6ce36ab28952e5`
- Prediction terminal SHA-256: `d0168756f3b46d4ebe9803a042f423d65e2b3d1ed932442b92e501531d87a3ba`
- Settlement terminal SHA-256: `efe307439c3ba67b39656e698a8956b4594c496ddbb991c5a42f2ef530d6bc98`
- Operational terminal SHA-256: `f7bbef89ba688326a3bd52735dc775a4e7585c842968505e9827aba80c7e9387`
- Source-panel chain SHA-256: `ee53210f0836a3e634bd61f8c4b1b6b3918126390f3f848985e0354627020713`

Raw runtime bytes and the ZIP remain outside the public repository. The public handoff binds the retained packet by filename, size, and hashes.

Historical handoffs are append-only. The packet builder requires explicit, distinct publication paths under the repository root and refuses to overwrite an existing manifest or receipt template. A later packet must use new versioned paths; it must not rewrite this July 21 snapshot or the retained July 16 predecessor.

## Frozen Result

- Source-panel rows: `88,628`
- Predictions: `486`
- Settlements: `469`
- Protocol authorities with prospective seals: `6 / 8`
- Authorities with zero prospective seals: `SWPP`, `TVA`
- Common settled hours across all authorities: `0`
- Preliminary gate: `false`
- Confirmatory gate: `false`
- Durability gate: `false`
- Independent reproduction complete: `false`
- Performance promotion allowed: `false`

The incomplete panel is a retained negative result. The descriptive router and fixed-model error values are not eligible for a promotion, field-performance, savings, reliability, trading-edge, or universal-superiority claim.

## Offline Verification

After checking the ZIP hash and extracting the packet, run:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir .
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt REVIEWER_RECEIPT_TEMPLATE.json --expect-template
```

The operator must not fill reviewer identity, independence, execution, decision, or signature fields. A completed receipt also requires reviewer-controlled independence evidence and a detached signature artifact.

## Operator Portability Check (Not Independent)

The frozen ZIP was extracted into a fresh temporary directory for each of CPython `3.11.9`, `3.12.10`, and `3.14.6` on the same operator-controlled Windows host. Under every runtime, the offline verifier passed packet integrity, blank reviewer-receipt integrity, and blank evaluator-protocol integrity.

- Runner: `code/ops/RUN_EIA_GRID_HOURLY_OPERATOR_PORTABILITY_CHECK.py`
- Receipt: `evidence/reproducibility/eia_grid_hourly_operator_portability_receipt_20260721.json`
- Receipt SHA-256: `8027a1451c6bb742f2ceeb917e04d5b3d150907a3f205115f37699d4abff8001`
- Transfer checksum sidecar: `EIA_GRID_HOURLY_REPRODUCTION_20260721T040212Z.zip.sha256`
- Fresh extraction per runtime: `true`
- Independent reproduction complete: `false`
- External validation complete: `false`
- Performance promotion allowed: `false`

This is software-portability evidence from one operator and one machine. It is not a reviewer-controlled execution and cannot satisfy the independent-reproduction gate.

## Action Boundary

No completed external receipt exists. No validator contact, packet transfer, or follow-up is authorized by this file. Outreach remains duplicate-locked and requires action-time HumanUnlock.
