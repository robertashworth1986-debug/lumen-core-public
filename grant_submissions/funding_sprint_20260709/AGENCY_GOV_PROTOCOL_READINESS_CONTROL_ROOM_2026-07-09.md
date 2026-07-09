# Agency And Government Protocol Readiness Control Room - 2026-07-09

Purpose: make LumenCore easier for agency reviewers, contracting officers, SBIR reviewers, and investors to diligence by reducing portal, eligibility, cybersecurity, proof, and claim-boundary friction.

This is a readiness control room, not a certification. It does not claim SAM active status, DSIP authority, CMMC compliance, security clearance, export-control clearance, or award eligibility unless those facts are separately verified by Robert in the official portal.

## Current Strong Position

LumenCore's strongest reviewer posture is:

- proof-to-pilot AI infrastructure validation;
- source provenance and evidence manifests;
- baseline-vs-candidate replay;
- reviewer-safe proof cards;
- domain translation into SBIR/RFI/BAA/CSO packets;
- strict claim boundaries.

The goal is to make funding LumenCore easy because the reviewer sees:

1. the opportunity fit;
2. the exact source and deadline;
3. the proof packet;
4. the claim boundary;
5. the portal gate;
6. the next validation step.

## Official Protocol Anchors

### SAM.gov

Official source:

- https://sam.gov/entity-registration

Current protocol facts to preserve:

- SAM.gov says registration is for organizations that want to directly bid on government contracts and apply for federal assistance.
- SAM.gov says a Unique Entity ID is assigned during registration.
- SAM.gov says registrations must be renewed every 365 days to stay active.
- SAM.gov says registration can take up to 10 business days to become active.

LumenCore gate:

- Robert must verify legal business name, active registration, UEI, CAGE if assigned, expiration/renewal date, entity POCs, bank/payment data, assertions, and reps/certs directly in SAM.gov.

Reviewer-safe wording:

- "Entity registration, UEI/CAGE, and reps/certs are treated as official-portal gates and are not represented from local files alone."

### DoW / DoD SBIR-STTR / DSIP

Official source:

- https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/

Current protocol facts to preserve:

- DoW SBIR/STTR proposals must be submitted electronically through DSIP.
- Proposals must respond to an open topic under an active BAA or CSO.
- DoW SBIR/STTR does not accept unsolicited proposals.
- Firms are advised to register early and submit early to avoid portal delays.
- During open periods, direct topic-author communication stops; Topic Q&A becomes the official written channel.

LumenCore gate:

- DSIP Firm PIN, Small Business Concern registration, submitter authority, organization linkage, topic forms, cost volume, certifications, upload preview, and final submit remain human-gated.

Reviewer-safe wording:

- "LumenCore will submit DoW SBIR/STTR material only through DSIP and only after Robert reviews the final certifications, upload preview, and cost package."

### NSF SBIR/STTR

Official source:

- https://seedfund.nsf.gov/project-pitch/

Current protocol facts to preserve:

- NSF requires a Project Pitch before a Phase I full proposal.
- A good-fit Project Pitch receives an official invitation to submit a full proposal.
- The pitch has four sections: technology innovation, technical objectives/challenges, market opportunity, and company/team.
- A small business can only submit one Project Pitch at a time and must wait for a response if a pitch is pending.

LumenCore gate:

- NSF login, pending-pitch status, invitation status, PI/company eligibility, and Research.gov proposal readiness must be verified before final submission.

Reviewer-safe wording:

- "NSF full proposal work remains invitation-gated; LumenCore is staging Project Pitch and evidence materials without representing an invitation unless NSF has issued one."

### CMMC / FCI / CUI

Official sources:

- https://dodcio.defense.gov/CMMC/
- https://dodcio.defense.gov/cmmc/About/

Current protocol facts to preserve:

- CMMC Phase 1 implementation began November 10, 2025 and runs through November 9, 2026.
- Phase 1 focuses primarily on CMMC Level 1 and Level 2 self-assessments.
- CMMC assessment requirements protect Federal Contract Information and Controlled Unclassified Information.
- Contractors and subcontractors entrusted with FCI or CUI must achieve a specified CMMC level as a condition of contract award.
- CMMC assessments require affirmations in SPRS.

LumenCore gate:

