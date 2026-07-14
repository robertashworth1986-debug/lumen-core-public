# Master Context Continuity Protocol

## Decision

Model context compaction cannot be disabled from this repository, and buying disk or RAM does not create unlimited model memory. Continuity therefore lives in a small external retrieval layer: canonical source registration, hashes, freshness checks, explicit privacy boundaries, and task-specific retrieval.

## Canonical Flow

1. Run `python code/ops/BUILD_LUMA_MASTER_CONTEXT_BUNDLE.py --check-only`.
2. If the canonical or freshness gate fails, refresh the named source builder instead of creating another master file.
3. Build the private bundle with `python code/ops/BUILD_LUMA_MASTER_CONTEXT_BUNDLE.py`.
4. Read `E:/LumaProofVault/PRIVATE_CONTEXT/LUMA_MASTER_CONTEXT_LATEST.md` first.
5. Retrieve source bodies only for the active task.

The registry is `config/luma_master_context_registry_v1.json`. It marks the May master snapshot and July 11 handoff as superseded rather than deleting historical evidence.

## Why This Avoids Rebuilding

- Every continuity role has exactly one canonical source.
- A second canonical source for the same role fails the gate.
- Missing and stale sources are named directly.
- Registered exact duplicates are reported by content hash.
- Private note bodies are never copied into Git or the master bundle.
- Each private bundle has an immutable run copy, latest pointers, SHA-256 receipts, and a previous-manifest chain.

## Last-Ten-Compaction Audit

The 2026-07-14 private audit covered the ten most recent retrievable compaction events. It found 132 changed-path occurrences across 113 unique paths. Nineteen paths appeared twice; none appeared more than twice. The repeats were adjacent continuation/hardening work in the FAA, gateway, private-index, EIA router, MDA, and reviewer lanes. No wholesale duplicate rebuild was detected.

## iCloud And Phone Notes

The private note index inventories locally available iCloud text, Markdown, RTF, Word, and Pages files by metadata and SHA-256. Cloud-only placeholders remain unhydrated. Native Apple Notes content is not assumed to be present merely because iCloud Drive is installed; it requires a deliberate export or an authenticated connector before indexing. Code or PowerShell found in notes is never executed automatically.

## Boundaries

- The master context is an orientation and retrieval map, not scientific evidence.
- Reviewer claims still resolve to frozen protocols, data identities, metrics, negative results, and receipts.
- Duplicate private files remain review-only because copies may preserve backup or legal-custody intent.
- Money, legal filings, submissions, outreach, credentials, and live execution still require action-time HumanUnlock.
