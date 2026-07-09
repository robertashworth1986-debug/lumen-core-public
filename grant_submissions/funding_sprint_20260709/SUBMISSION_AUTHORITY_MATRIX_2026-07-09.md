# Submission Authority Matrix - 2026-07-09

Purpose: make authority, account, counsel, pricing, and final-action responsibility explicit for every live LumenCore lane.

This matrix is not a submission approval. It separates preparation work from the human authority gates required before anything leaves the system.

## Gate Status

- Status: `SUBMISSION_AUTHORITY_MATRIX_READY`
- Lanes: `15`
- All artifacts present: `true`
- Reviewer gate clear: `true`
- All final actions blocked without human: `true`
- Internal prepare allowed: `13`
- No-solo or partner-only lanes: `4`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- External send without human: `false`
- Final submission without human: `false`
- Live trading allowed: `false`
- Authority matrix SHA-256: `d028a949e3dd6949ce9c586acc12c38cab97b262705089257bbd15d3589a74b7`

## Authority Rows

### 1. EVTit / Black Dog in-kind engineering fund

- Lane ID: `evtit_blackdog_inkind`
- Channel: `venture_engineering`
- Status: `RESET_NOTE_SENT_TECH_REVIEW_PENDING`
- Action type: `meeting_prep`
- Urgency: `IMMEDIATE_24H`
- Action due: `2026-07-09`
- Readiness mode: `MEETING_PREP_READY_FINAL_TERMS_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert attends the meeting and approves any follow-up, build scope, or equity-for-services discussion.
- First artifact: `grant_submissions/funding_sprint_20260709/EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md`
- Claim boundary: Meeting and application evidence only; no investment, services award, or partnership has been accepted.
- Decision question: Can an in-kind engineering team accelerate proof portal, replay runner, manifest, and pilot onboarding?
- Row SHA-256: `9ae3b0c8de662759cdbbd5d69c863a5705590071dcdb60efb36119b8edf3faeb`

Pre-action checks:
- Use only the public proof links and sanitized packet artifacts.
- Keep valuation, equity, and services terms human-decided.
- Do not include meeting access details in public or repo artifacts.

### 2. LvlUp Ventures First Check Fund

- Lane ID: `lvlup_first_check`
- Channel: `venture_cash`
- Status: `WAITING_REVIEW`
- Action type: `investor_watch`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-16`
- Readiness mode: `INVESTOR_WATCH_READY_RESPONSE_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves any investor reply, diligence material, investor terms, or capital commitment.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: Submission and acknowledgement only; no funding decision is represented.
- Decision question: Is a small first check useful enough to preserve execution velocity and unlock pilots?
- Row SHA-256: `f859089a74b4cf5796d801b5c393742ee1c1b8594536a1ce6a5ba3a1b79db195`

Pre-action checks:
- Send only requested materials or a measured follow-up after the review window.
- Reconfirm no performance, revenue, valuation, or award claim is overstated.
- Human reviews any instrument, SAFE, note, equity, or services term.

### 3. DARPA DICE full proposal sprint

- Lane ID: `darpa_dice_full_submission`
- Channel: `federal_baa`
- Status: `FULL_PROPOSAL_SPRINT`
- Action type: `federal_baa_build`
- Urgency: `URGENT_5D`
- Action due: `2026-07-12`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies the controlling BAA instructions, submission account authority, budget, representations, and final package.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Decision question: Does the proposal map a credible research objective to a bounded validation method?
- Row SHA-256: `6ddcae28149e2471e8be1924f9200d31693e397099043ab4bc814c52fd629b53`

Pre-action checks:
- Download or verify the controlling BAA package before final formatting.
- Build compliance matrix and attach only reviewed materials.
- Human approves budget, reps, certifications, and final upload.

### 4. FHWA TSMO Data Initiative

- Lane ID: `fhwa_tsmo_data_initiative`
- Channel: `federal_contract`
- Status: `PHASE_I_TECH_VOLUME`
- Action type: `federal_contract_build`
- Urgency: `WATCHLIST`
- Action due: `2026-08-03`
- Readiness mode: `FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies SAM access, solicitation attachments, pricing, reps/certs, and authorized representative status before submission.
- First artifact: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md`
- Claim boundary: Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.
- Decision question: Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?
- Row SHA-256: `d2256582834310d33c94d80423a545ae3a37b4f73dce24d32b80e3a98a09cdcd`

Pre-action checks:
- Verify current SAM.gov package, amendments, contacts, due time, and required volumes.
- Human approves price, exceptions, representations, and signature authority.
- Keep claims bounded to proof-to-pilot evidence and no field deployment claim.

### 5. NASA Data Center Infrastructure RFI

- Lane ID: `nasa_data_center_rfi`
- Channel: `federal_rfi`
- Status: `RFI_RESPONSE_PREP`
- Action type: `federal_rfi_build`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-17`
- Readiness mode: `RFI_DRAFT_READY_SEND_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies official RFI instructions, contact address, page limits, and final send approval.
- First artifact: `grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md`
- Claim boundary: RFI response only; no NASA partnership, contract, or infrastructure result is represented.
- Decision question: Does the response provide useful market intelligence without claiming award readiness?
- Row SHA-256: `3c43d66a4253d5452bb50bb8391fa21fee1f7dfe557383979b9b2892a373aec2`

Pre-action checks:
- Verify official response instructions and deadline.
- Use market-research framing, not award or deployment language.
- Human approves final email or portal upload.

### 6. DLA MissionWeave DSIP SBIR

- Lane ID: `dla_missionweave_sbir`
- Channel: `federal_sbir`
- Status: `DSIP_PACKAGE_PREP`
- Action type: `federal_sbir_build`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `SBIR_DRAFT_READY_PORTAL_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert controls DSIP or SBIR portal login, Firm PIN, cost approval, certifications, and final submit.
- First artifact: `grant_submissions/funding_sprint_20260709/DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md`
- Claim boundary: No DLA integration, procurement, or certified readiness claim.
- Decision question: Is the Phase I work scoped to produce independently reviewable technical evidence?
- Row SHA-256: `d0b0ddda5e4ced10566358c955109563c5f40ff61659d4b4c51c26b38cf4fdca`

