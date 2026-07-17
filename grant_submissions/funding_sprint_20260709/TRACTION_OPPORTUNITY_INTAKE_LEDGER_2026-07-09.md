# Traction Opportunity Intake Ledger - Current Control 2026-07-17 (Legacy Intake 2026-07-09)

Purpose: turn connected Gmail evidence, federal contract search, and official public sources into a reviewer-safe action queue.

This ledger does not authorize portal submissions, email sends, certifications, calendar edits, IP filings, trading, or capital movement. It is an intake and prioritization artifact for human review.

## Summary

- Status: `TRACTION_INTAKE_READY_HUMAN_ACTION_REQUIRED`
- Lanes tracked: `19`
- Top priority lanes: `10`
- Gmail references: `16`
- Sweetspot references: `8`
- Public references: `19`
- Current response records: `12`
- Current immediate human actions: `2`
- Current do-not-duplicate sends: `11`
- Current response queue records: `12`
- Exact legacy-lane overlays: `2`
- Related current controls: `5`
- MissionWeave gates: `13/50` passed; `37` open
- MissionWeave ready for human final click: `false`
- Current state supersedes legacy when present: `true`
- Human action required: `true`
- External send without human: `false`
- Final submission without human: `false`
- Ledger SHA-256: `a157a984945fbeedf432b1f64692107fedd25c2044674a5979bfe558fe84d3bf`

## Source Coverage

- gmail_profile: Robert Ashworth mailbox confirmed through Gmail connector.
- gmail_window: Gmail searched in:anywhere after 2026-04-09 for funding, SBIR, RFI/RFP, deadline, calendar, and application terms.
- gmail_latest_response_window: Gmail reconciled the July 16, 2026 response window for EPRI, CDC, LANL, NASA, Army, SAM, Terry/EVTit, USPTO, LinkedIn, venture, and account-notice updates.
- calendar_window: Google Calendar located the July 9 EVTit discovery meeting; public artifacts intentionally exclude meeting access details.
- sweetspot_window: Sweetspot federal contracts searched for active opportunities after 2026-07-09 and before 2026-08-31 across AI validation, lab data QA, data center, and transportation operations lanes.
- external_engagement_response_register: Tracked current-state register reconciled through 2026-07-17; its state and response decision supersede legacy July 9 lane status where both are present.
- missionweave_dsip_action_gate: Integrity-checked action gate reports 13/50 gates passed and 37 open; final submission remains human-only.

## Current Response Overlay

Nashville EC confirmed in writing that its application remains open until 11:59 PM on July 17; the timezone is operationally treated as America/Chicago because the message itself did not state one. The support reply is not an application, so complete the founder-fact gate and reviewed portal workflow well before the close. The FHWA response-lead acknowledgment was sent and must not be duplicated. The first FHWA route rejected delivery; the replacement route replied and referred the request to the subject matter expert leading this response, but no fit check or partner is confirmed. No additional email should be sent now. Complete the overdue SAM account-key action and keep the QA-passed LaunchTN 3686 package staged for founder facts, assumption approval, and final preview. FHWA, EPRI, Georgia PATENTS, CDC, LANL, Terry, NASA, and Army are monitor-only. LvlUp confirmed that declining its optional paid sponsor track does not affect the separate investment and accelerator review, so monitor that thread without spending or sending a duplicate packet; duplicate sends would reduce credibility.

This overlay is authoritative through the stated as-of date and supersedes a legacy lane status where the two differ. Historical status remains visible below for provenance.

- As of: `2026-07-17`
- Source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Register SHA-256: `4020be24c7df7cf0d5bdcc54111c98c0cdd0cd344be8e756babdffa63b3d529b`

| Organization | Current state | Current decision | Deadline | Send now | Duplicate send |
|---|---|---|---|---:|---:|
| Nashville Entrepreneur Center | `OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED` | `COMPLETE_PORTAL_BEFORE_CONFIRMED_CLOSE_NO_DUPLICATE_EMAIL` | 2026-07-17T23:59:00-05:00 | `false` | `true` |
| Launch Tennessee 3686 Pitch Competition | `PORTAL_PACKET_QA_PASSED_HUMAN_FACTS_AND_FOUNDER_APPROVAL_REQUIRED` | `STAGE_PORTAL_FINAL_PREVIEW_REQUIRED` | 2026-08-13T23:59:00-05:00 | `false` | `false` |
| EPRI Open Power AI Consortium | `OUTBOUND_SENT_MOU_PENDING` | `MONITOR_FOR_MOU_NO_DUPLICATE` | None recorded | `false` | `true` |
| Georgia PATENTS | `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING` | `MONITOR_NO_DUPLICATE` | None recorded | `false` | `true` |
| LvlUp Ventures / Power of the Pitch Week | `WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED` | `MONITOR_INDEPENDENT_REVIEW_NO_DUPLICATE` | None recorded | `false` | `true` |
| SAM.gov account credential control | `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED` | `HUMAN_ACCOUNT_ACTION_REQUIRED_NO_EMAIL_REPLY` | 2026-07-16 | `false` | `true` |
| Centers for Disease Control and Prevention | `RECEIPT_CONFIRMED_FOLLOW_UP_PENDING` | `MONITOR_NO_REPLY_REQUIRED` | 2026-07-30T21:00:00Z | `false` | `true` |
| Los Alamos National Laboratory | `OUTBOUND_SENT_RESPONSE_PENDING` | `MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP` | None recorded | `false` | `true` |
| Terry Anderton / Vynetic | `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY` | `MONITOR_NO_FURTHER_FOLLOWUP` | None recorded | `false` | `true` |
| Cambridge Systematics | `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING` | `MONITOR_REFERRED_RESPONSE_LEAD_NO_DUPLICATE` | 2026-08-03T09:00:00-04:00 | `false` | `true` |
| NASA | `SENT_VERIFIED_RESPONSE_PENDING` | `MONITOR_NO_DUPLICATE` | 2026-07-17T21:00:00Z | `false` | `true` |
| U.S. Army | `SENT_VERIFIED_RESPONSE_PENDING` | `MONITOR_NO_DUPLICATE` | None recorded | `false` | `true` |

