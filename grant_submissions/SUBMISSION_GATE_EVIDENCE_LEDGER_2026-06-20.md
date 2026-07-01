# Submission Gate Evidence Ledger

Generated: 2026-06-20

Status: local grant-operations ledger. This file does not authorize upload,
certification, consent, or submission.

## Purpose

This ledger converts the remaining grant blockers into evidence gates. A gate is
cleared only when the required fact is verified in the named source and the
evidence can be recorded without exposing passwords, MFA codes, bank data, TIN,
private screenshots, or secrets.

Current machine-readiness posture:

- Top-five local package posture: `LOCAL_READY_PORTAL_BLOCKED`
- Local blockers: 0
- Portal/user blockers: 23
- SAM.gov entity status: active registration recorded in the signed-in
  workspace, expiring 2026-08-30
- Boundary: SAM status does not verify BAAT, DSIP, Grants.gov, Research.gov,
  CMMC/SPRS, Affirming Official authority, cost validity, or final submit
  authority.
- DICE portal status update (2026-06-29): DARPA BAAT accepted and finalized
  the DICE Proposal Abstract as `HR001126S0010-DICE-PA-052`, Proposal ID
  `81177`.

## Universal No-Click Rule

Codex may prepare, inspect, summarize, render, test, and draft. Codex must not
click or trigger any of the following without fresh action-time approval from
the user:

- portal consent;
- upload;
- certification;
- representation;
- signature;
- final save that locks a submission;
- submit;
- payment or money movement;
- SPRS/CMMC score or affirmation entry.

## Priority Gate Order

| Order | Gate | Why it matters | Proof required | Next action after proof |
|---:|---|---|---|---|
| 1 | BAAT authority for DICE | DICE is the cleanest near-term federal research fit. | BAAT organization exists, user account works, user has submitter authority, DICE opportunity is visible, required upload format is known. | Open DICE package preview path; keep working-draft warning until final approval. |
| 2 | DICE final human review | Local DICE file hygiene is strong, but reviewer/cost/signoff gates remain. | Human confirms reference relevance, Heilmeier matrix, ROM cost boundary, 7-page render, and final upload preview. | Only then consider removing working-draft warning and preparing upload. |
| 3 | DSIP authority for Harbor/NV065/MissionWeave | Navy/DLA packages cannot move without organization linkage and submitter role. | DSIP organization is linked, topic visible, user role allows submission, volume upload requirements and budget fields are visible. | Preview Harbor Volume 2 and capture non-secret required-field checklist. |
| 4 | Harbor compliance representations | Harbor has advanced DoD/security implications. | DoD reps, U.S. ownership/operation, FOCI, export, cybersecurity, CMMC/SPRS/Affirming Official status verified or explicitly marked unknown. | Fill only factual representations; do not infer compliance. |
| 5 | Harbor cost basis review | Current Base/Option numbers are ROM planning values. | Direct labor, fringe, indirect, travel, cloud/HPC, consultant/subcontract, and fee assumptions reviewed. | Preserve ROM wording or replace with reviewed cost language. |
| 6 | Harbor domain/team signoff | The Navy reviewer matrix improves clarity but is not domain approval. | A credible Navy/maritime/sensor/domain reviewer or collaborator reviews approach and boundaries. | Record signoff summary; do not imply endorsement unless written. |
| 7 | NSF pitch paste check | Lowest portal burden and fastest possible traction path. | Legal name, PI/title, duplicate-pitch status, field paste counts, and final action-time approval verified. | Submit only if the portal state allows it and user approves. |
| 8 | CMMC/SPRS readiness support | DoD submissions may need accurate cybersecurity representations. | PIEE/SPRS access, Cyber Vendor User role, CAGE hierarchy, AO status, current score/status, or no-current-status explicitly documented. | Seek APEX/Project Spectrum/qualified CMMC advisor support before any claim. |

## DICE Gate Detail

| Gate | Evidence source | Clear when | Current status |
|---|---|---|---|
| BAAT account access | DARPA BAAT portal | User can log in without unresolved consent/account issue. | Verified for DICE finalization on 2026-06-29. |
| Organization profile | BAAT portal | Organization exists and is associated with user. | Verified enough for BAAT to create/finalize Proposal ID `81177`; broader organization/compliance representations remain separate gates. |
| Submitter authority | BAAT portal | User role allows abstract upload/submission. | Verified for this DICE abstract because BAAT accepted finalization after user action-time approval. |
| Opportunity access | BAAT portal | DICE HR001126S0010 is visible in the submission workflow. | Verified; workflow produced `HR001126S0010-DICE-PA-052`. |
| Final upload preview | BAAT or Word/portal preview | Latest DOCX/PDF renders as expected; no template or page-limit problem. | Portal accepted `LumenCore_DICE_Abstract_PORTAL_UPLOAD_FLATDOCX.zip` and allowed finalization. |
| Reference relevance | `DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md` | User/human reviewer confirms each reference supports adjacent claim. | Preliminary matrix exists; final signoff required. |
| Heilmeier/reviewer answers | `DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md` | User/human reviewer accepts wording and boundaries. | Matrix exists; final signoff required. |
| Cost boundary | `DICE_COST_BASIS_WORKING.md` | ROM planning language remains visible or reviewed cost basis replaces it. | ROM only. |
| Action-time approval | User approval at moment of action | User explicitly approves upload/certification/submit action. | Cleared for DICE finalization only: user instructed `finalize DICE now` immediately before action. |

