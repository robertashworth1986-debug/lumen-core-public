# Near-Deadline Submission Command Board - 2026-07-17

This is the action board for getting the closest credible grants and federal contract responses fully staged.

Direct answer: NASA, Army, and CDC are sent and receipt-backed. SAM.gov public credential rotation became overdue after 2026-07-16. Use the guarded hidden-input installer immediately, then require changed-fingerprint and live-API verification. Entity registration remains active; credential rotation is a separate account-maintenance action. Finish the July 17 Nashville EC TakeOff application, stage the rolling NSF Project Pitch, and monitor the single FHWA qualified-target outreach without claiming a partner or sending a duplicate while keeping DOJ/BOP partner-only.

## Control Line

- Status: `NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_WITH_VERIFIED_SENDS`
- Scan date: `2026-07-17`
- Lane count: `17`
- Stage-now lanes: `4`
- Sent and verified lanes: `3`
- Emergency eligibility gates: `0`
- No-bid or partner-only lanes: `6`
- Expired without verified send: `2`
- Human-gated lanes: `12`
- Strongest today action: Retrieve and install the already-generated SAM.gov replacement public API key without exposing it, complete the Nashville EC TakeOff human-fact gate if its portal remains open, preserve the QA-passed LaunchTN 3686 package for founder facts and final preview, then capture the complete Patent Center docket for separate U.S.-deadline and foreign/PCT-priority review; NASA, Army, and CDC are already sent and receipt-backed.
- Critical infrastructure action: SAM.gov public credential rotation became overdue after 2026-07-16. Use the guarded hidden-input installer immediately, then require changed-fingerprint and live-API verification. Entity registration remains active; credential rotation is a separate account-maintenance action.
- Closest deadline lane: NASHVILLE-EC-FALL-2026 Nashville Entrepreneur Center Fall 2026 Accelerators, due Applications close July 17, 2026; the official page does not list a closing time; command STAGE_APPLICATION; fit STRONG_TAKEOFF_MVP_AND_CUSTOMER_VALIDATION_FIT.
- Closest stage-ready lane: NASHVILLE-EC-FALL-2026 Nashville Entrepreneur Center Fall 2026 Accelerators, due Applications close July 17, 2026; the official page does not list a closing time; command STAGE_APPLICATION; fit STRONG_TAKEOFF_MVP_AND_CUSTOMER_VALIDATION_FIT.
- Best grants lane: NSF 26-510 Project Pitch gate; no fixed pitch due date is listed, and a full proposal requires an invitation. July 27, 2026 is officially listed but currently inaccessible; November 4, 2026 is planning only.
- Best contract lane: 693JJ326R000012 FHWA TSMO Data Initiative, due 2026-08-03: one qualified target was contacted July 17, but no solo bid and no partner claim unless written corporate-experience evidence arrives.
- Fastest low-friction lane: The Nashville EC TakeOff application is the nearest low-friction reviewer route, but six founder confirmations and final portal submission remain human-gated.
- Final submit without human: `false`
- External send without human: `false`
- Pricing without human: `false`
- Legal certification without human: `false`
- Command board SHA-256: `cbaa31953781f970c409bc9ca014fa07406b58d9c15b59248d00682a91fe97db`

## Operational Controls

### sam_public_key_rotation

- Status: `ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED`
- Deadline local: `2026-07-16`
- Deadline state: `PAST_DUE`
- Aliases consistent: `true`
- Replacement installation detected: `false`
- API probe: `HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE`
- Rotation verified: `false`
- Guarded installer: `code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py`
- Human action required: `true`
- Browser navigation performed: `false`
- Control artifact: `grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json`

### patent_deadline_evidence

- Status: `PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED`
- Payment acknowledgement found: `true`
- Filing Receipt found: `false`
- Official correspondence found: `false`
- Official status record found: `false`
- Required docket categories captured: `0/6`
- Complete docket capture: `false`
- Missing docket categories: `fee_history, filing_receipt, official_correspondence, official_status_record, submitted_document_list, transaction_history`
- U.S. prosecution deadline: `UNVERIFIED_REQUIRES_NEWEST_OFFICIAL_NOTICE`
- Foreign or PCT priority: `TIME_SENSITIVE_PRACTITIONER_REVIEW_REQUIRED_IF_FOREIGN_RIGHTS_DESIRED`
- Private capture workflow: `grant_submissions/funding_sprint_20260709/PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md`
- Human action required: `true`
- Browser navigation performed: `false`
- Control artifact: `grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json`

## Sent And Verified

### 1. 80TECH26RFI0020 - Strategic Partnerships for NASA Data Center Infrastructure

- Status: `SENT_WITH_ATTACHMENT`
- Sent UTC: `2026-07-13T21:27:12Z`
- Receipt: `grant_submissions/funding_sprint_20260709/EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json`
- Attachment SHA-256: `88A606678ACC62C60C914C515605D5D590CEACDC1A82AA20B47028B3444EEB0D`

### 3. ACCAPGAIDPRFI4 - Army Intelligence Data Platform RFI #4

- Status: `SENT_WITH_ATTACHMENT`
- Sent UTC: `2026-07-13T21:27:05Z`
- Receipt: `grant_submissions/funding_sprint_20260709/EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json`
- Attachment SHA-256: `D0528488B91C940E2A8401E3571BE72C59124F714883E25CF6D7D7716427B8BF`

