# MDA26BZ04-NV007 Synthetic Feasibility Evidence

Prepared: 2026-07-13

Purpose: record the current software-feasibility evidence and its limits for proposal drafting. This annex is not operational cyber evidence and is not a substitute for Phase I testing on lawfully obtained representative artifacts.

## Two Frozen Experiments

### V1: Static-First Lexical Router

- Protocol commit: `89fc1cf942611fd507ac4956127ed0cb67c2807d`
- Fixtures: 96 deterministic synthetic records; 48 development, 24 validation, 24 blind holdout.
- Candidate blind-holdout micro-F1: `0.9167`.
- Best-baseline blind-holdout micro-F1: `0.8936`.
- Candidate delta: `+0.02305`, below the frozen `+0.05` gate.
- Unsupported-record mapping rate: `1.0000`, above the frozen `0.02` maximum.
- Verdict: `NEGATIVE`. The router did not pass the synthetic feasibility gate.

V1 exposed two concrete risks: a lexical fallback can force mappings on out-of-domain findings, and a favorable point metric is insufficient when the gain over a transparent baseline is small.

### V2: Constrained Open-Set Router

- Final preregistration commit: `ff610a147b79350a37f92cfa65853cd402885922`.
- Fixtures: 128 new deterministic synthetic records; 56 development, 36 validation, 36 blind holdout.
- Independence: new seed and records; no v1 holdout record was used for selection or v2 scoring.
- Candidate blind-holdout micro-F1: `0.9434`.
- Supported-case coverage: `0.9583`.
- Unsupported-record mapping rate: `0.0000`.
- Best-baseline blind-holdout micro-F1: `0.9231`.
- Candidate delta: `+0.02032`, below the frozen `+0.03` gate.
- Verdict: `NEGATIVE`. Open-set safety and coverage gates passed, but the required effect-size gate did not.

V2 shows that the software can enforce a validation-selected abstention constraint on this synthetic corpus. It does not show that the approach is better than accepted operational tools, and it does not justify changing the gate after observing the holdout.

## Proposal-Safe Interpretation

LumenCore has implemented two preregistered synthetic feasibility experiments for control-correlation routing. The first experiment failed because it mapped unsupported findings. A separately seeded second experiment reduced unsupported mappings to zero while retaining 95.8% supported-case coverage, but it still failed its predeclared minimum improvement over the strongest baseline. These results motivate Phase I work on lawful corpus construction, open-set calibration, representative baselines, human adjudication, and independent replay. They do not establish operational mapping accuracy, compliance, MDA validation, labor savings, production readiness, or authorization to operate.

## Evidence Files

- `config/mda_control_mapping_feasibility_protocol_v1.json`
- `docs/MDA_CONTROL_MAPPING_FEASIBILITY_RESULT_2026-07-13.md`
- `out/mda_control_mapping_feasibility/mda_control_mapping_feasibility_manifest_latest.json`
- `config/mda_control_mapping_open_set_protocol_v2.json`
- `docs/MDA_CONTROL_MAPPING_OPEN_SET_RESULT_2026-07-13.md`
- `out/mda_control_mapping_open_set_v2/mda_control_mapping_open_set_manifest_latest.json`

Every generated bundle includes fixture, split, threshold-selection, full-prediction, failure/abstention, result, and artifact-chain receipts.

## Next Evidence Gate

1. Obtain lawful representative ACAS/Nessus and SCAP-like artifacts with documented license and handling authority.
2. Freeze a separately governed label protocol with a qualified cyber/RMF reviewer.
3. Compare accepted transparent baselines and the candidate on an independently held blind set.
4. Measure unsupported mapping, supported coverage, calibration, reviewer correction burden, parser failures, and disagreement.
5. Retain negative and inconclusive results and prohibit operational claims unless every preregistered gate passes.
