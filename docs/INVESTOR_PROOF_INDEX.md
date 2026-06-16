# Investor Proof Index

This index turns the public LumenCore repository into a fast diligence map for investors, grant reviewers, employers, and technical partners. The goal is simple: every major claim should point to a live surface, a machine-readable artifact, or a reproducible operating document.

## Diligence Ladder

| Review question | Primary proof surface | What to verify |
|---|---|---|
| Is there a live system? | [`README.md`](../README.md), [`dashboard/mission_control.html`](../dashboard/mission_control.html), live site links | Public status links, dashboard routes, and production-oriented operating surfaces. |
| Are executions/audits separated from marketing copy? | [`dashboard/evidence/index.html`](../dashboard/evidence/index.html), [`investor_txids/trade_log.json`](../investor_txids/trade_log.json) | Evidence pages and transaction/log artifacts are kept as standalone proof lanes. |
| Are runtime claims machine-readable? | [`full_beast_proof.json`](../full_beast_proof.json), [`live_registry_summary.json`](../live_registry_summary.json), [`stack_truth_report.json`](../stack_truth_report.json) | JSON artifacts can be inspected independently of the README narrative. |
| Is there a safety/control story? | [`config/profit_lock.json`](../config/profit_lock.json), [`config/lightning_guardrails.json`](../config/lightning_guardrails.json), [`EXECUTION_BLOCKS.md`](../EXECUTION_BLOCKS.md) | Runtime controls, guardrails, and execution blocks define the boundaries for autonomous action. |
| Is there institutional packaging? | [`INVESTOR_BRIEF.md`](../INVESTOR_BRIEF.md), [`RESUME_LUMENCORE.md`](../RESUME_LUMENCORE.md), [`docs/PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md`](PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md) | The platform is packaged for diligence, employment, funding, and public-sector review. |
| Is the grant package ready to submit? | [`docs/GRANT_SUBMISSION_CONTROL_ROOM.md`](GRANT_SUBMISSION_CONTROL_ROOM.md), [`dashboard/grants.html`](../dashboard/grants.html), grant package manifests | The authenticated operator has a final portal sequence, receipt checklist, and evidence-preservation path. |

## Evidence Rules

1. **Truth before polish.** Public claims should be backed by an artifact or live route before being amplified.
2. **Machine-readable where possible.** Prefer JSON, manifests, ledgers, and explicit dashboard routes over screenshots alone.
3. **No historical ledger rewrites.** Historical proof artifacts should be appended or superseded, not silently rewritten.
4. **Separate modeled value from executed value.** Forecasts, modeled opportunity, and closed execution telemetry must stay clearly labeled.
5. **Reviewer-first navigation.** A skeptical reviewer should be able to move from claim to proof in one or two clicks.

## One-Minute Reviewer Path

1. Start with the proof table in the root [`README.md`](../README.md).
2. Open the live evidence route: <https://lumen-core.ai/evidence/>.
3. Inspect machine-readable proof artifacts in the repository root.
4. Review [`INVESTOR_BRIEF.md`](../INVESTOR_BRIEF.md) for commercialization framing.
5. Review [`RESUME_LUMENCORE.md`](../RESUME_LUMENCORE.md) for operator capability and hiring/partner positioning.