### 5. 75D301-26-RFI-73483 - CDC Artificial Intelligence for Acquisition Support Reverse Industry Day

- Status: `RECEIPT_CONFIRMED_FOLLOW_UP_PENDING`
- Sent UTC: `2026-07-16T13:27:19Z`
- Receipt: `grant_submissions/funding_sprint_20260709/CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json`
- Attachment SHA-256: `570F6A6C86DD03649B6F5EE7F731D5E3F0884712CD06DA588D2A4C92C903B2B1`

## Stage Now

### 2. NASHVILLE-EC-FALL-2026 - Nashville Entrepreneur Center Fall 2026 Accelerators

- Command: `STAGE_APPLICATION`
- Deadline UTC: `None`
- Official deadline: Applications close July 17, 2026; the official page does not list a closing time
- Official URL: https://ec.co/apply/
- Package files:
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md`

### 4. LAUNCHTN-3686-2026 - 3686 Pitch Competition 2026, presented by Amazon

- Command: `STAGE_APPLICATION`
- Deadline UTC: `2026-08-14T04:59:00Z`
- Official deadline: August 13, 2026 at 11:59 PM Central Daylight Time
- Official URL: https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form
- Package files:
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx`

### 7. 26-510 - NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I

- Command: `STAGE_PROJECT_PITCH`
- Deadline UTC: `None`
- Official deadline: NSF 26-510 lists July 27 and November 4, 2026, then March 4 and July 7, 2027, as full-proposal deadlines. July 27 is not currently reachable because no official Project Pitch invitation was verified; November 4 is planning only.
- Official URL: https://seedfund.nsf.gov/project-pitch/
- Package files:
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PASTE_CHECK_2026-07-16.md`
  - `grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS.md`

### 8. W912HZ26SC005 - Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening

- Command: `STAGE_CONCEPT_PAPER`
- Deadline UTC: `2026-08-07T21:00:00Z`
- Official deadline: August 7, 2026 at 4:00 PM Central Time
- Official URL: https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view
- Package files:
  - `ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md`

## Emergency Gate

## No-Bid Or Partner-Only

### 6. 693JJ326R000012 - Transportation Systems Management and Operations Data Initiative

- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Deadline date: `2026-08-03`
- Eligibility: `QUALIFIED_TARGET_CONTACTED_PARTNER_CONFIRMATION_PENDING`
- Fit: `STRONG_TECHNICAL_FIT_MANDATORY_CORPORATE_EXPERIENCE_MISSING`
- Official URL: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view

### 9. 15BCMS26Q70000005 - Historical Medical Claims Data Analysis

- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Deadline date: `2026-07-23`
- Eligibility: `SMALL_BUSINESS_SET_ASIDE_SOLO_DELIVERY_GATES_NOT_MET`
- Fit: `ANALYTICS_COMPONENT_FIT_HIPAA_ATO_HSPD12_MEDICAL_CLAIMS_AND_FFP_GATES_OPEN`
- Official URL: https://sam.gov/opp/52680f2a89c241b3a055c35d816b7f20/view

### 14. 693JJ3-26-BAA-0004 - Intersection Safety Systems Prototyping

- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Deadline date: `2026-07-20`
- Eligibility: `OPEN_BAA_TEAM_COMPOSITION_REQUIRED`
- Fit: `STRONG_MEASUREMENT_FIT_TESTBED_AND_PUBLIC_SECTOR_PARTNERS_MISSING`
- Official URL: https://sam.gov/opp/a08fe6151b524fbd87e4c7ce8f6a4abb/view

### 15. 7571TE26R00004 - HHS AI Power User Advanced Models and Features Pilot

- Command: `PARTNER_OR_NO_BID`
- Deadline date: `2026-07-14`
- Eligibility: `OPEN_SOLICITATION_NO_SET_ASIDE`
- Fit: `THEMATIC_MEASUREMENT_FIT_PRIME_DELIVERY_REQUIREMENTS_NOT_MET`
- Official URL: https://sam.gov/workspace/contract/opp/d60ae511937b410fa6f13473acbae762/view

### 16. 26-508 - TechAccess: AI-Ready America - State/Territory Coordination Hubs

- Command: `NO_BID_MISSED_PREREQUISITE`
- Deadline date: `2026-07-16`
- Eligibility: `ROUND_ONE_REQUIRED_LOI_DUE_JUNE_16_WAS_MISSED`
- Fit: `STRATEGIC_PARTNER_FIT_WATCH_ROUND_TWO`
- Official URL: https://www.nsf.gov/funding/opportunities/techaccess-ai-ready-america/nsf26-508/solicitation

### 17. HHS-2026-ACF-ACYF-CA-0037 - Predictive Analytics in Child Welfare Demonstration Grants

- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Deadline date: `2026-07-13`
- Eligibility: `INELIGIBLE_AS_SOLO_SMALL_BUSINESS`
- Fit: `PARTNER_ONLY_CHILD_WELFARE_DOMAIN`
- Official URL: https://www.grants.gov/search-results-detail/361912

## Expired Without Verified Send

### 11. HHS-2026-ACL-NIDILRR-REGE-0212 - RERC on AI-Driven Assistive and Rehabilitation Technologies

- Deadline date: `2026-07-16`
- Prior command: `TECHNICAL_CAPACITY_AND_DOMAIN_GATE`
- Status: `DEADLINE_PASSED_NO_VERIFIED_SEND`
- Official URL: https://simpler.grants.gov/opportunity/c08bbf7a-563b-4af4-a79b-b1cb7bdd71ad

### 13. PDR-2600-DC-029Q - Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration

- Deadline date: `2026-07-13`
- Prior command: `ELIGIBILITY_AND_PARTNER_GATE`
- Status: `DEADLINE_PASSED_NO_VERIFIED_SEND`
- Official URL: https://www.grants.gov/search-results-detail/362360

## Full Lane Detail

### 1. 80TECH26RFI0020 - Strategic Partnerships for NASA Data Center Infrastructure

- Source: `SAM.gov`
- Agency: `NASA IT Procurement Office`
- Deadline UTC: `2026-07-17T21:00:00Z`
- Official deadline: 2026-07-17T21:00:00Z
- Days to close from scan date: `0`
- Deadline bucket: `48_hour_sprint`
- Command: `SENT_VERIFIED`
- Eligibility: `OPEN_RFI_RESPONSE`
- Fit: `STRONG_CAPABILITY_RESPONSE_FIT`
- Route: Email response per RFI instructions
- Official URL: https://sam.gov/opp/312af51a7fc14110b1239bdd32252213/view
- Why now: Fastest clean federal market-research lane: no pricing needed, response can be bounded to capability, proof-to-decision validation, and no agency-validation claims.
- Today work:
  - Monitor for an inbound response, amendment, or clarification request.
  - Do not resend unless the agency requests a replacement or the receipt fails verification.
- Package files:
  - `NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md`
  - `NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md`
  - `NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md`
  - `NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.pdf`
  - `NASA_DATA_CENTER_RFI_EMAIL_DRAFT_2026-07-11.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `cf152ed8995ad0a3c4f1d4db575f29d79f24cad58a787a1cdc47c170d11be357`

