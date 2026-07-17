# Traction Opportunity Intake Ledger - 2026-07-09

Purpose: turn connected Gmail evidence, federal contract search, and official public sources into a reviewer-safe action queue.

This ledger does not authorize portal submissions, email sends, certifications, calendar edits, IP filings, trading, or capital movement. It is an intake and prioritization artifact for human review.

## Summary

- Status: `TRACTION_INTAKE_READY_HUMAN_ACTION_REQUIRED`
- Lanes tracked: `19`
- Top priority lanes: `10`
- Gmail references: `16`
- Sweetspot references: `8`
- Public references: `19`
- Current response records: `6`
- Current immediate human actions: `2`
- Current do-not-duplicate sends: `4`
- Current state supersedes legacy when present: `true`
- Human action required: `true`
- External send without human: `false`
- Final submission without human: `false`
- Ledger SHA-256: `cdce8e5bcd4068300ab4480aeda2e3557a10f5f6293529349315398321af41c0`

## Source Coverage

- gmail_profile: Robert Ashworth mailbox confirmed through Gmail connector.
- gmail_window: Gmail searched in:anywhere after 2026-04-09 for funding, SBIR, RFI/RFP, deadline, calendar, and application terms.
- gmail_latest_response_window: Gmail reconciled the July 16, 2026 response window for EPRI, CDC, LANL, NASA, Army, SAM, Terry/EVTit, USPTO, LinkedIn, venture, and account-notice updates.
- calendar_window: Google Calendar located the July 9 EVTit discovery meeting; public artifacts intentionally exclude meeting access details.
- sweetspot_window: Sweetspot federal contracts searched for active opportunities after 2026-07-09 and before 2026-08-31 across AI validation, lab data QA, data center, and transportation operations lanes.
- external_engagement_response_register: Tracked current-state register reconciled through 2026-07-16; its state and response decision supersede legacy July 9 lane status where both are present.

## Current Response Overlay

Finish the Nashville EC human-fact gate before July 17 and send the existing EPRI administrative reply only after the exact `send EPRI` gate. CDC, LANL, NASA, and Army are monitor-only; duplicate sends would reduce credibility.

This overlay is authoritative through the stated as-of date and supersedes a legacy lane status where the two differ. Historical status remains visible below for provenance.

