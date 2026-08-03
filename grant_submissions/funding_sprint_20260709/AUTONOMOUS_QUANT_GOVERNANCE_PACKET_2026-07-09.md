# Autonomous Quant Governance Packet - 2026-07-09

Purpose: prove that LumenCore autonomy is currently governed as replay, paper-evaluation, opportunity-monitoring, and proof-factory work.

This packet does not authorize order placement, capital movement, runtime escalation, agency action, certification, public performance expansion, or external commitments.

## Status

- Status: `AUTONOMOUS_QUANT_GOVERNANCE_READY_HUMAN_RUNTIME_REQUIRED`
- Reviewer packaging gate clear: `true`
- Submission argument gate clear: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- All final actions blocked without human: `true`
- Global runtime paper: `true`
- Global live orders disabled: `true`
- Execution status paper: `true`
- Account runtimes: `2`
- Account live orders disabled: `true`
- Registered agents: `5`
- All agents require approval: `true`
- Auto-fire enabled count: `0`
- Runtime marker reconciliation count: `2`
- Capital movement allowed: `false`
- Order placement allowed: `false`
- External system action without human: `false`
- Agency action without human: `false`
- Packet SHA-256: `4216f91d6d6043f38a05675788ef5fe1ac45880a7f5e2d670f6574134c9c47aa`

## Runtime Snapshot

- Global runtime path: `config/runtime_control.json`
- Global runtime mode: `paper`
- Global paper enabled: `true`
- Global allow live orders: `false`
- Execution status path: `out/execution_status.json`
- Execution mode: `paper`
- Live arm: `OFF`

## Account Runtime Controls

- `config/accounts/KRAKEN_PRIMARY/runtime_control.json` | account=`KRAKEN_PRIMARY` | mode=`paper` | allow_live_orders=`false` | paper_enabled=`true` | x1000_auto_enabled=`false` | x1000_auto_apply=`false`
- `config/accounts/ALPACA_PRIMARY/runtime_control.json` | account=`ALPACA_PRIMARY` | mode=`paper` | allow_live_orders=`false` | paper_enabled=`true` | x1000_auto_enabled=`true` | x1000_auto_apply=`false`

## Runtime Markers

- `control/LIVE.flag` | present=`true` | value=`OFF` | requires_reconciliation=`false`
- `config/live_arm.confirm` | present=`true` | value=`ARM_LIVE_SUPER_SNIPER` | requires_reconciliation=`true`
- `config/multi_live_arm.confirm` | present=`true` | value=`ARM_MULTI_ACCOUNT_LIVE` | requires_reconciliation=`true`

## Agent Approval Registry

- `email_dispatch` | channel=`email` | auto_fire=`false` | requires_approval=`true` | queue=`opportunities/email/email_opportunities_latest.json`
- `grant_submission` | channel=`grants_gov` | auto_fire=`false` | requires_approval=`true` | queue=`funding/funding_approval_queue.json`
- `job_application` | channel=`linkedin_usajobs` | auto_fire=`false` | requires_approval=`true` | queue=`jobs/_queue/index.json`
- `linkedin_post` | channel=`linkedin` | auto_fire=`false` | requires_approval=`true` | queue=`opportunities/linkedin/lumalinkedin_v1_latest.json`
- `trade_ticket` | channel=`kraken` | auto_fire=`false` | requires_approval=`true` | queue=`execution_approval_queue.json`

## Allowed Autonomous Modes

### replay_lab

- Allowed: Approved public, synthetic, or local datasets may be used for baseline-vs-candidate comparison.
- Gate: No external system action, no order placement, and no capital movement.

### paper_evaluation

- Allowed: Paper simulation may produce research receipts, negative-result records, and benchmark dashboards.
- Gate: Paper output cannot be represented as external validation or deployable capital performance.

### opportunity_monitor

- Allowed: Official opportunities may be watched, ranked, and drafted into human-review packets.
- Gate: Human approval remains required before send, upload, filing, certification, pricing, or term action.

### proof_factory

- Allowed: Artifacts may be hashed, mirrored, classified, and scanned into the reviewer data room.
- Gate: Public claims remain bounded by reviewer gate and authority matrix.

## Human Gate

- capital_movement_allowed_without_human: `False`
- order_placement_allowed_without_human: `False`
- runtime_escalation_allowed_without_human: `False`
- agency_action_allowed_without_human: `False`
- public_performance_claim_allowed_without_human: `False`
- rule: `Autonomous quant work may build replay and paper-evaluation evidence only; human approval is required before runtime escalation, external action, or any capital-impacting step.`

## Evidence Sources

- `grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md` | present=`true` | bytes=`5263` | sha256=`050f64e5c86a866a3fd125e00911e4f3caeb387625f7c4386c355727ab3ac30a`
- `grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md` | present=`true` | bytes=`24099` | sha256=`cbd2ebec0acc44b92b5b16b96973675c19f5435c6ad521f8f15fb2b6a888b390`
- `grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md` | present=`true` | bytes=`23598` | sha256=`10f5206c8b65e329041c28caefec7f51c0744fcef70c0761b711470d62f13021`
- `grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md` | present=`true` | bytes=`17487` | sha256=`db8e56ed557b78bdd69fa27fddbc516eb4e00b2e4448fe24c030c393c52b9e1a`
- `config/runtime_control.json` | present=`true` | bytes=`14975` | sha256=`ad8cb516d3145d43e39300f35ae03304efc58070bd643a2bf8ee5b177909c448`
- `out/execution_status.json` | present=`true` | bytes=`211` | sha256=`4c206c4c8120a23c496b6f0aa1a46cd8df723b947e490ff1bfa88ed9c9c0a64a`
- `code/autonomous_agent_manifest.py` | present=`true` | bytes=`24801` | sha256=`f74c0a5d09541ce5fe7e8a7f055220b99478f61d09a66715a651471e0ae3438f`
- `config/accounts/KRAKEN_PRIMARY/runtime_control.json` | present=`true` | bytes=`489` | sha256=`341775322d161c6f7fe96dce4ecfe264c6694d60a1df1c19c1f54b32fedf0e39`
- `config/accounts/ALPACA_PRIMARY/runtime_control.json` | present=`true` | bytes=`488` | sha256=`06381e2a555aa912c1d8c66f986a7a2ade78107cbfcba57cd8333d164ec7d708`
- `control/LIVE.flag` | present=`true` | bytes=`5` | sha256=`3c1e6ffb9a2aa25c21bc68f118f83d2e8507a26578b5923d6430cc46a68b0217`
- `config/live_arm.confirm` | present=`true` | bytes=`23` | sha256=`a7f1a08f45fbf14175b8f456c8ee62a306b211717c8fb2756c5452417bd5ab04`
- `config/multi_live_arm.confirm` | present=`true` | bytes=`24` | sha256=`d97e05feffecfe9d5059954f0da44897b4155fdcc26986bcbd99b44673bb5a39`