### 2. NASHVILLE-EC-FALL-2026 - Nashville Entrepreneur Center Fall 2026 Accelerators

- Source: `Nashville Entrepreneur Center official site / Gmail newsletter`
- Agency: `Nashville Entrepreneur Center`
- Deadline UTC: `None`
- Official deadline: Applications close July 17, 2026; the official page does not list a closing time
- Days to close from scan date: `0`
- Deadline bucket: `48_hour_sprint`
- Command: `STAGE_APPLICATION`
- Eligibility: `MIDDLE_TENNESSEE_SOLO_FOUNDER_FIT_HUMAN_FACTS_UNVERIFIED`
- Fit: `STRONG_TAKEOFF_MVP_AND_CUSTOMER_VALIDATION_FIT`
- Route: Nashville Entrepreneur Center common accelerator application
- Official URL: https://ec.co/apply/
- Secondary URL: https://ec.co/accelerators/takeoff/
- Why now: This is the nearest legitimate local reviewer and commercialization route. TakeOff fits a Nashville-based solo founder with a working MVP and no claimed customers. The listed $500 program fee and $125 start payment are not authorized; the application should answer no on fee readiness and request financial aid before accepting terms.
- Today work:
  - Collect the six concise founder confirmations in the human-fact resolution artifact.
  - Paste the claim-bounded answers into the common application and select TakeOff.
  - Stop at final preview; do not accept a fee, terms, or cohort seat during application staging.
- Human gate:
  - Robert answers all six prompts covering founder status, weekly hours, conversation count, revenue, founder investment, received funding, and business debt.
  - Robert reviews the final portal preview and approves submission before the July 17 close.
  - Any later program fee, financial-aid arrangement, terms, or cohort acceptance requires a separate decision.
- Package files:
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json`
  - `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `2cbe84e796877173f726a8b056c18f3391fd0e502b66b8c8ee45d6e129571cac`

### 3. ACCAPGAIDPRFI4 - Army Intelligence Data Platform RFI #4

- Source: `SAM.gov`
- Agency: `U.S. Army Contracting Command - Aberdeen Proving Ground`
- Deadline UTC: `2026-07-15T21:00:00Z`
- Official deadline: July 15, 2026 at 5:00 PM Eastern Time
- Days to close from scan date: `-2`
- Deadline bucket: `past_due`
- Command: `SENT_VERIFIED`
- Eligibility: `OPEN_RFI_FEEDBACK_ATTACHMENT_ACCESS_REQUIRED`
- Fit: `STRONG_DATA_PLATFORM_AND_AUDITABILITY_FEEDBACK_FIT`
- Route: Email questions and feedback using the official spreadsheet attachment
- Official URL: https://sam.gov/workspace/contract/opp/3d72f2df3aaf459797c14cefb41fd235/view
- Why now: The Army is requesting structured feedback on a draft data-platform solution. LumenCore can contribute bounded comments on evidence provenance, replay, observability, and decision auditability without claiming to supply the entire platform.
- Today work:
  - Monitor for an inbound response, amendment, or clarification request.
  - Do not resend unless the agency requests a replacement or the receipt fails verification.
