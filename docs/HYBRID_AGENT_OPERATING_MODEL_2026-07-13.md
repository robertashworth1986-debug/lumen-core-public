# Hybrid Agent Operating Model

**Status:** bounded operating design
**Registry:** `config/hybrid_agent_capability_registry_v1.json`
**Control boundary:** local preparation may be automated; consequential external action may not.

## What The Model Is

The model coordinates specialized workflows around evidence intake, protocol freezing, baseline testing, hybrid routing, falsification, reproducibility, reviewer context, funding packages, counsel packages, and external actions.

It is not a claim that one system is an expert in every programming language. A language is treated as supported only when the repository contains relevant code and a concrete parser, compiler, runtime, or test gate is available. Unverified languages remain on-demand and must earn a receipt before reviewer-facing use.

## Two-Lane Reasoning

The phrase "left and right hemispheres" is used only as a design metaphor. This repository makes no neuroscience or medical claim.

| Lane | Function | Required tension |
|---|---|---|
| Hypothesis | Generate candidate models, routes, and explanations | Must not see held-out outcomes when selecting a route |
| Falsification | Search for leakage, weak baselines, instability, and unsupported claims | Must preserve negative results |
| Integration | Reconcile both lanes into a versioned artifact | Must expose the decision and HumanUnlock gate |

## Ten Bounded Roles

| Role | Primary output | Maximum autonomy |
|---|---|---|
| Evidence Ingest | Source receipt and schema audit | Local read and stage |
| Protocol Freezer | Versioned split, metric, and gate | Local write with review |
| Baseline Gauntlet Runner | Named comparisons and failure ledger | Sandboxed compute |
| Hybrid Route Evaluator | Route policy, ablation, held-out predictions | Sandboxed compute |
| Falsification Critic | Counterexamples and claim corrections | Local report |
| Reproducibility Auditor | Rebuild and custody receipt | Sandboxed compute |
| Reviewer Context Builder | Supported and unsupported claim table | Local write with review |
| Funding Package Builder | Draft package and compliance matrix | Draft only |
| Counsel Packet Builder | Private manifest, issues, draft correspondence | Private draft only |
| External Action Operator | External receipt or blocked status | HumanUnlock required |

## Five Coordination Cadences

These are operational cadences, not acoustic or neurological frequencies.

1. **Event ingest:** identify, authorize, and date every new source.
2. **Artifact seal:** hash every material artifact and record its provenance.
3. **Change validation:** rerun targeted tests and report benchmark deltas after changes.
4. **Action unlock:** obtain a recipient-specific or portal-specific decision immediately before consequences leave the system.
5. **Release promotion:** publish only a scoped, reproducible, cited bundle with known limitations.

## Promotion Rule

A candidate becomes reviewer-facing only when all of the following are true:

- its data and protocol identity are frozen;
- named baseline and ablation results are preserved;
- non-wins and test failures are visible;
- the output can be regenerated from documented commands;
- the public claim is no stronger than the evidence maturity;
- private data, credentials, and privileged records are excluded;
- any external action has a fresh HumanUnlock receipt.

No agent role can self-promote evidence to independent validation. Level 5 requires a named external evaluator, an agreed held-out or field protocol, and a dated receipt.