Pre-action checks:
- Human enters Firm PIN and confirms organization authority.
- Human approves cost volume, certifications, and upload preview.
- No integration or procurement readiness claim without agency evidence.

### 7. NSF SBIR/STTR Project Pitch

- Lane ID: `nsf_project_pitch`
- Channel: `federal_sbir`
- Status: `PITCH_READY_HUMAN_CHECK`
- Action type: `rolling_human_check`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `ROLLING_GATE_READY_RULE_CHECK_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies account status, platform-specific rules, one-pending-pitch limits, and final content before submit.
- First artifact: `grant_submissions/funding_sprint_20260709/NSF_PROJECT_PITCH_DRAFT_2026-07-09.md`
- Claim boundary: No NSF invitation or full-proposal eligibility is represented unless NSF issues it.
- Decision question: Is the Phase I work scoped to produce independently reviewable technical evidence?
- Row SHA-256: `225a2bf1f9fef28616edf264c2e8b570608fdf108f0d5dcc73cb5c95f6a87577`

Pre-action checks:
- Check whether any related pitch, invitation, or proposal is already pending.
- Confirm eligibility and portal account state before pressing submit.
- Human approves final text.

### 8. EPA Region 10 ICP-OES RFI route

- Lane ID: `epa_r10_icpoes_route`
- Channel: `federal_market_research`
- Status: `ROUTE_ONLY_LOW_FIT`
- Action type: `agency_routing_watch`
- Urgency: `ACTIVE_14D`
- Action due: `2026-07-21`
- Readiness mode: `ROUTING_SENT_WAIT_FOR_RESPONSE`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves any further agency contact after a routing response.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Decision question: Should LumenCore be routed to a data QA or validation need instead of a hardware buy?
- Row SHA-256: `9e249ca33c12d8e6cf72a79720173ca35204079422bd34a7988f0816d1298843`

Pre-action checks:
- Do not prepare a hardware or prime quote.
- Wait for routing signal or partner path.
- Human approves any follow-up message.

### 9. EPA UCMR 6 analytical chemistry lab services

- Lane ID: `epa_ucmr6_partner_only`
- Channel: `federal_sources_sought`
- Status: `PARTNER_ONLY`
- Action type: `partner_only`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-21`
- Readiness mode: `PARTNER_REQUIRED_NO_SOLO_SUBMISSION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Qualified partner and Robert approve any partner-led response.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Decision question: Is there a qualified prime or lab partner before any response is drafted?
- Row SHA-256: `6fdaad6d93557760304752a83d2c47a717b6d2c2be5d82ed0a65143e7e770f00`

Pre-action checks:
- Identify qualified prime or regulated-domain partner first.
- Do not claim prime qualifications LumenCore does not hold.
- Human approves outreach and role boundary.

### 10. FHWA Infrastructure R&D BAA Call 3.0

- Lane ID: `fhwa_infrastructure_baa_call3`
- Channel: `federal_baa`
- Status: `SCOUT_TOPIC_MATCH`
- Action type: `topic_fit_check`
- Urgency: `WATCHLIST`
- Action due: `2026-07-24`
- Readiness mode: `TOPIC_SCOUT_READY_SELECTION_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves topic selection after official attachments and topic fit are reviewed.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No claim that LumenCore fits all BAA topics.
- Decision question: Does the proposal map a credible research objective to a bounded validation method?
- Row SHA-256: `7c8fac74ab4f9e741e8acd4734b802436c2c14efc90bdda8b45456ef5dd0dbce`

