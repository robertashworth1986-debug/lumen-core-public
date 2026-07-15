# FALCON Requirement-to-Evidence Crosswalk

Topic: `DPA26BZ04-DV016`

Freeze date: 2026-07-15

Status vocabulary: `SUPPORTED`, `PARTIAL`, `OPEN`, `HUMAN`.

| Requirement | Current evidence | Status | Required closure / proposal location |
| --- | --- | --- | --- |
| Survey emerging ML for structured and unstructured large-scale data | EIA residual mixture-of-experts benchmark; direct XGBoost and LightGBM comparators; DICE related-work material | `PARTIAL` | Bounded literature matrix with primary citations, selection criteria, and excluded-method rationale / White Paper: state of the art |
| Combine selected ML with one or more LLMs | Frozen v1 combined a pinned Qwen model with fixed ML experts; the hybrid tied fixed ML and the promotion gate failed. v2 and v3 are routing qualification studies, not full hybrid-lift results | `PARTIAL` | Freeze a new same-row ML-only, LLM-only, and hybrid comparison on a reserved holdout / Feasibility and Technical Plan |
| Accuracy against ground truth | EIA untouched holdout reports MASE, MAE, direction accuracy | `SUPPORTED` for structured ML | Add balanced accuracy and macro-F1 on identical hybrid/ML-only/LLM-only test rows / Feasibility |
| Improvement over ML-only state of the art | Residual candidate beats direct XGBoost and LightGBM on bounded EIA MASE, while full composite gate remains closed | `PARTIAL` | Same-row FALCON hybrid comparison with uncertainty and predeclared pass gate / Feasibility |
| Improvement over LLM-only state of the art | v1 measured a real LLM-only comparator and the hybrid exceeded it on the bounded rows, but the LLM-only result was weak and no state-of-the-art claim is supported | `PARTIAL` | Compare against a justified current LLM-only baseline on the same reserved rows with uncertainty and invalid-output handling / Feasibility |
| New insights | Current routing evidence identifies authority-specific specialist differences; not yet an LLM-generated validated insight | `PARTIAL` | Predeclare insight schema and score correctness, novelty, support, and actionability / Technical Plan |
| Computational efficiency | v1-v3 record model calls or forward passes, inference time, device, revision, and trace counts; v3 also seals exact model bytes and weight hash | `PARTIAL` | Add peak CPU/GPU memory, energy where practical, end-to-end latency, throughput, and matched comparator costs / Feasibility |
| Cross-dataset generalization | Frozen v1-v3 contracts span breast-cancer diagnostic and wine-chemistry tasks; v3 reached `27/30` but failed the predeclared stability and per-context gates | `PARTIAL` | Run the full same-row comparison on a reserved cross-domain holdout and then extend to operational-scale source-backed data / Feasibility |
| Evaluate multiple applications and datasets | EIA, MDA, FAA, NASA and other lanes are indexed | `PARTIAL` | Select at least two FALCON-relevant datasets and explain users, decisions, ground truth, and scale / White Paper and Slide Deck |
| Mitigate hallucination | v1 enforced allowlists and abstention, exposing an `0.833333` unsupported route-output rate; v2-v3 reduced unsupported output to zero but did not pass semantic/stability qualification | `PARTIAL` | Preserve allowlists, parser rejection, abstention, source IDs, and prompt/output hashes in the full comparative protocol / Technical Plan |
| Verifiable and reproducible analytic traces | Reviewer capsule, pinned revisions, exact model-weight receipt, SHA-256 trace chains, source manifests, and preserved v1-v3 null results | `SUPPORTED` internally | Obtain an independent rerun receipt and extend identical controls to the next reserved-holdout comparison / Feasibility |
| Interactive incorporation of new insights | Historical/frozen routers exist; no FALCON interactive LLM demonstration | `OPEN` | Month-6 prototype design with analyst query, validated context update, rerun, provenance, and rollback / Phase II Plan |
| Initial demonstration by month 6 | No FALCON Phase II schedule yet | `OPEN` | Monthly SOW with month-6 integrated demo and measurable exit criteria / Technical Plan |
| Enterprise-scale interactive analysis by month 11 | No validated enterprise-scale run | `OPEN` | Define row count, schema count, latency, memory, concurrent users, and failure thresholds / Technical Plan |
| Final demonstrations on two different domains | Two domains were exercised in bounded internal development runs, but neither run is a Phase II demonstration or external validation | `OPEN` | Base-period month-11 and month-12 demonstration plan with named users, acceptance tests, and independently receipted outputs / Technical Plan |
| Open-source software preferred | Public repository exists; v3 pins `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` and seals the exact weight blob | `PARTIAL` | Record code license, third-party notices, model license, and any non-public modules / Management and IP |
| DP2 feasibility achieved outside SBIR/STTR | Internal dated work exists; funding provenance has not been attorney/accountant reviewed | `HUMAN` | Funding-source chronology and signed PI/SBC attestation; counsel review / Feasibility Documentation |
| Feasibility substantially performed by SBC/PI | Solo-developed repository history is relevant but not itself a signed representation | `HUMAN` | Attributable commit/artifact timeline and PI certification / Feasibility Documentation |
| SBC owns or licenses feasibility IP | Patent and source artifacts exist; legal scope/ownership not established by this packet | `HUMAN` | Counsel-controlled claim/ownership/license chart / Management and IP |
| Experience within prior three years | Most cited artifacts are dated 2026 | `PARTIAL` | Dated chronology with immutable hashes and source provenance / Feasibility Documentation |
| Scholarly impact strongly preferred | Internal reports and benchmarks exist; no independent scholarly-impact proof established | `OPEN` | Public technical report/preprint and documented independent review, citation, reproduction, or adoption / Feasibility Documentation |
| Commercialization in parallel | Buyer/pilot packet infrastructure exists; no signed FALCON-specific transition partner established | `PARTIAL` | Named customer archetypes, economic model, pilot design, and substantiated letters only / Transition Plan |
| Base cost at or below $1,000,000; option at or below $500,000 | Official cost workbook frozen; no reviewed budget | `HUMAN` | Formula-preserving workbook, rates, bases, quotes, and cost narrative / Volume 3 |

