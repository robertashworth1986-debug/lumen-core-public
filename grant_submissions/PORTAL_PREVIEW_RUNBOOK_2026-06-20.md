# Portal Preview Runbook

Generated UTC: 2026-06-24T19:22:41.139497+00:00

Freeze signature SHA-256: `939488dcb852201276d806b11f65fa7c198e87e8c3882707cd7723ea7d72f609`
Ready for upload or submit: False

## No-Click Rule

Stop before upload finalization, certification, consent, signature, workspace lock, or submit. Fresh action-time approval is required for each such action.

## Do Not Capture

- passwords
- MFA or one-time codes
- API keys or private tokens
- TIN/EIN or banking details
- private profile screenshots containing sensitive account data

## Portal Runbooks

### DICE (DARPA BAAT)

- URL: https://baa.darpa.mil/
- Opportunity/topic hint: `DICE / HR001126S0010`
- Preview goal: Confirm BAAT organization association, submitter authority, DICE opportunity visibility, accepted file type, and upload-preview rendering.
- Ready for preview: True
- Ready for upload or submit: False
- Stop before: BAAT consent, certification, final upload, submission, or any action that locks the workspace.
- Portal/user blockers: 6

#### Frozen Upload Candidates

| Role | Path | Bytes | SHA-256 |
|---|---|---:|---|
| upload_candidate_docx | `grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_WORKING_DRAFT.docx` | 33868 | `cf6b3a7dc1ec9930458f42a683c999093b65d9dc43d3e29627404bd586473ee6` |
| render_preview_pdf | `grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/LumenCore_DICE_Abstract_WORKING_DRAFT.pdf` | 154979 | `75acbb223bbb5f9784a11c1b3cc070af40a87044f92a41d03bddb2e54055907d` |

#### Steps

1. Open portal
   - Action: User logs in to DARPA BAAT at https://baa.darpa.mil/. Codex may observe and navigate after login.
   - Capture: Record only login success/failure and whether the expected organization/workspace is visible.
   - Stop if: Portal asks for consent, certification, sensitive profile data, or payment-like information.
2. Verify authority
   - Action: Check organization association and submitter/upload authority for the specific opportunity.
   - Capture: yes/no/unclear for organization linkage, user role, and submitter authority.
   - Stop if: Role is unclear or portal asks to certify authority.
3. Verify opportunity
   - Action: Find opportunity/topic `DICE / HR001126S0010` and record whether it is visible and open for the intended action.
   - Capture: Opportunity visibility, current portal deadline/window text, accepted file types, required sections, and page/size limits.
   - Stop if: Opportunity is not visible, closed, or instructions differ from the local package assumptions.
4. Compare upload candidate
   - Action: Use the frozen upload candidate `grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_WORKING_DRAFT.docx` only if its local SHA-256 still equals `cf6b3a7dc1ec9930458f42a683c999093b65d9dc43d3e29627404bd586473ee6`.
   - Capture: Record whether the portal accepts the file type and whether local hash matches the freeze packet.
   - Stop if: Hash differs, file type is rejected, page limit differs, or the portal converts the file unexpectedly.
5. Compare preview against render PDF
   - Action: Compare portal/Word preview against frozen render PDF `grant_submissions/DICE_HR001126S0010/render_qa_20260619_manual_clean_v5/LumenCore_DICE_Abstract_WORKING_DRAFT.pdf`.
   - Capture: Record preview page count, visible formatting issues, missing figures/tables, and whether the preview remains within page/size limits.
   - Stop if: Preview differs materially, page count exceeds limit, or portal strips required content.
6. Record stop state
   - Action: Update the worksheet with portal-safe facts and stop.
   - Capture: Record remaining blockers and next evidence needed. Do not capture secrets.
   - Stop if: Stop before upload finalization, certification, consent, signature, workspace lock, or submit. Fresh action-time approval is required for each such action.

### HarborSentinel (DSIP)

- URL: https://www.dodsbirsttr.mil/submissions/
- Opportunity/topic hint: `DON26BZ03-NV063 / HarborSentinel`
- Preview goal: Confirm DSIP organization linkage, submitter authority, topic visibility, required Volume 2/form fields, budget/forms, compliance pages, and attachment preview behavior.
- Ready for preview: True
- Ready for upload or submit: False
- Stop before: DSIP certification pages, final upload, submit, workspace lock, or any representation the user has not reviewed.
- Portal/user blockers: 5

#### Frozen Upload Candidates

| Role | Path | Bytes | SHA-256 |
|---|---|---:|---|
| upload_candidate_docx | `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx` | 43534 | `e73ed581d7c647766d4e727001ec319b7b95d0c9e36b7589c5a160b9a0e67878` |
| render_preview_pdf | `grant_submissions/NV063_HarborSentinel/render_qa_20260620_baselines_v1/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.pdf` | 99538 | `a40117d90d4ad081d106edfab5fe1e834b52b0e3edacc51402c09969b20f73d9` |

#### Steps

1. Open portal
   - Action: User logs in to DSIP at https://www.dodsbirsttr.mil/submissions/. Codex may observe and navigate after login.
   - Capture: Record only login success/failure and whether the expected organization/workspace is visible.
   - Stop if: Portal asks for consent, certification, sensitive profile data, or payment-like information.
2. Verify authority
   - Action: Check organization association and submitter/upload authority for the specific opportunity.
   - Capture: yes/no/unclear for organization linkage, user role, and submitter authority.
   - Stop if: Role is unclear or portal asks to certify authority.
3. Verify opportunity
   - Action: Find opportunity/topic `DON26BZ03-NV063 / HarborSentinel` and record whether it is visible and open for the intended action.
   - Capture: Opportunity visibility, current portal deadline/window text, accepted file types, required sections, and page/size limits.
   - Stop if: Opportunity is not visible, closed, or instructions differ from the local package assumptions.
4. Compare upload candidate
   - Action: Use the frozen upload candidate `grant_submissions/NV063_HarborSentinel/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx` only if its local SHA-256 still equals `e73ed581d7c647766d4e727001ec319b7b95d0c9e36b7589c5a160b9a0e67878`.
   - Capture: Record whether the portal accepts the file type and whether local hash matches the freeze packet.
   - Stop if: Hash differs, file type is rejected, page limit differs, or the portal converts the file unexpectedly.
5. Compare preview against render PDF
   - Action: Compare portal/Word preview against frozen render PDF `grant_submissions/NV063_HarborSentinel/render_qa_20260620_baselines_v1/NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.pdf`.
   - Capture: Record preview page count, visible formatting issues, missing figures/tables, and whether the preview remains within page/size limits.
   - Stop if: Preview differs materially, page count exceeds limit, or portal strips required content.
6. Record stop state
   - Action: Update the worksheet with portal-safe facts and stop.
   - Capture: Record remaining blockers and next evidence needed. Do not capture secrets.
   - Stop if: Stop before upload finalization, certification, consent, signature, workspace lock, or submit. Fresh action-time approval is required for each such action.