- As of: `2026-07-16`
- Source: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json`
- Register SHA-256: `434c04153e6f3908845e83feda5f5d438382257e0f599263a408c53987d1861f`

| Organization | Current state | Current decision | Duplicate send |
|---|---|---|---:|
| Nashville Entrepreneur Center | `PORTAL_PACKET_READY_HUMAN_FACTS_REQUIRED` | `COMPLETE_HUMAN_FACTS_AND_FINAL_PREVIEW` | `false` |
| EPRI Open Power AI Consortium | `INBOUND_ADMIN_REQUEST_DRAFT_READY` | `SEND_EXISTING_GMAIL_DRAFT_AFTER_EXACT_GATE` | `false` |
| Centers for Disease Control and Prevention | `RECEIPT_CONFIRMED_FOLLOW_UP_PENDING` | `MONITOR_NO_REPLY_REQUIRED` | `true` |
| Los Alamos National Laboratory | `OUTBOUND_SENT_RESPONSE_PENDING` | `MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP` | `true` |
| NASA | `SENT_VERIFIED_RESPONSE_PENDING` | `MONITOR_NO_DUPLICATE` | `true` |
| U.S. Army | `SENT_VERIFIED_RESPONSE_PENDING` | `MONITOR_NO_DUPLICATE` | `true` |

## Priority Queue

### 0. SAM.gov registration external validation watch

- Lane ID: `sam_registration_external_validation_watch`
- Channel: `federal_registration`
- Status: `SUBMITTED_EXTERNAL_VALIDATION_PENDING`
- Fit score: `100`
- Gate: SAM confirmation says the entity registration remains Submitted until IRS TIN validation and DLA CAGE validation complete; DLA may contact the Government Business POC.
- Reviewer action: Monitor SAM status and any DLA email; prepare notarized Entity Administrator letter if required.
- Human gate: Human handles any DLA response, notarized letter, registration correction, or federal certification.
- Claim boundary: Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.
- Evidence hash: `e1d3b13f7730556520325e8f516c95b0a1108832cba74e250a51d31b57fac2d3`
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
- Status: `RESET_NOTE_SENT_TECH_REVIEW_PENDING`
- Fit score: `92`
- Gate: Discovery call window occurred July 9, 2026; reset note sent after the timing mix-up; public launch event July 22, 2026.
- Reviewer action: Prepare a concise follow-up packet, technical walkthrough, build-scope menu, and proof-card appendix.
- Human gate: Human approves any follow-up send, scheduling, equity-for-services discussion, or services terms.
- Claim boundary: Meeting and application evidence only; no investment, services award, or partnership has been accepted.
- Evidence hash: `4033f54c72eae8c8e4278d2e5f31ebf0f13578e8f968b4abecabd42b1b72e87b`
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
- Status: `WAITING_POC_RETURN`
- Fit score: `88`
- Gate: LANL reply says Mike Erickson is the main point of contact and is out until next week.
- Reviewer action: Prepare a short licensing-fit note, evidence-replay boundary, and technical questions for Mike Erickson.
- Human gate: Human approves any LANL reply, NDA, licensing discussion, export-control response, or disclosure package.
- Claim boundary: This is a POC routing response only; no LANL license, partnership, endorsement, or technical validation is claimed.
- Evidence hash: `6ca0a46d29df2eb40f8468e3f1ae64a5a9e9384d2653673a9ccb616fa6599894`
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
- Status: `WAITING_REVIEW`
- Fit score: `86`
- Gate: Submitted July 9, 2026; Gmail reply acknowledged the update.
- Reviewer action: Keep investor brief and short walkthrough ready for under-one-week review.
- Human gate: Human approves any diligence reply or investor terms.
- Claim boundary: Submission and acknowledgement only; no funding decision is represented.
- Evidence hash: `f366f3a91ae3b99524825aafcbcc48c59d7326950affc5359c2137b7d79a2351`
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
- Status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- Fit score: `100`
- Gate: USPTO Pro Bono response says Georgia PATENTS serves Tennessee inventors; counsel must verify actual patent deadlines and filing posture.
- Reviewer action: Prepare Georgia PATENTS intake packet: filed materials, invention timeline, public disclosure map, claim boundary, and counsel questions.
- Human gate: Human and licensed counsel decide any filing, claim, continuation, PCT, disclosure, or legal strategy.
- Claim boundary: This is not legal advice and does not assert patentability, ownership, deadline sufficiency, or filing entitlement.
- Evidence hash: `022552f991c7f796cd67f0d57a1835f0d7dbd5b271d7703020e03958f3a389c5`
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
- Status: `FULL_PROPOSAL_SPRINT`
- Fit score: `90`
- Gate: Abstract ID HR001126S0010-DICE-PA-052 recorded; full proposal instructions must be confirmed against the controlling BAA before upload.
- Reviewer action: Build full submission matrix, compute plan, performer/team map, and acceptance-test narrative.
- Human gate: Human confirms BAA requirements, reps, budgets, and submission package before any portal action.
- Claim boundary: Abstract receipt is not award selection and not permission to skip BAA instructions.
- Evidence hash: `06e709b2b3a6ee7687344a8a77110ccdf187f7dbd5db5912ccc456bb6226d177`
- Evidence:
  - Gmail sent follow-up records receipt of the abstract and the assigned identifying number.
  - Official DARPA DICE page aligns with decentralized coordination and local inference control.
- Sources:
  - `gmail:19f4332ca917d603`
  - `public:darpa_dice`

### 4. FHWA TSMO Data Initiative

- Lane ID: `fhwa_tsmo_data_initiative`
- Channel: `federal_contract`
- Status: `PHASE_I_TECH_VOLUME`
- Fit score: `95`
- Gate: Active until 2026-08-03 13:00 UTC per Sweetspot search; official SAM notice ID 693JJ326R000012 located.
- Reviewer action: Convert the existing outline into a compliance matrix, capability volume, and teaming decision.
- Human gate: Human verifies SAM attachments, terms, pricing, reps/certs, and final submission authority.
- Claim boundary: Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.
- Evidence hash: `4874481d91ab906a8777822d57f549a3c7f4afa9d2cbee6d9e3464b9b93f6102`
- Evidence:
  - Sweetspot matched prototype algorithms/models for AI-enabled TSMO data barriers.
  - Existing LumenCore sprint already contains a Phase I technical capability outline.
- Sources:
  - `public:sam_fhwa_tsmo`
  - `sweetspot:693JJ326R000012`

### 5. NASA Data Center Infrastructure RFI

- Lane ID: `nasa_data_center_rfi`
- Channel: `federal_rfi`
- Status: `RFI_RESPONSE_PREP`
- Fit score: `89`
- Gate: Active until 2026-07-17 21:00 UTC per Sweetspot search; official RFI number 80TECH26RFI0020 located.
- Reviewer action: Package the RFI response as architecture, evidence manifest, and operations-risk framing.
- Human gate: Human verifies official response instructions, page limits, contacts, and final send.
- Claim boundary: RFI response only; no NASA partnership, contract, or infrastructure result is represented.
- Evidence hash: `5aa640eab40ca1540aa6fcddabc4f14673bf845114787810ead220818c15b602`
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
- Status: `DSIP_PACKAGE_PREP`
- Fit score: `87`
- Gate: Current sprint records July 22, 2026 as the active DSIP gate; verify DSIP before final action.
- Reviewer action: Prepare DSIP technical volume, cost notes, and Firm PIN handoff checklist.
- Human gate: Human-only Firm PIN, certifications, cost approval, and final submit.
- Claim boundary: No DLA integration, procurement, or certified readiness claim.
- Evidence hash: `a735702bc3b82970aff94c8abe17101ea9f5c48b457dd13108722f23a8bb0df1`
- Evidence:
  - Existing sprint contains a MissionWeave fast submission plan.
  - SBIR.gov topic framework confirms SBIR/STTR topics define the response rules.
- Sources:
  - `public:sbir_topics`
  - `local:DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md`

### 7. NSF SBIR/STTR Project Pitch

- Lane ID: `nsf_project_pitch`
- Channel: `federal_sbir`
- Status: `PITCH_READY_HUMAN_CHECK`
- Fit score: `78`
- Gate: Rolling pitch gate; NSF requires waiting if a Project Pitch, open invitation, or full proposal is already pending.
- Reviewer action: Check the one-pending-pitch rule and submit only if no conflicting NSF item is pending.
- Human gate: Human approves pitch content and submission.
- Claim boundary: No NSF invitation or full-proposal eligibility is represented unless NSF issues it.
- Evidence hash: `4610f5c33a4083a7a9836da688422061f7ed5062598537fcd0bb8a6e6be16527`
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
- Status: `CUSTOMER_DISCOVERY_SIGNAL_ONLY`
- Fit score: `66`
- Gate: Recruiter asked Robert to apply for an ITS Engineer role on a Georgia highway infrastructure project if interested.
- Reviewer action: Use as market-context evidence; optionally respond only if it supports partner/customer-discovery.
- Human gate: Human decides whether to reply, apply, or use it only as a customer-discovery clue.
- Claim boundary: This is not a customer commitment, contract, employment acceptance, or pilot demand signal.
- Evidence hash: `6531fbe0250e2583c922fdd0026c8757d1492ecb6c3ed5cfff1b80ea3677693c`
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
- Status: `ROUTE_ONLY_LOW_FIT`
- Fit score: `42`
- Gate: Active until 2026-07-21 21:30 UTC per Sweetspot search; official notice ID 68HE0726Q0027 located.
- Reviewer action: Wait for agency routing response; do not prepare a hardware quote.
- Human gate: Human approves any further agency contact.
- Claim boundary: No instrument supply, OEM, reseller, or lab-services qualification claim.
- Evidence hash: `6015008a628cd6e369994c16a295c3bf14813a2b1f6071bbbb16a108d1578e5c`
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
- Status: `PARTNER_ONLY`
- Fit score: `46`
- Gate: Active until 2026-07-21 20:00 UTC per Sweetspot search.
- Reviewer action: Hold for qualified lab partner; do not chase as prime.
- Human gate: Human approves partner outreach.
- Claim boundary: No testing lab, contaminant monitoring, or regulated lab-services claim.
- Evidence hash: `e720a50aaddaa9a8465bdb3d1d76b3efb1eaa32554e3a942f14c9fc028d193e9`
- Evidence:
  - Scope is analytical chemistry laboratory services, not a software-only proof-to-pilot lane.
  - Possible fit only as a data QA, anomaly review, or reporting subcontractor to a qualified lab.
- Sources:
  - `sweetspot:68HERW26R0020`

### 10. FHWA Infrastructure R&D BAA Call 3.0

- Lane ID: `fhwa_infrastructure_baa_call3`
- Channel: `federal_baa`
- Status: `SCOUT_TOPIC_MATCH`
- Fit score: `64`
- Gate: Active until 2026-07-24 17:00 UTC per Sweetspot search; official SAM call located.
- Reviewer action: Download official attachments and score each Appendix C topic before drafting.
- Human gate: Human approves topic selection and submission.
- Claim boundary: No claim that LumenCore fits all BAA topics.
- Evidence hash: `e10dd4c3c4d0ca44284e986d50c7fe6cf522b87161387f5faab9c46ce3a015c2`
- Evidence:
  - Could fit if a topic supports evidence replay, digital asset validation, or nondestructive-evaluation data workflows.
  - Requires topic-by-topic Appendix C fit check before effort.
- Sources:
  - `public:sam_fhwa_baa_call_3`
  - `sweetspot:693JJ3-23-BAA-0002-3`

### 11. HHS AI Power User Advanced Models and Features Pilot

- Lane ID: `hhs_ai_power_user_pilot`
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Fit score: `38`
- Gate: Active until 2026-07-14 21:00 UTC per Sweetspot search.
- Reviewer action: Do not chase solo; use as partner-target intelligence only.
- Human gate: Human approves any partner route.
- Claim boundary: No FedRAMP, ATO, HHS pilot, or government production-access claim.
- Evidence hash: `5d9cad79e8b6a798b80a2ae8da310a182403a911efbca1a145080cc3c7a16f12`
- Evidence:
  - Attractive AI governance language, but Sweetspot indicates a strict security/authorization pathway.
  - Solo-prime posture is not reviewer-safe unless a qualified platform partner leads.
- Sources:
  - `sweetspot:7571TE26R00004`

### 12. CSOSA Public Safety Data Analytics Platform

- Lane ID: `csosa_public_safety_analytics`
- Channel: `federal_contract`
- Status: `DO_NOT_PRIME_SOLO`
- Fit score: `35`
- Gate: Active until 2026-07-14 16:00 UTC per Sweetspot search.
- Reviewer action: Park as a partner-only signal; do not spend proposal time as prime.
- Human gate: Human approves any partner route.
- Claim boundary: No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.
- Evidence hash: `fde7add2a7322595242c4152c9e1567f101feae8d67bb87e926e6e84952a423f`
- Evidence:
  - Analytics platform language is relevant, but Sweetspot indicates an active FedRAMP Moderate gate at quote submission.
  - LumenCore should not represent qualification for this without a compliant platform partner.
- Sources:
  - `sweetspot:9594CS26Q0053`

### 13. Defense Energy Consortium CMO

- Lane ID: `defense_energy_consortium`
- Channel: `federal_contract`
- Status: `PARTNER_INTRO_ONLY`
- Fit score: `58`
- Gate: Active until 2026-07-30 19:00 UTC per Sweetspot search.
- Reviewer action: Use as investor/strategic-partner conversation material, not immediate solo proposal.
- Human gate: Human approves any partner or investor intro.
- Claim boundary: No consortium management, energy project financing, or installation-performance claim.
- Evidence hash: `c5c979bcd7a9ed640269d21a5011fcaccd48ff0d3182e9552e464b6d600ca45a`
- Evidence:
  - Energy resilience and facility-management language can map to proof-to-pilot evidence workflows.
  - The prime role appears to require consortium management and private-capital mobilization beyond current solo posture.
- Sources:
  - `sweetspot:FA8003-26-R-0023`

### 14. OpenAI API continuity request

- Lane ID: `openai_api_continuity`
- Channel: `vendor_credit_or_partner_route`
- Status: `HUMAN_FORM_READY`
- Fit score: `80`
- Gate: No deadline found; request should be submitted through official contact-sales path if still needed.
- Reviewer action: Submit or update the official contact request with conservative proof-to-pilot framing.
- Human gate: Human submits the vendor form and approves any billing or credit terms.
- Claim boundary: No credit, free account, or vendor approval is represented.
- Evidence hash: `6edd6faf7c157c03bc28407c1bf4acb03178ba89494d9dc4d74ef7ff20e9667f`
- Evidence:
  - Self-sent packet frames API continuity as a blocker for grant factory and proof-stack maintenance.
  - Official contact-sales page is the clean route for enterprise/startup routing.
- Sources:
  - `gmail:19f43a156bcf0ab6`
  - `public:openai_contact_sales`

### 15. Patent counsel / IP deadline defense

- Lane ID: `patent_deadline_counsel`
- Channel: `ip_readiness`
- Status: `PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED`
- Fit score: `100`
- Gate: Dossier email states a July 25, 2025 filing date; USPTO Pro Bono routed Tennessee inventors to Georgia PATENTS; counsel must verify all actual patent deadlines before action.
- Reviewer action: Prepare Georgia PATENTS intake packet, monitor counsel replies, and avoid public claim expansion until counsel reviews.
- Human gate: Human and licensed counsel decide any filing, claim, continuation, PCT, or disclosure action.
- Claim boundary: This ledger is not legal advice and does not assert patentability, ownership, or filing sufficiency.
- Evidence hash: `550b4cabefcf3b9407ced6d7850379351173b3de563ecd1997e3430b9f7fc58d`
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

- Review the EVTit follow-up packet and send only after human approval.
- Do not duplicate-send NASA, Army, CDC, or LANL packages already recorded by the current response control.
- Complete the Nashville EC human-fact gate before July 17 and use the exact EPRI action-time send gate.
- Advance FHWA TSMO into a final human-review package after official re-verification.
- Build DICE full-proposal compliance matrix after confirming controlling BAA instructions.
- Submit or refresh OpenAI API continuity request through official contact route if still needed.
- Monitor patent counsel replies and prepare filed-materials packet for licensed review.

## Human-Only Boundary

No final portal action, email send, certification, legal filing, pricing approval, account authorization, or investor term acceptance is authorized by this ledger.
