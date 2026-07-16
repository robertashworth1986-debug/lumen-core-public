# DICE Benchmark Freeze Reconciliation Register - v0.2

**Project:** LumenCore / Coherence-Bounded Peer Mesh (CBPM)  
**Abstract ID:** HR001126S0010-DICE-PA-052  
**Prepared:** 2026-07-16  
**Status:** Internal evidence-control asset. Not a submission, certification, or representation to the Government.

## 0. Control boundary

This register converts the existing benchmark inventory into a file-by-file freeze and verification gate. It does not establish DICE metric attainment, operational performance, adversarial security, field validation, independent reproduction, TA3 conformance, or Government acceptance. Final proposal use requires a fresh check against the controlling solicitation and explicit founder approval.

## 1. Current decision

- Preliminary synthetic benchmark summaries exist for 500, 5,000, and 100,000 modeled agents.
- A fourteen-scenario frozen live-breadth replay summary exists.
- The cited raw trial files, scorecards, summaries, environments, and manifests have not yet been consolidated into one controlled packet in this repository.
- The final packet is therefore **not ready for portal attachment or submission**.

## 2. Frozen-run inventory

| Lane | Run identifier / scope | Current summary | Required source artifacts | Reconciliation status |
|---|---|---|---|---|
| Synthetic scale | `20260613T_DICE_V1_500A_200PAIRS_OPT` | 500 agents; 1,200 tasks; 200 paired trials | `trials.csv`, `summary.json`, `SCORECARD.md`, `manifest.sha256.json`, code commit, environment record | Locate and copy without modification |
| Synthetic scale | `20260613T_DICE_V1_5000A_50PAIRS` | 5,000 agents; 15,000 tasks; 50 paired trials | Same artifact set | Locate and copy without modification |
| Synthetic scale | `20260613T_DICE_V1_100KA_5PAIRS` | 100,000 agents; 250,000 tasks; 5 paired trials | Same artifact set | Locate and copy without modification |
| Frozen replay | 14 deterministic Kraken/EIA stress windows | 180 agents; 8 roles; deterministic derived labels | Raw replay trial table, replay summary, scorecard, source-file inventory, provenance/rights note, manifest | Locate and copy without modification |

## 3. Claim-to-artifact reconciliation

| Candidate claim | Current bounded value | Artifact that must support it | Portal-safe status |
|---|---:|---|---|
| Modeled message reduction at 500 agents | 31.5% | 500-agent `summary.json`, paired `trials.csv`, scorecard, verified manifest | Hold until rehashed |
| Modeled recovery-message reduction at 500 agents | 40.1% | Same 500-agent artifact set | Hold until rehashed |
| Modeled role-coherence delta at 500 agents | +6.45 percentage points | Same 500-agent artifact set and locked metric definition | Hold until rehashed |
| Modeled message reduction at 5,000 agents | 31.8% | 5,000-agent artifact set | Hold until rehashed |
| Modeled recovery-message reduction at 5,000 agents | 33.4% | 5,000-agent artifact set | Hold until rehashed |
| Modeled message reduction at 100,000 agents | 30.1% | 100,000-agent artifact set | Hold until rehashed |
| Modeled recovery-message reduction at 100,000 agents | 38.3% | 100,000-agent artifact set | Hold until rehashed |
| Mission-success superiority | Not established | Bootstrap output shows intervals crossing zero at larger scales | Prohibited claim |
| Replay safe-completion delta | +0.0437 mean | Replay raw trials and summary | Research signal only |
| Replay constraint-violation delta | -0.1216 mean | Replay raw trials and summary | Research signal only |
| Replay messages per safe completion | -2.8157 mean | Replay raw trials and summary | Research signal only |
| Replay false-rejection delta | +0.0514 mean | Replay raw trials and summary | Mandatory negative result |

## 4. Artifact reconciliation table

Complete one row for every file before freezing the packet.

