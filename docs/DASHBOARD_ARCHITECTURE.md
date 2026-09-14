# Dashboard Architecture

Updated: September 13, 2026

## September 13 connected review revision

At the founder's request, the eight legacy public redirect routes are now
source-backed, dated research review pages in the proposed source change.
`code/ops/build_research_review_surfaces.py` builds Mission Control, Quant Lab,
Kraken research, Grant Factory, Forecast, Anomalies, Explainer and Lab from
existing committed evidence. Mission Control leads the shared navigation.
This advances the existing external validation / paid-pilot review outcome.

The table below describes the original operator responsibilities. Public review
pages summarize their evidence and connect the remaining tools; they do not
reconnect the private operator runtime. Full August 8 implementations are
preserved in Git history at `987e37ea47858c9c7dcc03f179f859f78fc9e995`.

Public pages retain HOLD boundaries, dated sources and noindex metadata, and
never request private snapshots or submit orders/applications. Shared dynamic
requests remain limited to `/health` and `/api/public/status`. Historical
TXIDs, selected strategy results, later held paper tests and accounting gaps
are shown separately. Zero measured PnL and unknown PnL are distinct.

Run the builder with `--check` to detect stale generated pages. The existing
release allowlist already contains all eight routes and shared assets; this
revision adds no live-data endpoint or deployment authority. The exact snapshot
release and live byte verification remain separate from source review.

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

## Connected research browser review - September 14, 2026

The eight dated public research pages were rendered from the exact 189-file
release for UI source `027d924f12c3c953dd1fb649582d76a6a4d3ddd8` at 1440x1000
and 390x1000. All 16 renders returned HTTP 200 with one main heading, the dated
review badge, the matching active workspace and no document-width overflow.
The first mobile review found cramped strategy names. The existing generator
now keeps tables with at least four columns 640 pixels wide inside their
labeled, focusable scroll region. Print rendering removes that width floor.
A focused region moved 40 pixels after ArrowRight and retained focus; the
bottom-of-page source and evidence caveats remained readable.

The [review receipt and selected screenshots](../evidence/public_research_review/20260914/BROWSER_QA.json)
record the exact UI source, the 24 passing focused checks and local-preview
limits. Missing `/health` and `/api/public/status` responses were expected in
the static preview and displayed as GATEWAY OFFLINE. This review does not
establish deployed byte parity, backend integration, private dashboard
restoration or a full accessibility audit.

## Storage

- Source code and canonical dashboard assets remain in the Git repository on C:.
- E: is suitable for large simulation inputs, immutable run artifacts, model
  caches, and archived worktree recovery patches.
- F: is a small 1.6 GB media volume and is not suitable for model or simulation
  storage.
- The 83 GB `E:\INSTITUTIONAL_STACK_V2` tree is a legacy snapshot, not a Git
  repository. It contains environments, outputs, and credential-bearing `.env`
  files and must not be merged into the public repository.
