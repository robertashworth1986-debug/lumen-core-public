# Portal Live Fill Status

Generated local date: `2026-07-06`

Purpose: live handoff for portal work performed with Robert signed in. This note does not contain passwords, MFA codes, API keys, or authority to submit/certify.

## Grants.gov

Status: signed in and inspected.

Observed page: Applicant Center for Robert Ashworth.

Available actions observed:

- Apply Now
- Manage Workspaces
- Check Application Status
- Manage Applicants
- Manage Organization Profile
- Manage Organization Roles

Action taken: read-only inspection only. No workspace was created, edited, uploaded, or submitted.

## NSF TIP / Project Pitch

Status: signed in and NSF Project Pitch draft filled up to the final `Submit` button.

Portal route:

- `SBIR / STTR Project Pitches`
- `Submit New Project Pitch`
- `Submit Project Pitch`

Fields filled:

- Contact/basic details using verified local grant-packet facts.
- Company: `LumenCore`
- Company state: `TN`
- Topic area: `Artificial Intelligence (AI)`
- Fast Track consideration: `No`
- Q10 prior full proposal not awarded: `No`
- Q11 prior NSF SBIR/STTR award: `No`
- Q12 full Phase I proposal currently under review: `No`
- Q13 Technology Innovation pasted from `grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-06-19.md`.
- Q14 Technical Objectives and Challenges pasted from the same packet.
- Q15 Market Opportunity pasted from the same packet.
- Q16 Company and Team pasted from the same packet.
- Q17 How heard about program: `General web search or social media advertisement`.

Portal character counts observed after paste:

| Field | Count | Limit |
| --- | ---: | ---: |
| Technology Innovation | 2,852 | 3,500 |
| Technical Objectives and Challenges | 2,419 | 3,500 |
| Market Opportunity | 1,517 | 1,750 |
| Company and Team | 1,223 | 1,750 |

Stop point: final `Submit` button visible. It has not been clicked by the agent.

Review before submit:

1. Confirm Q10-Q12 answers are factually correct.
2. Confirm the portal account spelling/name issue visible in the account header does not need correction before submission.
3. Confirm no other NSF Project Pitch, open invitation, or full SBIR/STTR Phase I proposal is pending.
4. Robert must personally approve before clicking final `Submit`.

## DARPA BAAT

Status: signed in and inspected.

Observed DICE submission:

- Submission ID: `HR001126S0010-DICE-PA-052`
- Office: `IPTO`
- Type: `Proposal Abstract`
- Status: finalized
- Finalized timestamp visible in BAAT: `2026-06-29 12:19 PM ET`
- Title: `Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives`

Action taken: read-only inspection only. No new BAAT submission was started and no full proposal was opened.

Recommended DARPA next step: do not start the DICE full proposal unless either (a) DARPA invites/allows the next phase under the BAA rules, or (b) Robert explicitly chooses to stage a full-proposal draft and confirms the eligibility/portal path.

## DSIP / DoW SBIR-STTR

Status: signed in far enough to start Small Business Concern registration. Firm registration form is partially filled but not continued.

DSIP registration facts entered:

- UEI: pulled from the local SAM.gov status capture.
- Firm Name: `Robert Ashworth`
- CAGE Code: entered from local SAM.gov status capture.
- Address/City/State/Phone/Website: entered from the local grant packet.
- ZIP+4: completed after USPS lookup/user confirmation as `37214-1120`.

Fields intentionally left for Robert to enter directly in-browser:

- Firm PIN and Confirm Firm PIN — private account/security credential.
- Tax ID — DSIP text says this is required before contract award but not needed to create a firm or start a proposal; do not store in repo/chat.

Current DSIP stop point: `Registration - Small Business Concern (SBC)` page with `Continue` visible. Do not click continue until Robert enters the Firm PIN directly.

Most relevant active Release 3 targets from the local packet queue:

