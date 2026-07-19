# Cloud Redundancy Plan

As of UTC: `2026-07-18T18:00:00Z`
Manifest state: `LOCAL_MANIFEST_READY_REMOTE_REDUNDANCY_NOT_PROVEN`
Manifest SHA-256: `8afd1c33356de4c4523d249db7b4d3f80f5b0aad5b6d0cab49cfbda661cd505c`

## Decision

The allowlisted receipt bytes passed local hashing and safety checks. Remote redundancy remains unproven; this lane performed no copy, sync, upload, readback, network, registry, credential, publication, commit, or push action.

## Storage Failure Domains

| Surface | Role | State | Redundancy credit |
|---|---|---|---|
| `C:` | Repository source volume | `LOCAL_PHYSICAL_DISK_0` | none by itself |
| `E:` | Local vault volume | same physical disk as `C:` | none; a disk failure can affect both volumes |
| iCloud Drive local folder | Local sync candidate only | remote completion `NOT_PROVEN` | none until provider-side presence and hash readback are verified |
| Google Drive | Off-device target | separate connector upload/readback `NOT_PERFORMED` | none until upload receipt and remote hash readback exist |

## Exact Allowlist

| ID | Source | Bytes | SHA-256 | State |
|---|---|---:|---|---|
| `falcon_model_weights_identity_receipt` | `evidence/falcon/qwen2_5_1_5b_instruct_weights_receipt_20260715.json` | 862 | `42e7e7324900c90ce72755f2af229f90f468710971ce697d0fd54dfc032faa2f` | `ELIGIBLE_LOCAL_SOURCE` |
| `flowform_concept_lineage_receipt` | `build_week/prooflock_console/sample_receipt.json` | 4221 | `dee8c4779a74e4e34f5b5ee8ae127c49eb88d3cbc6693d1d419f103b39636c63` | `ELIGIBLE_LOCAL_SOURCE` |

## Connector Boundary

- iCloud: the named local folder is a sync candidate. Local presence does not prove remote completion.
- Google Drive: it is the intended off-device target. Upload and readback are a separate connector action.
- Completion evidence: provider-side presence and a SHA-256 readback matching each source are required.
- This builder imports no connector client and does not enumerate cloud folders or local drives.

## Claim Boundary

This local manifest proves only the byte identity and policy eligibility of the exact allowlisted source receipts. C: and E: share one physical disk and do not form independent redundancy. The iCloud folder is only a local sync candidate whose remote completion is not proven. Google Drive is an off-device target, but upload and hash readback require a separate connector action that this lane does not perform.
