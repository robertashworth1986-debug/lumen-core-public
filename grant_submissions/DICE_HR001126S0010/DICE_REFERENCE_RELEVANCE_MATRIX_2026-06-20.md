# DICE Reference Relevance Matrix

Date: June 20, 2026 UTC

Artifact reviewed:
`grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_WORKING_DRAFT.docx`

Builder source:
`grant_submissions/DICE_HR001126S0010/build_dice_abstract.py`

Status: preliminary Codex relevance review complete; final human relevance
signoff remains required before upload.

## Purpose

This matrix maps every visible external reference in the DICE abstract package
to the proposal claim it can defensibly support. It is not a source-quality
guarantee, legal review, endorsement, or permission to submit. It is a
claim-boundary checklist for the final human reviewer.

## Relevance Matrix

| Reference | Where used | Supports | Does not support | Review status |
|---|---|---|---|---|
| DARPA DICE program page, `https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence` | Opportunity identification and TA1/TA2 framing | Confirms the DICE opportunity family, the public program framing, and the relevance of decentralized AI coordination/control language. | Does not validate LumenCore performance, eligibility, BAAT access, submission completeness, or any award likelihood. | Link/source checked in QA; final portal/BAA cross-check remains required. |
| Turner et al., "Steering Language Models with Activation Engineering", `https://arxiv.org/abs/2308.10248` | TA2 local inference-control context | Supports the technical plausibility of influencing model behavior through internal/activation-oriented steering in open-weight settings. | Does not prove black-box control, safety, adversarial robustness, DICE metric attainment, or LumenCore implementation performance. | Relevant as background for open-weight control only. |
| Shapira et al., "Prompt Infection", `https://arxiv.org/abs/2410.07283` | Multi-agent prompt/tool contamination risk | Supports the risk argument that multi-agent systems can propagate malicious or destabilizing prompt effects, making local challenge/isolation mechanisms relevant. | Does not prove CBPM detects prompt infection or prevents all multi-agent compromise. | Relevant to threat model and failure-mode motivation. |
| Friston et al., "Designing Ecosystems of Intelligence from First Principles", `https://doi.org/10.1177/26339137231222481` | Ecosystem-of-intelligence framing | Supports broad conceptual grounding for interacting intelligent systems, boundaries, and first-principles coordination language. | Does not prove CBPM, decentralized consensus, DICE scalability, or operational defense utility. | Source metadata confirmed; use as conceptual background only. |
| Zhou et al., "ReSo", `https://aclanthology.org/2025.emnlp-main.808/` | Self-organizing multi-agent reasoning background | Supports the relevance of self-organizing LLM-based multi-agent systems and reward-driven coordination as a related research area. | Does not establish LumenCore superiority, resilience under compromise, or DICE metric attainment. | Relevant as related-work context. |
| Lee et al., "Robust Multi-Agent LLMs under Byzantine Faults", `https://arxiv.org/abs/2605.09076` | Byzantine/compromise risk context | Supports the need to evaluate multi-agent LLM systems under Byzantine or compromised-agent conditions. | Does not prove CBPM Byzantine security, cryptographic security, or high-collusion robustness. | Relevant to adversarial evaluation motivation. |
| Model Context Protocol project, `https://github.com/modelcontextprotocol` | Interface and tool-connection compatibility | Supports the statement that MCP-compatible transports/interfaces are plausible integration targets. | Does not prove official partnership, endorsement, DICE compliance, or production integration. | Relevant only as public interface ecosystem context. |
| Agent2Agent Protocol project, `https://github.com/a2aproject` | Multi-agent communication/interface context | Supports the statement that A2A-compatible transports/interfaces are plausible integration targets. | Does not prove official partnership, endorsement, DICE compliance, or production integration. | Relevant only as public interface ecosystem context. |
| vLLM documentation, `https://docs.vllm.ai/` | Efficient inference-stack planning | Supports the cost/schedule note that efficient inference stacks can be benchmarked in Phase I. | Does not prove the proposed system will meet DICE scale, latency, token-cost, or cloud-cost targets. | Relevant to implementation planning, not performance proof. |
| Fujimoto, "Parallel Discrete Event Simulation", `https://doi.org/10.1145/84537.84545` | Synthetic discrete-event benchmark methodology | Supports the use of discrete-event simulation as a legitimate method for scalable coordination experiments. | Does not validate the model assumptions, mission realism, operational performance, or DICE metric attainment. | Source metadata confirmed; relevant to methodology. |
| `https://lumen-core.ai` | Public demonstration/evidence portal | Supports the existence of a public LumenCore web presence for non-sensitive demos and public evidence material. | Does not prove customer adoption, institutional deployment, grant eligibility, or trading performance. | Relevant to public presence only. |
| `https://github.com/robertashworth1986-debug/lumen-core-public` | Public code/evidence repository | Supports the existence of a public repository for public-safe code, evidence governance, and reproducibility artifacts. | Does not prove private grant packet completeness, portal compliance, partner commitment, or DICE performance. | Relevant to public-safe reproducibility trail only. |

## Claim Boundary Decisions

- The references support technical motivation, related-work positioning,
  interface planning, and simulation methodology.
- The references do not independently validate CBPM, LumenCore, DICE metric
  attainment, operational defense performance, classified-environment
  performance, CMMC status, partner commitments, or award eligibility.
- The DICE synthetic runs remain the only local performance evidence cited in
  the package; those runs are bounded software simulations with preserved
  negative results and high-collusion limitations.
- Public repository and website links are presence/reproducibility references,
  not adoption, revenue, trading, or deployment claims.

## Final Human Review Checklist

Before upload, the human reviewer should confirm:

1. Each reference is still visible or source-confirmed in the actual upload
   environment.
2. Each reference is relevant to the adjacent sentence in the final DOCX.
3. No citation is used as a substitute for missing DICE program evidence.
4. No citation implies official endorsement, partnership, or operational
   validation.
5. The final uploaded file still contains the current bibliography and no
   hidden template/reviewer artifacts.

## Recommendation

The reference set is defensible for a working abstract if the final reviewer
keeps the current claim boundaries. The remaining blocker is final human
signoff, not missing source links or unresolved citation style.