- Package files:
  - `ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `9bd27e40c2e04d0858ba4ef974a20e7870a3b0813f52bd76f03240fa93d3a8db`

### 4. LAUNCHTN-3686-2026 - 3686 Pitch Competition 2026, presented by Amazon

- Source: `Launch Tennessee official 3686 Airtable application`
- Agency: `Launch Tennessee`
- Deadline UTC: `2026-08-14T04:59:00Z`
- Official deadline: August 13, 2026 at 11:59 PM Central Daylight Time
- Days to close from scan date: `27`
- Deadline bucket: `thirty_day_sprint`
- Command: `STAGE_APPLICATION`
- Eligibility: `TENNESSEE_STARTUP_FIT_HUMAN_ATTESTATION_REQUIRED`
- Fit: `STRONG_WORKING_MVP_AND_COMMERCIALIZATION_FIT`
- Route: Launch Tennessee 3686 Airtable application
- Official URL: https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form
- Why now: The application-specific deck and formula-driven five-year model have passed visual, content, formula, and attachment-hash QA. The remaining gates are founder-controlled facts, Tennessee eligibility, pricing and raise approval, and the live final preview.
- Today work:
  - Confirm the 11 private, legal, employment, Tennessee-eligibility, funding-history, and pricing facts in the application manifest.
  - Approve or revise the illustrative pricing ranges and $250,000 validation-bridge funding need.
  - Upload only the two hash-verified QA-passed attachments and stop at the complete final preview.
- Human gate:
  - Robert enters private contact and address facts only inside the authenticated portal.
  - Robert verifies the legal entity, formation year, employee count, Tennessee eligibility, and prior LaunchTN capital history.
  - Robert approves the pricing, funding assumptions, attachments, and final portal preview before submission.
- Package files:
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx`
  - `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `10d4c44a850e9047159fb7924f552c9e8579dad218063af7428b8cd1c99f8065`

### 5. 75D301-26-RFI-73483 - CDC Artificial Intelligence for Acquisition Support Reverse Industry Day

- Source: `SAM.gov / Gmail receipt`
- Agency: `Centers for Disease Control and Prevention`
- Deadline UTC: `2026-07-30T21:00:00Z`
- Official deadline: July 30, 2026 at 5:00 PM Eastern Time
- Days to close from scan date: `13`
- Deadline bucket: `two_week_sprint`
- Command: `SENT_VERIFIED`
- Eligibility: `RFI_MARKET_RESEARCH_RESPONSE_RECEIVED`
- Fit: `BOUNDED_AI_ACQUISITION_EVIDENCE_RESPONSE_DELIVERED`
- Route: Email response per the official RFI instructions
- Official URL: https://sam.gov/opp/3b42d94270da435fa690c2fc5f26e157/view
- Why now: CDC confirmed receipt and said it will follow up. Preserve the receipt and monitor; do not duplicate-send.
- Today work:
  - Monitor the existing Gmail thread for a CDC clarification or follow-up.
  - Do not resend unless CDC asks for a replacement or additional material.
- Package files:
  - `CDC_AI_ACQUISITION_RFI_75D301-26-RFI-73483_2026-07-15.md`
  - `LumenCore_CDC_AI_Acquisition_RFI_75D301-26-RFI-73483_2026-07-15.pdf`
  - `CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `bf728626b079d827c2e154282b1a67f4c17e5c53157a07e869351660cfb690c5`

### 6. 693JJ326R000012 - Transportation Systems Management and Operations Data Initiative

- Source: `SAM.gov`
- Agency: `Federal Highway Administration`
- Deadline UTC: `2026-08-03T13:00:00Z`
- Official deadline: 2026-08-03T13:00:00Z
- Days to close from scan date: `17`
- Deadline bucket: `thirty_day_sprint`
- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Eligibility: `QUALIFIED_TARGET_CONTACTED_PARTNER_CONFIRMATION_PENDING`
- Fit: `STRONG_TECHNICAL_FIT_MANDATORY_CORPORATE_EXPERIENCE_MISSING`
- Route: SAM.gov / official solicitation instructions
- Official URL: https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view
- Why now: LumenCore has a strong bounded technical fit, but the solicitation requires documented corporate TSMO data-processing experience that LumenCore cannot claim. One qualified target was contacted on July 17; contact is not a partner.
- Today work:
  - Monitor the single qualified-target outreach for a response.
  - Do not send a duplicate follow-up before July 23 and do not claim a partner.
  - If a response arrives, verify role, references, conflicts, facilities, data rights, and permission to cite corporate experience.
- Human gate:
  - A qualified organization confirms a role and documentable corporate experience in writing.
  - Robert approves any teaming terms, Phase I claims, and final submission preview.