## Current Response Queue

### Nashville Entrepreneur Center

- Lane ID: `nashville_ec_takeoff_fall_2026`
- State: `OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED`
- Decision: `COMPLETE_PORTAL_BEFORE_CONFIRMED_CLOSE_NO_DUPLICATE_EMAIL`
- Deadline: 2026-07-17T23:59:00-05:00
- Send now: `false`
- Do not duplicate: `true`
- Next action: Run the hidden-prompt private collector, use its ignored 11-answer fill map in the live portal, and complete the reviewed portal flow well before the confirmed close. Do not resend the deadline query or treat it as an application; review the complete preview plus any terms or fee before action-time approval.
- Action gate: Founder answers all six concise confirmation prompts, reviews the complete live portal preview plus any terms or fee, and authorizes final submission at action time.
- Claim boundary: This receipt proves that the official Nashville Entrepreneur Center contact replied to the bounded deadline query with a July 17 close time. It does not prove a portal application was completed, submitted, accepted, reviewed, extended, funded, selected, validated, or awarded. The operational timezone is an explicit inference, not wording contained in the reply.
- Record SHA-256: `a8b869c9c3347e79c7f3edf808feabbea7092a165be5db9bd1a6bf79ae7ff6af`

### Launch Tennessee 3686 Pitch Competition

- Lane ID: `launchtn_3686_pitch_2026`
- State: `PORTAL_PACKET_QA_PASSED_HUMAN_FACTS_AND_FOUNDER_APPROVAL_REQUIRED`
- Decision: `STAGE_PORTAL_FINAL_PREVIEW_REQUIRED`
- Deadline: 2026-08-13T23:59:00-05:00
- Send now: `false`
- Do not duplicate: `false`
- Next action: Keep the portal staged. After founder facts and assumptions are confirmed, attach the hash-verified deck and financial model, inspect the final rendered application, and obtain action-time approval before submitting by August 13 at 11:59 PM CDT.
- Action gate: Founder enters the 11 private, legal, employment, Tennessee-eligibility, funding-history, and pricing confirmations; approves the $250,000 illustrative raise and pricing assumptions; verifies both attachment hashes; then reviews the complete live preview before final submission.
- Claim boundary: This is an application-preparation artifact. It does not claim a paying customer, booked revenue, signed pilot, external or field validation, partnership, endorsement, award, realized savings, product-market fit, investment, competition selection, or permission to submit without a founder-reviewed final preview.
- Record SHA-256: `c8bf0aadfd308ab93664a3c1d22d4b78182b4ad60cf4242f1b6520ceb155a2a8`

### EPRI Open Power AI Consortium

- Lane ID: `epri_open_power_ai_mou`
- State: `OUTBOUND_SENT_MOU_PENDING`
- Decision: `MONITOR_FOR_MOU_NO_DUPLICATE`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Monitor the existing thread for the DocuSign envelope or a clarification request; do not resend identity details.
- Action gate: Reply only when EPRI sends the MOU, requests a correction, or asks for additional onboarding information.
- Claim boundary: This receipt records MOU-routing information only. The Gmail SENT record proves transmission of the administrative reply only. It does not establish an executed MOU, consortium membership, EPRI endorsement, independent validation, a pilot, funding, procurement, a contract, deployment, realized savings, or technical performance.
- Record SHA-256: `dc4d563f61332f4261e235bb738eac440d7b75f67af95a28206dc0ca5a020a7b`

### Georgia PATENTS

- Lane ID: `georgia_patents_pro_bono_intake`
- State: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Decision: `MONITOR_NO_DUPLICATE`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Monitor through July 23 without a duplicate email. In parallel, populate the six ignored Patent Center role folders and use USPTO Pro Se procedural support; send the held practitioner request only after recipient and secure-channel confirmation.
- Action gate: Reply only if Georgia PATENTS requests intake facts or directs the founder to a reviewed application channel; do not disclose unpublished application materials by ordinary email.
- Claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Record SHA-256: `155c39511691f2d5bc6005b40a3869a6e86e24611363d439f57662a38c6aae4f`

### LvlUp Ventures / Power of the Pitch Week

- Lane ID: `lvlup_optional_paid_event`
- State: `WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED`
- Decision: `MONITOR_INDEPENDENT_REVIEW_NO_DUPLICATE`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Monitor the existing thread. Reply only if LvlUp's Investment Committee requests additional information; do not purchase the optional sponsor track or send an unsolicited duplicate packet.
- Action gate: Reply only if LvlUp's Investment Committee requests additional information. No sponsor purchase, unsolicited duplicate packet, valuation disclosure, or reuse of the July 3 draft without a fresh claim review and explicit founder approval.
- Claim boundary: This receipt proves only that LvlUp Ventures stated in writing that declining the sponsor-backed track would not affect the separate investment and accelerator review and that the application would continue through its standard investment process. It does not prove Investment Committee consideration, diligence, selection, investment interest, funding, accelerator admission, endorsement, validation, or an offer.
- Record SHA-256: `39e225300492b8d807f8acdf76d68d675cacbcbaefd831f04d0ce0047bc9b4b1`

### SAM.gov account credential control