## DICE Finalization Record - 2026-06-29

- Portal: DARPA BAAT
- Opportunity: DICE / `HR001126S0010`
- Submission type: Proposal Abstract
- Proposal ID: `81177`
- Submission identifier: `HR001126S0010-DICE-PA-052`
- Uploaded file accepted before finalization:
  `LumenCore_DICE_Abstract_PORTAL_UPLOAD_FLATDOCX.zip`
- Portal final URL:
  `https://baa.darpa.mil/submission/Success?SubmissionIdentifier=HR001126S0010-DICE-PA-052&SubmissionType=Proposal%20Abstract&ProposalID=81177`
- Portal success state observed: finalized; no further user action required by
  the portal for this abstract.
- Confirmation screenshot:
  `C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops\darpa_dice_finalized_20260629T162305Z.png`
- Boundary: this proves BAAT portal upload/finalization for the DICE Proposal
  Abstract. It does not prove award selection, review outcome, field validation,
  realized dollar savings, DICE metric attainment, or any fixed value per frozen
  delta.

## HarborSentinel Gate Detail

| Gate | Evidence source | Clear when | Current status |
|---|---|---|---|
| DSIP account access | DSIP portal | User can log in and topic/release is visible. | Unverified. |
| Organization linkage | DSIP portal | Organization is linked to user and correct entity. | Unverified. |
| Submitter authority | DSIP portal | User role allows package upload/submission. | Unverified. |
| Required forms/volumes | DSIP portal | Required fields, file types, names, and page limits are known. | Unverified. |
| Latest local render | `render_qa_20260620_baselines_v1/` | Six-page PDF and six page PNGs inspected with no visible defects after the stronger-baseline update. | Passed locally. |
| Public AIS evidence | `NV063_AIS_*` artifacts and public proof packet | Raw hash, splits, I/O preflight, split cache, and controlled-injection benchmark are recorded. | Present. |
| Navy reviewer matrix | `NV063_NAVY_REVIEWER_PROOF_MATRIX_2026-06-20.md` | Human/domain reviewer accepts evidence, objections, and no-claim boundaries. | Matrix exists; signoff required. |
| DoD representations | DSIP/SAM/company records | U.S. ownership/operation, FOCI, export, cybersecurity, and required reps are factual. | Unverified. |
| CMMC/SPRS/AO | PIEE/SPRS and CMMC readiness records | Current role/status/score/affirming official fact is known or accurately marked absent. | Unverified. |
| Cost basis | `NV063_COST_BASIS_WORKING.md` plus reviewer notes | ROM is reviewed or preserved as planning estimate. | ROM only. |
| Clearance transition | Proposal text plus advisor/domain review | Advanced-phase Secret facility/personnel path is credible and bounded. | Unverified. |
| Action-time approval | User approval at moment of action | User explicitly approves upload/certification/submit action. | Required. |

## Evidence That Is Strong Now

- DICE local package lock exists with render, URL, cost-boundary, reference, and
  reviewer-answer artifacts.
- HarborSentinel latest Volume 2 render packet has six-page PDF and six page
  PNGs after the public AIS injection update.
- HarborSentinel public AIS raw acquisition, held-out split, I/O preflight,
  local split cache, and controlled-injection benchmark exist.
- Public repo now has sanitized reviewer traction, Harbor proof packet, and
  corrected claim-boundary copy.

## Evidence That Is Still Missing

- BAAT submitter authority.
- DSIP organization linkage and submitter authority.
- Portal upload previews for DICE and Harbor.
- Reviewed cost proposal or explicit decision to preserve ROM language.
- CMMC/SPRS/Affirming Official status.
- FOCI/export/U.S. ownership/operation review.
- Credible Harbor domain/team signoff.
- Any written partner/customer/Navy reviewer endorsement.
- Final action-time approval for any portal upload, certification, or submit.

## How This Moves Toward Funding

The fastest credible path is not to claim the blockers are solved. It is to
show reviewers, collaborators, and portals a package where the evidence is
clean, the boundaries are visible, and the remaining gates are concrete. That
turns the work into something a serious reviewer can help advance instead of
something they must untangle.
