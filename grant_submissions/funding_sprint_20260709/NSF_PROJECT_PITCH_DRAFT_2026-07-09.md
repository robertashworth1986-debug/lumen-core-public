# NSF Project Pitch Draft - LumenCore

## Working Title
LumenCore Proof-to-Pilot Instrumentation for AI Infrastructure Validation

## Suggested NSF Framing
- Solicitation: NSF SBIR/STTR Scientific Instrumentation Pilot, NSF 26-511.
- Topic fit: Scientific instrumentation, artificial intelligence, trustworthy AI, infrastructure validation.
- Company stage: pre-revenue / pilot-stage small business.
- Submission caution: submit only if no other NSF Project Pitch is pending, invited, or under review.

## Technology Innovation

LumenCore is building a proof-to-pilot instrumentation platform for validating AI infrastructure claims before buyers deploy them in operational environments. The innovation is not another dashboard or model wrapper; it is an evidence instrument that freezes source data, records provenance, locks an incumbent baseline and acceptance metric before scoring, runs candidate-vs-baseline replay, and packages the result into a traceable proof manifest for technical, commercial, and grant reviewers.

Today, infrastructure AI evaluation is fragmented. Buyers are asked to trust vendor claims, ad hoc demos, or retrospective benchmarks that do not preserve data lineage, baseline selection, acceptance thresholds, and replay reproducibility in one reviewer-safe package. This is especially painful for utilities, labs, data centers, transportation operators, and other technical buyers who need to distinguish real performance improvement from overfit demonstrations before authorizing pilots.

The proposed Phase I work would convert LumenCore from an internal proof stack into a repeatable scientific instrumentation product for AI validation. The platform will ingest public or buyer-authorized operational data, compute source-quality measurements, preserve hashes and run metadata, register locked evaluation plans, execute replay against pre-selected baselines, and produce a machine-readable evidence manifest plus a human-readable validation packet. The long-term product goal is to make AI validation auditable enough for technical buyers to compare candidate systems, replicate scoring, and advance only those improvements that survive controlled replay.

Existing internal evidence supports feasibility but is intentionally bounded. LumenCore currently tracks a 29-source inventory with 25 measured providers and 2,580 measured rows in its latest live-source measurement artifact. Its internal replay stack has produced champion-vs-baseline results across source-conditioned scenarios, but those results are not being represented as field validation or realized savings. Phase I will replace ad hoc internal proof with a controlled, repeatable instrumentation workflow that can be tested on public benchmark-style infrastructure data and prepared for independent pilot review.

The high-risk technical question is whether heterogeneous AI infrastructure evaluation can be converted into a repeatable instrument-grade workflow that preserves provenance, prevents metric leakage, supports fair baseline comparison, and generates evidence that both technical reviewers and commercial buyers can trust. If successful, LumenCore would provide a new validation layer for the trustworthy deployment of AI in infrastructure settings.

## Technical Objectives And Challenges

Objective 1: Build an instrument-grade replay controller. The controller will register evaluation plans before scoring, including source identifiers, allowed transformations, incumbent baseline, candidate method, acceptance metric, holdout policy, and run configuration. Success means each run can be reproduced from the manifest and checked for metric or baseline drift.

Objective 2: Implement a source provenance and measurement gate. The system will ingest public or buyer-authorized datasets, compute freshness, completeness, schema, numeric coverage, hash, and transformation records, and block scoring when source quality falls below pre-registered thresholds. Success means every result is tied to source-quality measurements rather than unverified data pulls.

Objective 3: Create a baseline/candidate scoring module for infrastructure AI workflows. Phase I will test at least three controlled domains, such as energy, weather/environmental, and transportation/operations data, using simple incumbent baselines and candidate algorithms. Success means the same replay protocol can evaluate different data domains without changing the evidence standard.

Objective 4: Produce evidence manifests and reviewer packets. Each validation run will output a machine-readable manifest, summary table, visualization, and plain-English claim boundary. Success means reviewers can see what was measured, what was compared, what was excluded, and what evidence is not yet proven.

Key technical challenges include source heterogeneity, metric leakage, baseline selection bias, overfitting to public datasets, run reproducibility, and translating technical proof into buyer-readable evidence without overstating results. LumenCore will manage these risks through locked evaluation plans, hash-based provenance, pre-selected acceptance metrics, explicit claim boundaries, and repeatable replay against both synthetic and public datasets.

Phase I success metrics: (1) complete replay workflow for three infrastructure-relevant domains; (2) evidence manifests reproduce run configuration, hashes, metrics, and baseline/candidate outputs; (3) at least one controlled candidate-vs-baseline evaluation per domain; (4) no result published without source-quality and claim-boundary metadata; and (5) external advisor or pilot stakeholder review of the evidence packet format.

## Market Opportunity

AI infrastructure buyers need a practical way to validate technical claims before they authorize pilots, procurement, or deployment. Initial customers include utilities, energy analytics teams, national and university labs, data center operators, transportation and infrastructure operators, and enterprise AI teams that must prove model or workflow improvements under operational constraints. These buyers face high switching costs, safety and reliability concerns, procurement scrutiny, and pressure to document why one AI system should be trusted over an incumbent baseline.

Current alternatives include generic ML observability, model evaluation tools, consulting studies, vendor demos, and manual spreadsheet-based pilots. These approaches often fail to combine buyer-authorized data capture, locked evaluation plans, baseline/candidate replay, source-quality measurement, and reviewer-ready proof packages. LumenCore's opportunity is to become the evidence layer between AI vendors and infrastructure buyers: a validation product that helps buyers decide which claims are ready for pilots and helps vendors present proof without relying on unsupported marketing.

The initial business model is a paid proof-to-pilot package for technical buyers and AI vendors, followed by recurring validation workspaces for teams that need repeated evaluations across datasets, models, and operational sites. A successful NSF Phase I would fund the technical hardening needed to turn LumenCore from founder-built proof stack into a repeatable product. Phase II would support pilot deployments, integrations, security hardening, and commercial evidence workflows.

## Company And Team

LumenCore is led by Robert Ashworth, a technical founder building an AI infrastructure validation platform from Nashville, Tennessee. Robert has built the current proof stack, public proof portal, live-source measurement workflow, replay artifacts, grant/funding evidence packages, and early federal submission materials. Recent activity includes DSIP access, a submitted DARPA DICE abstract, SBIR-focused LumaJet and LumaSuit/LumaSkin concept tracks, and active outreach to venture, infrastructure, and lab validation channels.

The company is intentionally early and pre-revenue. Phase I funds would be used to harden the validation instrument, document reproducibility, add independent technical review, and prepare pilot-ready evidence packages. Near-term hiring or contracting needs include a senior software/AI validation engineer, a data provenance/security reviewer, and domain advisors in energy, infrastructure operations, or scientific computing.

LumenCore's advantage is speed of iteration and a clear evidence discipline: the company separates measured proof from aspirational claims, preserves source and replay boundaries, and packages evidence in a way reviewers can inspect. The main company risk is that the current stack is founder-built and needs independent validation, product hardening, and focused pilot partners. NSF Phase I is the right next step because it funds exactly that transition: from promising technical proof stack to reviewer-safe scientific instrumentation for trustworthy AI validation.