- Lane ID: `sam_public_credential_rotation`
- State: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`
- Decision: `HUMAN_ACCOUNT_ACTION_REQUIRED_NO_EMAIL_REPLY`
- Deadline: 2026-07-16
- Send now: `false`
- Do not duplicate: `true`
- Next action: Rotate the public API key inside the authenticated SAM.gov account, run the guarded installer, and rerun the verifier until the private fingerprint changes and an authenticated probe is observable.
- Action gate: Founder completes the official SAM.gov one-time verification code flow, supplies the replacement key only through the hidden local installer prompt, and authorizes the final account confirmation. No secret may enter this register.
- Claim boundary: This control proves only bounded local credential-discovery state, fingerprint comparison, and the recorded API probe result. It never stores or publishes a credential value. A changed fingerprint proves that the configured value changed, not that SAM.gov accepted it. Only a successful authenticated probe can establish live API acceptance, and no browser, account, submission, or opportunity state is changed by this control.
- Record SHA-256: `b33fac024a6456f54cb75d5aa0dc744a739c7b631c2dbab149635fa95202afca`

### Centers for Disease Control and Prevention

- Lane ID: `cdc_ai_acquisition_rfi`
- State: `RECEIPT_CONFIRMED_FOLLOW_UP_PENDING`
- Decision: `MONITOR_NO_REPLY_REQUIRED`
- Deadline: 2026-07-30T21:00:00Z
- Send now: `false`
- Do not duplicate: `true`
- Next action: Preserve the acknowledgment and monitor the existing thread; do not resend the response.
- Action gate: Reply only if CDC asks for clarification, replacement material, or scheduling.
- Claim boundary: The Gmail SENT record and CDC acknowledgment prove transmission and receipt only. They do not establish evaluation, selection, technical validation, endorsement, award, deployment, a pilot, or contract performance.
- Record SHA-256: `e461af1a6d92e3892663518d6a4fb8f7c16efc710e5bede386e03fa282911df0`

### Los Alamos National Laboratory

- Lane ID: `lanl_vision_licensing_followup`
- State: `OUTBOUND_SENT_RESPONSE_PENDING`
- Decision: `MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Wait for LANL. If no reply by July 23, use the single bounded follow-up template in this register.
- Action gate: No follow-up before 2026-07-23 unless LANL replies first; any NDA, licensing term, export-control question, or disclosure remains human-reviewed.
- Claim boundary: The Gmail SENT record and attachment hash prove transmission only. They do not establish LANL receipt, evaluation, a license, endorsement, independent validation, a pilot, funding, deployment, or contract performance.
- Record SHA-256: `b58d53ebda9f491c1411d2e6a883d9a1b12d793b7df656956b57333707ad454b`

### Terry Anderton / Vynetic

- Lane ID: `terry_vynetic_followup`
- State: `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY`
- Decision: `MONITOR_NO_FURTHER_FOLLOWUP`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Send nothing further unless Terry replies with a specific ask; then answer only that ask in the existing thread.
- Action gate: No additional outbound message. If Terry replies, read the complete thread and answer only the specific ask without sending another broad deck.
- Claim boundary: The mailbox record proves only that two near-duplicate follow-ups were sent and no inbound reply was observed at reconciliation time. It does not prove interest, rejection, selection, funding, or validation.
- Record SHA-256: `ae8344c154e7a7eb0d8fe2c6211f0cd8759b677cf093e7841606986f0f4fef67`

### Cambridge Systematics

- Lane ID: `fhwa_tsmo_qualified_partner_outreach`
- State: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING`
- Decision: `MONITOR_REFERRED_RESPONSE_LEAD_NO_DUPLICATE`
- Deadline: 2026-08-03T09:00:00-04:00
- Send now: `false`
- Do not duplicate: `true`
- Next action: Monitor the referred response lead for scheduling or a specific question and do not reuse the rejected address. If no response arrives by July 21, send at most one short scheduling follow-up. Before any teaming or proposal claim, verify written role, documentable corporate experience, conflicts, references, facilities, data rights, and schedule.
- Action gate: Do not claim a partner, cite corporate experience, or draft a joint submission unless a reply supplies written role and evidence permission.
- Claim boundary: The Gmail records prove that the first route was rejected, the replacement message received a substantive reply, the request was referred to the subject matter expert leading this response, and one bounded acknowledgment was sent in that thread. The referral does not establish pursuit, a fit-check commitment, a teaming relationship, permission to cite corporate experience, independent validation, proposal compliance, submission, award, or funding.
- Record SHA-256: `37f7e769c47f17bf85f99b10752fefa0acdc9fcfcb610f05ab4f97ad85e6099c`

### NASA

- Lane ID: `nasa_data_center_rfi`
- State: `SENT_VERIFIED_RESPONSE_PENDING`
- Decision: `MONITOR_NO_DUPLICATE`
- Deadline: 2026-07-17T21:00:00Z
- Send now: `false`
- Do not duplicate: `true`
- Next action: Retain the SENT receipt and attachment hash; do not resend before the deadline.
- Action gate: Respond only to an agency clarification or replacement request.
- Claim boundary: Transmission does not establish agency acceptance, evaluation, validation, an award, or a contract.
- Record SHA-256: `955029063d2e7f8901c9f8a00bf8a3390b50394152321ec770b7c1e067fced24`

### U.S. Army

- Lane ID: `army_aidp_draft_cfs_feedback`
- State: `SENT_VERIFIED_RESPONSE_PENDING`
- Decision: `MONITOR_NO_DUPLICATE`
- Deadline: None recorded
- Send now: `false`
- Do not duplicate: `true`
- Next action: Retain the SENT receipt and attachment hash; monitor for agency feedback.
- Action gate: Respond only to an agency clarification or replacement request.
- Claim boundary: Transmission does not establish agency acceptance, evaluation, validation, an award, or a contract.
- Record SHA-256: `65d68edb83d30739376fc5ae1c5248f075531bac684f06417b9d09e1fb6ce277`

## Legacy Intake Queue With Effective-State Controls

### 0. SAM.gov registration external validation watch

- Lane ID: `sam_registration_external_validation_watch`
- Channel: `federal_registration`
- Legacy intake status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Effective current status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Fit score: `100`
- Legacy intake gate: SAM confirmation says the entity registration remains Submitted until IRS TIN validation and DLA CAGE validation complete; DLA may contact the Government Business POC.
- Effective current gate: SAM confirmation says the entity registration remains Submitted until IRS TIN validation and DLA CAGE validation complete; DLA may contact the Government Business POC.
- Effective reviewer action: Monitor SAM status and any DLA email; prepare notarized Entity Administrator letter if required.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human handles any DLA response, notarized letter, registration correction, or federal certification.
- Effective claim boundary: Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.
- Evidence hash: `abef25e538e1b7b2bd80b927ddcbd2aa5acc48b5e27864b939f7cdf3cdca7578`
- Related current control `sam_public_credential_rotation`: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED` / `HUMAN_ACCOUNT_ACTION_REQUIRED_NO_EMAIL_REPLY`
- Related current next action: Rotate the public API key inside the authenticated SAM.gov account, run the guarded installer, and rerun the verifier until the private fingerprint changes and an authenticated probe is observable.
- Related current do-not-duplicate send: `true`
- Evidence:
  - SAM.gov confirmed the entity registration was successfully submitted.
  - The confirmation states IRS validation can take two business days.
  - The confirmation states DLA CAGE validation averages two business days and can take up to ten business days or longer in peak periods.
  - The confirmation warns that DLA questions must be answered promptly or the registration can return to Work in Progress.
