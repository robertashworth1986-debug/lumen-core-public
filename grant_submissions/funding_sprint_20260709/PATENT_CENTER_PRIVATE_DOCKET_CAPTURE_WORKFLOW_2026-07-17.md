# Patent Center Private Docket Capture Workflow - 2026-07-17

## Direct Answer

The current local evidence proves a payment acknowledgement, not a complete application, official filing posture, or U.S. response deadline. The user-reported July 25 date is not treated as a verified legal deadline. The newest official Patent Center notice controls any response period.

This workflow hashes and classifies private Patent Center downloads without publishing application numbers, filenames, paths, source hashes, correspondence, payment identifiers, or document contents. It does not file, pay, sign, submit, or navigate the browser.

## Initialize

```powershell
python code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py --initialize
```

This creates a Git-ignored private root at `out/private/patent_center_capture/`, one folder for each docket role, and `metadata.private.json`. Editing the metadata file is optional; its values never enter the public control.

## Six Required Categories

Place each Patent Center download into the matching private folder:

1. `official_status_record` - application data and current status.
2. `filing_receipt` - the official Filing Receipt.
3. `official_correspondence` - all outgoing correspondence, including a page or export that proves none is listed if applicable.
4. `submitted_document_list` - the official submitted-documents listing.
5. `fee_history` - assessed, paid, and outstanding fee history.
6. `transaction_history` - chronological transaction history.

Optional folders hold `claims_record`, `payment_acknowledgement`, and `payment_receipt_screenshot` evidence. Files are treated only as bytes for hashing and are never executed.

## Check

```powershell
python code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py --check
```

The check prints role counts and missing role names only. It does not print private filenames, hashes, metadata values, or document contents.

## Build

```powershell
python code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py --build
```

The default build fails closed until all six required categories contain at least one nonempty file. It writes a private hashed docket inside the ignored capture root and regenerates only a redacted public control. `--build-partial` exists for an explicit interim audit and cannot establish a complete-docket state.

## Human And Legal Gate

- Review the newest official correspondence for any mailing date, response period, extension rule, surcharge, or missing-item notice.
- Confirm any deadline with the USPTO Pro Se Assistance Program or a registered patent practitioner.
- Use the held practitioner template only through an appropriate intake channel.
- Do not transmit unpublished claims, specifications, drawings, identifiers, or private docket records by ordinary email before a secure or confidential channel is confirmed.
- Any filing, fee, signature, certification, engagement, or final legal decision remains human-controlled.

Held response template: `grant_submissions/funding_sprint_20260709/PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md`.