1. `DON26BZ03-NV063` — Anomalous Behavior Detection and Alerting for Congested Maritime Environments.
2. `DON26BZ03-NV065` — Adaptive Sensor Management.
3. `DLA26BZ03-NV011` — Digital Twin of the Organization for Enhanced Mission Readiness.

Observed DSIP schedule for Release 3:

- Pre-release: `2026-06-03`
- Open date: `2026-06-24`
- Close date: `2026-07-22`

Recommended DSIP next step: after Robert enters Firm PIN and the registration continues, inspect whether organization/SBC control number/submitter authority are ready, then start with NV063 HarborSentinel only if DSIP permits a draft without final certification.

## SAM.gov Renewal / Re-Registration / API-Key Lane

Status: SAM.gov workspace tab opened, but the entity workspace returned `401` and requested Login.gov sign-in.

Action taken: navigated to SAM.gov Login.gov sign-in page. No credentials entered.

Known local status from `grant_submissions/SAM_GOV_ENTITY_STATUS_CAPTURE_2026-06-20.md`:

- SAM registration was previously captured as `Active Registration`.
- Purpose: `All Awards`.
- Expiration date: `2026-08-30`.

Urgent next steps after Robert signs into SAM.gov:

1. Open the entity workspace / active registration record.
2. Confirm whether the email is a renewal/re-registration requirement or only an API-key rotation reminder.
3. If renewal/re-registration is required, start the renewal/update workflow but stop before final representations/certifications/submit.
4. If API-key rotation is required, rotate with Robert present and store only in local secret storage, never in committed files.

## Gmail / Outreach Response Lane

Status: Gmail tab opened to a targeted search for LevelUp/Power of the Pitch, Black Dog, SAM.gov, patent/pro bono, EPRI, Incubatenergy, and ORNL responses. Gmail requires sign-in.

Action taken: no email read/sent/moved because sign-in is pending.

Next step after Robert signs into Gmail: inspect only the targeted outreach/funding/portal-response threads, extract action items, and draft replies or complete forms as appropriate. Do not send messages without final approval.

## Patent / Pro Bono IP Counsel Lane

Status: urgent because Robert reports the one-year non-provisional window ends at the end of July 2026.

Verified/opened routes:

- USPTO Patent Pro Bono Program: USPTO states financially under-resourced inventors/small businesses may be matched with volunteer patent attorneys/agents.
- USPTO map routes Tennessee to `Georgia PATENTS`.
- Georgia PATENTS page says applicants should use the `For Inventors` / `apply` path and must do their own prior-art search before placement.
- Vanderbilt IP & Arts Clinic opened as a local Nashville triage/referral route, but the public page emphasizes copyright, trademark, contracts, licensing, and related IP rather than utility patent prosecution.

Immediate patent counsel packet needed before outreach:

1. Provisional application number.
2. Provisional filing receipt PDF.
3. Exact filing date / deadline.
4. Invention summary and current claim draft.
5. Public-disclosure list: GitHub, website, decks, grants, outreach, investor docs.
6. Any co-inventor/contributor list.

## LevelUp / Power of the Pitch Lane

Status: LevelUp application tab remains open. Robert reports a Power of the Pitch Week invitation and a 48-hour completion deadline.

Action needed: use Gmail invitation details to determine whether this is the same funding application, a follow-up form, event registration, or investor-readiness questionnaire. Do not submit until the rendered form is reviewed.

## Live-Breadth Provider Unlock Tabs

Opened or attempted:

- EPA AQS API documentation.
- The Odds API.
- api.data.gov API-key signup.
- BLS Developers.
- NREL developer pages attempted but did not resolve from this browser session.

Next live-breadth action: after immediate portal deadlines are stable, prioritize failed/thin adapters (`EPA_AQS`, `NREL`, `THE_ODDS_API`, and location-blocked `BINANCE_PUBLIC`) and update only local secret/env storage for new keys.

## Global Boundary

No final submit, certification, upload-finalization, representation, or signature action is authorized by this note. The safe working mode is: fill draft fields, review rendered portal summary, stop, and let Robert approve the final submit action.