## Local Evidence Anchors

- `docs/EIA_GRID_RESIDUAL_MOE_BENCHMARK_2026-07-13.md`
- `docs/EIA_GRID_PROSPECTIVE_HYBRID_ROUTER_2026-07-13.md`
- `docs/EIA_GRID_PROSPECTIVE_HOURLY_ROUTER_2026-07-14.md`
- `docs/REVIEWER_REPRODUCIBILITY_CAPSULE_2026-07-14.md`
- `docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md`
- `config/falcon_hybrid_context_protocol_v1.json`
- `code/falcon_hybrid_context_benchmark.py`
- `grant_submissions/DPA26BZ04_DV016_FALCON/DPA26BZ04_DV016_HYBRID_CONTEXT_REAL_MODEL_NULL_RESULT_2026-07-15.md`
- `grant_submissions/DPA26BZ04_DV016_FALCON/DPA26BZ04_DV016_CONSTRAINED_ROUTER_V2_NULL_RESULT_2026-07-15.md`
- `grant_submissions/DPA26BZ04_DV016_FALCON/DPA26BZ04_DV016_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md`
- `docs/FALCON_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md`
- `dashboard/data/falcon_permutation_calibrated_router.json`

The historical `30/30` score belongs to `model.kind = deterministic_qualification_test_double` with `model_id = fixture-not-an-llm`. It proves software-path behavior only and is excluded from model-performance evidence. The real-model sequence is v2 `25/30` and v3 `27/30`; both qualification gates failed and remain preserved.

No row in this crosswalk constitutes agency validation, patent advice, a legal certification, or permission to submit.
