# Submission Authority Matrix - 2026-07-09

Purpose: make authority, account, counsel, pricing, and final-action responsibility explicit for every live LumenCore lane.

This matrix is not a submission approval. It separates preparation work from the human authority gates required before anything leaves the system.

## Gate Status

- Status: `SUBMISSION_AUTHORITY_MATRIX_BLOCKED`
- Control integrity: `CONTROL_INTEGRITY_PASS_ACTION_BLOCKED`
- Lanes: `26`
- Source lane counts match: `false`
- All action types mapped: `true`
- Unmapped action types: `none`
- All artifacts present: `true`
- Reviewer gate clear: `false`
- All final actions blocked without human: `true`
- Internal prepare allowed: `24`
- No-solo or partner-only lanes: `4`
- Unsafe sensitive hits: `0`
- Unsafe claim hits: `0`
- External send without human: `false`
- Final submission without human: `false`
- Live trading allowed: `false`
- Authority matrix SHA-256: `935049ac08ccca25188823f9efc7547069b2e90961529797590fb357bffc0a4e`

## Authority Rows

### -10. Nashville EC Fall 2026 TakeOff onboarding

- Lane ID: `nashville_ec_takeoff_fall_2026`
- Channel: `OFFICIAL_ONBOARDING_ROUTE`
- Status: `COHORT_SELECTED_ONBOARDING_AND_PARTICIPATION_AGREEMENT_DUE`
- Action type: `cohort_onboarding`
- Urgency: `URGENT_5D`
- Action due: `2026-07-31`
- Readiness mode: `COHORT_ONBOARDING_REVIEW_HUMAN_ACCEPTANCE_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert reviews cohort obligations, dates, publicity permissions, data terms, and any attendance or participation commitment.
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json`
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Decision question: Are every onboarding answer, participation term, and financial commitment truthful and acceptable before the founder acts?
- Row SHA-256: `d03eeec7f2de3e1aef983062f671a71b5c975487066d90746c96392a4d80f494`

Pre-action checks:
- Verify the official onboarding source and current participation status.
- Separate informational scheduling from binding terms or publicity consent.
- Human approves any acceptance, signature, payment, or external response.

### -9. Login.gov new-device sign-in review

- Lane ID: `login_gov_new_device_signin`
- Channel: `AUTHENTICATED_ACCOUNT`
- Status: `NEW_DEVICE_SIGNIN_REQUIRES_USER_RECOGNITION`
- Action type: `account_security_review`
- Urgency: `IMMEDIATE_24H`
- Action due: `None`
- Readiness mode: `ACCOUNT_SECURITY_EVENT_HUMAN_REVIEW_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies whether the account-security event was expected and controls every sign-in, device, recovery, or session action.
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json`
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Decision question: Was the reported sign-in yours?
- Row SHA-256: `a9e6b09598f545381d99071c0de3bc44a52e6a91ede5fe8a92b6b44c97e96fd1`

Pre-action checks:
- Use official account-security pages reached independently of message links.
- Do not expose one-time codes, recovery data, device identifiers, or session details.
- Human decides whether to revoke sessions or change account settings.

### -8. SAM.gov credential rotation

- Lane ID: `sam_public_credential_rotation`
- Channel: `AUTHENTICATED_ACCOUNT`
- Status: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`
- Action type: `account_credential_rotation`
- Urgency: `OVERDUE_ACTION`
- Action due: `2026-07-16`
- Readiness mode: `ACCOUNT_CREDENTIAL_ROTATION_HUMAN_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert controls the official account, installs the replacement credential through the guarded private workflow, and verifies rotation.
- First artifact: `out/ops/external_engagement_response_register_latest.json`
- Claim boundary: This control proves only bounded local credential-discovery state, fingerprint comparison, and the recorded API probe result. It never stores or publishes a credential value. A changed fingerprint proves that the configured value changed, not that SAM.gov accepted it. Only a successful authenticated probe can establish live API acceptance, and no browser, account, submission, or opportunity state is changed by this control.
- Decision question: Has a replacement credential been created and verified privately?
- Row SHA-256: `ce4ef9bc2e7688a1d5c933790dcde69696771bdc80fac58ed01a968626a112f3`

Pre-action checks:
- Use only the official account route and guarded hidden-input installer.
- Never place credential values in logs, chat, repository files, or public receipts.
- Human verifies changed fingerprint and a bounded live client probe.

### -7. DLA MissionWeave DSIP recorded-status verification

