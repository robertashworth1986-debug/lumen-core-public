# CODECHECK EIA Immutable Release Plan

Prepared: 2026-07-21 (America/Chicago)

Status: `UNPUBLISHED_RELEASE_CANDIDATE`

No release, DOI, CODECHECK request, independent execution, certificate, or external validation is claimed by this plan.

## Purpose

Freeze one bounded, public, reviewer-executable snapshot without turning first-party evidence into an external claim. The proposed release is limited to the preprint and the three-suite reproducibility capsule declared in `codecheck.yml`.

The source bundle also includes the digest-pinned container recipe, fail-closed reviewer-runtime verifier, and first-party receipts that reconcile Ubuntu 24.04, x86-64, CPython 3.11.9, glibc 2.39, deterministic environment variables, dependency-lock hash, release manifest, source bundle, and isolation controls. These checks reduce environment ambiguity but do not satisfy any external gate.

## Deterministic Candidate

Build locally with:

```bash
python code/ops/BUILD_CODECHECK_EIA_RELEASE_CANDIDATE.py
```

The builder emits five files under `out/release_candidates/codecheck-eia-v0.1.0/`:

- `LumenCore_CODECHECK_EIA_Source_Bundle_v0.1.0.zip`
- `LumenCore_CODECHECK_EIA_Preprint_v0.1.0.pdf`
- `LumenCore_CODECHECK_EIA_RELEASE_NOTES_v0.1.0.md`
- `LumenCore_CODECHECK_EIA_RELEASE_RECEIPT_v0.1.0.json`
- `SHA256SUMS`

The ZIP uses fixed entry timestamps, sorted paths, fixed permissions, portable LF normalization for UTF-8 text, and byte hashes for every packaged input. A repeat build from the same commit must be byte-identical across Windows and Linux checkouts.

## Current Gates

| Gate | Current truth | Owner |
|---|---:|---|
| Author review | `false` | Robert Ashworth |
| GitHub immutable releases enabled | `unverified` | Robert Ashworth |
| GitHub draft release created | `false` | Robert Ashworth |
| Release assets attached and reconciled | `false` | Robert Ashworth and Luma3 |
| GitHub release published | `false` | Robert Ashworth |
| Zenodo repository enabled | `unverified` | Robert Ashworth |
| Zenodo DOI issued | `false` | Zenodo |
| Stable public preprint identifier | `not assigned` | GitHub or Zenodo |
| CODECHECK request opened | `false` | Robert Ashworth and CODECHECK |
| Independent execution complete | `false` | Independent codechecker |
| Certificate issued | `false` | CODECHECK |
| External validation complete | `false` | External authority |

## Official Route

GitHub documents that immutable releases lock the associated tag and attached assets after publication and create a release attestation. GitHub recommends creating the release as a draft, attaching all assets, and publishing only after the draft is complete.

Zenodo documents that an enabled GitHub repository is automatically ingested when a new release is published. Zenodo then exposes the archived record and its DOI after processing. This repository uses `CITATION.cff` as the single metadata source; adding `.zenodo.json` would cause Zenodo to ignore the CFF metadata.

- GitHub immutable releases: https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- GitHub release verification: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity
- Zenodo repository connection: https://help.zenodo.org/docs/github/enable-repository/
- Zenodo GitHub release archiving: https://help.zenodo.org/docs/github/archive-software/github-upload/
- Zenodo `CITATION.cff` guidance: https://help.zenodo.org/docs/github/describe-software/citation-file/
- CODECHECK author workflow: https://codecheck.org.uk/guide/community-workflow-author

## Shortest Safe Completion Sequence

1. Robert reviews the preprint, release notes, exact bundle manifest, claim boundary, and proposed tag.
2. Reconcile PR overlap and merge the exact reviewed source without adding unrelated implementations.
3. Resolve or explicitly document the GitHub Actions account lock, then rerun current-head checks if service is available.
4. Confirm GitHub immutable releases are enabled and Zenodo is connected to the correct public repository.
5. Obtain fresh action-time HumanUnlock before creating any draft release or changing an external integration.
6. Create one GitHub draft release targeting the exact reviewed commit and proposed tag.
7. Attach the five generated assets and reconcile each uploaded asset against `SHA256SUMS`.
8. Obtain fresh action-time HumanUnlock before publishing the immutable release.
9. Verify the immutable release and attached assets, wait for Zenodo processing, and record the release URL and version-specific DOI.
10. Update the readiness receipt with those observed identifiers. Do not infer them from a pending integration.
11. Reconcile Gmail, GitHub, and local outreach controls for duplicate CODECHECK requests.
12. Obtain fresh action-time HumanUnlock before opening exactly one production CODECHECK request.

## Claim Boundary

A deterministic release candidate proves only that a bounded set of public files can be packaged reproducibly with reconciled hashes. It is not a published release, DOI, CODECHECK request, independent execution, certificate, scientific validation, field validation, performance endorsement, or company valuation.

An immutable release and later independent execution may reduce diligence risk around provenance and executability. Neither establishes scientific validity, commercial demand, realized savings, model superiority, trading alpha, or valuation.