- Sources:
  - `gmail:19f48d20c59295b2`

### 1. EVTit / Black Dog in-kind engineering fund

- Lane ID: `evtit_blackdog_inkind`
- Channel: `venture_engineering`
- Legacy intake status: `RESET_NOTE_SENT_TECH_REVIEW_PENDING`
- Effective current status: `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY`
- Fit score: `92`
- Legacy intake gate: Discovery call window occurred July 9, 2026; reset note sent after the timing mix-up; public launch event July 22, 2026.
- Effective current gate: No additional outbound message. If Terry replies, read the complete thread and answer only the specific ask without sending another broad deck.
- Effective reviewer action: Send nothing further unless Terry replies with a specific ask; then answer only that ask in the existing thread.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:terry_vynetic_followup`
- Human gate: Human approves any follow-up send, scheduling, equity-for-services discussion, or services terms.
- Effective claim boundary: The mailbox record proves only that two near-duplicate follow-ups were sent and no inbound reply was observed at reconciliation time. It does not prove interest, rejection, selection, funding, or validation.
- Evidence hash: `36cb5c9b3e824d0ea99f0cf59c3c3c18d73a8a2413f65d4bb94aaf32f606711f`
- Related current control `terry_vynetic_followup`: `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY` / `MONITOR_NO_FURTHER_FOLLOWUP`
- Related current next action: Send nothing further unless Terry replies with a specific ask; then answer only that ask in the existing thread.
- Related current do-not-duplicate send: `true`
- Evidence:
  - EVTit internal process form requested by Terry Anderton.
  - LumenCore reply indicates the EVTit application form was submitted.
  - EVTit email indicated Bruno and Aron were reviewing the materials already sent.
  - Robert sent a same-day reset note after the meeting-time confusion.
  - Latest thread evidence shows Terry sent a 4 PM invite after the reset note.
- Sources:
  - `gmail:19f43c8a4ba9346e`
  - `gmail:19f44a3d4a48d2c6`
  - `gmail:19f47e797960c0cd`
  - `gmail:19f4822c21a4a861`
  - `gmail:19f484a1fe4aea3b`
  - `gmail:19f485a69ba2410d`
  - `public:evtit_event`
  - `public:black_dog`

### 2. LANL VISION licensing opportunity follow-up

- Lane ID: `lanl_vision_licensing_followup`
- Channel: `federal_lab_tech_transfer`
- Legacy intake status: `WAITING_POC_RETURN`
- Effective current status: `OUTBOUND_SENT_RESPONSE_PENDING`
- Fit score: `88`
- Legacy intake gate: LANL reply says Mike Erickson is the main point of contact and is out until next week.
- Effective current gate: No follow-up before 2026-07-23 unless LANL replies first; any NDA, licensing term, export-control question, or disclosure remains human-reviewed.
- Effective reviewer action: Wait for LANL. If no reply by July 23, use the single bounded follow-up template in this register.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Human gate: Human approves any LANL reply, NDA, licensing discussion, export-control response, or disclosure package.
- Effective claim boundary: The Gmail SENT record and attachment hash prove transmission only. They do not establish LANL receipt, evaluation, a license, endorsement, independent validation, a pilot, funding, deployment, or contract performance.
- Evidence hash: `3d579c2cee9fc1d6f5c0cf053dbffa2e77b560b87a6006e177f1f574c05104bb`
- Current response state: `OUTBOUND_SENT_RESPONSE_PENDING`
- Current response decision: `MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP`
- Current do-not-duplicate send: `true`
- Current next action: Wait for LANL. If no reply by July 23, use the single bounded follow-up template in this register.
- Evidence:
  - LANL replied to the VISION licensing opportunity outreach.
  - The reply identified Mike Erickson as the main point of contact.
  - The reply indicates follow-up is expected after the POC returns next week.
- Sources:
  - `gmail:19f43fa33e165230`

### 2. LvlUp Ventures First Check Fund

- Lane ID: `lvlup_first_check`
- Channel: `venture_cash`
- Legacy intake status: `WAITING_REVIEW`
- Effective current status: `WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED`
- Fit score: `86`
- Legacy intake gate: Submitted July 9, 2026; Gmail reply acknowledged the update.
- Effective current gate: Reply only if LvlUp's Investment Committee requests additional information. No sponsor purchase, unsolicited duplicate packet, valuation disclosure, or reuse of the July 3 draft without a fresh claim review and explicit founder approval.
- Effective reviewer action: Monitor the existing thread. Reply only if LvlUp's Investment Committee requests additional information; do not purchase the optional sponsor track or send an unsolicited duplicate packet.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:lvlup_optional_paid_event`
- Human gate: Human approves any diligence reply or investor terms.
- Effective claim boundary: This receipt proves only that LvlUp Ventures stated in writing that declining the sponsor-backed track would not affect the separate investment and accelerator review and that the application would continue through its standard investment process. It does not prove Investment Committee consideration, diligence, selection, investment interest, funding, accelerator admission, endorsement, validation, or an offer.
- Evidence hash: `b50b331e0094340b54ef8917bc36d524069e977404b618da4f549b195f4ce41f`
- Related current control `lvlup_optional_paid_event`: `WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED` / `MONITOR_INDEPENDENT_REVIEW_NO_DUPLICATE`
- Related current next action: Monitor the existing thread. Reply only if LvlUp's Investment Committee requests additional information; do not purchase the optional sponsor track or send an unsolicited duplicate packet.
- Related current do-not-duplicate send: `true`
- Evidence:
  - LumenCore application submitted with proof-to-pilot public proof link.
  - Jackson Hellmann replied positively to the submitted-update email.
  - Public program describes first-check funding and startup perks for early founders.
