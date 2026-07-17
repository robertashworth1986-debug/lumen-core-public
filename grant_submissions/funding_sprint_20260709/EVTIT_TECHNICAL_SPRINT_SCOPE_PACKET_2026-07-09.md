# EVTit Technical Sprint Scope Packet - 2026-07-09

Purpose: give Terry and the EVTit technical team a concrete 30-day sprint shape without accepting terms, sharing private material, or claiming a partnership.

This packet is preparation-only. It does not send email, schedule a meeting, accept equity or services terms, grant access, share files, or authorize final external action.

## Status

- Status: `EVTIT_TECHNICAL_SPRINT_SCOPE_INTERNAL_ONLY_MONITOR_NO_SEND`
- Lane ID: `evtit_blackdog_inkind`
- Lane status: `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY`
- Legacy intake status: `RESET_NOTE_SENT_TECH_REVIEW_PENDING`
- State source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:terry_vynetic_followup`
- Fit score: `92`
- Workstreams: `6`
- Milestones: `5`
- Reviewer gate clear: `true`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- Registry enabled sources: `29`
- Registry measured sources: `25`
- Current probe measured sources: `23`
- Measured-source reconciliation required: `true`
- Human terms required: `true`
- Monitor only: `true`
- Do not duplicate send: `true`
- External send without human: `false`
- Schedule without human: `false`
- Share private files without human: `false`
- Equity or services terms without human: `false`
- Partnership claimed: `false`
- Investment claimed: `false`
- Services award claimed: `false`
- Customer outcome value claimed: `false`
- Production deployment claimed: `false`
- Packet SHA-256: `c4bb5cad52a5eed0e0cf4b30ef6b9366f55086cd194d46a0217acd4bf35877b3`

## Positioning

- One sentence: A 30-day technical sprint to convert LumenCore's proof-to-pilot stack into a cleaner reviewer portal, repeatable evidence receipts, measured-source visibility, and pilot-ready intake gates.
- Decision question: What internal sprint scope should remain ready if Terry sends a specific technical ask?
- Best next meeting: None scheduled; consider a technical fit call only after a specific inbound request.

## Claim Boundary

The mailbox record proves only that two near-duplicate follow-ups were sent and no inbound reply was observed at reconciliation time. It does not prove interest, rejection, selection, funding, or validation.

## Workstreams

### Proof portal front door

- Workstream ID: `proof_portal_front_door`
- Problem: Reviewers need one clean path from thesis to artifacts without reading the whole repository.
- Deliverable: A reviewer-facing portal surface with proof-card navigation, source register, and data-room links.
- Acceptance check: A reviewer can identify thesis, source register, claim boundaries, and next validation gate in under five minutes.
- Evidence output: public-safe screenshot, route map, hash-linked front-door artifact list

### Replay runner and manifest

- Workstream ID: `replay_runner_manifest`
- Problem: Evidence needs a repeatable path from source snapshot to baseline comparison to reviewer receipt.
- Deliverable: A replay runner shell that records source, baseline, candidate, metric, run config, and SHA-256 receipt.
- Acceptance check: A dry-run receipt can be generated without external send, credentials, or capital movement.
- Evidence output: run manifest JSON, markdown receipt, failure/negative-result slot

### Measured-source register UI

- Workstream ID: `measured_source_register_ui`
- Problem: The source inventory must distinguish registry continuity from current hash-backed probe rows.
- Deliverable: A concise UI/table for registry sources, current measured rows, hash status, and refresh gaps.
- Acceptance check: The UI visibly separates registry-measured rows from current hash-backed measured rows.
- Evidence output: source-register component, reconciliation note, no-claim banner

### Pilot onboarding path

- Workstream ID: `pilot_onboarding_path`
- Problem: A serious partner needs to know exactly how a validation study would start without accepting terms on the call.
- Deliverable: A gated onboarding flow: problem, data owner, baseline, metric, holdout window, scope, economics review.
- Acceptance check: The flow blocks until human approves data boundary, economics, legal terms, and final share.
- Evidence output: pilot intake checklist, authority stop points, acceptance-standard template

### API reliability and cost controls

- Workstream ID: `api_reliability_cost_controls`
- Problem: Proof generation must be reliable enough for demos and bounded enough for budget review.
- Deliverable: Retry, timeout, cost-limit, source-refresh, and status-receipt controls for proof-stack jobs.
- Acceptance check: Each job records success/failure status, cost boundary, and whether human action is required.
- Evidence output: job receipt schema, status dashboard row, cost-control policy

### Grant and investor packet automation

- Workstream ID: `grant_investor_packet_automation`
- Problem: Funding materials need to stay synchronized with source, claim, IP, and agency-readiness gates.
- Deliverable: A packet refresh workflow that rebuilds public-safe reviewer artifacts and machine controls.
- Acceptance check: A refresh produces manifest counts, gate status, E-drive receipt, and blocked-final-action flags.
- Evidence output: packet build log, data-room manifest, reviewer gate, E-drive hash receipt

## 30-Day Milestones

### Days 1-3 - Scope lock

- Output: Choose workstreams, owner roles, artifacts, non-goals, and approval boundaries.
- Human gate: Robert approves any shared scope, schedule, economics, or contributor access.

### Days 4-10 - Front-door prototype

- Output: Portal/navigation prototype and measured-source register view.
- Human gate: No private file, account, portal, or credential material is exposed.

### Days 11-18 - Replay receipt skeleton

- Output: Runner receipt schema, baseline/candidate fields, and no-claim result template.
- Human gate: No external data owner result is represented without explicit owner acceptance.

### Days 19-24 - Pilot intake and authority gates

- Output: Pilot intake checklist, approval stops, and reviewer-safe data-room handoff.
- Human gate: Terms, economics, file sharing, and schedule remain human-approved only.

### Days 25-30 - Reviewer handoff

- Output: Final sprint packet, demo script, hash manifest, and next validation ask.
- Human gate: Human decides whether to send, schedule, accept terms, or share the packet.

## Human Gate

- scope_share_allowed_without_human: `False`
- email_send_allowed_without_human: `False`
- meeting_schedule_allowed_without_human: `False`
- terms_acceptance_allowed_without_human: `False`
- private_file_share_allowed_without_human: `False`
- rule: `Current control is monitor-only. Keep this scope internal and send nothing unless Terry replies with a specific ask; any later action still requires Robert's review.`