- Package files:
  - `FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md`
  - `LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf`
  - `FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md`
  - `FHWA_TSMO_COMPLIANCE_MATRIX_DRAFT_2026-07-11.md`
  - `FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md`
  - `FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `0b0699fb78e670940be64b6c1104dbfe4ee003ddebcc6eaa8deabfe80140b099`

### 7. 26-510 - NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I

- Source: `NSF Seed Fund Project Pitch`
- Agency: `U.S. National Science Foundation`
- Deadline UTC: `None`
- Official deadline: NSF 26-510 lists July 27 and November 4, 2026, then March 4 and July 7, 2027, as full-proposal deadlines. July 27 is not currently reachable because no official Project Pitch invitation was verified; November 4 is planning only.
- Days to close from scan date: `110`
- Deadline bucket: `later`
- Command: `STAGE_PROJECT_PITCH`
- Eligibility: `PROJECT_PITCH_REQUIRED_INVITATION_NOT_VERIFIED`
- Fit: `STRONG_TRUSTWORTHY_AI_FIT_26_510_26_511_STAFF_CONFIRMATION_REQUIRED`
- Route: NSF Seed Fund Project Pitch now; Research.gov full proposal only after an official invitation
- Official URL: https://seedfund.nsf.gov/project-pitch/
- Secondary URL: https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation
- Deadline date semantics: `INVITATION_CONTINGENT_PLANNING_TARGET_NOT_PROJECT_PITCH_DUE_DATE`
- Why now: This is the strongest grants-side route, but the immediate action is the rolling Project Pitch. July 27 is an official full-proposal deadline but is currently inaccessible without a verified invitation. NSF 26-510 is the cleaner general deep-technology fit; use 26-511 only if NSF confirms the software-defined scientific-instrumentation framing.
- Today work:
  - Confirm in the Project Pitch portal that no pitch is pending and no invitation or full proposal is open.
  - Paste the four locally counted, claim-bounded fields from the canonical portal packet.
  - Stop at final review so the legal company facts and submission certification can be checked.
- Human gate:
  - Robert confirms the legal company profile, PI eligibility, and portal status.
  - Robert reviews the final portal preview and approves the Project Pitch submission.
- Package files:
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PASTE_CHECK_2026-07-16.md`
  - `grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json`
  - `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `f2774d5e283b4c470e1eff3849be1007fda1f2b27bc55a8ee7c5aa69e00ef8fa`

### 8. W912HZ26SC005 - Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening

- Source: `SAM.gov / ERDCWERX`
- Agency: `ERDC Information Technology Laboratory / HPCMP`
- Deadline UTC: `2026-08-07T21:00:00Z`
- Official deadline: August 7, 2026 at 4:00 PM Central Time
- Days to close from scan date: `21`
- Deadline bucket: `thirty_day_sprint`
- Command: `STAGE_CONCEPT_PAPER`
- Eligibility: `OPEN_CSO_COMMERCIAL_SOLUTION`
- Fit: `STRONG_MODULAR_PROOF_FABRIC_COMPONENT_FIT`
- Route: ERDCWERX Commercial Solutions Opening portal
- Official URL: https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view
- Secondary URL: https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/
- Why now: Good concept-paper lane if LumenCore is framed as a proof fabric module, not a full sovereign cloud prime.
- Today work:
  - Open ERDCWERX and confirm form fields.
  - Stage concept title, problem, modular solution, and data-rights boundary.
- Human gate:
  - Robert approves title, commercial item framing, data rights, and any price.
  - Robert approves final portal submit.
- Package files:
  - `ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `996db15b113cf8782aea41259f4aacba9125ca51e02b8a2934008274bc1be922`

### 9. 15BCMS26Q70000005 - Historical Medical Claims Data Analysis

- Source: `SAM.gov`
- Agency: `Federal Bureau of Prisons`
- Deadline UTC: `2026-07-23T15:00:00Z`
- Official deadline: July 23, 2026 at 11:00 AM Eastern Time
- Days to close from scan date: `6`
- Deadline bucket: `seven_day_sprint`
- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Eligibility: `SMALL_BUSINESS_SET_ASIDE_SOLO_DELIVERY_GATES_NOT_MET`
- Fit: `ANALYTICS_COMPONENT_FIT_HIPAA_ATO_HSPD12_MEDICAL_CLAIMS_AND_FFP_GATES_OPEN`
- Route: Email quote per solicitation instructions
- Official URL: https://sam.gov/opp/52680f2a89c241b3a055c35d816b7f20/view
- Why now: Official-source review supports only a conditional partner route. LumenCore does not currently evidence the HIPAA officer, ATO/ISSO delivery capacity, screened personnel, medical-claims expertise, or firm-fixed-price delivery posture required for a responsible solo quote.
- Today work:
  - Do not send a solo quote.
  - Use the bounded partner template only if a qualified healthcare-claims and federal-security prime is identified.
  - Require the partner to own compliance, staffing, pricing, and protected-data delivery commitments.
- Human gate:
  - A qualified prime confirms HIPAA, ATO/ISSO, HSPD-12, medical-claims, and delivery responsibility in writing.
  - Robert approves the partner outreach, role, price, representations, and any final quote.