- Sources:
  - `gmail:19f44c59a4189d31`
  - `public:lvlup_first_check`

### 3. USPTO / Georgia PATENTS pro bono routing

- Lane ID: `uspto_georgia_patents_route`
- Channel: `ip_readiness`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- Effective current status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Fit score: `100`
- Legacy intake gate: USPTO Pro Bono response says Georgia PATENTS serves Tennessee inventors; counsel must verify actual patent deadlines and filing posture.
- Effective current gate: Reply only if Georgia PATENTS requests intake facts or directs the founder to a reviewed application channel; do not disclose unpublished application materials by ordinary email.
- Effective reviewer action: Monitor through July 23 without a duplicate email. In parallel, populate the six ignored Patent Center role folders and use USPTO Pro Se procedural support; send the held practitioner request only after recipient and secure-channel confirmation.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Human gate: Human and licensed counsel decide any filing, claim, continuation, PCT, disclosure, or legal strategy.
- Effective claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Evidence hash: `8d7a435fe2e0ca5779ddd9f640cf70a953a1196e0c7c0f07c0df494461e6d176`
- Related current control `georgia_patents_pro_bono_intake`: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING` / `MONITOR_NO_DUPLICATE`
- Related current next action: Monitor through July 23 without a duplicate email. In parallel, populate the six ignored Patent Center role folders and use USPTO Pro Se procedural support; send the held practitioner request only after recipient and secure-channel confirmation.
- Related current do-not-duplicate send: `true`
- Evidence:
  - USPTO Pro Bono replied to the urgent patent routing request.
  - The reply points Tennessee inventors to Georgia PATENTS, sponsored by Georgia Lawyers for the Arts.
  - The route gives LumenCore a concrete counsel-intake path instead of a generic legal search.
- Sources:
  - `gmail:19f47bc2564305ae`
  - `public:uspto_probono`
  - `public:georgia_patents`

### 3. DARPA DICE full proposal sprint

- Lane ID: `darpa_dice_full_submission`
- Channel: `federal_baa`
- Legacy intake status: `FULL_PROPOSAL_SPRINT`
- Effective current status: `FULL_PROPOSAL_SPRINT`
- Fit score: `90`
- Legacy intake gate: Abstract ID HR001126S0010-DICE-PA-052 recorded; full proposal instructions must be confirmed against the controlling BAA before upload.
- Effective current gate: Abstract ID HR001126S0010-DICE-PA-052 recorded; full proposal instructions must be confirmed against the controlling BAA before upload.
- Effective reviewer action: Build full submission matrix, compute plan, performer/team map, and acceptance-test narrative.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human confirms BAA requirements, reps, budgets, and submission package before any portal action.
- Effective claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Evidence hash: `56e6c85f69134d68cba74f321efd15a2c103fbe1730bc818643c7799f3c0bc55`
- Evidence:
  - Gmail sent follow-up records receipt of the abstract and the assigned identifying number.
  - Official DARPA DICE page aligns with decentralized coordination and local inference control.
- Sources:
  - `gmail:19f4332ca917d603`
  - `public:darpa_dice`

### 4. FHWA TSMO Data Initiative

- Lane ID: `fhwa_tsmo_data_initiative`
- Channel: `federal_contract`
- Legacy intake status: `PHASE_I_TECH_VOLUME`
- Effective current status: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING`
- Fit score: `95`
- Legacy intake gate: Active until 2026-08-03 13:00 UTC per Sweetspot search; official SAM notice ID 693JJ326R000012 located.
- Effective current gate: 2026-08-03T09:00:00-04:00
- Effective reviewer action: Monitor the referred response lead for scheduling or a specific question and do not reuse the rejected address. If no response arrives by July 21, send at most one short scheduling follow-up. Before any teaming or proposal claim, verify written role, documentable corporate experience, conflicts, references, facilities, data rights, and schedule.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:fhwa_tsmo_qualified_partner_outreach`
- Human gate: Human verifies SAM attachments, terms, pricing, reps/certs, and final submission authority.
- Effective claim boundary: The Gmail records prove that the first route was rejected, the replacement message received a substantive reply, the request was referred to the subject matter expert leading this response, and one bounded acknowledgment was sent in that thread. The referral does not establish pursuit, a fit-check commitment, a teaming relationship, permission to cite corporate experience, independent validation, proposal compliance, submission, award, or funding.
- Evidence hash: `c32368bac63b4aaa578369c9e3fc3e137bab31f362ea0bb46b53490204532a5d`
- Related current control `fhwa_tsmo_qualified_partner_outreach`: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING` / `MONITOR_REFERRED_RESPONSE_LEAD_NO_DUPLICATE`
- Related current next action: Monitor the referred response lead for scheduling or a specific question and do not reuse the rejected address. If no response arrives by July 21, send at most one short scheduling follow-up. Before any teaming or proposal claim, verify written role, documentable corporate experience, conflicts, references, facilities, data rights, and schedule.
- Related current do-not-duplicate send: `true`
- Evidence:
  - Sweetspot matched prototype algorithms/models for AI-enabled TSMO data barriers.
  - Existing LumenCore sprint already contains a Phase I technical capability outline.
- Sources:
  - `public:sam_fhwa_tsmo`
  - `sweetspot:693JJ326R000012`

### 5. NASA Data Center Infrastructure RFI

