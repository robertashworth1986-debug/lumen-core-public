# LumaSkin Protocol Status

- Generated UTC: `2026-07-18T22:03:39.225319Z`
- Protocol: `lumaskin_xr_research_v1` version `1.0.0`
- Protocol SHA-256: `6e79b1432e93fb4a20d395f319c18aa68ebb70a7ee9be3b93f64f45045779a95`
- Artifact manifest SHA-256: `383da79c78290abb00fbc9778dd09aef4752fa09f0bd41c24df603d9dd7b0c0e`
- Status: **BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED**
- Test families defined: **8**
- Authority gates open: **8 / 8**
- Human testing authorized: **No**
- Independent validation complete: **No**

## Test Families

| ID | Test family | Stage | Current evidence |
| --- | --- | --- | --- |
| TF-01 | Cue integrity and fail-silent behavior | software_and_bench | PROTOCOL_DEFINED_NOT_RUN |
| TF-02 | Cross-modal timing | bench_then_human | PROTOCOL_DEFINED_NOT_RUN |
| TF-03 | Garment fit, contact, and thermal envelope | mannequin_then_passive_fit | PROTOCOL_DEFINED_NOT_RUN |
| TF-04 | Spatial cue localization | single_zone_human | PROTOCOL_DEFINED_NOT_RUN |
| TF-05 | XR comfort and cybersickness | xr_multimodal_human | PROTOCOL_DEFINED_NOT_RUN |
| TF-06 | Fatigue and movement burden | passive_fit_then_human | PROTOCOL_DEFINED_NOT_RUN |
| TF-07 | Adaptive cue governor | offline_then_prospective | PROTOCOL_DEFINED_NOT_RUN |
| TF-08 | Privacy, provenance, and independent reproduction | all_stages | PROTOCOL_DEFINED_NOT_RUN |

## Authority Gates

| ID | Gate | Status | Evidence items required |
| --- | --- | --- | ---: |
| AG-01 | Claim and requirements freeze | OPEN | 4 |
| AG-02 | Executable controller and synthetic fault sweep | OPEN | 4 |
| AG-03 | Unoccupied electrical and thermal bench | OPEN | 5 |
| AG-04 | Mannequin fit and contact fixture | OPEN | 4 |
| AG-05 | Materials, hygiene, and wearable risk review | OPEN | 4 |
| AG-06 | Human-research authority | OPEN | 5 |
| AG-07 | Preregistered randomized human-factors study | OPEN | 4 |
| AG-08 | Independent reproduction and claim review | OPEN | 4 |

## Next Bounded Action

Run the executable controller and synthetic fault sweep for AG-02; do not energize a garment on a person.

## Claim Boundary

LumaSkin V1 is a non-medical research architecture and simulation/bench protocol. It is not a fabricated product. It is not protective equipment. It is not an exoskeleton. It is not a medical device. It is not a safety certification. It is not an injury-prevention system and is not proof that haptics prevent motion sickness. No strength amplification is in scope. No electrical muscle stimulation, autonomous force, pain stimulus, or impact-protection claim is in scope. No unsupervised human use is in scope.
