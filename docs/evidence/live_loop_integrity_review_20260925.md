# Live-loop integrity review — September 25, 2026

**Active outcome:** 2 — one external validation or paid-pilot conversion.  
**Evidence type:** First-party source inspection and local regression tests.  
**Base commit:** `dfc45fe2a05102c835dafe05d9b847cd04566086`.  
**Scope:** Existing source monitor, government collection summary and public
live-breadth manifest. This receipt covers the working-file identities below;
it is not a deployment or independent-validation receipt.

## Observed defects and corrections

| Component | Failure reproduced or inspected | Correction and boundary |
|---|---|---|
| API source monitor | The monitor expected a registry `sources` list and a flat provider mapping; the checked-in inputs use `rows` and a `providers` mapping. Metadata could be treated as a provider and cause a crash. | Normalize the supported canonical and legacy shapes. Reject malformed, duplicate or conflicting source definitions. The checked-in 17-source registry can now be evaluated without reviving archived observations. |
| Probe health | Credential presence and registry status could substitute for successful probe evidence; missing timestamps were not necessarily stale. | ACTIVE requires enabled=true, probe_ok=true and a timezone-qualified, non-future timestamp within a finite positive age limit. Key diagnostics stay separate. The monitor makes no network request and marks dataset readiness NOT_EVALUATED. |
| Collection summary | A failed direct check could be replaced by a historical successful registry record; archived providers could also enter current counts. | Count only current direct checks with explicit boolean success and a positive integer item count. Retain registry information under historical context, without live-success authority. Preserve failed checks and their errors. |
| Count meaning | Metadata entries, content objects and output-field counts were added to data-row totals. | Keep returned data rows separate from heterogeneous response items. Neither counter establishes a decision-ready dataset or unique portfolio coverage. |
| Diagnostic redaction | Error-string handling prefixed credential values with REDACTED_ while retaining the original value. | Remove the complete named credential assignment value, including mixed-case and quoted assignments. Invalid URLs are withheld rather than returned unredacted. This is a scoped redaction regression check, not a comprehensive secret audit. |
| Manifest freshness | A fresh probe and dataset hash could permit readiness with no snapshot observation time or with an old/future snapshot timestamp. | Gate snapshot age separately from probe age. Missing, malformed, timezone-free, future or stale snapshot observations fail readiness. Use the accepted finite positive max_age_hours independently for both clocks. |
| Boundary arithmetic | Fractional count/threshold coercion and rounded age comparisons could turn invalid or just-stale inputs into a pass. | Reject fractional counts and compare unrounded elapsed time against the threshold; retain exact-boundary inclusion. |

The governance example now exposes `dataset_snapshot_observed_utc` as an
explicit required-to-complete field. Existing historical manifest bytes were
not regenerated and no source-owner approval was invented.

## Validation

Environment: Python **3.12.14**, pytest **9.1.1**, local Linux workspace.

From the repository root with the test dependencies installed:

```sh
python3 -m pytest -q \
  tests/test_api_source_agent_monitor.py \
  tests/test_canonical_gov_data_collector.py \
  tests/test_public_live_breadth_manifest.py \
  tests/test_live_breadth_governance_worklist.py \
  tests/test_live_breadth_claim_safety.py \
  tests/test_public_live_breadth_provenance_gate.py \
  tests/test_gov_snapshot_guard.py
```

Observed result: **134 passed in 1.07s**. The actual interpreter used was the
workspace's `../loop-venv/bin/python3`. `git diff --check` passed for the reviewed
changes. No provider collection was invoked. Collector tests use local fixtures
and explicitly guard import against credential reads, output writes and
network requests. Monitor CLI tests write only into temporary test directories.

This is a focused regression suite, not a complete repository test pass,
performance benchmark, prospective holdout, exact-commit CI result, security
certification or external audit. Test count does not measure independent model
evidence or customer value.

## Reviewed source identities

SHA-256 values identify the changed executable/configuration/test bytes used in
the focused check. A later edit requires a new check and updated identity.

| File | SHA-256 |
|---|---|
| `code/CANONICAL_GOV_DATA_COLLECTOR.py` | `2b97ba4f300efe2aa97cfacbb3c6c6be46661c38bffb10a995bbb41481c4c989` |
| `code/ops/build_api_source_agent_monitor.py` | `bccdb119a2d455bc82e92a171e5ba89f9ef2141fc96c041cd8dcddf4938b2fad` |
| `code/ops/build_public_live_breadth_manifest.py` | `07df3f95b95b5e07adf559e26580f9ecaa8003286633c71355f83b7fbc8471e4` |
| `config/public_live_breadth_governance.example.json` | `acce129947502eb6cb7ce5b3db8f1a60a5d3e22a900f29fa57c4129180725052` |
| `tests/test_api_source_agent_monitor.py` | `e651459eb60320b3f974f2ffd23dac5f9caf8fb8d3035caac4dd9bebc31fe402` |
| `tests/test_canonical_gov_data_collector.py` | `af9174f1a37092e792793ed3a7eeeaa0f9da129b8869c82f2871195249404df2` |
| `tests/test_public_live_breadth_manifest.py` | `f86bdbddec6391853a1106a6917b318457e5fb0bf2ac95a4304eab9d48f84cff` |

## Remaining operating gates

1. Run the reviewed collectors only in the authorized runtime, preserving
   source identity, actual receipt time, errors and capacity limits. A web page
   returning HTTP 200 or an archived successful probe does not establish
   current provider availability.
2. Bind each permissioned dataset snapshot to its hash, observation time,
   rights, decision relevance and accepted thresholds. Check measurement/issue
   times and availability at the decision cutoff separately from receipt age.
3. Apply the accepted comparison contract to matched eligible rows, retaining
   missingness, exclusions, adverse subgroups and all failed promotion gates.
   Existing frozen EIA packets remain unchanged and on HOLD.
4. Freeze any newly measured comparison only after reproduction and review.
   Connect an accepted improvement to a buyer-owned action and economic
   denominator before making a savings claim.

No live feed was probed by this repair pass; no current provider-health claim,
continuous scheduling proof, new delta, savings, revenue, external acceptance
or production deployment follows from it. The public application telemetry
check and upstream provider collection are separate observations: failure of
the former alone does not diagnose every upstream source.
