# LumenCore Portal and Compliance Action Matrix

Date: June 19, 2026

Purpose: keep the five-package grant push moving through the correct portals
without treating accounts, certifications, security status, partners, or
submission authority as solved before the user verifies them.

This is a planning matrix, not legal advice, an assessment, a certification
representation, or authorization to submit.

Safe portal fact-capture worksheet:
`grant_submissions/PORTAL_USER_GATE_CAPTURE_WORKSHEET_2026-06-20.md`

## Official Source Checks

Checked on June 19, 2026; rechecked for current-source consistency on
June 20, 2026 UTC:

| Area | Official source | Decision impact |
|---|---|---|
| SAM registration | `https://sam.gov/entity-registration` | A prime applicant needs active registration to bid/apply for federal awards; SAM assigns the Unique Entity ID, and existing registrations must be renewed every 365 days. |
| DSIP submissions | `https://www.dodsbirsttr.mil/submissions/` | Navy and DLA SBIR/STTR packages should be handled through DSIP, not Grants.gov workspaces. |
| DARPA BAAT | `https://baa.darpa.mil/` | DICE abstract/proposal work belongs in DARPA BAAT; login/consent and submission controls require user action-time approval. |
| DARPA DICE program page | `https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence` | Confirms the HR001126S0010 DICE opportunity family and BAAT path. The local official BAA/PDF remains the controlling artifact for exact abstract/package instructions before upload. |
| NSF Project Pitch | `https://seedfund.nsf.gov/apply/project-pitch/` | The NSF path starts with a Project Pitch covering technology innovation, technical objectives/challenges, market opportunity, and company/team. An invitation does not imply Phase I funding. |
| SPRS CMMC | `https://www.sprs.csd.disa.mil/cmmc.htm` | SPRS is the place for vendors to enter and affirm CMMC Level 1 and Level 2 compliance, accessed through PIEE. |
| SPRS Level 2 quick-entry guide | `https://www.sprs.csd.disa.mil/pdf/CMMCL2SelfQuickEntryGuide.pdf` | Level 2 self-assessment entry requires PIEE/SPRS Cyber Vendor User access, assessment scope, employee count, included CAGEs, and SAM-imported CAGE hierarchy; conditional Level 2 self-assessment is score 88-109 and final is 110. |
| SPRS Affirming Official tutorial | `https://www.sprs.csd.disa.mil/pdf/training/AffirmingOfficialTutorialforCMMC-Transcript.pdf` | The AO must be authorized to affirm continuing compliance, needs PIEE/SPRS access, and must certify the affirmation statement personally. |
| CMMC regulation | eCFR Title 32 Part 170, latest available issue date checked: June 17, 2026 | Section 170.16 covers Level 2 self-assessment and SPRS submission; section 170.17 covers Level 2 C3PAO certification assessment and eMASS/SPRS transmission. |

DoD CIO's public CMMC documentation page is still a relevant user-openable
reference (`https://dodcio.defense.gov/CMMC/Documentation/`), but the site
returned HTTP 403 to automated fetch from this environment. Use SPRS/eCFR for
machine-checked language and the DoD CIO page for manual document downloads.

## Portal Map

| Package | Primary portal | Use Grants.gov? | Current portal posture |
|---|---|---|---|
| DARPA DICE HR001126S0010 | DARPA BAAT | No, except discovery/reference | Do not upload until BAAT organization access, final portal/Word preview, reference-relevance review, preserved ROM cost wording, and human approval clear. |
| Navy NV063 HarborSentinel | DSIP | No | Do not upload before the Navy/DLA window opens and DSIP organization linkage, compliance, cost, representative-data, clearance-transition, and portal-preview gates clear. |
| NSF SBIR Project Pitch | NSF Seed Fund Project Pitch portal | No at pitch stage | Fastest paste-check path after legal name, PI/title, duplicate-pitch status, and final character-count confirmation. |
| DLA NV011 MissionWeave | DSIP | No | Hold until one bounded unclassified process and DSIP budget/form requirements are confirmed. |
| Navy NV065 Adaptive Sensor Management | DSIP | No | Hold until representative radar-resource assumptions, sensor-domain review, cost review, and compliance gates clear. |
| HUD PDR-2600-DC-029Q draft | Grants.gov | Yes | Deprioritize unless a real housing/manufacturing/robotics demonstration partner and site are secured. |