| Packet path | Source location | Expected bytes | Existing SHA-256 | Independently computed SHA-256 | Match | Verified by/date | Notes |
|---|---|---:|---|---|---|---|---|
| `05_RAW_TRIALS/500A_trials.csv` | TBD | TBD | TBD | TBD | TBD | TBD | Do not open/save through spreadsheet software before hashing |
| `06_SUMMARIES/500A_summary.json` | TBD | TBD | TBD | TBD | TBD | TBD | Preserve original timestamp metadata separately |
| `06_SUMMARIES/500A_SCORECARD.md` | TBD | TBD | TBD | TBD | TBD | TBD | Text copy must be byte-identical |
| `03_MANIFESTS/500A_manifest.sha256.json` | TBD | TBD | TBD | TBD | TBD | TBD | Verify listed file set and hashes |
| `05_RAW_TRIALS/5000A_trials.csv` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `06_SUMMARIES/5000A_summary.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `06_SUMMARIES/5000A_SCORECARD.md` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `03_MANIFESTS/5000A_manifest.sha256.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `05_RAW_TRIALS/100KA_trials.csv` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `06_SUMMARIES/100KA_summary.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `06_SUMMARIES/100KA_SCORECARD.md` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `03_MANIFESTS/100KA_manifest.sha256.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `05_RAW_TRIALS/replay_trials.csv` | TBD | TBD | TBD | TBD | TBD | TBD | 14 scenarios expected |
| `06_SUMMARIES/replay_summary.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `06_SUMMARIES/replay_SCORECARD.md` | TBD | TBD | TBD | TBD | TBD | TBD |  |
| `03_MANIFESTS/replay_manifest.sha256.json` | TBD | TBD | TBD | TBD | TBD | TBD |  |

## 5. Mandatory negative-result and defect register

| Item | Required disclosure | Treatment |
|---|---|---|
| Mission-success confidence intervals | At 5,000 and 100,000 agents, bootstrap confidence intervals crossed zero. | State that mission completion was approximately preserved; do not claim superiority. |
| False rejection | Frozen replay increased false rejection by +0.0514 mean. | Retain as an availability/safety tradeoff and Phase I reduction target. |
| Initial comparator defect | The first scale attempt allowed repeated full-population scans by the centralized comparator. | Preserve the defect history and corrected cached-role-index rerun. |
| Agent realism | Current scale benchmark uses stochastic task executors, not language models. | Do not imply heterogeneous LLM-agent validation. |
| Adversarial scope | Current perturbations are modeled failures/compromise, not demonstrated real adversaries. | Do not claim adversarial security. |
| TA3 integration | No tested TA3 adaptor is evidenced in the current packet. | Describe adaptor work as proposed. |
| Independent reproduction | No independent reproduction is complete. | State explicitly as pending. |

## 6. Rehash and freeze procedure

1. Locate each original run directory and copy it into a read-only staging directory without opening or rewriting the files.
2. Record the original path, file size, modified timestamp, code commit, Python version, operating system, and command line.
3. Compute SHA-256 independently for every raw artifact.
4. Compare each computed digest against the original run manifest. Any mismatch stops the freeze.
5. Confirm that each `summary.json` value can be recomputed from the paired raw trial rows using the locked metric definitions.
6. Confirm that the scorecard wording matches the underlying values and retains the evidence boundary.
7. Add the defect and negative-result register without altering any original run artifact.
8. Generate a packet-level manifest covering every included file, including the original per-run manifests.
9. Mark the packet read-only. Any later change creates a new version and a new packet-level manifest.
10. Permit technical-volume use only after explicit founder review of the exact claim-to-artifact map.

## 7. Proposed final packet tree

```text
DICE_BENCHMARK_EVIDENCE_PACKET_V1_0/
├── 00_README_AND_EVIDENCE_BOUNDARY.md
├── 01_CLAIM_LEDGER.csv
├── 02_PREREGISTERED_BENCHMARK_PLAN.md
├── 03_MANIFESTS/
│   ├── 500A_manifest.sha256.json
│   ├── 5000A_manifest.sha256.json
│   ├── 100KA_manifest.sha256.json
│   └── replay_manifest.sha256.json
├── 04_CODE_AND_ENVIRONMENT/
│   ├── git_commit.txt
│   ├── environment.txt
│   ├── reproduction_commands.md
│   └── source_hashes.json
├── 05_RAW_TRIALS/
│   ├── 500A_trials.csv
│   ├── 5000A_trials.csv
│   ├── 100KA_trials.csv
│   └── replay_trials.csv
├── 06_SUMMARIES/
│   ├── 500A_summary.json
│   ├── 5000A_summary.json
│   ├── 100KA_summary.json
│   ├── replay_summary.json
│   └── SCORECARD.md
├── 07_FAILURE_AND_NEGATIVE_RESULT_REGISTER.md
├── 08_STATISTICAL_METHODS.md
├── 09_DATA_PROVENANCE_AND_RIGHTS.md
├── 10_SAFETY_BOUNDARY_MEMO.md
└── 11_PACKET_MANIFEST_SHA256.json
```

## 8. Freeze acceptance gate

Every field below must be complete before the packet is labeled frozen:

- [ ] Original raw files located for all three synthetic runs and all fourteen replay scenarios.
- [ ] Source paths and file sizes recorded.
- [ ] Original manifests present.
- [ ] Independent SHA-256 values match every original manifest.
- [ ] Code commit and environment recorded for every run.
- [ ] Metric formulas and denominators locked.
- [ ] Summary values recomputed from raw trials.
- [ ] Negative results and corrected-comparator history retained.
- [ ] Data provenance and rights documented.
- [ ] No credentials, portal identifiers, controlled information, or private data included.
- [ ] Packet-level manifest generated last.
- [ ] Founder has approved the exact evidence wording for proposal use.

## 9. Reviewer-safe technical-volume language

> Preliminary internal evaluation used paired synthetic discrete-event trials to compare a cached centralized assignment proxy with a bounded peer-auction architecture incorporating local reputation and role-coherence repair. Across frozen configurations ranging from 500 to 100,000 modeled agents, the peer architecture reduced modeled message burden by approximately 30-32% and recovery-message burden by approximately 33-40%, while mission-success differences at the larger scales were not statistically established. A separate fourteen-scenario deterministic stress-replay lane produced favorable safe-completion, constraint-violation, and communication-cost signals but also increased false rejection. These results are feasibility evidence for the measurement harness and research hypotheses only; they do not establish DICE metric attainment, operational performance, adversarial security, TA3 conformance, or independent validation.

## 10. Current readiness flags

- `raw_artifacts_consolidated`: **false**
- `manifest_reverification_complete`: **false**
- `summary_recomputation_complete`: **false**
- `negative_result_register_defined`: **true**
- `packet_tree_defined`: **true**
- `ready_for_technical_volume_claim_use`: **false**
- `ready_for_portal_upload`: **false**
- `ready_for_submit`: **false**

**Next execution item:** locate the four original run directories, copy the byte-identical artifacts into the packet tree, and complete the reconciliation table before generating the packet-level manifest.