- Lane ID: `dla_missionweave_sbir`
- Channel: `READ_ONLY_PORTAL`
- Status: `OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED`
- Action type: `read_only_portal_verification`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `PORTAL_READ_ONLY_STATUS_VERIFICATION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert controls the authenticated session and permits only a read-only status check unless a separate exact action is approved.
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json`
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Decision question: What exact status does the read-only Past Proposals view show?
- Row SHA-256: `1a641254458a81c90695f384355ac961f5a51c6aad15ba61572d7bbefec3ca1a`

Pre-action checks:
- Verify the official portal and read only the minimum status needed.
- Do not change answers, upload, certify, sign, submit, or expose identifiers.
- Record a bounded status receipt without authentication or controlled-content details.

### -6. DLA AMPS application-role verification

- Lane ID: `dla_amps_application_access`
- Channel: `AUTHENTICATED_ACCOUNT`
- Status: `ACCOUNT_CREATED_EXACT_ROLE_NOT_YET_VERIFIED`
- Action type: `account_role_verification`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `ACCOUNT_ROLE_READ_ONLY_VERIFICATION_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert signs in through the official account route and decides whether to request, accept, or change any application role.
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json`
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Decision question: Which exact application role has the sponsoring program confirmed?
- Row SHA-256: `22e216263f823cf31bd0af55c104e158a1ebd2cddf35a48a4d34c5f954d1d948`

Pre-action checks:
- Verify the official domain and current session before reading role state.
- Record role status without exposing identifiers or authentication material.
- Stop before requesting or accepting a role unless the human approves that exact action.

### -5. EPRI Open Power AI completed-MOU custody review

- Lane ID: `epri_open_power_ai_mou_completed`
- Channel: `PRIVATE_DOCUMENT_CUSTODY`
- Status: `MOU_COMPLETED_BY_ALL_PARTIES_PRIVATE_CUSTODY_REQUIRED`
- Action type: `private_agreement_obligation_review`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `PRIVATE_AGREEMENT_CUSTODY_AND_OBLIGATION_REVIEW`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert and qualified counsel, when needed, review the executed agreement, obligations, confidentiality, IP, export, and termination terms.
- First artifact: `grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json`
- Claim boundary: This privacy-safe register records observed official routing and status events only. It does not establish eligibility, selection, endorsement, funding, an award, a contract, independent validation, licensing, portal completion, or technical performance.
- Decision question: What dated onboarding obligations, if any, appear in the private agreement?
- Row SHA-256: `c7610da5474788e55af12cb31d8c3fe0da0da576aef513456b31110be1c9f709`

Pre-action checks:
- Keep executed agreements and sensitive terms in approved private custody.
- Extract obligations without publishing signatures, identifiers, or confidential text.
- Human and counsel approve any amendment, disclosure, or performance commitment.

### -4. LANL VISION licensing follow-up