- Lane ID: `nasa_data_center_rfi`
- Channel: `federal_rfi`
- Legacy intake status: `RFI_RESPONSE_PREP`
- Effective current status: `SENT_VERIFIED_RESPONSE_PENDING`
- Fit score: `89`
- Legacy intake gate: Active until 2026-07-17 21:00 UTC per Sweetspot search; official RFI number 80TECH26RFI0020 located.
- Effective current gate: 2026-07-17T21:00:00Z
- Effective reviewer action: Retain the SENT receipt and attachment hash; do not resend before the deadline.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Human gate: Human verifies official response instructions, page limits, contacts, and final send.
- Effective claim boundary: Transmission does not establish agency acceptance, evaluation, validation, an award, or a contract.
- Evidence hash: `6ab3a422f7a600a1ee70617677465ce9cacaa952f1b310fc4af43dfd83183913`
- Current response state: `SENT_VERIFIED_RESPONSE_PENDING`
- Current response decision: `MONITOR_NO_DUPLICATE`
- Current do-not-duplicate send: `true`
- Current next action: Retain the SENT receipt and attachment hash; do not resend before the deadline.
- Evidence:
  - Sweetspot describes NASA interest in modernization, AI-driven operations, resilience, efficiency, and mission continuity.
  - Existing LumenCore sprint already contains a response outline.
- Sources:
  - `public:sam_nasa_data_center`
  - `sweetspot:80TECH26RFI0020`

### 6. DLA MissionWeave DSIP SBIR

- Lane ID: `dla_missionweave_sbir`
- Channel: `federal_sbir`
- Legacy intake status: `DSIP_PACKAGE_PREP`
- Effective current status: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`
- Fit score: `87`
- Legacy intake gate: Current sprint records July 22, 2026 as the active DSIP gate; verify DSIP before final action.
- Effective current gate: July 22, 2026 at 12:00 p.m. Eastern Time (2026-07-22T16:00:00Z); live DSIP recheck required
- Effective reviewer action: Resolve the 37 open gates out of 50, review the complete portal preview, and retain the human-only final-submit boundary.
- Effective state source: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json`
- Human gate: Human-only Firm PIN, certifications, cost approval, and final submit.
- Effective claim boundary: This public gate proves package integrity, document-format checks, and the completion state of a bounded private DSIP fact workflow. It does not expose legal identifiers, a Firm PIN, the assigned proposal number, private portal evidence, or unsupported compliance facts. It does not establish DLA validation, CMMC status, ITAR compliance, award eligibility, proposal acceptance, submission, selection, contract, award, deployment, or realized performance.
- Evidence hash: `1021295b524e12658764ad5f0e75539683094d6d51cb08ee7929d667f0cfd884`
- Current action-gate progress: `13/50` passed; `37` open
- Ready for human final click: `false`
- Current action-gate source: `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json`
- Current action-gate SHA-256: `fb86f26cb06843158187444a60795e2359bbef96a6e1488c3ec4bcff68f42784`
- Evidence:
  - Existing sprint contains a MissionWeave fast submission plan.
  - SBIR.gov topic framework confirms SBIR/STTR topics define the response rules.
- Sources:
  - `public:sbir_topics`
  - `local:DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md`

### 7. NSF SBIR/STTR Project Pitch

- Lane ID: `nsf_project_pitch`
- Channel: `federal_sbir`
- Legacy intake status: `PITCH_READY_HUMAN_CHECK`
- Effective current status: `PITCH_READY_HUMAN_CHECK`
- Fit score: `78`
- Legacy intake gate: Rolling pitch gate; NSF requires waiting if a Project Pitch, open invitation, or full proposal is already pending.
- Effective current gate: Rolling pitch gate; NSF requires waiting if a Project Pitch, open invitation, or full proposal is already pending.
- Effective reviewer action: Check the one-pending-pitch rule and submit only if no conflicting NSF item is pending.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves pitch content and submission.
- Effective claim boundary: No NSF invitation or full-proposal eligibility is represented unless NSF issues it.
- Evidence hash: `143aa3b96eb7ef242e94590184ed984beadb3527f4a51cf00cbaf3515db82a07`
- Evidence:
  - Existing sprint contains an NSF Project Pitch draft.
  - NSF public guidance confirms the Project Pitch is the gate before invited full proposal submission.
- Sources:
  - `public:nsf_project_pitch`
  - `public:nsf_project_pitch_apply`
  - `local:NSF_PROJECT_PITCH_DRAFT_2026-07-09.md`

### 8. Protecnium ITS infrastructure signal

- Lane ID: `protecnium_its_infrastructure_signal`
- Channel: `infrastructure_market_signal`
- Legacy intake status: `CUSTOMER_DISCOVERY_SIGNAL_ONLY`
- Effective current status: `CUSTOMER_DISCOVERY_SIGNAL_ONLY`
- Fit score: `66`
- Legacy intake gate: Recruiter asked Robert to apply for an ITS Engineer role on a Georgia highway infrastructure project if interested.
- Effective current gate: Recruiter asked Robert to apply for an ITS Engineer role on a Georgia highway infrastructure project if interested.
- Effective reviewer action: Use as market-context evidence; optionally respond only if it supports partner/customer-discovery.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human decides whether to reply, apply, or use it only as a customer-discovery clue.
- Effective claim boundary: This is not a customer commitment, contract, employment acceptance, or pilot demand signal.
- Evidence hash: `0b32bfb482df96b4bb1c03db3260ceaeb43a2a48d7b6fefd6d4b78cbdb8f36e9`
- Evidence:
  - LinkedIn recruiter message indicates external recognition of Robert's infrastructure systems profile.
  - The role maps to highway infrastructure, ITS, and Georgia deployment context.
  - The signal can inform customer-discovery language for FHWA/TSMO and infrastructure validation, without reframing LumenCore as a job search.
- Sources:
  - `gmail:19f485d99c69a63a`
  - `public:protecnium_its_georgia`

### 8. EPA Region 10 ICP-OES RFI route

