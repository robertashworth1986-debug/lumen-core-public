# Cross-sector scenario sensitivity

The existing pipeline is an offline calculator over three hardcoded examples.
It does not fetch infrastructure, health, financial, or government source feeds.
The ISO_NE, HHS_FEED and FEDWIRE_OPS labels are historical scenario labels.

## September 14 correction

Four synthetic regressions reproduced these legacy behaviors:

- a caller-supplied `gov_audit_ready` label and `key_present: true` appeared on a hardcoded example;
- a parameter sweep with `optimization_auto_apply: true` rewrote runtime configuration;
- the highest assumed detection/mitigation pair was presented as recommended operating parameters;
- zero detection efficiency was silently replaced with the 0.72 default, creating a positive modeled avoided-cost result.

The corrected calculator preserves the hypothetical formula and example inputs,
but labels every report `HARDCODED_SCENARIO` / `MODELED_ONLY`. Numerical fields
inside the model are hypothetical arithmetic. Measured savings, verified source
presence, operational failure time and recommendations remain unknown. The
sweep is pure and cannot apply parameters or write files. Higher assumed
fractions mechanically improve the formula; this is sensitivity analysis, not
learned detection/mitigation performance or a new experiment.

The legacy drift, confidence and lag clamps remain part of the stated formula.
They have no calibration or probability interpretation. Repeated runs do not
create new observations. No buyer ROI, agency readiness, grant eligibility,
realized savings, revenue or company valuation follows from these examples.

## Run the existing calculator

Use the reviewed Python environment and an explicitly named **new** directory:

```powershell
python code/execution/run_cross_sector_intel.py --output-dir path/to/new-scenario
```

Optional `--assumptions path/to/assumptions.json` reads a bounded 64 KiB JSON
object. Duplicate members, invalid numbers, unsafe axis sizes and invalid
budgets are rejected before creating outputs. The runtime configuration file
is not read implicitly and is never updated. Zero fractions remain zero.

The output directory contains:

- `scenario_report.json`: the declared inputs, base modeled records, sweep rows, evaluated maximum and limits;
- `scenario_matrix.csv`: numeric formula cases, not measured observations;
- `scenario_readme.md`: interpretation and evidence limits;
- `SCENARIO_MANIFEST.json`: sizes and SHA-256 hashes of those three files, supporting file custody only.

The grid has at most 101 values per axis and evaluates at most 5,000 cases.
A truncated sweep is labeled, and its maximum is only the maximum among the
evaluated cases. It is not an operating recommendation. Requested auto-apply
is recorded but always remains disabled. Output directories cannot be reused,
so old scenario runs and historical evidence are preserved.

## Compatibility and delivery boundary

Legacy invocations without `--output-dir` now exit 2 with a usage message.
The wrapper keeps its existing path. Direct `run_pipeline()` callers must pass
an output directory. `run_optimization_simulations()` returns a report without
writing output. `freeze_delta()` is retained as a compatibility name for a
modeled record; it does not freeze, append or authenticate evidence.

The calculator no longer appends to the shared infrastructure ledgers, writes
`investor_and_grant_evidence.json`, produces operational failure timestamps,
updates runtime settings, or feeds federal/investor summaries automatically.
Historical files and the original running checkout were not changed. Other
legacy consumers and generated summaries require their own review; changing
this source does not retrospectively correct those reports or activate a new
runtime. Use the buyer-owned evaluation and economic-conversion gates for any
actual measurement or commercial claim.
