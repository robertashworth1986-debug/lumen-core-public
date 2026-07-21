# Kuramoto Public Reproducibility Audit

Generated UTC: `2026-07-21T08:21:51.4534416Z`

## Decision

The historical Kuramoto source-conditioned replay is not reproducible from a fresh public checkout today. It remains internal exploratory evidence.

## Measured Gap

- Fresh detached checkout at audited commit: `0` eligible holdouts; the integration expectation was at least `20`.
- Current cached local manifest: `24` configured routes, `5` evidence-eligible, `19` excluded as missing/fallback.
- Git-tracked eligible source inputs: `0`.
- Public clean-checkout replay ready: `false`.
- Independent reproduction completed: `false`.
- External or field validation completed: `false`.

## Repair Applied

- Missing or fallback inputs no longer count toward the internal holdout gate.
- Missing paths are no longer hashed as if they were source-file bytes.
- Bounded source hashes disclose their exact byte scope, and public clean-checkout readiness requires full-file SHA-256 coverage.
- Public dashboard and Markdown projections remove private workstation paths.
- Holdout and chain hashes no longer depend on machine-local path strings.
- Unit tests use explicit generated fixtures and include a zero-input fail-closed case.

## Unlock Sequence

1. Freeze a redistributable public input bundle or deterministic downloader with immutable upstream identifiers.
2. Record source URLs, retrieval timestamps, licenses, and complete SHA-256 hashes.
3. Freeze candidate, baseline, metrics, exclusions, thresholds, and route selection before the rerun.
4. Reproduce from a fresh checkout and preserve environment, logs, hashes, and negative results.
5. Obtain an attributable independent reproduction receipt before changing any external-validation field.

Machine-readable receipt: `evidence/reproducibility/kuramoto_public_reproducibility_audit_20260721.json`
