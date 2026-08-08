# Deadline Recovery Checklist

Updated: July 27, 2026 (America/Chicago)

## Immediate Priority

### 1. USPTO

Verified evidence:

- A utility nonprovisional application was filed and paid on July 25, 2025.
- The local screenshots are payment/application receipts, not deadline notices.
- No local Office Action, notice of missing parts, or response deadline was
  found.

Required action:

1. Sign in to Patent Center.
2. Open the application and download the complete correspondence history.
3. Identify the newest USPTO notice and its mailing date.
4. Record the statutory response period and whether extensions are permitted.
5. Have a registered patent practitioner review any substantive response.

Do not calculate an extension from July 25, 2025. The controlling date, if a
response is due, will be in the relevant USPTO notice.

Status: `BLOCKED_ON_AUTHENTICATED_CORRESPONDENCE`

### 2. SAM.gov, UEI, And CAGE

Verified evidence:

- A local SAM application pack was created November 4, 2025.
- The pack contains UEI/CAGE identifiers but no registration expiration date.
- SAM registrations must be renewed every 365 days.
- SAM advises allowing up to 10 business days for activation.

Required action:

1. Sign in to SAM.gov and open the entity record.
2. Record the exact registration expiration date and current status.
3. Start renewal immediately if the record is inactive or within 60 days of
   expiration.
4. Verify legal business name, physical address, banking, representations and
   certifications, points of contact, UEI, and CAGE data.
5. Save the confirmation and activation notice in a dedicated compliance
   folder.

Status: `BLOCKED_ON_AUTHENTICATED_ENTITY_RECORD`

### 3. NSF SBIR/STTR

Current path: Project Pitch for the next full-proposal cycle.

Verified July 27 reconciliation:

- NSF 26-510 requires an official Project Pitch invitation for a Phase I or
  Fast-Track full proposal.
- No official invitation was found in the full-mailbox audit.
- The July 27 full-proposal route is therefore closed by eligibility, not by
  document quality.

Required action:

1. Select one bounded research lane and prepare a truthful Project Pitch.
2. Run the grant preflight and remove every placeholder.
3. Submit the pitch only after final human review.
4. If invited, prepare the full proposal for the earliest deadline covered by
   the invitation.

Known full-proposal deadlines:

- July 27, 2026
- November 4, 2026
- March 4, 2027

The full proposal requires an invitation and active SAM registration.

Status: `TARGET_NEXT_CYCLE_BLOCKED_NO_INVITATION`

## Grant Queue Rules

- Do not submit the 98 quarantined stale approvals without revalidation.
- DOE FY2026 Release 2 closed February 25, 2026.
- NIST currently has no verified open Phase I NOFO in the local catalog.
- Preserve the 673-series benchmark, but use the measured 2,586-dataset breadth
  when describing current evidence coverage.
- Never submit an application with generic placeholders, unsupported metrics,
  or an agency/program mismatch.

## Browser-Assisted Submission

The Codex in-app browser could not start because of a Windows process-permission
failure. Once browser control is available, the safe workflow is:

1. The user signs in directly.
2. Luma reads the page and prepares field values.
3. The user reviews identity, certifications, budget, and legal attestations.
4. Luma may populate reversible fields.
5. The user confirms before final submission or payment.

## Credential Recovery

- Rotate exchange and OpenAI credentials previously stored in plaintext.
- Move active secrets to environment variables or a secret manager.
- Disable withdrawal on exchange API keys.
- Do not place secret values in grant bundles, logs, screenshots, or the repo.
