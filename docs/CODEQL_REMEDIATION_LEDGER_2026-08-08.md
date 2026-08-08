# CodeQL Remediation Ledger — 2026-08-08

## Review boundary

This is a remediation ledger, not a certification and not a zero-finding claim.
It records the first bounded response to the CodeQL analysis enabled by the
repository security-assurance work.

Baseline source commit: `ff834a8189b9e5e136730b267de9b78c75dce48f`

At capture time GitHub reported:

- 124 open CodeQL alerts
- 88 high-severity alerts
- 36 medium-severity alerts
- no critical-severity alerts

The largest rule groups were:

- 22 Python stack-trace exposure alerts
- 20 JavaScript incomplete URL-substring sanitization alerts
- 18 Python clear-text storage alerts
- 15 Python path-injection alerts
- 10 Python clear-text logging alerts
- 9 JavaScript client-side request-forgery alerts
- 9 JavaScript XSS alerts

## Tranche 1 — active API and dashboard boundaries

This change addresses active/public or operator-facing routes before legacy and
offline tooling:

- grant IDs no longer become filesystem paths in `code/grants_api.py`
- forecast dataset IDs select only server-enumerated CSV files
- grant print HTML escapes application, budget, note, route, and run content
- API failures return bounded public messages instead of exception strings
- external grant links require HTTPS and an explicit government/program domain
  allow-list
- grant routing no longer trusts hostname substrings or unanchored URL regexes
- live toast, forecast log, command palette, print bundle, evidence table, and
  sector-opportunity views use DOM node construction for streamed values
- evidence-run query parameters are constrained to known local bases and strict
  UTC identifiers

Regression coverage:

```text
python -m pytest -q tests/test_active_surface_security.py tests/test_api_auth_fail_closed.py
python -m pytest -q tests/test_repository_security_assurance.py tests/test_repository_trust_policy.py tests/test_institutional_readiness.py tests/test_institutional_assurance_crosswalk.py tests/test_active_surface_security.py
```

## Remaining backlog

The remaining alerts must be reviewed by execution context, not bulk-dismissed.
The next priority groups are:

1. sensitive-value logging/storage in execution, registry, and grant-factory
   tooling;
2. legacy gateway path and exception exposure;
3. legacy/offline dashboard HTML sinks;
4. remaining request-forgery and redirect findings;
5. test-only or generated-artifact findings that need a documented
   false-positive decision, source repair, or quarantine.

## Gate

- GitHub CodeQL must evaluate this branch before alert-resolution counts are
  reported.
- Existing alerts are not dismissed merely to improve a count.
- Production deployment remains **HOLD** until the separately governed public
  snapshot and live-domain verification gates pass.