- Lane ID: `lanl_vision_licensing_followup`
- Channel: `EMAIL_MONITOR_ONLY`
- Status: `BOUNDED_FOLLOWUP_SENT_RESPONSE_PENDING_INBOUND_ONLY`
- Action type: `inbound_only_monitor`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `INBOUND_ONLY_MONITOR_NO_OUTBOUND_ACTION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert reviews any new inbound message and separately approves a response only if the lane policy permits one.
- First artifact: `grant_submissions/funding_sprint_20260709/OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json`
- Claim boundary: This queue evaluates communication timing and routing controls only. A hold expiration or open deadline requires a fresh mailbox check that is recent, timestamped, and receipted; a current draft is not a sent message, and prior proactive sends are derived from a sealed receipt ledger. None of those conditions authorizes a draft or send. Any future send must also bind the exact subject, body, recipient route, attachments, mailbox receipt, single-use action-time approval, and possession of a private HumanUnlock bearer token before an explicit Gmail action. The bearer proof records token possession only; it does not establish identity or legal signing authority. The queue does not establish submission, receipt, selection, funding, endorsement, validation, technical performance, or authority to disclose private information.
- Decision question: Has a specific substantive inbound request arrived?
- Row SHA-256: `40c51dcb510b27d5d08b810134b8321febc68979fde7027c6e0724120ba7a6a6`

Pre-action checks:
- Monitor only the verified thread or official source.
- Reconcile prior sends and lane-specific follow-up limits before drafting.
- No outbound response is implied by an inbound-only monitor state.

### 0. SAM.gov registration external validation watch

- Lane ID: `sam_registration_external_validation_watch`
- Channel: `federal_registration`
- Status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Action type: `federal_registration_watch`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-13`
- Readiness mode: `FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert verifies SAM status, responds to any official DLA or SAM request, and approves any notarized Entity Administrator letter or correction.
- First artifact: `grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md`
- Claim boundary: Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.
- Decision question: What external validation or entity-administrator action is needed before active-registration claims are safe?
- Row SHA-256: `f52489f84abb2b29d04d681ed1ccb6abe9ff7ed33dad6ab36a6b77b0e397bedc`

Pre-action checks:
- Do not claim Active registration until SAM confirms Active status.
- Respond only to official SAM.gov, FSD, or DLA channels verified by the human.
- Human approves any notarized letter, correction, or certification.

### 1. EVTit / Black Dog in-kind engineering fund

- Lane ID: `evtit_blackdog_inkind`
- Channel: `venture_engineering`
- Status: `OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY`
- Action type: `meeting_prep`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-09`
- Readiness mode: `MEETING_PREP_READY_FINAL_TERMS_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert attends the meeting and approves any follow-up, build scope, or equity-for-services discussion.
- First artifact: `grant_submissions/funding_sprint_20260709/EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md`
- Claim boundary: The mailbox record proves only that two near-duplicate follow-ups were sent and no inbound reply was observed at reconciliation time. It does not prove interest, rejection, selection, funding, or validation.
- Decision question: Can an in-kind engineering team accelerate proof portal, replay runner, manifest, and pilot onboarding?
- Row SHA-256: `4a03f72a75c5a695487d68ec4dd723329749583423cf58101f121ff9576eb588`

Pre-action checks:
- Use only the public proof links and sanitized packet artifacts.
- Keep valuation, equity, and services terms human-decided.
- Do not include meeting access details in public or repo artifacts.

### 2. LvlUp Ventures First Check Fund

- Lane ID: `lvlup_first_check`
- Channel: `venture_cash`
- Status: `WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED`
- Action type: `investor_watch`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-16`
- Readiness mode: `INVESTOR_WATCH_READY_RESPONSE_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves any investor reply, diligence material, investor terms, or capital commitment.
- First artifact: `grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md`
- Claim boundary: This receipt proves only that LvlUp Ventures stated in writing that declining the sponsor-backed track would not affect the separate investment and accelerator review and that the application would continue through its standard investment process. It does not prove Investment Committee consideration, diligence, selection, investment interest, funding, accelerator admission, endorsement, validation, or an offer.
- Decision question: Is a small first check useful enough to preserve execution velocity and unlock pilots?
- Row SHA-256: `52a3b62abbd93d5fbaaa4017e06607bfa9203e1609e5cbcd3847789ecc30af85`

Pre-action checks:
- Send only requested materials or a measured follow-up after the review window.
- Reconfirm no performance, revenue, valuation, or award claim is overstated.
- Human reviews any instrument, SAFE, note, equity, or services term.

### 2. OpenAI Build Week - ProofLock Console

- Lane ID: `openai_build_week_prooflock`
- Channel: `developer_challenge`
- Status: `PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN`
- Action type: `developer_challenge_build`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-21`
- Readiness mode: `DEVELOPER_CHALLENGE_LOCAL_BUILD_FINAL_SUBMIT_BLOCKED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert approves public claims, account terms, media rights, and the final challenge submission.
- First artifact: `grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.md`
- Claim boundary: This is a verified project-readiness lane, not proof of Devpost registration, model identity, final submission, eligibility acceptance, judging outcome, OpenAI endorsement, prize entitlement, external validation, or commercial value.
- Decision question: Does the post-start ProofLock extension provide a coherent, non-trivial, judge-testable developer tool?
- Row SHA-256: `fad7cc62b99843c011073fe3aa27e2876e634d967237ae90e951ddd21d0f21a0`

Pre-action checks:
- Verify the current official challenge rules, deadline, and required disclosures.
- Use only claim-bounded public artifacts and privacy-reviewed media.
- Human reviews the final preview and performs any certification or submit action.

### 3. USPTO / Georgia PATENTS pro bono routing

- Lane ID: `uspto_georgia_patents_route`
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Action type: `licensed_counsel_review`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-10`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- First artifact: `grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md`
- Claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Decision question: What filing or claim action must licensed counsel verify before public expansion?
- Row SHA-256: `8e2c464a23f6ef53dd3f02df3e66323e2aa505abf2cf84ee930fd0b2933b0553`

Pre-action checks:
- Prepare filed materials and claim-boundary packet.
- Do not expand public patent, ownership, or freedom-to-operate claims without counsel.
- Human and counsel approve any filing or disclosure action.

### 3. DARPA DICE full proposal sprint

- Lane ID: `darpa_dice_full_submission`
- Channel: `federal_baa`
- Status: `FULL_PROPOSAL_SPRINT`
- Action type: `federal_baa_build`
- Urgency: `PAST_DATE_RECHECK`
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
- Row SHA-256: `398f42afaf29d50e563b3b1a7564ea82543ef4f192515a14fdde2e1c448a58b2`