## Entity And Account Data To Capture

Capture only non-sensitive status facts while the user is logged in. Do not
record passwords, one-time codes, API keys, banking information, tax forms, or
private portal screenshots containing secrets.

Use `grant_submissions/PORTAL_USER_GATE_CAPTURE_WORKSHEET_2026-06-20.md` as
the live checklist during SAM, BAAT, DSIP, NSF, and SPRS/PIEE portal review.
Use `grant_submissions/SUBMISSION_GATE_EVIDENCE_LEDGER_2026-06-20.md` as the
evidence-gate source of truth for what clears each blocker.
Use `grant_submissions/ACTION_TIME_SUBMISSION_BOARD_2026-06-20.md` as the
current live-session order of operations before opening BAAT, DSIP, NSF,
PIEE/SPRS, or any submission portal.

| Gate | Record | Do not record |
|---|---|---|
| SAM.gov | Legal business name, UEI, CAGE if assigned, active/inactive status, expiration date, entity administrator status. | Login credentials, TIN/EIN screenshots, banking details, full address screenshots unless the user explicitly chooses to save them. |
| BAAT | Whether the organization exists, whether the user has submitter authority, DICE opportunity access, allowed file types, required fields. | Passwords, MFA codes, private profile data unrelated to submission. |
| DSIP | Whether the organization is linked, user role, submitter authority, release/topic visibility, required volumes, budget ceilings, form status. | Passwords, MFA codes, private account tokens. |
| NSF | Account identity, company name, PI/founder consistency, duplicate-pitch status, field limits, paste-count result. | Passwords, MFA codes, personal identifiers beyond what the application requires. |
| SPRS/PIEE | Whether PIEE/SPRS access exists, Cyber Vendor User role status, CAGE hierarchy, Affirming Official identity/status, whether any score/status/UID is already recorded, and affirmation expiration if shown. | Passwords, MFA codes, control evidence screenshots unless a CMMC advisor confirms storage boundaries. |

## CMMC And Security Path

The current grant drafts and synthetic benchmark evidence should remain
Unclassified and non-CUI unless an authorized source marks material otherwise.

| Topic | Current safe posture | Action before DoD submission |
|---|---|---|
| DICE | Abstract proposes unclassified research and does not require current CUI handling in the draft. | Keep CUI out of the abstract and supporting files; do not claim CMMC status unless actually recorded. |
| NV063 HarborSentinel | Navy instructions identify projected CMMC Level 2 (Self); advanced phases may involve classified work. | Prepare Level 2 self-assessment/SPRS path, CUI enclave plan, and clearance transition narrative without claiming certification. |
| NV065 Adaptive Sensor Management | Same DoD/Navy compliance posture: likely FCI/CUI sensitivity if awarded, but current draft evidence is synthetic/unclassified. | Use the enclave plan; verify DSIP-specific reps; avoid classified radar-performance claims. |
| MissionWeave | DLA SBIR package should assume DoD cybersecurity representations may apply. | Confirm DSIP topic instructions and whether Level 1, Level 2 Self, Level 2 C3PAO, export, or EJCP requirements apply. |
| Public repo evidence | Public-safe synthetic benchmarks and scorecards only. | Keep CUI, proprietary portal forms, private business data, secrets, and unreviewed partner details out of public GitHub. |
| Trading/dashboard evidence | Treat current Kraken/dashboard/live-breadth work as fail-closed software-governance evidence only. | Do not cite trading profit, institutional trading readiness, account value, or frozen-delta dollar value in federal proposals unless independently verified, reproducible, legally reviewable, and separated from live-money credentials. |

Level 2 (Self) is not the same as Level 2 (C3PAO). For Level 2 (Self), the
organization performs the assessment and submits results in SPRS. For Level 2
(C3PAO), an authorized/accredited third party performs the certification
assessment and results transmit through the CMMC system path. Do not represent
either status until the required assessment, scope, score/status, and
affirmation are actually current.

