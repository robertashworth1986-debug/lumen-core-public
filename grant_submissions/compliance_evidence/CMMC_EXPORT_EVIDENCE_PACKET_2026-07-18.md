# CMMC and Export Evidence Packet

Packet state: `EVIDENCE_INCOMPLETE`
Generated UTC: `2026-07-19T03:11:29Z`
Packet SHA-256: `ba150a381b53a8cb7eba4df94e18b6dd383b3e5cd0b89c0ed3661145da179a40`

## Claim Boundary

Evidence inventory only. This packet does not determine or claim compliance, certification, award eligibility, export authorization, JCP approval, or satisfaction of any solicitation. Only the named authoritative issuer, contracting authority, or qualified reviewer can make the corresponding determination.

## Evaluation Limit

The builder validates only supplied metadata, chronology, scope markers, source-class policy, and deterministic integrity. It does not open referenced private evidence or authenticate an issuer, signature, portal session, legal opinion, or agency determination.

## Inventory Summary

- Programs: `3`
- Requirements: `19`
- Authoritative proof inventoried: `0`
- Supported not-applicable reviews: `0`
- Open requirements: `19`
- Fail-closed issues: `19`

## DICE

Requirements sources:
- `grant_submissions/DICE_HR001126S0010/HR001126S0010_AMENDMENT_01_OFFICIAL.pdf` - Amendment 01 CMMC and proposal-security requirements

| Fact | Control | Applicability | Evidence state | Proofs | Issues |
|---|---|---|---|---:|---:|
| `dice.cmmc_l1_sprs_final` | `CMMC_L1_SPRS_FINAL` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `dice.cmmc_annual_affirmation` | `CMMC_ANNUAL_AFFIRMATION` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `dice.fci_cui_boundary` | `FCI_CUI_BOUNDARY` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `dice.foreign_person_boundary` | `FOREIGN_PERSON_AND_EXPORT_BOUNDARY` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `dice.subcontractor_flowdown` | `SUBCONTRACTOR_SECURITY_AND_EXPORT_FLOWDOWN` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |

## HarborSentinel

Requirements sources:
- `grant_submissions/NV063_HarborSentinel/NAVY_26BZ_PH_I_R3_INSTRUCTIONS.pdf` - Navy Release 3 instructions and projected CMMC/export requirements

| Fact | Control | Applicability | Evidence state | Proofs | Issues |
|---|---|---|---|---:|---:|
| `harbor.cmmc_l2_self_status` | `CMMC_L2_SELF_STATUS` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `harbor.jcp_application_submitted` | `JCP_APPLICATION_SUBMITTED` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `harbor.dd2345_certified` | `DD2345_CERTIFIED` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `harbor.itar_classification` | `ITAR_CLASSIFICATION` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `harbor.ear_classification` | `EAR_CLASSIFICATION` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `harbor.fci_cui_boundary` | `FCI_CUI_BOUNDARY` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `harbor.subcontractor_flowdown` | `SUBCONTRACTOR_SECURITY_AND_EXPORT_FLOWDOWN` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |

## MissionWeave

Requirements sources:
- `grant_submissions/DLA26BZ03_NV011_MissionWeave/source_attachments/DLA_26BZ_RELEASE_3_COMPONENT_INSTRUCTIONS.pdf` - DLA component instructions for JCP and ITAR or EAR requirements
- `grant_submissions/DLA26BZ03_NV011_MissionWeave/source_attachments/DoW_2026_SBIR_BAA_RELEASE_3_AMENDMENT_2.pdf` - Controlling generic BAA amendment

| Fact | Control | Applicability | Evidence state | Proofs | Issues |
|---|---|---|---|---:|---:|
| `missionweave.cmmc_l2_self_status` | `CMMC_L2_SELF_STATUS` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `missionweave.jcp_application_submitted` | `JCP_APPLICATION_SUBMITTED` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `missionweave.dd2345_certified` | `DD2345_CERTIFIED` | `APPLIES` | `MISSING_OFFICIAL_PROOF` | 0 | 1 |
| `missionweave.itar_classification` | `ITAR_CLASSIFICATION` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `missionweave.ear_classification` | `EAR_CLASSIFICATION` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `missionweave.fci_cui_boundary` | `FCI_CUI_BOUNDARY` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |
| `missionweave.subcontractor_flowdown` | `SUBCONTRACTOR_SECURITY_AND_EXPORT_FLOWDOWN` | `UNKNOWN` | `APPLICABILITY_UNRESOLVED` | 0 | 1 |

## Frozen Rules

- A boolean or locally generated receipt never upgrades its source class.
- Wrong-entity, wrong-scope, stale, conflicting, malformed, or missing proof fails closed.
- ITAR and EAR remain separate classification branches.
- NOT_APPLICABLE requires a named legal or contracting review and a hashed decision reference.
- A JCP submission receipt is distinct from a JCP-certified DD2345.
- No output may claim compliance, certification, export authorization, or award eligibility.

## Prohibited Conclusions

- `compliant`
- `certified`
- `award_eligible`
