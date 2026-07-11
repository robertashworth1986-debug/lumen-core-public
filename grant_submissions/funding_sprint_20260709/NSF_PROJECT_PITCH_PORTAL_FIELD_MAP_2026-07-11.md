# NSF Project Pitch Portal Field Map - 2026-07-11

- Opportunity: `26-511`
- Portal: NSF Seed Fund Project Pitch
- Status: `PORTAL_READY_DRAFT_HUMAN_SUBMIT_REQUIRED`
- External submit without human: `false`
- Final submit without human: `false`
- Source constraint: NSF Project Pitch asks for four fields: Technology Innovation up to 3500 characters, Technical Objectives and Challenges up to 3500 characters, Market Opportunity up to 1750 characters, and Company and Team up to 1750 characters.

## Technology Innovation

LumenCore is building proof-to-pilot instrumentation for validating AI infrastructure claims before buyers deploy AI systems in operational environments. The innovation is not another dashboard or model wrapper. It is an evidence instrument that freezes source data, records provenance, locks an incumbent baseline and acceptance metric before scoring, runs candidate-vs-baseline replay, and packages the result into a traceable proof manifest for technical and commercial reviewers.

Infrastructure AI evaluation is fragmented. Buyers are often asked to trust vendor claims, ad hoc demos, or retrospective benchmarks that do not preserve data lineage, baseline selection, acceptance thresholds, and replay reproducibility in one reviewer-safe package. This is especially painful for data centers, utilities, labs, transportation operators, and technical buyers that must distinguish real performance improvement from overfit demonstrations before authorizing pilots.

Phase I would convert LumenCore from an internal proof stack into a repeatable scientific instrumentation product for AI validation. The platform will ingest public or buyer-authorized operational data, compute source-quality measurements, preserve hashes and run metadata, register locked evaluation plans, execute replay against pre-selected baselines, and produce a machine-readable evidence manifest plus a human-readable validation packet.

The high-risk technical question is whether heterogeneous AI infrastructure evaluation can be converted into an instrument-grade workflow that preserves provenance, prevents metric leakage, supports fair baseline comparison, and generates evidence that both technical reviewers and commercial buyers can trust.

## Technical Objectives And Challenges

Objective 1: Build an instrument-grade replay controller. The controller will register evaluation plans before scoring, including source identifiers, allowed transformations, incumbent baseline, candidate method, acceptance metric, holdout policy, and run configuration. Success means each run can be reproduced from the manifest and checked for metric or baseline drift.

Objective 2: Implement a source provenance and measurement gate. The system will ingest public or buyer-authorized datasets, compute freshness, completeness, schema, numeric coverage, hash, and transformation records, and block scoring when source quality falls below pre-registered thresholds. Success means every result is tied to source-quality measurements rather than unverified data pulls.

Objective 3: Create a baseline/candidate scoring module for infrastructure AI workflows. Phase I will test at least three controlled domains, such as energy, weather/environmental, and transportation/operations data, using simple incumbent baselines and candidate algorithms. Success means the same replay protocol can evaluate different data domains without changing the evidence standard.

Objective 4: Produce evidence manifests and reviewer packets. Each validation run will output a machine-readable manifest, summary table, visualization, and plain-English claim boundary. Success means reviewers can see what was measured, what was compared, what was excluded, and what evidence is not yet proven.

Key challenges include source heterogeneity, metric leakage, baseline selection bias, overfitting to public datasets, run reproducibility, and translating technical proof into buyer-readable evidence without overstating results. LumenCore will manage these risks through locked evaluation plans, hash-based provenance, pre-selected acceptance metrics, explicit claim boundaries, and repeatable replay against public and buyer-authorized datasets.

## Market Opportunity

AI infrastructure buyers need a practical way to validate technical claims before they authorize pilots, procurement, or deployment. Initial customers include data center operators, utilities, energy analytics teams, national and university labs, transportation and infrastructure operators, and enterprise AI teams that must prove model or workflow improvements under operational constraints.

Current alternatives include generic ML observability, model evaluation tools, consulting studies, vendor demos, and manual spreadsheet-based pilots. These approaches often fail to combine buyer-authorized data capture, locked evaluation plans, baseline/candidate replay, source-quality measurement, and reviewer-ready proof packages.

LumenCore's opportunity is to become the evidence layer between AI vendors and infrastructure buyers: a validation product that helps buyers decide which claims are ready for pilots and helps vendors present proof without relying on unsupported marketing.

## Company And Team

LumenCore is led by Robert Ashworth, a technical founder building an AI infrastructure validation platform from Nashville, Tennessee. Robert has built the current proof stack, public proof portal, live-source measurement workflow, replay artifacts, grant/funding evidence packages, and early federal submission materials.

The company is early and pre-revenue. Phase I funds would be used to harden the validation instrument, document reproducibility, add independent technical review, and prepare pilot-ready evidence packages. Near-term hiring or contracting needs include a senior software/AI validation engineer, a data provenance/security reviewer, and domain advisors in energy, infrastructure operations, or scientific computing.

LumenCore's advantage is speed of iteration and evidence discipline: the company separates measured proof from aspirational claims, preserves source and replay boundaries, and packages evidence in a way reviewers can inspect.

## Human Gate

- Confirm no NSF Project Pitch is currently pending for the same company.
- Confirm company profile, ownership, PI eligibility, and authorized submitter information.
- Robert approves final portal submit.