Pre-action checks:
- Download or verify the controlling BAA package before final formatting.
- Build compliance matrix and attach only reviewed materials.
- Human approves budget, reps, certifications, and final upload.

### 4. FHWA TSMO Data Initiative

- Lane ID: `fhwa_tsmo_data_initiative`
- Channel: `federal_contract`
- Status: `QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING`
- Action type: `human_review`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert reviews the current official evidence and decides whether this lane remains open, closed, inbound-only, or eligible for a separately approved action.
- First artifact: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md`
- Claim boundary: The Gmail records prove that the first route was rejected, the replacement message received a substantive reply, the request was referred to the subject matter expert leading this response, and one bounded acknowledgment was sent in that thread. The referral does not establish pursuit, a fit-check commitment, a teaming relationship, permission to cite corporate experience, independent validation, proposal compliance, submission, award, or funding.
- Decision question: Can LumenCore contribute a bounded evidence workflow without overstating operational deployment?
- Row SHA-256: `4961606732cdcca08589e37d78cb96f0e3189d6779718f806b1edbd641f20f78`

Pre-action checks:
- Reconcile the latest official source, deadline, route status, and duplicate-action history.
- Do not infer send, submission, or partner authority from local package presence.
- Human approves any change from review-only status.

### 5. NASA Data Center Infrastructure RFI

- Lane ID: `nasa_data_center_rfi`
- Channel: `federal_rfi`
- Status: `SENT_VERIFIED_RESPONSE_PENDING`
- Action type: `human_review`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert reviews the current official evidence and decides whether this lane remains open, closed, inbound-only, or eligible for a separately approved action.
- First artifact: `grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md`
- Claim boundary: Transmission does not establish agency acceptance, evaluation, validation, an award, or a contract.
- Decision question: Does the response provide useful market intelligence without claiming award readiness?
- Row SHA-256: `7c0b519413f53bfe8571db1518979a583d643be4da418c4ea7272952b120f980`

Pre-action checks:
- Reconcile the latest official source, deadline, route status, and duplicate-action history.
- Do not infer send, submission, or partner authority from local package presence.
- Human approves any change from review-only status.

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
- Row SHA-256: `2243120670b644aafe3c9526aacefae0beb0b9131b6d015be92ad985a669c581`

Pre-action checks:
- Check whether any related pitch, invitation, or proposal is already pending.
- Confirm eligibility and portal account state before pressing submit.
- Human approves final text.

### 8. Protecnium ITS infrastructure signal

- Lane ID: `protecnium_its_infrastructure_signal`
- Channel: `infrastructure_market_signal`
- Status: `CUSTOMER_DISCOVERY_SIGNAL_ONLY`
- Action type: `customer_discovery_watch`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `CUSTOMER_DISCOVERY_SIGNAL_READY_HUMAN_REPLY_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert decides whether the infrastructure signal should become a reply, customer-discovery call, partner outreach, or no action.
- First artifact: `grant_submissions/funding_sprint_20260709/CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md`
- Claim boundary: This is not a customer commitment, contract, employment acceptance, or pilot demand signal.
- Decision question: Does the ITS signal sharpen customer-discovery language without claiming a customer or pilot?
- Row SHA-256: `ec7b8b4e956ad64221c0134427cf1a36f077345966d92afa291060a70758c361`

Pre-action checks:
- Use the signal to sharpen buyer language only.
- Do not claim a customer, pilot, contract, or employment commitment.
- Human approves any reply or discovery call.

### 8. EPA Region 10 ICP-OES RFI route

- Lane ID: `epa_r10_icpoes_route`
- Channel: `federal_market_research`
- Status: `ROUTE_ONLY_LOW_FIT`
- Action type: `agency_routing_watch`
- Urgency: `PAST_DATE_RECHECK`
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
- Row SHA-256: `d93f7282cf13790940aff49632263c59f6c8673f7e55d4b64cc2972ce3590d1a`

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
- Row SHA-256: `8d354c5bcb819fd6f1b9468a38ba4d495dd646074018e1e899e2881806eee0db`

Pre-action checks:
- Identify qualified prime or regulated-domain partner first.
- Do not claim prime qualifications LumenCore does not hold.
- Human approves outreach and role boundary.

### 10. FHWA Infrastructure R&D BAA Call 3.0