SPRS quick-entry guidance shows CMMC Level 2 Conditional Self-Assessment at
scores 88-109 and Final Self-Assessment at 110. Conditional status is time-
limited and depends on POA&M eligibility; final status requires annual
affirmations during the three-year validity period. Do not enter, transfer, or
affirm any score/status unless the underlying evidence supports it and the
company's Affirming Official personally approves it.

## Claims And Evidence Boundary

Use strong evidence, but name it honestly.

| Evidence family | Can support | Cannot support yet |
|---|---|---|
| DICE constraint-contract run | Bounded synthetic evidence for role-shuffle, collusion, abstention, and contract-check behavior. | Operational distributed consensus performance or universal superiority claims. |
| HarborSentinel v5 run | Bounded synthetic evidence for multi-source quality gates, contradiction handling, confidence, and abstention behavior. | SSDS integration, field harbor performance, classified performance, or certified operational readiness. |
| MissionWeave run | Generated-workflow evidence for constraint-aware mission process simulation. | Any named agency process result without representative data and domain review. |
| NV065 run | Synthetic constrained sensor-tasking evidence for marginal contribution, release gates, and human review boundaries. | Real radar/sensor performance, classified resource behavior, or combat-system integration. |
| NSF pitch fields | Clear commercial/technical narrative for trustworthy AI orchestration. | A full NSF award, clinical/medical outcome, trading profit, or government endorsement. |

## Package Action Matrix

| Rank | Package | Submit path | Next user-only gate | Next Codex-safe work |
|---:|---|---|---|---|
| 1 | DICE | BAAT | Confirm BAAT account, organization profile, submitter authority, and fresh approval before upload. | Keep DOCX warning, optionally preview in Word/BAAT after local 7-page render QA, review reference relevance, and preserve ROM cost/evidence boundaries. |
| 2 | NSF Project Pitch | NSF Project Pitch portal | Confirm legal company name, PI/founder title, duplicate-pitch status, and portal paste counts. | Paste-check fields with user control, keep within field limits, and avoid universal harmonic/trading claims. |
| 3 | HarborSentinel | DSIP | Confirm DSIP organization linkage, submitter authority, CMMC/FOCI/export reps, and cost/budget fields after window opens. | Execute representative-data plan, check the generated 6-page Volume 2 DOCX in the DSIP upload preview, and keep synthetic evidence clearly labeled. |
| 4 | MissionWeave | DSIP | Confirm DSIP topic budget/form requirements and choose one bounded process the user can defend. | Add representative process assumptions, then freeze a smaller process-specific evidence packet. |
| 5 | NV065 | DSIP | Confirm DSIP access, topic requirements, and sensor-domain review path. | Define unclassified representative radar-resource assumptions and extend tests for covariance, latency, and measurement cost. |

## Do-Not-Click Controls

Codex can navigate, read, draft, compare, and help paste after the user logs in.
Codex must not click any of the following without fresh action-time approval:

- Submit
- Certify
- Sign
- Agree
- Consent
- Upload final application
- Lock workspace
- Enter or affirm SPRS/CMMC score or status
- Invite/add a collaborator as committed
- Save a representation that the user has not personally verified

## 48-Hour Action Order

1. Paste-check the NSF Project Pitch first, because it has the lowest portal
   friction and does not need a demo site at pitch stage.
2. Finish BAAT account verification and optional BAAT/Word preview for DICE
   next, because local DOCX render QA has passed and the abstract deadline is
   near.
3. Prepare DSIP account verification for NV063, NV065, and MissionWeave.
4. For NV063, execute the representative AIS/ADS-B/notional-radar data plan
   and verify the final DSIP attachment preview before submission.
5. For NV065 and MissionWeave, add one more bounded, topic-specific assumption
   sheet before any upload.
6. Treat the HUD Grants.gov draft as reserve only until a real demonstration
   partner and site exist.

## Working Decision

The grant push is credible only if portal authority and compliance claims stay
strictly factual. The fastest credible movement is NSF pitch first, DICE
second, then DSIP packages after account/compliance verification and final
format conversion. The system should optimize for submission quality, not raw
submission count.
