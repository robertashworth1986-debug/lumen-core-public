# ProofLock Fixed-Scope Public Release Receipt

Status: `PUBLIC_RELEASE_VERIFIED_BRANCH_NOT_MERGED_TO_MAIN`

## Published

- Reviewer page: `https://lumen-core.ai/proof_to_pilot.html`
- Public offer feed: `https://lumen-core.ai/data/evidence_protocol_review_fixed_scope_offer.json`
- Release branch: `codex/public-reviewer-release-20260729`
- Release commit: `650094a7862deff922b8c2bf1fe582342d938b9d`
- Plan SHA-256: `8d76823580b87155589b0ca324e6fb2d0a55ec8580f8b55dcf823929b8b58c96`
- Successful workflow: `https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/30517828717`

Both public artifacts returned HTTP 200 with the expected MIME type and exact
sealed SHA-256. The one-use HumanUnlock was deleted after deployment.

## Preserved Failure

The first workflow run stopped before SSH because Windows and GitHub checked out
the offer JSON with different line endings. No VPS mutation occurred. The
replacement release made the public byte policy explicit and passed the full
immutable-hash verification.

Failed preflight:
`https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/30517706575`

## Boundary

This receipt proves publication and exact public-byte verification for the
bounded reviewer page and draft service feed. It does not prove customer
acceptance, revenue, contract award, external validation, model superiority,
field performance, savings, or main-branch inclusion.