## Evidence Sources

- `out/ops/evtit_technical_sprint_scope_packet_latest.json` | present=`true` | bytes=`10148` | sha256=`c92cc4b3007f2ad0333c5629dffddd47d3d3def061e0bfa60a74827f6e5bed18`
- `out/ops/traction_opportunity_intake_ledger_latest.json` | present=`true` | bytes=`85341` | sha256=`fb88ac9d2b61d3c07ef04eeaa33756dae839b64271c9d5dfd1893e8ad061f7b8`
- `out/ops/traction_followup_packet_latest.json` | present=`true` | bytes=`12366` | sha256=`bf8f2f49c3b8662980a22c8935ec6ef3c9f5401b5a9080744ea4e7f53155d1c5`
- `out/ops/funding_sprint_reviewer_gate_latest.json` | present=`true` | bytes=`73041` | sha256=`355a17d60db1ac7ca05e5442698eb34491ecdd4b97d30e2857b628c167e6c9ab`
- `out/ops/data_room_manifest_latest.json` | present=`true` | bytes=`49467` | sha256=`c92dd8bd0be7dbc8f7ab222a3a9590389b5dffa39b744460f90daf2abb8d84af`
- `out/ops/measured_source_evidence_register_latest.json` | present=`true` | bytes=`42951` | sha256=`e12e23d62f60d2b677fa288a09c023e4a688cd6f395105030b9fc6544dcc3669`
- `out/ops/federal_submission_protocol_packet_latest.json` | present=`true` | bytes=`12389` | sha256=`dbf19b6dcb218b1beba9824e1da8178c59c41856b2c542839b5e6362e9fb1d88`
- `out/ops/submission_authority_matrix_latest.json` | present=`true` | bytes=`33418` | sha256=`616519280f524711e6e11c43e059a90cb5490efbcd3f29f4e22530dd3f6fa1ca`
- `out/ops/ip_counsel_diligence_packet_latest.json` | present=`true` | bytes=`13031` | sha256=`1c1e7133bd44e3bb568972c018b37406cb43ae4ca37d19278b8b5f191ae7b846`
- `out/ops/autonomous_quant_governance_packet_latest.json` | present=`true` | bytes=`10038` | sha256=`fb2fa17cfc4da39ec4c95659e679462fba202af881d2ebad4307419261a77c81`