- Package files:
  - `grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json`
  - `grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md`
  - `grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_PARTNER_OUTREACH_TEMPLATE_2026-07-16.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `9c543bfd7bd43811b0775448be4bf127a73e9c7b8c989cb9b8daef9a8bb99100`

### 10. 1131PL26R0049 - Indo-Pacific Digital Infrastructure Project Scoping Services

- Source: `SAM.gov`
- Agency: `U.S. Trade and Development Agency`
- Deadline UTC: `2026-07-22T17:00:00Z`
- Official deadline: July 22, 2026 at 1:00 PM Eastern Time
- Days to close from scan date: `5`
- Deadline bucket: `seven_day_sprint`
- Command: `PRICE_PAST_PERFORMANCE_AND_CAPACITY_GATE`
- Eligibility: `TOTAL_SMALL_BUSINESS_SET_ASIDE_US_FIRM`
- Fit: `ADJACENT_DIGITAL_INFRASTRUCTURE_FIT_SCOPING_CAPACITY_UNPROVEN`
- Route: Proposal under the official RFP instructions
- Official URL: https://sam.gov/workspace/contract/opp/fdefc4a420e04049a6a768f744d040c9/view
- Why now: It is a total small-business set-aside and adjacent to digital-infrastructure evaluation, but the prime must prove project-scoping capacity, international delivery, price, and relevant past performance.
- Today work:
  - Review Sections B through E and the performance work statement.
  - Run a strict responsibility, staffing, travel, and past-performance gate.
  - Proceed only if every mandatory role and deliverable can be evidenced.
- Human gate:
  - Robert confirms staffing, international-delivery capacity, and past performance.
  - Robert approves price, representations, and final proposal submission.
- Package files:
  - `USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `97b90181fb7c2fe5d95cb35063e3d117663d099d3533cb224fe0d583f97c201b`

### 11. HHS-2026-ACL-NIDILRR-REGE-0212 - RERC on AI-Driven Assistive and Rehabilitation Technologies

- Source: `Grants.gov / Simpler.Grants.gov`
- Agency: `Administration for Community Living`
- Deadline UTC: `2026-07-17T03:59:00Z`
- Official deadline: July 16, 2026 at 11:59 PM Eastern Time
- Days to close from scan date: `-1`
- Deadline bucket: `past_due`
- Command: `EXPIRED_NO_SUBMISSION`
- Eligibility: `SMALL_BUSINESS_ELIGIBLE`
- Fit: `POTENTIAL_LUMA_SKIN_SUIT_FIT_NOT_YET_EVIDENCED_IN_REPOSITORY`
- Route: Grants.gov Workspace
- Official URL: https://simpler.grants.gov/opportunity/c08bbf7a-563b-4af4-a79b-b1cb7bdd71ad
- Why now: The response deadline passed without a verified transmission receipt. This lane is archival and must not be represented as submitted.
- Today work:
  - Archive the lane as missed; do not imply a submission occurred.
  - Retain reusable public-safe material only for a future verified opportunity.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `4d886add66d033d924c14d134e837b8299a6dc158f28d72fd5ae714d8d63c725`

### 12. USDA-NIFA-KFBMB-32830 - Farm Business Management and Benchmarking Competitive Grants Program

- Source: `Grants.gov / NIFA`
- Agency: `USDA National Institute of Food and Agriculture`
- Deadline UTC: `2026-07-20T21:00:00Z`
- Official deadline: July 20, 2026 at 5:00 PM Eastern Time
- Days to close from scan date: `3`
- Deadline bucket: `seven_day_sprint`
- Command: `AGRICULTURE_PARTNER_AND_DATA_GATE`
- Eligibility: `PRIVATE_ORGANIZATIONS_AND_CORPORATIONS_ELIGIBLE`
- Fit: `BENCHMARKING_METHOD_FIT_FARM_NETWORK_AND_FINBIN_DELIVERY_UNPROVEN`
- Route: Grants.gov Workspace
- Official URL: https://simpler.grants.gov/opportunity/a6c41cc0-e597-45c5-8507-1037d8cf7360
- Secondary URL: https://www.nifa.usda.gov/grants/funding-opportunities/farm-business-management-benchmarking-competitive-grants-program
- Why now: LumenCore's measurement methods are adjacent and private corporations are eligible, but the program requires genuine farm-management delivery, partner associations, outreach, and required farm-data contributions.
- Today work:
  - Extract the mandatory partner, farm-record, outreach, and FINBIN requirements.
  - Stop unless real agriculture partners and qualifying farm records are already available.
- Human gate:
  - Robert confirms qualifying agriculture partners, farm records, and program-delivery capacity.
  - Robert approves the budget, certifications, and final submission.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `634b9e5a632a9076f882734c3e7f275a428c62ae45f197afd81ca9dab73e28be`

### 13. PDR-2600-DC-029Q - Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration

- Source: `Grants.gov / HUD`
- Agency: `Department of Housing and Urban Development`
- Deadline UTC: `2026-07-14T03:59:59Z`
- Official deadline: July 13, 2026 at 11:59:59 PM Eastern Time
- Days to close from scan date: `-4`
- Deadline bucket: `past_due`
- Command: `EXPIRED_NO_SUBMISSION`
- Eligibility: `BUSINESS_ELIGIBILITY_POSSIBLE_PROJECT_CAPACITY_UNPROVEN`
- Fit: `TITLE_MATCH_ONLY_NO_CONSTRUCTION_DEMONSTRATION_EVIDENCE`
- Route: Grants.gov Workspace package if eligibility and demonstration facts are supportable
- Official URL: https://www.grants.gov/search-results-detail/362360
- Why now: The response deadline passed without a verified transmission receipt. This lane is archival and must not be represented as submitted.
- Today work:
  - Archive the lane as missed; do not imply a submission occurred.
  - Retain reusable public-safe material only for a future verified opportunity.
