# Grant Submission Control Room

This is the operator-facing control room for moving LumenCore grant packages from **ready** to **submitted** once the authenticated portals are already connected through Login.gov.

## Connected Portal Stack

| Portal | Use now | Direct route |
|---|---|---|
| Login.gov | Identity and connected-account hub. Use only for account/MFA management. | <https://secure.login.gov/account/connected_accounts> |
| SAM.gov | Confirm active entity registration, UEI, CAGE, reps/certs, and entity administrator data. | <https://sam.gov/entity-registration> |
| Grants.gov / Simpler Grants | Open opportunity workspaces, attach final files, validate package, and submit as the authorized user. | <https://apply07.grants.gov/apply/login.faces> |
| DOE OneID / PAMS | DOE-specific account lane for Office of Science / DOE SBIR-STTR workflows and LOI/package checks. | <https://pamspublic.science.energy.gov/webpamsepsexternal/login.aspx> |
| SBIR.gov | Small business applicant registration, SBC Control ID, and agency opportunity metadata. | <https://www.sbir.gov/> |

## Human-in-the-Loop Boundary

The system can prepare, check, route, and record the package. The authorized operator must perform the final portal certification and submit action because the submission represents legal attestations tied to the entity, UEI, CAGE, reps/certs, budget, and authorized organizational representative authority.

## Submit-Ready Sequence

1. **Open SAM.gov** and verify the entity shows active registration, correct UEI, correct CAGE, current points of contact, and no renewal blocker.
2. **Open the target opportunity** in Grants.gov, Simpler Grants, DOE PAMS, or the agency-specific portal.
3. **Create or open the workspace/application** for the opportunity number.
4. **Attach the prepared package files** in the exact field order required by the portal.
5. **Run portal validation** and resolve every missing-field, file-type, file-size, budget, or attachment warning.
6. **Confirm reps/certs and AOR authority** before any irreversible submit action.
7. **Submit as the authorized operator.** Do not submit if the portal displays warnings that change scope, budget, eligibility, or certifications.
8. **Capture receipt evidence**: tracking number, application ID, workspace ID, confirmation timestamp, and any downloadable receipt.
9. **Record submission evidence** in the repository or deployment evidence lane using the existing grant submission ledger tools.

## Receipt Evidence Checklist

After submission, preserve these values:

- Agency name.
- Opportunity title.
- Opportunity number.
- Assistance listing / CFDA number, if shown.
- Workspace ID or application ID.
- Grants.gov tracking number or agency tracking number.
- Submitter name.
- Submission timestamp and timezone.
- Receipt PDF or confirmation screenshot path.
- Final package file manifest and SHA256 manifest, if available.

## Fast Operator Prompt For This Assistant

Paste this after opening the portal screen:

```text
I am on [portal name] for [opportunity number/title]. The screen shows: [paste labels/errors only]. My package files are located at: [folder/path]. Walk me field-by-field and tell me what to attach or enter next.
```

Do not paste passwords, MFA codes, private financial account values, or private keys.
