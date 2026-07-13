# DICE Benchmark Evidence Packet — Draft v0.1

**Project:** LumenCore / Coherence-Bounded Peer Mesh (CBPM)  
**Abstract ID:** HR001126S0010-DICE-PA-052  
**Abstract title:** Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives  
**Prepared:** 2026-07-13  
**Status:** Internal working draft only. Not a submission. Not legal advice. Not a government certification.

---

## 0. Submission-control boundary

This packet inventories current evidence and defines the freeze gate for a future proposal attachment or technical-volume appendix. The official solicitation, BAAT instructions, required templates, page limits, data-rights markings, representations, certifications, and portal controls govern any actual submission.

Nothing in this document establishes:

- DICE program-metric attainment,
- operational DoD performance,
- adversarial security,
- field validation,
- deployment authorization,
- certified safety,
- independent verification,
- award likelihood, or
- government acceptance.

No proposal or certification may be submitted without explicit founder approval and a fresh review against the official solicitation package.

---

## 1. Evidence position

LumenCore currently has two useful but bounded DICE evidence lanes:

1. **Preliminary synthetic scale benchmark:** paired discrete-event comparisons between a cached centralized assignment baseline and a sparse peer-auction mesh with local reputation and role-coherence repair.
2. **Frozen live-breadth replay capsule:** deterministic stress scenarios derived from frozen Kraken and EIA time-series windows, used as replay signals rather than native DICE task labels.

The evidence presently supports a research-feasibility claim: LumenCore can construct paired, reproducible coordination experiments; measure communication, recovery, coherence, safety-cost tradeoffs; retain negative results; and emit hash-manifested artifacts.

The evidence does **not** yet support claims about heterogeneous LLM-agent performance, TA3 conformance, real adversaries, real missions, or independent evaluation.

---

## 2. Claim ledger

| Candidate proposal statement | Current status | Evidence source | Safe interpretation | Prohibited interpretation |
|---|---|---|---|---|
| Sparse peer coordination can reduce modeled communication burden relative to the current centralized proxy. | Demonstrated in synthetic benchmark under specified model assumptions. | DICE preliminary synthetic benchmark, three frozen scale configurations. | Feasibility evidence for message-efficiency and harness scaling. | Universal superiority or operational network efficiency. |
| Sparse peer re-auction can reduce modeled recovery-message burden. | Demonstrated in synthetic benchmark under specified perturbations. | Paired runs using identical tasks, failures, compromised fractions, and seeds. | Supports testing recovery-cost hypotheses. | Proven recovery under real cyberattack or mission disruption. |
| Local role-coherence repair can improve the benchmark's modeled coherence metric. | Demonstrated in the synthetic executor model. | Preliminary benchmark role-coherence deltas. | Supports further inference-control experimentation. | Proof that language-model agents remain mission aligned. |
| Peer architecture improves mission success. | Not established at larger scales. | Bootstrap confidence intervals crossed zero at 5,000 and 100,000 agents. | Mission completion was approximately preserved in those benchmark runs. | Statistically established mission superiority. |
| Constraint checking improves safe completion on frozen stress replays. | Replay signal only. | Fourteen frozen live-breadth scenarios. | Justifies a controlled Phase I validation lane. | DICE metric proof, semantic correctness, or field safety. |
| Current evidence is independently reproducible. | Not yet independently established. | Code and output protocol exist; independent reproduction is pending. | The harness is designed to emit reproducibility artifacts. | Independent verification or third-party validation. |
| Current system is TA3-compatible. | Planned, not demonstrated. | Technical architecture identifies an adaptor dependency. | An external integration interface is a proposed work product. | Existing TA3 integration or acceptance. |
| Current system has been tested on heterogeneous agentic AI models. | Not demonstrated. | Present preliminary benchmark uses stochastic task executors. | This is a required next evidence step. | LLM-agent validation at scale. |

---

## 3. Frozen synthetic benchmark record

### 3.1 Research question

Can a bounded-neighborhood peer task market with local reputation and role-coherence repair reduce coordination and recovery messages relative to a cached centralized assignment baseline without materially reducing mission completion?

### 3.2 Comparator discipline

The two architectures receive the same:

- task stream,
- role assignments,
- failed-agent fraction,
- compromised-agent fraction, and
- random seeds.

The current benchmark compares:

- `centralized_baseline`: cached role index, periodic global status collection, centralized dispatch; and
- `peer_auction_with_local_control`: bounded neighborhood advertisements, local ranking, reputation updates, role repair, challenge, and re-auction.

### 3.3 Current frozen snapshot

| Agents | Tasks | Paired trials | Peer messages, mean | Message reduction | Recovery-message reduction | Mission-success delta | Role-coherence delta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 500 | 1,200 | 200 | 3,539 | 31.5% | 40.1% | +0.008 points | +6.45 points |
| 5,000 | 15,000 | 50 | 43,119 | 31.8% | 33.4% | +0.002 points | +6.57 points |
| 100,000 | 250,000 | 5 | 734,102 | 30.1% | 38.3% | +0.001 points | +6.53 points |

