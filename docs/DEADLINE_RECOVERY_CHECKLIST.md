# Deadline Recovery Checklist

Updated: July 16, 2026 (America/Chicago)

## Immediate Priority

### 1. USPTO

Verified evidence:

- The local official record set contains six source files and five unique
  hashes. Every item is a view or copy of the same payment acknowledgement.
- The acknowledgement identifies a utility nonprovisional submission and a
  basic filing-fee payment. It is not a Filing Receipt, Office Action, OPAP
  notice, or current-status record.
- The acknowledgement does not verify a granted filing date, claims in the
  official file, completeness, current pendency, or absence of an outstanding
  notice.
- No local Filing Receipt, Office Action, notice of missing parts, abandonment
  notice, or response deadline was found. A bounded Gmail search also found no
  official USPTO correspondence for the application.

Required action:

1. Sign in to Patent Center.
2. Open the application and download the Filing Receipt, application data and
   current status, all outgoing correspondence, submitted-document list, fee
   payment history, and transaction history.
3. Identify the newest USPTO notice and its mailing date.
4. Record the response period and extension language stated in that notice.
5. Verify whether the official file contains the specification, claims,
   abstract, drawings, ADS, oath or declaration, and all required fees.
6. Have a registered patent practitioner review any substantive response and
   any foreign or PCT priority strategy.

Do not calculate a U.S. prosecution response deadline from a filing
anniversary. The controlling date, if a response is due, will be in the
relevant USPTO notice. Foreign or PCT priority is a separate, potentially
time-sensitive question; do not assume either preservation or restoration.

Status: `PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED`

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

Current path: Project Pitch.

Required action:

1. Complete the Project Pitch with specific customer problem, innovation,
   technical risk, market, team, and company impact.
2. Run the grant preflight and remove every placeholder.
3. Submit the pitch after final human review.
4. If invited, prepare the full proposal against the earliest feasible
   deadline.

Known full-proposal deadlines:

- July 27, 2026
- November 4, 2026
- March 4, 2027

The full proposal requires an invitation and active SAM registration.

Status: `ACTIONABLE_NOW`

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
