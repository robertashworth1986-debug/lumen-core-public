# MDA Control-Mapping Feasibility Preregistration

Prepared: 2026-07-13

Protocol: `config/mda_control_mapping_feasibility_protocol_v1.json`

## Question

Can a deterministic static-first, lexical-second, abstaining router improve synthetic control-mapping feasibility metrics over a static identifier crosswalk and TF-IDF lexical retrieval while preserving complete provenance and a low unsupported-mapping rate?

## Why Synthetic First

No lawful representative ACAS, Nessus, or SCAP corpus is currently documented in the repository. Synthetic fixtures can test parsers, routing, failure handling, metrics, and receipts without pretending to establish operational cyber accuracy. The synthetic lane is therefore a software conformance gate before partner data, not a substitute for it.

## Frozen Elements

- 96 deterministic fixtures across eight synthetic control archetypes
- 48 development, 24 validation, and 24 blind-holdout records
- explicit ambiguous and unsupported cases
- static identifier-crosswalk baseline
- TF-IDF lexical-retrieval baseline
- static-first, lexical-second hybrid candidate with abstention
- fixed threshold grid and validation-only threshold selection
- primary and secondary metrics
- parser, provenance, coverage, unsupported-mapping, and baseline-delta gates
- full negative-result retention and strict claim boundary

## Promotion Boundary

Even a complete synthetic pass remains feasibility evidence only. The next gate requires lawfully obtained representative artifacts, a qualified cyber/RMF reviewer, and an independently held blind set. No operational, compliance, CMMC, MDA, savings, or production claim can be made from this protocol.