- Lane ID: `epa_r10_icpoes_route`
- Channel: `federal_market_research`
- Legacy intake status: `ROUTE_ONLY_LOW_FIT`
- Effective current status: `ROUTE_ONLY_LOW_FIT`
- Fit score: `42`
- Legacy intake gate: Active until 2026-07-21 21:30 UTC per Sweetspot search; official notice ID 68HE0726Q0027 located.
- Effective current gate: Active until 2026-07-21 21:30 UTC per Sweetspot search; official notice ID 68HE0726Q0027 located.
- Effective reviewer action: Wait for agency routing response; do not prepare a hardware quote.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves any further agency contact.
- Effective claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Evidence hash: `d87cb6270ffd836b54ec78e0af0eb759e1c6bc3be1e2a480854ea7022e3acf3a`
- Evidence:
  - LumenCore already sent a boundary-safe email clarifying it is not an ICP-OES OEM/reseller.
  - The only viable angle is routing to lab data QA or audit-ready reporting needs.
- Sources:
  - `gmail:19f4332fa2615bd6`
  - `public:sam_epa_icpoes`
  - `sweetspot:68HE0726Q0027`

### 9. EPA UCMR 6 analytical chemistry lab services

- Lane ID: `epa_ucmr6_partner_only`
- Channel: `federal_sources_sought`
- Legacy intake status: `PARTNER_ONLY`
- Effective current status: `PARTNER_ONLY`
- Fit score: `46`
- Legacy intake gate: Active until 2026-07-21 20:00 UTC per Sweetspot search.
- Effective current gate: Active until 2026-07-21 20:00 UTC per Sweetspot search.
- Effective reviewer action: Hold for qualified lab partner; do not chase as prime.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves partner outreach.
- Effective claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Evidence hash: `166227278493f3beb8350f07b6080fb1f5ee6e78403238bcb4bbc4260c231718`
- Evidence:
  - Scope is analytical chemistry laboratory services, not a software-only proof-to-pilot lane.
  - Possible fit only as a data QA, anomaly review, or reporting subcontractor to a qualified lab.
- Sources:
  - `sweetspot:68HERW26R0020`

### 10. FHWA Infrastructure R&D BAA Call 3.0

- Lane ID: `fhwa_infrastructure_baa_call3`
- Channel: `federal_baa`
- Legacy intake status: `SCOUT_TOPIC_MATCH`
- Effective current status: `SCOUT_TOPIC_MATCH`
- Fit score: `64`
- Legacy intake gate: Active until 2026-07-24 17:00 UTC per Sweetspot search; official SAM call located.
- Effective current gate: Active until 2026-07-24 17:00 UTC per Sweetspot search; official SAM call located.
- Effective reviewer action: Download official attachments and score each Appendix C topic before drafting.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves topic selection and submission.
- Effective claim boundary: No claim that LumenCore fits all BAA topics.
- Evidence hash: `7a0d547308ab29dfcd105bb43083b2d96aed1845c76507e57dc1df250125dba3`
- Evidence:
  - Could fit if a topic supports evidence replay, digital asset validation, or nondestructive-evaluation data workflows.
  - Requires topic-by-topic Appendix C fit check before effort.
- Sources:
  - `public:sam_fhwa_baa_call_3`
  - `sweetspot:693JJ3-23-BAA-0002-3`

### 11. HHS AI Power User Advanced Models and Features Pilot

- Lane ID: `hhs_ai_power_user_pilot`
- Channel: `federal_contract`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- Effective current status: `DO_NOT_PRIME_SOLO`
- Fit score: `38`
- Legacy intake gate: Active until 2026-07-14 21:00 UTC per Sweetspot search.
- Effective current gate: Active until 2026-07-14 21:00 UTC per Sweetspot search.
- Effective reviewer action: Do not chase solo; use as partner-target intelligence only.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves any partner route.
- Effective claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Evidence hash: `fdab7383f89e8ae854796d7ecc133d8bf8224d8c7b1f67075130b201d7712b60`
- Evidence:
  - Attractive AI governance language, but Sweetspot indicates a strict security/authorization pathway.
  - Solo-prime posture is not reviewer-safe unless a qualified platform partner leads.
- Sources:
  - `sweetspot:7571TE26R00004`

### 12. CSOSA Public Safety Data Analytics Platform

- Lane ID: `csosa_public_safety_analytics`
- Channel: `federal_contract`
- Legacy intake status: `DO_NOT_PRIME_SOLO`
- Effective current status: `DO_NOT_PRIME_SOLO`
- Fit score: `35`
- Legacy intake gate: Active until 2026-07-14 16:00 UTC per Sweetspot search.
- Effective current gate: Active until 2026-07-14 16:00 UTC per Sweetspot search.
- Effective reviewer action: Park as a partner-only signal; do not spend proposal time as prime.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves any partner route.
- Effective claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Evidence hash: `af354aeb018e7faa1652364649beda10f150978379b94331cc0a8f5d2b14c57c`
- Evidence:
  - Analytics platform language is relevant, but Sweetspot indicates an active FedRAMP Moderate gate at quote submission.
  - LumenCore should not represent qualification for this without a compliant platform partner.
- Sources:
  - `sweetspot:9594CS26Q0053`

### 13. Defense Energy Consortium CMO

- Lane ID: `defense_energy_consortium`
- Channel: `federal_contract`
- Legacy intake status: `PARTNER_INTRO_ONLY`
- Effective current status: `PARTNER_INTRO_ONLY`
- Fit score: `58`
- Legacy intake gate: Active until 2026-07-30 19:00 UTC per Sweetspot search.
- Effective current gate: Active until 2026-07-30 19:00 UTC per Sweetspot search.
- Effective reviewer action: Use as investor/strategic-partner conversation material, not immediate solo proposal.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human approves any partner or investor intro.
- Effective claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Evidence hash: `1dcd38a18d577b95dd01d6d8c8114a081aa1e03b839083570ecacd0cbee132c4`
- Evidence:
  - Energy resilience and facility-management language can map to proof-to-pilot evidence workflows.
  - The prime role appears to require consortium management and private-capital mobilization beyond current solo posture.
