# LumenCore Platform, Proof, and Commercialization Map

Updated: August 19, 2026

## What Was Built

LumenCore is currently four related products sharing an evidence layer:

1. **Market intelligence and guarded execution** ranks symbols, timing windows,
   and risk signals, then records paper and historical execution evidence.
2. **Forecast and evidence lab** benchmarks model families across 673 datasets
   and trains routers and stackers to choose among them.
3. **Grant factory** qualifies opportunities, creates application packages,
   checks blockers, and preserves submission artifacts.
4. **LumaScout** ranks artist discovery signals and produces auditable
   shortlists.

Frozen deltas, manifests, hashes, ledgers, and proof packs are the shared
evidence infrastructure. They make a result reproducible and reviewable. They
do not create economic value by themselves.

## Active Production Graph

The public VPS runs the gateway/API, dashboard refresh, LumaScout API, paper
ticker, and symbol-awareness services. The large `live_executor.py` and
`execution_orchestrator.py` are separate engines and are not the public VPS
paper loop. Their presence and line count do not mean they are combined or
authorized.

The authoritative runtime gate currently reports:

- mode: `paper`
- execution authorized: `false`
- allow live orders: `false`
- paper enabled: `true`

## Evidence Status

### Supported

- Reproducible 673-dataset benchmark artifacts exist.
- The measured benchmark supports adaptive routing and stacking as useful model
  selection methods.
- Harmonic methods win on a subset of series, not universally.
- Public APIs, paper-execution controls, grant package generation, and
  evidence-building code exist. A runtime ledger or audit chain is not treated
  as reconciled until the read-only reconciliation receipt passes.

### Not Yet Supported

- Profitable live or institutional trading performance.
- Universal harmonic superiority.
- Physical FlowForm, hardware phase-locking, thermal, impedance, or battery
  performance claims.
- Realized multibillion-dollar savings.
- A fixed government or commercial price for each frozen delta.

The exploratory V6 harmonic-versus-backprop script contains holdout leakage.
Use `docs/HARMONIC_VALIDATION_PROTOCOL.md` for the required V7 evidence gate.

## Patent Boundary

Local records contain a USPTO application receipt and multiple draft invention
families. A filing receipt is evidence that an application was submitted; it is
not an issued patent, a validity opinion, or proof that every later software
feature is covered.

The hardware geometry, identity architecture, and software evidence/trading
systems must be mapped as separate invention families. Software benchmark
results do not prove curved-PCB, thermal, impedance, battery, or physical
phase-locking claims. Current application status and deadlines must be checked
in USPTO Patent Center and reviewed with a registered patent practitioner.

## Commercial Path

The shortest credible revenue path is:

1. Submit one narrow NSF Project Pitch around a measurable, technically risky
   evidence-routing or decision-integrity innovation.
2. Sell a scoped pilot with a named baseline, acceptance metric, data boundary,
   implementation cost, and reproducible result package.
3. Convert successful pilots into evidence-platform licensing or managed
   validation services.
4. Treat trading as a separate capital-risk product. Start live only after
   positive forward evidence after fees and slippage, reconciliation, risk
   limits, and a tiny canary allocation.

The current paper record is negative and is therefore a live-capital blocker,
not a reason to bypass paper validation.

## Paper Ledger Reconciliation Boundary

The paper ledger uses JSONL as its authoritative record. New records use a
deterministic hash chain anchored to the terminal legacy or current record.
The CSV is a derived mirror rebuilt from the union of observed fields, so buy
and sell rows cannot silently acquire different widths. Audit-chain appenders
verify their existing chain and use an exclusive append lock before writing.

`code/ops/VERIFY_PAPER_LEDGER_RECONCILIATION.py` is read-only and fails unless
the JSONL record hashes, CSV parity, audit hash chain, and ledger-to-audit links
all pass. `code/ops/MIGRATE_PAPER_LEDGER_RECONCILIATION.py` never rewrites the
source files: it requires an explicit acknowledgement, preserves the source
audit bytes, rebuilds the CSV into a new destination, and labels imported
ledger links as retrospective migration custody.

A passing reconciliation receipt proves internal file integrity and linkage.
It does not prove alpha, profitability, external validation, production
readiness, or authority to trade live capital.

## Immediate Priorities

1. Preserve and migrate any legacy paper ledger that fails the reconciliation
   receipt before restarting its writer.
2. Finish the actionable NSF Project Pitch.
3. Verify or renew SAM.gov, Grants.gov linkage, and AOR authority.
4. Remove stale grant opportunities and use official deadlines.
5. Run leakage-free V7 validation with surrogate and bootstrap tests.
6. Produce one customer-facing frozen delta tied to a real baseline and paid
   pilot acceptance criterion.