At 5,000 and 100,000 agents, the bootstrap confidence intervals for mission-success difference crossed zero. The defensible claim is therefore reduced modeled communication/recovery burden with approximately preserved mission completion—not improved mission success.

### 3.4 Run identifiers

- `20260613T_DICE_V1_500A_200PAIRS_OPT`
- `20260613T_DICE_V1_5000A_50PAIRS`
- `20260613T_DICE_V1_100KA_5PAIRS`

These identifiers are inventory references, not substitutes for verified artifact hashes.

### 3.5 Corrected benchmark defect

The first scale attempt allowed the centralized baseline to rescan an entire role population for every task, measuring Python search overhead rather than only the intended coordination policy. The implementation was corrected to use a cached role index while preserving the assignment rule. The 500-agent comparison was rerun after the correction and reproduced the prior aggregate metrics.

This defect and correction must remain in the evidence history. It is a credibility asset when disclosed, not a result to hide.

---

## 4. Frozen live-breadth replay record

### 4.1 Replay construction

- Source families: Kraken market time series and EIA power-grid time series.
- Source files: 6.
- Deterministic replay windows: 14.
- Agents per replay scenario: 180.
- Roles per replay scenario: 8.
- Task multiplier per source row: 3.

The source rows are stress signals. Replay labels are deterministic derived labels, not native DICE task labels.

### 4.2 Public-safe result snapshot

| Metric | Mean delta | Favorable fraction | Scenarios | Evidence boundary |
|---|---:|---:|---:|---|
| Safe completion | +0.0437 | 0.857 | 14 | Stress-replay signal only. |
| Constraint violation | -0.1216 | 0.929 | 14 | Supports a constraint-check validation lane. |
| Messages per safe completion | -2.8157 | 1.000 | 14 | Modeled coordination-cost behavior on frozen windows. |
| False rejection | +0.0514 | 0.000 | 14 | Known cost and explicit Phase I reduction target. |

The false-rejection increase is a material negative result. It must be retained and discussed as a safety/availability tradeoff rather than omitted.

---

## 5. Reproducibility controls already present

The preliminary benchmark implementation includes:

- deterministic paired seeds,
- explicit platform and Python-version capture,
- Git commit capture where available,
- raw trial export to `trials.csv`,
- aggregate and paired statistics in `summary.json`,
- plain-language interpretation in `SCORECARD.md`,
- SHA-256 calculation over generated artifacts, and
- a `manifest.sha256.json` output.

The code writes the evidence boundary into machine-readable results and uses bootstrap confidence intervals for paired metric differences.

### Current implementation references

- `code/dice_preliminary_benchmark.py`
- `tests/test_dice_preliminary_benchmark.py`
- `docs/DICE_PRELIMINARY_BENCHMARK_2026-06-13.md`
- `docs/DICE_PUBLIC_LIVE_BREADTH_REPLAY_CAPSULE_2026-06-21.md`

---

## 6. Required final evidence-packet structure

The final frozen packet should be assembled in this order:

```text
DICE_BENCHMARK_EVIDENCE_PACKET/
├── 00_README_AND_EVIDENCE_BOUNDARY.md
├── 01_CLAIM_LEDGER.csv
├── 02_PREREGISTERED_BENCHMARK_PLAN.md
├── 03_CONFIGS/
│   ├── baseline_config.json
│   ├── cbpm_config.json
│   └── scenario_matrix.json
├── 04_CODE_AND_ENVIRONMENT/
│   ├── git_commit.txt
│   ├── environment.txt
│   └── source_hashes.json
├── 05_RAW_TRIALS/
│   ├── synthetic_trials.csv
│   └── replay_trials.csv
├── 06_SUMMARIES/
│   ├── synthetic_summary.json
│   ├── replay_summary.json
│   └── SCORECARD.md
├── 07_FAILURE_AND_NEGATIVE_RESULT_REGISTER.md
├── 08_STATISTICAL_METHODS.md
├── 09_MANIFEST_SHA256.json
├── 10_SAFETY_BOUNDARY_MEMO.md
└── 11_REPRODUCTION_COMMANDS.md
```

No file should be added after the final manifest is generated. Any correction requires a new packet version and new manifest.

---

## 7. Proposed Phase I benchmark matrix

The following matrix is **planned work**, not current evidence.

