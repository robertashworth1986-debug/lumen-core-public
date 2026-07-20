# LumenCore External Replication Docket v1

**Purpose:** Convert an internal result into a pre-registered, independently executable evaluation contract without allowing founder-authored status, hashes, or prose to impersonate outside validation.

**Current state:** `template_unassigned` / `HOLD`

The docket is not a scientific endorsement, certification, customer agreement, government authorization, or field result. It is the machine-readable contract that must be completed before a qualified evaluator can generate stronger evidence.

## Why this exists

The strongest remaining valuation and credibility gap in LumenCore is not a shortage of concepts, code, or internal tests. It is the absence of a repeatable outside-review protocol that prevents post-outcome tuning, holdout leakage, selective reporting, ambiguous authority, and claim inflation.

The docket addresses that gap by separating five layers:

1. **Pre-registration** — source rights, hypothesis, comparator, primary metric, threshold, uncertainty method, sample-adequacy plan, exclusions, failures, and stop rules are fixed before scoring.
2. **Custody** — the docket, code revision, dependencies, environment, manifests, and run receipt are hash-addressed.
3. **Independence** — evaluator identity, relationship, conflicts, data control, run control, analysis control, and publication permission are explicit.
4. **Replication** — a second environment, offline verifier, tolerance rule, negative-result register, and deviations register are mandatory.
5. **Decision** — `hold`, `reject`, `rerun`, `independent_replication`, or `pilot_candidate`; no other status is accepted.

## Canonical state machine

| State | Meaning | Strongest allowed decision |
|---|---|---|
| `template_unassigned` | No evaluator, dataset, or frozen protocol exists | `hold` |
| `preregistered` | Rights, evaluator, protocol, holdout, code, environment, and analysis plan are frozen | `hold` or `independent_replication` |
| `internal_complete` | LumenCore completed the frozen run, but external run and attestation are absent | `hold`, `reject`, `rerun`, or `independent_replication` |
| `external_complete` | A non-founder-controlled evaluator completed the frozen run and recorded the required receipt and attestation | any bounded decision, including `pilot_candidate` |
| `rejected` | The hypothesis, design, integrity, rights, or result failed the declared gate | `reject` |
| `retired` | The docket is preserved as history and is no longer active | bounded archival state |

`pilot_candidate` does not authorize a pilot. It means only that the named evaluator's bounded result may be considered by a separate buyer or authority owner.

## Nine promotion gates

The machine-readable docket carries nine explicit gates:

1. source rights resolved;
2. evaluator assigned;
3. protocol frozen;
4. holdout locked;
5. code pinned;
6. environment locked;
7. analysis plan locked;
8. external run complete;
9. reviewer attestation present.

A template cannot assert any gate. `external_complete` requires all nine. An unknown field such as `action_authority`, `portal_submission_authorized`, or `certification_authorized` is rejected rather than silently accepted.

## Anti-bias and anti-p-hacking controls

Every docket requires:

- one primary metric;
- a null hypothesis and an explicit falsification condition;
- inclusion and exclusion rules fixed before holdout exposure;
- a locked threshold and direction;
- a confidence or uncertainty method;
- a power, precision, coverage, or minimum-sample justification;
- a multiplicity policy for secondary analyses;
- missing-data, outlier, incomplete-run, failure, and stop rules;
- no post-outcome tuning;
- contamination controls separating development from the evaluator-controlled holdout;
- retention of adverse, neutral, incomplete, and failed outcomes;
- a deviations register.

These controls do not guarantee a good study. They make design changes and exceptions visible so a reviewer can accept, reject, or rerun the work.

## Independence contract

`external_complete` is unavailable until the docket identifies:

- evaluator name, organization, and role;
- relationship to LumenCore;
- conflict disclosure;
- who controlled the data;
- who executed the run;
- who calculated the analysis;
- what result language may be published.

A founder, self-reviewer, or founder-controlled evaluator cannot satisfy the external relationship gate.

## Reproducibility contract

The docket permanently requires:

- an input manifest;
- an output manifest;
- a run receipt;
- a second execution environment;
- a deterministic equality or stochastic tolerance rule;
- an offline verifier;
- negative-result retention;
- a deviations register.

The validator verifies the contract and its custody hash. It does not independently reproduce the experiment or authenticate a reviewer signature. Those remain external evidence.

## Run the validator

From the repository root:

```bash
python code/ops/validate_external_replication_docket.py \
  config/external_replication_docket_v1.json
```

The current canonical template should return:

```json
{
  "valid": true,
  "status": "template_unassigned",
  "decision": "hold",
  "preregistration_gates_passed": 0,
  "external_gates_passed": 0,
  "safe_for_external_validation_claim": false
}
```

Run the focused adversarial suite:

```bash
python -m unittest discover \
  -s tests \
  -p "test_external_replication_docket.py" \
  -v
```

## How a real evaluator uses the template

1. Copy the canonical template into a buyer- or evaluator-specific private work area.
2. Name the source-rights owner and permitted use.
3. Assign the evaluator and disclose conflicts.
4. Freeze the hypothesis, null, falsification condition, baseline, candidate version, holdout, metric, threshold, uncertainty method, sample plan, and all failure rules.
5. Pin the code commit, dependency lock, environment, and protocol hash.
6. Recompute the docket custody hash.
7. Execute the candidate and baseline without post-outcome tuning.
8. Preserve every outcome and deviation.
9. Produce manifests, a run receipt, and offline verification instructions.
10. Record the evaluator's bounded attestation and only the approved public sentence.

The public repository should contain only material that the source owner and evaluator have authorized for release.

## Claim boundary

A valid `template_unassigned` or `preregistered` docket proves only that a review contract exists. An `internal_complete` docket remains internal evidence. An `external_complete` docket supports a bounded external-validation statement only for the exact source, comparator, metric, threshold, window, code, environment, and written permission recorded in that docket.

It never establishes universal superiority, certification, safety approval, production authorization, agency endorsement, customer deployment, revenue, guaranteed savings, or patent conclusions.

**Operating principle:** evidence before claims; bounded light speed.
