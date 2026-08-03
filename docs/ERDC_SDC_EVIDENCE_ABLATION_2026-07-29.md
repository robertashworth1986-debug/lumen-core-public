# ERDC SDC Evidence-Control Ablation - 2026-07-29

Status: `SYNTHETIC_CONTROL_ABLATION_PASS_EXTERNAL_TRUST_ROOT_HPCMP_AND_INDEPENDENT_VALIDATION_REQUIRED`

## Decision

The deterministic surrogate compares the complete LumenCore control profile only with three LumenCore ablations. The complete profile retains the declared controls relative to a separately supplied local anchor; each ablation loses at least one control. OpenTelemetry and SLSA are complementary interoperability contexts and are not ranked.

## Protocol

- Protocol: `ERDC-SDC-EVIDENCE-ABLATION-V2`
- Protocol SHA-256: `61337e3493f63f46a700152748d5a586635dfb9338fb5ba6766e084d6ae5a723`
- Synthetic workflow count: `48`
- Adverse workflow count: `30`
- Artifact-bearing workflow count: `30`
- Synthetic-row SHA-256: `11136486390eb11af0a1937080ac3f35171fab83a7152f77030a6ea23a134182`
- Raw synthetic rows published: `false`

## Trusted Anchor Boundary

The local verifier receives a trusted-anchor object generated before attack mutation and separately from the mutable receipt. The anchor pins the protocol, source-population counts, profile counts, terminal chain root, and predeclared gate hash. This models a separately pinned local input only. It is not an external signature, independent timestamp, tamper-proof store, production trust root, or Government validation. Phase II must bind the anchor outside the mutable receipt through a Government-approved signing or custody mechanism.

## Control Ablation Results

| LumenCore profile | Control attacks detected | Adverse recall | Artifact bytes rehashed | Gates executed | Bytes |
|---|---:|---:|---:|---:|---:|
| LumenCore full evidence controls | 7/7 | 1.000 | 1.000 | true | 32642 |
| LumenCore ablation: no event chain | 4/7 | 1.000 | 1.000 | false | 24947 |
| LumenCore ablation: no predeclared gates | 7/7 | 1.000 | 1.000 | false | 32402 |
| LumenCore ablation: success-only retention | 3/7 | 0.000 | 0.600 | false | 13755 |

Serialized bytes describe these small synthetic LumenCore profiles only; they are not an HPCMP capacity, latency, cost, or performance result.

## Checks

- `full_clean_profile_valid`: `true`
- `full_detects_all_declared_control_attacks`: `true`
- `full_detects_adaptive_delete_rechain_and_reseal`: `true`
- `full_detects_adaptive_policy_rechain_and_reseal`: `true`
- `full_retains_all_adverse_outcomes`: `true`
- `full_rehashes_all_artifact_bytes`: `true`
- `full_executes_predeclared_gates`: `true`
- `full_detects_posthoc_promotion_change`: `true`
- `every_ablation_loses_at_least_one_declared_control`: `true`
- `standards_are_context_only_not_ranked`: `true`

## Interoperability Contexts - Not Ranked

- OpenTelemetry Logs Data Model 1.59.0: https://opentelemetry.io/docs/specs/otel/logs/data-model/ - A stable vendor-neutral log-record data model. It is treated as a complementary event interchange context, not an integrity or runtime promotion-control baseline. Comparison role: `INTEROPERABILITY_CONTEXT_NOT_RANKED`.
- SLSA Build Provenance 1.2 with in-toto Statement v1: https://slsa.dev/spec/v1.2/build-provenance - An approved artifact build-provenance model. It is treated as a complementary provenance context, not a runtime workflow ledger or promotion-control baseline. Comparison role: `INTEROPERABILITY_CONTEXT_NOT_RANKED`.

## Phase II Use

Use this benchmark only to justify a Government-approved Phase II experiment: lock one representative unclassified workflow, select an equivalent integrated comparator if one is required, pin or sign the protocol and terminal root outside the mutable receipt, predeclare thresholds, run adaptive attacks and ablations, and have a separate reviewer execute the delivered verifier.

## Claim Boundary

This is a deterministic synthetic, unclassified workflow-control ablation. It compares the complete LumenCore control profile only with its own no-chain, no-predeclaration, and no-failure-retention ablations. OpenTelemetry and SLSA are listed only as complementary interoperability contexts and are not ranked or attacked. The result is not an HPCMP workload, Government test, independent validation, security assessment, cost study, production benchmark, or proof of superiority. The local anchor is not an external trust root.
