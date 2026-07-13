# MDA Control-Mapping Open-Set Preregistration

Prepared: 2026-07-13

Protocol: `config/mda_control_mapping_open_set_protocol_v2.json`

## Falsifiable Question

Can a static-first, score-and-margin-gated lexical router preserve at least 80% supported-case coverage on an independent synthetic blind holdout while mapping no more than 5% of unsupported records and improving micro-F1 by at least 0.03 over the better frozen baseline?

## Why V2 Exists

The sealed v1 experiment did not pass. Its hybrid candidate mapped every unsupported holdout record and improved micro-F1 by only `0.02305`, below the preregistered `0.05` delta. That negative result is retained unchanged. V2 isolates the exposed risk: open-set refusal.

V1 holdout records are not used to build, select, or score v2. V1 supplies only the hypothesis that unsupported mapping needs an explicit gate.

## Frozen V2 Elements

- new random seed and 128 newly generated fixtures;
- eight supported and four unsupported archetypes;
- unsupported titles that cannot contain a supported archetype or control name;
- 56 development, 36 validation, and 36 blind-holdout records;
- static and unconstrained lexical baselines;
- static-first candidate with joint score and top-two-margin thresholds;
- validation constraints for unsupported mapping and supported coverage;
- a deterministic feasible and infeasible threshold-selection order;
- parser, provenance, coverage, unsupported-mapping, and baseline-delta gates;
- separate fixture, split, threshold, prediction, failure, result, and artifact-chain receipts;
- full negative-result retention.

## Promotion Boundary

Even a complete v2 pass remains synthetic feasibility evidence. Representative ACAS or SCAP artifacts, qualified cyber/RMF review, and a separately held blind set remain mandatory before operational, compliance, MDA, savings, production, or authorization claims.