| Condition | Baselines/ablations | Primary measurements | Required negative-result output |
|---|---|---|---|
| Benign heterogeneous agents | Centralized proxy; peer market without coherence control; CBPM | Safe completion, messages, role coherence, latency | Any coordination overhead or unnecessary abstention. |
| Random failure | Same paired baselines | Recovery time, re-auctions, completion loss | Failure levels where CBPM loses its advantage. |
| Compromised agents | Same paired baselines | Constraint violations, propagation, false commitments | Cases where compromised agents evade isolation. |
| Collusion cluster | Same paired baselines | Collusion success, concentration, diversity | Cluster sizes/topologies causing breakdown. |
| Monitor shift | Fixed threshold and adaptive threshold variants | False rejection, abstention, completion | Availability loss caused by over-sensitive controls. |
| High-compromise stress | All variants | Collapse threshold, safe degradation, communication cost | Earliest reproducible failure envelope. |
| Model heterogeneity | Open-weight and approved black-box agents | Cross-model task completion and control consistency | Models/roles where local controls fail to transfer. |
| External adaptor test | TA3-compatible interface target | Schema conformance, replay ingestion, artifact completeness | Integration incompatibilities and missing fields. |

All conditions must use identical paired seeds/configurations across comparator variants wherever technically possible.

---

## 8. Metric definitions to lock before the next run

Before scoring, the next packet must define formulas and denominators for:

- safe completion rate,
- constraint violation rate,
- role-coherence length,
- recovery latency,
- messages per safe completion,
- protocol byte/token cost,
- task-concentration index,
- selected-agent diversity,
- false rejection rate,
- abstention rate,
- compromised-agent propagation rate,
- collusion success rate,
- failure/collapse threshold, and
- manifest completeness.

A metric whose definition changes after inspecting outcomes must be versioned as a new experiment, not silently substituted.

---

## 9. Stop-ship evidence gaps

The benchmark packet is **not ready for proposal attachment** until all of the following are resolved:

1. Raw `trials.csv`, `summary.json`, `SCORECARD.md`, and `manifest.sha256.json` files for each cited frozen run are collected into one controlled packet.
2. Every manifest is independently rehashed and reconciled against the listed files.
3. Exact code commit and environment are recorded for each frozen run.
4. The V2 adversarial suite is frozen with benign, compromise, collusion, monitor-shift, and high-compromise conditions.
5. False rejection, diversity, latency, protocol cost, and negative-result registers are complete.
6. At least one stronger comparator beyond the current centralized proxy is included.
7. Heterogeneous agentic AI systems replace or supplement stochastic executors.
8. Any TA3-compatibility statement is backed by an implemented and tested adaptor.
9. Independent evaluator, lab, or qualified reviewer reproduction is either completed or explicitly listed as pending.
10. Proposed metrics are mapped to the controlling DICE solicitation language without claiming attainment.
11. Data provenance and rights are documented for every replay source.
12. No private portal material, account identifier, API key, or controlled information is embedded in the packet.

---

## 10. Freeze gate

A benchmark claim may enter the technical volume only when the following fields are complete:

| Gate field | Required state |
|---|---|
| Source/dataset named | Complete |
| Comparator named | Complete |
| Metric definition locked before scoring | Complete |
| Run type labeled | Synthetic, replay, measured, modeled, or estimated |
| Paired seeds/configurations recorded | Complete |
| Raw results retained | Complete |
| Negative results retained | Complete |
| Code/environment recorded | Complete |
| SHA-256 manifest verified | Complete |
| Claim boundary written | Complete |
| Independent status stated | Verified or explicitly pending |
| Founder approval for submission use | Explicitly granted |

Until every field is complete, the result remains internal development evidence.

---

## 11. Reviewer-safe technical-volume paragraph

> Preliminary internal evaluation used paired synthetic discrete-event trials to compare a cached centralized assignment proxy with a bounded peer-auction architecture incorporating local reputation and role-coherence repair. Across frozen configurations ranging from 500 to 100,000 modeled agents, the peer architecture reduced modeled message burden by approximately 30–32% and recovery-message burden by approximately 33–40%, while mission-success differences at the larger scales were not statistically established. A second lane converted frozen Kraken and EIA time-series windows into fourteen deterministic stress-replay scenarios; those replays produced favorable safe-completion, constraint-violation, and communication-cost signals but also increased false rejection, which remains an explicit Phase I optimization target. These results are feasibility evidence for the harness and research hypotheses only; they do not establish DICE metric attainment, operational performance, adversarial security, or independent validation.

---

## 12. Current readiness decision

- `benchmark_packet_inventory_defined`: **true**
- `synthetic_summary_available`: **true**
- `live_replay_summary_available`: **true**
- `raw_artifacts_consolidated`: **false**
- `manifest_reverification_complete`: **false**
- `v2_adversarial_packet_frozen`: **false**
- `heterogeneous_agent_validation_complete`: **false**
- `ta3_adaptor_tested`: **false**
- `independent_reproduction_complete`: **false**
- `ready_for_portal_upload`: **false**
- `ready_for_submit`: **false**

**Next execution item:** collect and reconcile the raw frozen artifacts and SHA-256 manifests for the three synthetic scale runs and the fourteen replay scenarios, then create a single versioned manifest and negative-result register without changing any underlying result.