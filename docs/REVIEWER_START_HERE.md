# Reviewer Start Here

This page separates the current public execution check, the retained hourly packet,
and the historical predecessor record. They answer different questions and must not
be combined into a stronger claim.

## Current State

- Repository-wide supported evidence maturity: **Level 3**.
- CODECHECK author packet: `AUTHOR_PACKET_READY_FOR_HUMAN_REVIEW`.
- Reviewed executable-computation source: `1c0eb51754beffac6f4df484914e35efc21c253f`.
- Hourly packet snapshot: `486` predictions and `469` settlements.
- Later runtime diagnostic: `546` predictions and `486` settlements. It is not
  substituted into the frozen packet.
- Common settled hours across all eight hourly authorities: `0`.
- Independent execution, CODECHECK assignment, certificate, external validation,
  field validation, agency acceptance, performance promotion, realized savings,
  trading performance, patent scope, and valuation validation: **not established**.

GitHub checks are head-specific. Read the checks attached to the exact pull-request
head; do not infer current CI state from an older receipt or run.

## Choose One Review Decision

| Route | Exact question | Public starting point | Current boundary |
|---|---|---|---|
| CODECHECK executable computation | Can an independent runner reproduce the six outputs declared by `codecheck.yml` from the pinned public source? | `docs/CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md` | Author packet ready; independent execution and certificate false |
| EIA hourly packet | Can a reviewer rehash the retained packet and independently recompute its chains, settlement arithmetic, and authority coverage? | `docs/EIA_GRID_HOURLY_INDEPENDENT_REPRODUCTION_HANDOFF_2026-07-21.md` | Retained ZIP required; completed external receipt absent |
| Historical daily predecessor | Did the earlier evaluator-acceptance controls reconcile? | `docs/EXTERNAL_EVALUATOR_ACCEPTANCE_HANDOFF_2026-07-14.md` | Historical only; it does not govern the hourly successor |

## Fast Author-Packet Check

From the current review branch, run the non-mutating readiness check first:

```powershell
python code/ops/BUILD_CODECHECK_EIA_READINESS.py --check-only
```

Expected status: `PASS`. This checks author-side artifact coherence only. It is not
an independent run, CODECHECK acceptance, scientific validation, or a certificate.

Read next:

1. `docs/CODECHECK_EIA_AUTHOR_READINESS_2026-07-20.md`
2. `docs/preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf`
3. `codecheck.yml`
4. `CITATION.cff`
5. `LICENSE`

## Independent CODECHECK Execution

The reviewed public source is frozen at commit
`1c0eb51754beffac6f4df484914e35efc21c253f`. On Ubuntu 24.04 x86-64 with
CPython 3.11.9 and glibc 2.39:

```bash
git clone https://github.com/robertashworth1986-debug/lumen-core-public.git
cd lumen-core-public
git checkout 1c0eb51754beffac6f4df484914e35efc21c253f
python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only
python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py
python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --requirement requirements-reviewer-ubuntu-py311.lock
python -m pip check
python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia
```

The bounded capsule declares three suites, 31 machine assertions, and six manifest
outputs. The source includes negative gates, and a passing execution must preserve
them. The repository's existing receipts are operator-controlled and remain
first-party evidence. Only an independently controlled execution and external report
can change that state.

The exact community-request draft is intentionally held at
`docs/CODECHECK_COMMUNITY_REQUEST_DRAFT_2026-07-21.md`. Its Launch Pad identifier
currently collides with an existing open register issue. Do not open a production
request until that collision is resolved, duplicate-request reconciliation is fresh,
Robert has reviewed the packet, and action-time HumanUnlock is recorded.

## EIA Hourly Packet Review

The public repository binds the retained packet by filename, size, hashes, protocol,
and terminal chains. Raw runtime bytes and the packet ZIP are not public, so the
hourly packet cannot be independently reproduced from this repository alone.

After an authorized transfer and independent ZIP-hash check, extract the packet and
run:

```powershell
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir .
python code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py --packet-dir . --receipt REVIEWER_RECEIPT_TEMPLATE.json --expect-template
```

Current public records:

- `evidence/external_validation/eia_grid_hourly_independent_reproduction_handoff_20260721.json`
- `evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260721.json`
- `config/eia_grid_hourly_independent_reproduction_receipt_template_20260721_v1.json`

The operator may not fill reviewer identity, independence, execution, decision, or
signature fields. A completed receipt requires reviewer-controlled independence
evidence and a detached signature artifact. Even a valid receipt would establish
only the bounded packet facts; it would not convert the incomplete authority panel
into a performance pass.

## Historical Predecessor Controls

The preserved predecessor files remain useful for control design and audit history:

```powershell
python code/ops/BUILD_EXTERNAL_VALIDATION_AUTHORITY_DOCKET.py --check-only
python code/ops/VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py --expect-template
```

Their handoff is `docs/EXTERNAL_EVALUATOR_ACCEPTANCE_HANDOFF_2026-07-14.md`.
It must be explicitly amended or replaced before it can govern the hourly successor.

## Independent Review Roles

| Review role | Decision owned by reviewer | Evidence or receipt |
|---|---|---|
| Reproducibility reviewer | Can the bounded public result be replayed from pinned inputs on an independent runner? | Capsule receipt, logs, SBOM, checksums, and external report |
| Domain and data owner | Are the source, eligible population, exclusions, baselines, and operational metric suitable for the stated use? | Dated protocol acceptance and authority artifact |
| Security and privacy reviewer | Are custody, access, dependency, secret-scanning, privacy, and HumanUnlock controls adequate for the bounded evaluation? | Scoped findings, disposition record, and artifact hashes |
| Independent technical evaluator | Did the frozen prospective experiment meet its predeclared gate without operator substitution or backfill? | Completed evaluator-owned acceptance and result receipts |

Each role is independent of the operator. A reviewer may accept one bounded decision
without endorsing the platform, a patent, an agency use, or a commercial claim.

## Claim Check

| Question | Current answer |
|---|---|
| Is the platform implemented? | Yes, for the bounded workflows represented by code and tests |
| Are source-conditioned comparisons recorded? | Yes, with both wins and non-wins |
| Is prospective performance established? | No; the current hourly sample gates remain false |
| Has an independent evaluator validated the platform? | No Level 5 receipt or CODECHECK certificate is present |
| May this repository authorize a submission, legal filing, spend, live order, or external contact? | No; those actions require their own HumanUnlock and duplicate-action checks |

Use `CITATION.cff` for the software record. Cite the exact dated evidence artifact
separately for any result-specific statement.