- Package files:
  - `HUD_ROBOTICS_AI_EMERGENCY_ELIGIBILITY_GATE_2026-07-11.md`
  - `NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-11.md`
  - `FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md`
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `64d3ec0c4e1a8444321e2d1b32f7cf6923b466959f58acecd5dd3c99be120679`

### 14. 693JJ3-26-BAA-0004 - Intersection Safety Systems Prototyping

- Source: `SAM.gov`
- Agency: `Federal Highway Administration`
- Deadline UTC: `2026-07-20T19:00:00Z`
- Official deadline: July 20, 2026 at 3:00 PM Eastern Time
- Days to close from scan date: `3`
- Deadline bucket: `seven_day_sprint`
- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Eligibility: `OPEN_BAA_TEAM_COMPOSITION_REQUIRED`
- Fit: `STRONG_MEASUREMENT_FIT_TESTBED_AND_PUBLIC_SECTOR_PARTNERS_MISSING`
- Route: Email proposal per the BAA instructions
- Official URL: https://sam.gov/opp/a08fe6151b524fbd87e4c7ce8f6a4abb/view
- Why now: The measurement and data-fusion problem is relevant, but a compliant team needs a lead system developer, an access-controlled roadway testbed, and a public-sector partner with jurisdictional authority.
- Today work:
  - Treat as a teaming lane, not a solo proposal.
  - Stage a bounded validation work-package only if qualified partners are already identified.
- Human gate:
  - Qualified lead, testbed, and public-sector partners confirm participation.
  - Robert approves role, price, representations, and final proposal.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `d29276d0c312541ad18fa827415e3bc2dd70f924219d2c6eab27e9770a86e27a`

### 15. 7571TE26R00004 - HHS AI Power User Advanced Models and Features Pilot

- Source: `SAM.gov`
- Agency: `Department of Health and Human Services`
- Deadline UTC: `2026-07-14T21:00:00Z`
- Official deadline: July 14, 2026 at 5:00 PM Eastern Time
- Days to close from scan date: `-3`
- Deadline bucket: `past_due`
- Command: `PARTNER_OR_NO_BID`
- Eligibility: `OPEN_SOLICITATION_NO_SET_ASIDE`
- Fit: `THEMATIC_MEASUREMENT_FIT_PRIME_DELIVERY_REQUIREMENTS_NOT_MET`
- Route: SAM.gov solicitation instructions
- Official URL: https://sam.gov/workspace/contract/opp/d60ae511937b410fa6f13473acbae762/view
- Why now: The baselining and auditability language is highly relevant, but the prime must provide an integrated enterprise model-access bundle for up to 1,000 users plus security, administration, reporting, and authorization-path artifacts. LumenCore should not represent that capacity without an eligible platform prime.
- Today work:
  - Do not submit as a solo prime.
  - Preserve the solicitation as market validation for LumenCore's measurement and persistent-validation architecture.
- Human gate:
  - A qualified enterprise AI platform prime requests a documented subcontract role.
  - Robert approves any teaming terms, price, and external response.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `dab0bec8e8779abe1b84a6598da554ac4c214b99300b5f3d2d0e46ad7aeead66`

### 16. 26-508 - TechAccess: AI-Ready America - State/Territory Coordination Hubs

- Source: `NSF / Research.gov`
- Agency: `U.S. National Science Foundation`
- Deadline UTC: `None`
- Official deadline: July 16, 2026 at 5:00 PM submitting organization's local time
- Days to close from scan date: `-1`
- Deadline bucket: `past_due`
- Command: `NO_BID_MISSED_PREREQUISITE`
- Eligibility: `ROUND_ONE_REQUIRED_LOI_DUE_JUNE_16_WAS_MISSED`
- Fit: `STRATEGIC_PARTNER_FIT_WATCH_ROUND_TWO`
- Route: Research.gov or Grants.gov after required Letter of Intent
- Official URL: https://www.nsf.gov/funding/opportunities/techaccess-ai-ready-america/nsf26-508/solicitation
- Why now: Round one cannot be pursued because the required June 16 Letter of Intent deadline passed. The January 15, 2027 round-two deadline remains a legitimate statewide consortium target.
- Today work:
  - Mark round one no-bid; do not waste portal time.
  - Start a round-two partner map with statewide conveners, workforce organizations, universities, and government stakeholders.
- Human gate:
  - Robert approves partner outreach for the round-two consortium.
  - An eligible lead institution and statewide partner structure are confirmed.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `9bc75b58a095626d6d92430406dffea781aef615dc879ec7b778bf834c6640b2`

### 17. HHS-2026-ACF-ACYF-CA-0037 - Predictive Analytics in Child Welfare Demonstration Grants

- Source: `Grants.gov`
- Agency: `Administration for Children and Families`
- Deadline UTC: `2026-07-14T03:59:00Z`
- Official deadline: 2026-07-14T03:59:00Z
- Days to close from scan date: `-4`
- Deadline bucket: `past_due`
- Command: `NO_SOLO_SUBMIT_PARTNER_ONLY`
- Eligibility: `INELIGIBLE_AS_SOLO_SMALL_BUSINESS`
- Fit: `PARTNER_ONLY_CHILD_WELFARE_DOMAIN`
- Route: Partner with eligible public/tribal child-welfare agency only
- Official URL: https://www.grants.gov/search-results-detail/361912
- Why now: The title is relevant, but it is not a safe solo submission lane unless an eligible agency partner controls the application.
- Today work:
  - Do not spend the sprint here unless an eligible agency partner is already available.
  - Keep as a future proof-to-pilot target for predictive analytics ethics and validation.