- Sources:
  - `sweetspot:FA8003-26-R-0023`

### 14. OpenAI API continuity request

- Lane ID: `openai_api_continuity`
- Channel: `vendor_credit_or_partner_route`
- Legacy intake status: `HUMAN_FORM_READY`
- Effective current status: `HUMAN_FORM_READY`
- Fit score: `80`
- Legacy intake gate: No deadline found; request should be submitted through official contact-sales path if still needed.
- Effective current gate: No deadline found; request should be submitted through official contact-sales path if still needed.
- Effective reviewer action: Submit or update the official contact request with conservative proof-to-pilot framing.
- Effective state source: `legacy_intake_baseline`
- Human gate: Human submits the vendor form and approves any billing or credit terms.
- Effective claim boundary: No credit, free account, or vendor approval is represented.
- Evidence hash: `6643da182a53a3c6f453653eae289090520d40f37c1cfe3aabb37ac267650c6d`
- Evidence:
  - Self-sent packet frames API continuity as a blocker for grant factory and proof-stack maintenance.
  - Official contact-sales page is the clean route for enterprise/startup routing.
- Sources:
  - `gmail:19f43a156bcf0ab6`
  - `public:openai_contact_sales`

### 15. Patent counsel / IP deadline defense

- Lane ID: `patent_deadline_counsel`
- Channel: `ip_readiness`
- Legacy intake status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- Effective current status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Fit score: `100`
- Legacy intake gate: Dossier email states a July 25, 2025 filing date; USPTO Pro Bono routed Tennessee inventors to Georgia PATENTS; counsel must verify all actual patent deadlines before action.
- Effective current gate: Reply only if Georgia PATENTS requests intake facts or directs the founder to a reviewed application channel; do not disclose unpublished application materials by ordinary email.
- Effective reviewer action: Monitor through July 23 without a duplicate email. In parallel, populate the six ignored Patent Center role folders and use USPTO Pro Se procedural support; send the held practitioner request only after recipient and secure-channel confirmation.
- Effective state source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json#related:georgia_patents_pro_bono_intake`
- Human gate: Human and licensed counsel decide any filing, claim, continuation, PCT, or disclosure action.
- Effective claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Evidence hash: `7b354076599f9d59cdd6d2ce0fe40247cbe81d7818305c14027e5d5a3611971c`
- Related current control `georgia_patents_pro_bono_intake`: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING` / `MONITOR_NO_DUPLICATE`
- Related current next action: Monitor through July 23 without a duplicate email. In parallel, populate the six ignored Patent Center role folders and use USPTO Pro Se procedural support; send the held practitioner request only after recipient and secure-channel confirmation.
- Related current do-not-duplicate send: `true`
- Evidence:
  - Patent counsel outreach was sent with application number, title, and requested limited-scope/pro bono routing.
  - USPTO Pro Bono response identified Georgia PATENTS as the Tennessee inventor route.
  - USPTO public guidance confirms provisional-to-nonprovisional timing is deadline-sensitive when applicable.
- Sources:
  - `gmail:19f43b89dd51e2fd`
  - `gmail:19f47bc2564305ae`
  - `public:uspto_provisional`
  - `public:uspto_utility`
  - `public:uspto_probono`
  - `public:georgia_patents`

## Public Source Map

- `black_dog`: https://blackdogceo.com/
- `darpa_dice`: https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence
- `evtit_event`: https://www.eventbrite.com/e/the-equity-for-code-revolution-evtits-10m-in-kind-venture-fund-tickets-1993026582158
- `georgia_patents`: https://glarts.org/georgia-patents/
- `lvlup_first_check`: https://www.lvlup.vc/fund/first-check-fund
- `nsf_project_pitch`: https://seedfund.nsf.gov/project-pitch/
- `nsf_project_pitch_apply`: https://seedfund.nsf.gov/apply/project-pitch/
- `openai_contact_sales`: https://openai.com/contact-sales/
- `protecnium_its_georgia`: https://protecnium.viterbit.site/its-engineer-highway-infrastructure-project-georgia-usa-rvXJvh2d6fuH/
- `sam_epa_icpoes`: https://sam.gov/opp/d9cebf54026d4eae918897e0c34d5a28/view
- `sam_fhwa_baa_call_3`: https://sam.gov/opp/99e6bba615c746e9af27e1527a05a897/view
- `sam_fhwa_tsmo`: https://sam.gov/opp/0ebbe1e43167440ebb111f80fd065ed4/view
- `sam_nasa_data_center`: https://sam.gov/workspace/contract/opp/b6d14a4b9eac476b997894d0c5a47a27/view
- `sbir_topics`: https://www.sbir.gov/topics
- `uspto_probono`: https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program
- `uspto_provisional`: https://www.uspto.gov/patents/basics/apply/provisional-application
- `uspto_utility`: https://www.uspto.gov/patents/basics/apply/utility-patent

## Immediate Next Actions

- Complete the Nashville EC founder-fact gate and reviewed portal workflow well before 2026-07-17T23:59:00-05:00; do not duplicate the deadline-support email.
- Do not duplicate-send NASA, Army, CDC, LANL, EPRI, Georgia PATENTS, FHWA, Terry/Vynetic, or LvlUp packets already controlled by the current register.
- Resolve MissionWeave's 37 open gates and recheck the live DSIP deadline before the expected July 22, 2026 noon Eastern close.
- Monitor the existing FHWA referral thread; no fit check, partner commitment, or additional send is currently supported.
- Build DICE full-proposal compliance matrix after confirming controlling BAA instructions.
- Submit or refresh OpenAI API continuity request through official contact route if still needed.
- Monitor patent counsel replies and prepare filed-materials packet for licensed review.

## Human-Only Boundary

No final portal action, email send, certification, legal filing, pricing approval, account authorization, or investor term acceptance is authorized by this ledger.
