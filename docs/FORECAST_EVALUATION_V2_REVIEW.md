# Forecast evaluation v2: bounded offline review

This review path advances active outcome 2, one external validation or paid-pilot
conversion, by repairing the comparison boundary for the next owner-reviewed
evaluation. It is an adjunct to the existing [EIA computation note](CODECHECK_EIA_EXECUTABLE_COMPUTATION_NOTE_2026-07-20.md),
not a replacement result. Frozen v1 protocols, inputs, forecasts, metrics and
historical receipts remain unchanged.

`code/forecast_evaluation_v2.py` evaluates supplied forecasts. The included
protocol and two-entity CSV fixture are synthetic software checks. Their declared
publication times do not establish availability of historical EIA data. This
path does not train a model, query a provider or conduct a prospective trial.

## Run the synthetic review

Run from the repository root. This command pins the exact included protocol:

```bash
python code/forecast_evaluation_v2.py \
  --protocol config/forecast_evaluation_protocol_v2_synthetic.json \
  --protocol-sha256 bb9ab73f0dc4bb3bdac18220a8ecf66510a0b0eee2492dcab9f4fd52c3ecf617 \
  --predictions tests/fixtures/forecast_evaluation_v2/predictions.csv \
  --history tests/fixtures/forecast_evaluation_v2/history.csv \
  --json-out out/forecast_evaluation_v2/synthetic_review.json
```

The digest is mandatory. A previous digest cannot accept amended protocol bytes,
including whitespace changes. Invalid inputs fail before a review report is
written. A successful command produces `HUMAN_REVIEW_HOLD`; software acceptance
does not clear an evidence or promotion gate.

The command preserves an existing output instead of overwriting it. Choose a new
output path for another review. Without `--json-out`, it returns JSON on stdout.

## What the reviewer can inspect

- Every declared candidate and baseline must cover exactly the scheduled
  entity/calendar-date set. Missing rows, extra rows and duplicate identities
  fail. Paired strategies must agree on actual values and their availability.
- Issue times follow the locked UTC schedule. Predictions must be available by
  issue time, and scored actuals must become available afterward. History lags
  and seasonal pairs use retained calendar dates and only observations available
  at the issue cutoff. Missing dates cannot become observation-index lags.
  Seasonal MASE uses the mean absolute difference over available pairs exactly
  seven calendar days apart. Insufficient support or a zero scale fails; no
  undeclared denominator floor is applied.
- Timestamps use `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` with at most six fractional
  digits. Excess precision rejects instead of rounding a late publication into
  the accepted issue cutoff. Seasonal scale reads only the declared lookback
  calendar dates, at most 730 history lookups per target, preserving gaps and
  publication availability without scanning the full history for every target.
- Descriptive error summaries preserve every required comparison, adverse
  results and dependent observations. They do not interpret repeated rows as
  independent trials or supply a significance-based promotion decision.
- The protocol and input identities make the supplied evidence inspectable.
  The report also records current evaluator source and interpreter identities.
  A digest establishes byte identity; a reviewer still must verify the source,
  data rights, publication-time evidence and accepted operational comparator.

Run the adversarial and end-to-end software checks:

```bash
python -m pytest -q tests/test_forecast_evaluation_v2.py
```

The suite checks every strategy for damaged identity sets, contradictory actuals,
nonfinite values, ambiguous or late timestamps, unavailable history and calendar
gaps. It also checks mandatory protocol identity and the CLI report path.
Record the actual interpreter, test result and source identity with a review.
These stdlib fixture checks do not establish an exact Python 3.11.9 numerical
replay of the frozen capsule.

## Remaining decision

An owner and reviewer must agree the workflow, permissioned data, operational
baseline, metric, threshold, dependence model, prospective capture and one
go/no-go decision before any new evaluation can support promotion. The current
result remains `HUMAN_REVIEW_HOLD`; independent validation, prospective readiness,
operating performance and economic value remain unestablished.