- Human gate:
  - Eligible agency partner identified and approves participation.
  - Robert approves partner outreach or subrecipient role.
- External send without human: `false`
- Final submit without human: `false`
- Lane SHA-256: `a5287577b8b11fcdce5ced16e5a84d6f4e9b91411498f35ced14a511ca55be5c`

## Submission Boundary

- can_open_pages: `true`
- can_stage_drafts: `true`
- can_fill_nonfinal_routine_fields_after_user_login: `true`
- can_final_submit_without_human: `false`
- must_stop_before:
  - final Grants.gov submit
  - final SAM.gov submit
  - final email send
  - legal certification
  - signature
  - terms acceptance
  - pricing or quote amount
  - claim of agency validation, award, realized savings, or customer ROI

## Source Ledgers

- `sam_rush_board`: `out/ops/sam_rush_submission_board_latest.json` present=`true` sha256=`4c60072e0b0294de5e80f29f3af263c7fb00d07b0767bdf1357bcf84970c720d`
- `grants_ranked`: `out/grants/grants_ranked_v2.json` present=`true` sha256=`acf5df0330e5d281c2c504e943f6ba752516449ff5356d53ca5019b97b48743d`
- `funding_reviewer_zero_friction_pack`: `out/ops/funding_reviewer_zero_friction_pack_latest.json` present=`true` sha256=`9d893142736fde4fd15f834bbf5eb4c579ab8feb886d3cdc54b9f92cfb3acee1`
- `external_submission_receipt`: `grant_submissions/funding_sprint_20260709/EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json` present=`true` sha256=`2dac72c484bb39a6ab5891405c00ad68c66a2d99a5152d0e53ccbe8603fbae01`
- `cdc_engagement_receipt`: `grant_submissions/funding_sprint_20260709/CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json` present=`true` sha256=`292157621b722b1973a1aa55140f08586ab41d07fbe38672b348c73e8a865b78`
- `doj_bop_go_no_go`: `grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md` present=`true` sha256=`bd188bcb6a23f9786ed08dc0717d5e9c93fdd583e830b53983d9c5379850caa0`
- `doj_bop_source_manifest`: `grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json` present=`true` sha256=`0282a6778ecc0c31890b93c1f68ffdb011139086ee640595262b95600df6af46`
- `nsf_project_pitch_portal_fields`: `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md` present=`true` sha256=`d8d64a91508a4bc7eefcfa40afbc3057f03505756ef781fd505c382801274169`
- `nsf_project_pitch_routing_manifest`: `grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json` present=`true` sha256=`ccad75e6650082a067bc37f514f54f489f9dd3f869a6b5c089822f93078acb01`
- `nashville_ec_portal_field_map`: `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md` present=`true` sha256=`63bdfafebade22432a6d1ffc3509c8c5ee1685270144f12cc8124ae483bca017`
- `nashville_ec_application_manifest`: `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json` present=`true` sha256=`cd9501d1a61e248a62329595297592d00593bf0086c87da58e120df43de2ef11`
- `nashville_ec_human_fact_resolution`: `grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json` present=`true` sha256=`998a267a08df9e8923fab1e57740f00f52270228a49417f40da73af4aa6d4d33`
- `launchtn_3686_portal_field_map`: `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md` present=`true` sha256=`0fe19453f1595e4af89109824cb6d3ef58bb8234a199c4dd9c88bf7ad629bafd`
- `launchtn_3686_application_manifest`: `grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json` present=`true` sha256=`16fe4e214430055532f6fb7f57453e0f47daa648ee3e3b92b6050e17c98e3dc8`
- `launchtn_3686_pitch_deck`: `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx` present=`true` sha256=`c607e94d8e072ec9d9f93da0d8c372fd5592b01d2ca3b4f71c0a079417c18a69`
- `launchtn_3686_financial_model`: `grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx` present=`true` sha256=`9da46f8ad94fc53ef561ee33dcfa6df907897caeadf6afbd08fb113fc6887d94`
- `external_engagement_response_register`: `grant_submissions/funding_sprint_20260709/EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json` present=`true` sha256=`8dd5f17d0241c5bd909a085029c87e07761fc13252b124e734fa551814d6a037`
- `fhwa_partner_outreach_control`: `grant_submissions/funding_sprint_20260709/FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json` present=`true` sha256=`8a6d0b28cc7afd33a376fe4908a99e5ee008795637c4bb995a5519660b5744e4`
- `sam_public_key_rotation_control`: `grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json` present=`true` sha256=`aac20e903a5055e731da65e5e5a82f08d5c34a7288aa6bed4d0ed78c4f0be159`
- `patent_deadline_evidence_control`: `grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json` present=`true` sha256=`096904e114457c56383e495cfad6c6e3d0d31596d6b53e2920099608b2b7519b`
