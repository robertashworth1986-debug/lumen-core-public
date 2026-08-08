# Public Live-Breadth Manifest

Manifest generated UTC: 2026-08-08T10:13:16.722571+00:00
Registry generated UTC: 2026-08-06T22:31:16.191451+00:00
Registry SHA-256: `ed21b17516aafa3561cce03c27f7c86e9615ec194188046bc6e7102e303aa82b`
Manifest SHA-256: `ff8331a1e018409a6bb9dbd500d5d25b2b1d4c85c0be12095d3f51522e019019`

## Reviewer Result

This manifest makes the source-count denominator auditable without publishing provider names, credential field names, or economic estimates.

| Gate | Count |
|---|---:|
| Registry rows | 17 |
| Configured/enabled | 17 |
| First-party measured flag | 14 |
| Explicit probe success | 14 |
| Material row depth | 0 |
| Fresh under accepted threshold | 0 |
| Rights verified for review | 0 |
| Decision relevance verified | 0 |
| Dataset snapshot bound | 0 |
| Governance complete | 0 |
| Review-ready sources | 0 |

## Data-Quality Assessment

- Intended use: technical reviewer source-provenance triage
- Grain: one row per configured source identifier
- Structurally valid: `true`
- Completeness issues: 0
- Registry freshness status: `threshold_missing`
- Freshness-assessable sources: 0
- Row-depth-assessable sources: 0
- Sources with governance gaps: 17
- Analytical risk: Configured, measured, or successful-probe counts can materially overstate usable breadth when source-specific row depth, freshness, rights, relevance, and dataset hashes are absent.

## Claim Gate

- Review-ready source-count claim allowed: `false`
- Current runtime state proven: `false`
- Independent validation claim allowed: `false`
- Performance claim allowed: `false`
- Economic value claim allowed: `false`
- Live-capital recommendation allowed: `false`

## Required Promotion Work

For each source intended to count as review-ready, supply a private governance sidecar with:

- accepted minimum row depth,
- accepted maximum probe age,
- rights status for reviewer use,
- relevance to the named decision, and
- SHA-256 of the underlying dataset snapshot.

## Reproduction

Run the builder against an authorized private registry and governance sidecar:

```text
python code/ops/build_public_live_breadth_manifest.py --registry <registry.json> --governance <governance.json> --output <manifest.json> --markdown <manifest.md>
```

Omit `--governance` only for a diagnostic manifest; review-ready counts will fail closed to zero.

## Limitations

- This is a first-party point-in-time manifest, not an independent validation.
- A source probe can succeed while the observation is too thin, stale, irrelevant, or restricted.
- The registry hash binds the input registry, not any underlying dataset unless a per-source dataset hash is supplied.
- No source count in this artifact proves alpha, savings, field performance, or production readiness.