- Do not claim CMMC status, SPRS score, CUI handling, FCI/CUI processing, facility clearance, personnel clearance, export authorization, or foreign ownership/control/influence status unless official records support it.

Reviewer-safe wording:

- "Current proposal material is handled as Unclassified and non-CUI unless an authorized source marks otherwise. If awarded work requires FCI/CUI, LumenCore will isolate federal work in a scoped enclave and submit only evidence-supported cybersecurity representations."

### USPTO / IP

Official sources:

- https://www.uspto.gov/patents/basics/apply/provisional-application
- https://www.uspto.gov/patents/basics/apply/utility-patent
- https://www.uspto.gov/subscription-center/2023/connecting-eligible-inventors-and-entrepreneurs-free-legal-assistance

Current protocol facts to preserve:

- USPTO says a provisional application has a 12-month pendency from filing.
- A corresponding nonprovisional must be filed during that period to benefit from the earlier provisional filing date.
- Provisional applications are not examined and cannot become patents by themselves.
- USPTO recommends consulting a registered attorney or agent.
- USPTO describes the Patent Pro Bono Program as a network matching eligible under-resourced inventors and small businesses with volunteer patent professionals.

LumenCore gate:

- Exact provisional filing date, application number, inventor list, public disclosure list, claim support, assignment, and counsel review remain required before any strong patent-rights language.

Reviewer-safe wording:

- "LumenCore has invention-family and evidence artifacts that may support patent strategy, but no granted patent, claim scope, or freedom-to-operate position is represented unless verified by counsel and official records."

## Reviewer-Ready Control Map

| Lane | Current Value | Gate | Evidence To Attach |
| --- | --- | --- | --- |
| Air Force AAC RFI | Fast market-research traction | SAM instructions, address, page limit | `AIR_FORCE_AAC_RFI_CAPABILITY_STATEMENT_2026-07-09.md` |
| NASA Data Center RFI | High-density compute / AI ops fit | SAM attachments and format | `NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md` |
| DSIP MissionWeave | Cleanest July 22 software SBIR lane | Firm PIN, DSIP registration, certs, cost | `DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md` |
| FHWA TSMO | Strongest near-term contract-fit lane | SAM package and compliance matrix | `FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md` |
| Nuclear cost-share | Still open, partner-first | Qualified nuclear/licensing applicant and cost-share | `NUCLEAR_LICENSING_EVIDENCE_PARTNER_ONE_PAGER_2026-07-09.md` |
| NSF SBIR/STTR | Strong non-dilutive fit | Project Pitch invite and one-pending-pitch rule | `NSF_PROJECT_PITCH_DRAFT_2026-07-09.md` |

## Government-Ready Evidence Stack

Every agency-facing packet should include:

1. Opportunity source URL and deadline.
2. Fit paragraph.
3. Work LumenCore can truthfully perform.
4. Proof gateway link.
5. Bounded evidence posture.
6. Claim boundary.
7. Portal gate.
8. Cyber/data handling statement.
9. IP/disclosure boundary.
10. Next validation ask.

## Minimum Agency Submission Gate

Do not final-submit any government package until these are checked:

- official portal access;
- legal entity and submitter authority;
- deadline and time zone;
- format/page/attachment rules;
- cost/price volume requirements;
- reps/certs and signature authority;
- FCI/CUI/export/FOCI/security clearance implications;
- IP/disclosure risk;
- proof packet is public-safe;
- no raw credentials, logs, private keys, or unreviewed archives are attached.

## Traction Protocol

For every outreach, RFI, SBIR, grant, investor, or partner touch:

1. Create or update the opportunity file.
2. Attach the proof gateway only if it is relevant and public-safe.
3. Capture the sent email, portal confirmation, calendar booking, or reply as a receipt.
4. Add the receipt to the E-drive proof vault.
5. Hash the receipt and packet.
6. Record the next action date.
7. Promote the claim level only when external evidence supports it.

## Highest-Leverage Next Actions

1. Finalize/send Air Force AAC RFI if SAM instructions are simple.
2. Build NASA RFI into final PDF.
3. Clear DSIP Firm PIN and start MissionWeave.
4. Build FHWA TSMO compliance matrix.
5. Send nuclear one-pager only to qualified reactor/licensing/utility partners.
6. Locate patent filing receipt and exact provisional date.
7. Build a small federal-work enclave plan before any FCI/CUI work.