- Lane ID: `fhwa_infrastructure_baa_call3`
- Channel: `federal_baa`
- Status: `SCOUT_TOPIC_MATCH`
- Action type: `topic_fit_check`
- Urgency: `PAST_DATE_RECHECK`
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
- Row SHA-256: `4003a6845510b5402ca44b7ba5e552acc1e5ef80adab94f6f042bdcfa85a795d`

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
- Row SHA-256: `01ed2de987d7022cf9e67b7b1efa519000dc8bb0e98f82b4e80d4b7f63c6152e`

Pre-action checks:
- Do not spend proposal time without a qualified partner.
- Keep as market intelligence only.
- Human approves any partner-specific reactivation.

### 12. Argos teaming inquiry monitor

- Lane ID: `argos_emi_teaming_inquiry`
- Channel: `EMAIL_THREAD_MONITOR`
- Status: `INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND`
- Action type: `inbound_only_monitor`
- Urgency: `ROLLING_OR_EVENT_GATED`
- Action due: `None`
- Readiness mode: `INBOUND_ONLY_MONITOR_NO_OUTBOUND_ACTION`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Robert reviews any new inbound message and separately approves a response only if the lane policy permits one.
- First artifact: `grant_submissions/funding_sprint_20260709/OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json`
- Claim boundary: This queue evaluates communication timing and routing controls only. A hold expiration or open deadline requires a fresh mailbox check that is recent, timestamped, and receipted; a current draft is not a sent message, and prior proactive sends are derived from a sealed receipt ledger. None of those conditions authorizes a draft or send. Any future send must also bind the exact subject, body, recipient route, attachments, mailbox receipt, single-use action-time approval, and possession of a private HumanUnlock bearer token before an explicit Gmail action. The bearer proof records token possession only; it does not establish identity or legal signing authority. The queue does not establish submission, receipt, selection, funding, endorsement, validation, technical performance, or authority to disclose private information.
- Decision question: Has a specific inbound reply arrived that requires a bounded response?
- Row SHA-256: `90cfba516afbfef524e26cf062588f54c316f5aaf90601b7cb5acbbffc6977c3`

Pre-action checks:
- Monitor only the verified thread or official source.
- Reconcile prior sends and lane-specific follow-up limits before drafting.
- No outbound response is implied by an inbound-only monitor state.

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
- Row SHA-256: `a7dcf8a7173a44b8a1426da0fc0e8ad09a5ea0e28c5a01dbe9381611adf84949`

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
- Row SHA-256: `d37c0260c10f7a59906f22578d89f3840b83d1ff058aad02fdf021144a1c2807`

Pre-action checks:
- Use as partner/investor context, not a solo bid.
- Human approves the intro target and positioning.
- No project-financing or performance claim unless externally documented.

### 14. OpenAI API continuity request

- Lane ID: `openai_api_continuity`
- Channel: `vendor_credit_or_partner_route`
- Status: `HUMAN_FORM_READY`
- Action type: `vendor_route`
- Urgency: `PAST_DATE_RECHECK`
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
- Row SHA-256: `6ede8726fdebc4605a3f8e2b8f6ba804d81fd2db74201fad18308d3532719ee2`

Pre-action checks:
- Use official vendor route only.
- Human reviews billing, account, and program terms.
- Do not represent credit approval unless the vendor grants it.

### 15. Patent counsel / IP deadline defense

- Lane ID: `patent_deadline_counsel`
- Channel: `ip_readiness`
- Status: `OUTBOUND_SENT_INTAKE_RESPONSE_PENDING`
- Action type: `licensed_counsel_review`
- Urgency: `PAST_DATE_RECHECK`
- Action due: `2026-07-25`
- Readiness mode: `IP_PACKET_READY_COUNSEL_REQUIRED`
- Can prepare internally: `true`
- Can send externally without human: `false`
- Can submit without human: `false`
- Can accept terms without human: `false`
- Required authority: Licensed patent counsel and Robert decide any filing, continuation, PCT, disclosure, or claim strategy action.
- First artifact: `grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md`
- Claim boundary: This receipt records transmission of a nonconfidential intake-routing inquiry only. It does not establish program eligibility, acceptance, attorney-client representation, confidentiality, a verified USPTO deadline, preservation of rights, patentability, prosecution status, funding, or legal advice.
- Decision question: What filing or claim action must licensed counsel verify before public expansion?
- Row SHA-256: `ea99307843590ac42eb7a9c6f68882958e1a80f46ffb425cfb637742cb55d765`

Pre-action checks:
- Prepare filed materials and claim-boundary packet.
- Do not expand public patent, ownership, or freedom-to-operate claims without counsel.
- Human and counsel approve any filing or disclosure action.

## Authority Stop Rule

No lane may be sent, uploaded, certified, filed, priced, accepted, traded, or funded without the named human authority gate.
