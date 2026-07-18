# Dashboard Architecture

Updated: July 18, 2026

## Canonical Public Surfaces

The public product now separates the indexable company and evidence experience from
operator-only control surfaces.

| Surface | Route | Responsibility | Search policy |
| --- | --- | --- | --- |
| Public Home | `/` or `/operator_home.html` | Plain-English product, commercial offer, proof boundaries, sectors, and contact path | Index |
| Proof-to-Pilot | `/proof_to_pilot.html` | Public capsule, verifier, source summary, claim boundary, and external-validation gate | Index |
| Bounded Validation Sprint | `/review_sprint.html` | Commercial fit criteria, phases, deliverables, stop conditions, and inquiry path | Index |
| Mission Control | `/mission_control.html` | System health, evidence, approvals, and operating posture | Noindex |
| Quant Lab | `/quant_lab.html` | Unified research cockpit and navigation host | Noindex |
| Kraken Execution | `/kraken_execution_dashboard.html` | Paper execution, order evidence, positions, and market awareness | Noindex |
| Grants | `/grants.html` | Opportunity qualification, application readiness, and submission workflow | Noindex |
| Forecast | `/forecast.html` | Forecast scenarios and model comparison | Noindex |
| Explainer | `/explain.html` | Per-series router rationale and evidence interpretation | Noindex |

The public pages share `assets/public_site.css`, `assets/public_site.js`,
`assets/luma_command_fabric.css`, and `assets/luma_command_fabric.js`.
The command fabric provides canonical navigation, Ctrl+K routing, public API
health, artifact freshness, and truthful execution mode. Public pages remain
useful when the runtime gateway is unavailable.

`robots.txt` and `sitemap.xml` expose only the public company, proof, and
commercial-review paths. `code/ops/ensure_dashboard_command_fabric.py` injects
`noindex,nofollow,noarchive` into canonical operator-only pages when they do not
already declare a robots policy.

The canonical HTML files are explicit Git exceptions even though other
generated dashboard HTML remains ignored. Deployment runs
`code/ops/ensure_dashboard_command_fabric.py` before publishing so regenerated
pages cannot silently lose the shared layer or indexing boundary.

## Truth Rules

- `LIVE` is shown only when the runtime gate reports
  `execution_authorized=true`.
- Paper execution is labeled `PAPER`.
- Research-only or disarmed operation without paper execution is labeled
  `SHADOW`.
- Unreachable health data is labeled `OFFLINE`.
- Paper equity and paper PnL must not be described as realized profit.
- Dashboard claims must identify whether they are measured, modeled, simulated,
  credential-only, independently validated, or still open.
- Public artifact integrity is never presented as proof of scientific truth,
  safety, patentability, commercial performance, or release authority.
- External validation is claimed only after an independent or buyer-controlled
  reviewer performs and documents the agreed test.
- Commercial review timing, fees, handling requirements, deliverables, and
  acceptance criteria are controlled by a written scope.

## Supporting Surfaces

Investor rooms, evidence packs, staleness tools, scenario views, source
registries, and generated premium boards remain useful supporting surfaces.
They should be linked from a canonical surface rather than promoted as another
top-level product.

## Generated Pages

Generated dashboards must retain the shared command-fabric references.
Builders that overwrite a canonical page are responsible for emitting those
references. The deployment copies the dashboard directory to the public web
root, so a generated page that omits the shared layer can create visual, truth,
or indexing drift.

## Storage

- Source code and canonical dashboard assets remain in the Git repository on C:.
- E: is suitable for large simulation inputs, immutable run artifacts, model
  caches, and archived worktree recovery patches.
- F: is a small 1.6 GB media volume and is not suitable for model or simulation
  storage.
- The 83 GB `E:\INSTITUTIONAL_STACK_V2` tree is a legacy snapshot, not a Git
  repository. It contains environments, outputs, and credential-bearing `.env`
  files and must not be merged into the public repository.
