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
- Reviewer packaging gate clear: `true`
- Submission argument gate clear: `false`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- Registry enabled sources: `17`
- Registry measured sources: `11`
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
- Packet SHA-256: `cf8f3edb6986b81ebe1a679594a84230b7f7a53e830cad7e252e357004fc1abf`

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

- `out/ops/evtit_technical_sprint_scope_packet_latest.json` | present=`true` | bytes=`11895` | sha256=`0c8097920208bd71ca943faafcc0f08e8cdde469796d70f81381bc136e38cd80`
- `out/ops/traction_opportunity_intake_ledger_latest.json` | present=`true` | bytes=`88416` | sha256=`d06a06b44c4db3f802544101b71a9275fe8181ac6f40e39193828554b327af78`
- `out/ops/traction_followup_packet_latest.json` | present=`true` | bytes=`12366` | sha256=`bf8f2f49c3b8662980a22c8935ec6ef3c9f5401b5a9080744ea4e7f53155d1c5`
- `out/ops/funding_sprint_reviewer_gate_latest.json` | present=`true` | bytes=`123836` | sha256=`e8f78f0a8794c348c78900eef551fd812cd9e4df62fb0e42229c6c74424ea190`
- `out/ops/data_room_manifest_latest.json` | present=`true` | bytes=`77725` | sha256=`24d6517bee4a94ddaed3282cccd952a3390d0a81e581d9379f78579d4e0e2711`
- `out/ops/measured_source_evidence_register_latest.json` | present=`true` | bytes=`45290` | sha256=`363cad2b175ee6f155d1e1c68a13bef66ba1586da7da170abb72facb434c8853`
- `out/ops/federal_submission_protocol_packet_latest.json` | present=`true` | bytes=`12448` | sha256=`bad5334a73520a8f5d422e7ae16475ccc8068c16509773a8ac51d53b0aa4affd`
- `out/ops/submission_authority_matrix_latest.json` | present=`true` | bytes=`51903` | sha256=`c02fda030889fb387cba67e7c15d13e219453b2700bea75ebfadbbba57b44d4c`
- `out/ops/ip_counsel_diligence_packet_latest.json` | present=`true` | bytes=`13089` | sha256=`d1ef448f97a2360f191f3f07d2cf61627ff1c527ee5fe4a82c1455166ce54d41`
- `out/ops/autonomous_quant_governance_packet_latest.json` | present=`true` | bytes=`10096` | sha256=`58cd3145ac2982918b96943dcb7ba0c20610492f21c608c2fbd87c9fa13e433c`
