# EVTit Technical Sprint Scope Packet - 2026-07-09

Purpose: give Terry and the EVTit technical team a concrete 30-day sprint shape without accepting terms, sharing private material, or claiming a partnership.

This packet is preparation-only. It does not send email, schedule a meeting, accept equity or services terms, grant access, share files, or authorize final external action.

## Status

- Status: `EVTIT_TECHNICAL_SPRINT_SCOPE_READY_HUMAN_TERMS_REQUIRED`
- Lane ID: `evtit_blackdog_inkind`
- Lane status: `RESET_NOTE_SENT_TECH_REVIEW_PENDING`
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
- External send without human: `false`
- Schedule without human: `false`
- Share private files without human: `false`
- Equity or services terms without human: `false`
- Partnership claimed: `false`
- Investment claimed: `false`
- Services award claimed: `false`
- Customer outcome value claimed: `false`
- Production deployment claimed: `false`
- Packet SHA-256: `457b660f34f0bd715a0da7a52728fd695e98ee3494849683bc0a12ed94f7fb64`

## Positioning

- One sentence: A 30-day technical sprint to convert LumenCore's proof-to-pilot stack into a cleaner reviewer portal, repeatable evidence receipts, measured-source visibility, and pilot-ready intake gates.
- Decision question: Can EVTit help productize the evidence system so serious reviewers can inspect it faster?
- Best next meeting: 30-minute technical fit call with named engineering owners and a workstream selection decision.

## Claim Boundary

Meeting and application evidence only; no investment, services award, or partnership has been accepted.

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
- rule: `This packet is a scope-preparation artifact only. Robert approves any external send, meeting schedule, access grant, economics, equity/service terms, or file sharing.`

## Evidence Sources

- `out/ops/evtit_technical_sprint_scope_packet_latest.json` | present=`true` | bytes=`10147` | sha256=`2c0af339310fa1f6cf3cad6ec5f3e1e4cbb0e60131091466190adde721e6427e`
- `out/ops/traction_opportunity_intake_ledger_latest.json` | present=`true` | bytes=`23378` | sha256=`6d8b07f3454aa843f0095e51f578d110355c5f0a0b7899e7d70a8c85724e6278`
- `out/ops/traction_followup_packet_latest.json` | present=`true` | bytes=`10154` | sha256=`e82ac1ef626d962395244228f0506b1cb7a914594a87a58f0d71c1232ff53178`
- `out/ops/funding_sprint_reviewer_gate_latest.json` | present=`true` | bytes=`36615` | sha256=`550c4690c7864e31398af439432464ab196f8f7b73b3c59d670a8847619017d8`
- `out/ops/data_room_manifest_latest.json` | present=`true` | bytes=`30618` | sha256=`a76ac7df79ba4d25bf479b43b581377e5bdb591ed24cd89008a6d0b761edd39e`
- `out/ops/measured_source_evidence_register_latest.json` | present=`true` | bytes=`42569` | sha256=`7fbadbbcc2304df545bc99b089115aee1bb72ede154743aab8eb4af910539646`
- `out/ops/federal_submission_protocol_packet_latest.json` | present=`true` | bytes=`12389` | sha256=`3cbd27bfe5966b188e92d78206d00c69251040398529585e24609482f3bf56d8`
- `out/ops/submission_authority_matrix_latest.json` | present=`true` | bytes=`26227` | sha256=`157a95c4f9607beba3fa7aa9894c586a80cec2ace86632b60b2bc567baf7239c`
- `out/ops/ip_counsel_diligence_packet_latest.json` | present=`true` | bytes=`11291` | sha256=`51fed2d69e85dc589429af22f19590f4db11ce1e0e593257ceaea512cc423ba1`
- `out/ops/autonomous_quant_governance_packet_latest.json` | present=`true` | bytes=`10038` | sha256=`fb2fa17cfc4da39ec4c95659e679462fba202af881d2ebad4307419261a77c81`