Pre-action checks:
- Download official attachments.
- Score topic fit before drafting.
- Human approves the selected topic and response plan.

### 11. HHS AI Power User Advanced Models and Features Pilot

- Lane ID: `hhs_ai_power_user_pilot`
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Action type: `park_partner_only`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Can prepare internally: `false`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Decision question: Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?
- Row SHA-256: `68d8922d721ccbcb556da21b736aa6afe31ebe9e3ac8166466440c2124a409dd`

Pre-action checks:
- Do not spend proposal time without a qualified partner.
- Keep as market intelligence only.
- Human approves any partner-specific reactivation.

### 12. CSOSA Public Safety Data Analytics Platform

- Lane ID: `csosa_public_safety_analytics`
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Action type: `park_partner_only`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-14`
- Readiness mode: `PARKED_NO_SOLO_ACTION`
- Can prepare internally: `false`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Qualified compliant platform or prime partner must lead before this lane is reopened.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Decision question: Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?
- Row SHA-256: `b82c4d00c943d6967c220c87dfbd85b1abe20ce7641a332a696a0747e6c4f3d5`

Pre-action checks:
- Do not spend proposal time without a qualified partner.
- Keep as market intelligence only.
- Human approves any partner-specific reactivation.

### 13. Defense Energy Consortium CMO

- Lane ID: `defense_energy_consortium`
- Channel: `federal_contract`
- Status: `PARTNER_INTRO_ONLY`
- Action type: `partner_intro_only`
- Urgency: `PARKED_UNLESS_PARTNER`
- Action due: `2026-07-30`
- Readiness mode: `INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves any strategic partner or investor introduction before outreach.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Decision question: Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?
- Row SHA-256: `5421470c607b453f2c797ea1eeba12f6d0518edbed1ed564202162fb5fa8d09b`

Pre-action checks:
- Use as partner/investor context, not a solo bid.
- Human approves the intro target and positioning.
- No project-financing or performance claim unless externally documented.

### 14. OpenAI API continuity request

- Lane ID: `openai_api_continuity`
- Channel: `vendor_credit_or_partner_route`
- Status: `HUMAN_FORM_READY`
- Action type: `vendor_route`
- Urgency: `IMMEDIATE_24H`
- Action due: `2026-07-10`
- Readiness mode: `VENDOR_FORM_READY_HUMAN_SUBMIT_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves vendor form content, account/billing implications, and any credit or discount terms.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: No credit, free account, or vendor approval is represented.
- Decision question: Can a temporary credit or startup route preserve grant/proof-factory continuity?
- Row SHA-256: `4979c1a000a0e537429faafeb52883c99ebb02eb200e3f97df3018a59d7b5b27`

Pre-action checks:
- Use official vendor route only.
- Human reviews billing, account, and program terms.
- Do not represent credit approval unless the vendor grants it.

### 15. Patent counsel / IP deadline defense

- Lane ID: `patent_deadline_counsel`
- Channel: `ip_readiness`
- Status: `URGENT_COUNSEL_WATCH`
- Action type: `licensed_counsel_review`
- Urgency: `WATCHLIST`
- Action due: `2026-07-25`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- First artifact: `grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md`
- Claim boundary: This ledger is not legal advice and does not assert patentability, ownership, or filing sufficiency.
- Decision question: What filing or claim action must licensed counsel verify before public expansion?
- Row SHA-256: `3ea04e892d2f820680cdf722abb85dfbc5deeabe0112310472658b1ba3dcd8ba`

Pre-action checks:
- Prepare filed materials and claim-boundary packet.
- Do not expand public patent, ownership, or freedom-to-operate claims without counsel.
- Human and counsel approve any filing or disclosure action.

## Authority Stop Rule

No lane may be sent, uploaded, certified, filed, priced, accepted, traded, or funded without the named human authority gate.
