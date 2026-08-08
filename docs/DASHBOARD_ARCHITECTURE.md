# Dashboard Architecture

Updated: June 12, 2026

## Canonical Surfaces

The public product has a plain-English home plus six primary operator surfaces:

| Surface | Route | Responsibility |
| --- | --- | --- |
| Operator Home | `/` or `/operator_home.html` | Product map, proof boundaries, commercialization, and live readiness |
| Mission Control | `/mission_control.html` | System health, evidence, approvals, and operating posture |
| Quant Lab | `/quant_lab.html` | Unified research cockpit and navigation host |
| Kraken Execution | `/kraken_execution_dashboard.html` | Paper execution, order evidence, positions, and market awareness |
| Grants | `/grants.html` | Opportunity qualification, application readiness, and submission workflow |
| Forecast | `/forecast.html` | Forecast scenarios and model comparison |
| Explainer | `/explain.html` | Per-series router rationale and evidence interpretation |

These surfaces share `assets/luma_command_fabric.css` and
`assets/luma_command_fabric.js`. The command fabric provides canonical
navigation, Ctrl+K routing, public API health, artifact freshness, and truthful
execution mode.

The canonical HTML files are explicit Git exceptions even though other
generated dashboard HTML remains ignored. Deployment runs
`code/ops/ensure_dashboard_command_fabric.py` before publishing so regenerated
pages cannot silently lose the shared layer.

## Truth Rules

- `LIVE` is shown only when the runtime gate reports
  `execution_authorized=true`.
- Paper execution is labeled `PAPER`.
- Research-only or disarmed operation without paper execution is labeled
  `SHADOW`.
- Unreachable health data is labeled `OFFLINE`.
- Paper equity and paper PnL must not be described as realized profit.
- Dashboard claims must identify whether they are measured, modeled, simulated,
  or credential-only.

## Supporting Surfaces

Investor rooms, evidence packs, staleness tools, scenario views, source
registries, and generated premium boards remain useful supporting surfaces.
They should be linked from a canonical surface rather than promoted as another
top-level product.

## Generated Pages

Generated dashboards must retain the shared command-fabric references. Builders
that overwrite a canonical page are responsible for emitting those references.
The deployment copies the dashboard directory to the public web root, so a
generated page that omits the shared layer can create visual and truth drift.

## Exact-Snapshot Release Lane

For reviewer-facing releases that require byte-level custody, use the manual
`Deploy exact public-site snapshot to VPS` workflow documented in
[`PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md`](PUBLIC_SITE_EXACT_SNAPSHOT_PROTOCOL.md).
That lane packages only its public allowlist from immutable Git blobs, records
per-file SHA-256 identities, captures bounded rollback material, and verifies
the canonical live URLs byte-for-byte. It complements the automatic site
maintenance workflow and does not authorize itself.

## Storage

- Source code and canonical dashboard assets remain in the Git repository on C:.
- E: is suitable for large simulation inputs, immutable run artifacts, model
  caches, and archived worktree recovery patches.
- F: is a small 1.6 GB media volume and is not suitable for model or simulation
  storage.
- The 83 GB `E:\INSTITUTIONAL_STACK_V2` tree is a legacy snapshot, not a Git
  repository. It contains environments, outputs, and credential-bearing `.env`
  files and must not be merged into the public repository.
