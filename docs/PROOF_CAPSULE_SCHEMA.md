# Proof Capsule Schema

**Purpose:** Standardize how LumenCore promotes evidence from internal artifacts into public-safe reviewer reports.

A Proof Capsule is a bounded evidence unit. It is not a sales claim, revenue claim, certification claim, or field-validation claim unless external validation is attached.

---

## 1. Required fields

```json
{
  "capsule_id": "string",
  "title": "string",
  "module": "LumenCore | LumaTrader | LumaScout | LumaJet | LumaSuit | LumaSkin | EchoForm | FlowForm | Other",
  "evidence_type": "measured | replay | synthetic | modeled | estimated | conceptual | externally_validated",
  "source": {
    "name": "string",
    "type": "dataset | stream | sensor | benchmark | sample | document | dashboard | simulation",
    "rights_status": "public | private | buyer_authorized | synthetic | unknown",
    "row_count_or_window": "string"
  },
  "baseline": {
    "name": "string",
    "baseline_type": "incumbent | naive | named_method | synthetic_control | historical | benchmark",
    "selection_time": "before_scoring | after_scoring | unknown"
  },
  "locked_metric": {
    "name": "string",
    "definition": "string",
    "locked_before_run": true
  },
  "run": {
    "run_id": "string",
    "run_type": "measured | replay | synthetic | bench | modeled",
    "timestamp_utc": "ISO-8601 UTC string",
    "code_commit": "git SHA or explicit unknown value",
    "dependency_lock": "path or unknown",
    "seed_or_window": "string"
  },
  "manifest": {
    "input_hashes": [],
    "output_hashes": [],
    "manifest_hash": "64-character SHA-256 digest",
    "public_safe": true
  },
  "result": {
    "summary": "string",
    "primary_delta": "string",
    "secondary_metrics": [],
    "negative_results": [],
    "failure_notes": []
  },
  "claim_boundary": {
    "proves": [],
    "does_not_prove": [],
    "safe_public_sentence": "string"
  },
  "pilot_decision": {
    "status": "promote | rerun | external_review | hold | reject",
    "next_gate": "string",
    "owner": "string"
  }
}
```

---

## 2. Evidence-type meanings

| Evidence type | Meaning | Public posture |
|---|---|---|
| measured | rows, files, logs, outputs, or runs exist | strongest internal evidence |
| replay | controlled replay result exists | useful, not field validation |
| synthetic | generated/simulated benchmark exists | feasibility evidence only |
| modeled | simulation or internal model output exists | useful with limitations |
| estimated | economic conversion or opportunity framing | not revenue or realized savings |
| conceptual | architecture, disclosure, roadmap, or theory | not performance proof |
| externally_validated | qualified outside party verifies agreed run | strongest public proof |

---

## 3. Promotion gate

A capsule may be public only when:

- source/dataset is named,
- data rights are resolved and labeled,
- baseline/comparator is named and selected before scoring,
- metric is locked before scoring,
- evidence type and run type are compatible,
- the run timestamp is explicit UTC,
- manifest paths are canonical repository-relative POSIX paths,
- at least one artifact hash is verified,
- manifest and artifact hashes are valid SHA-256 digests,
- negative or neutral findings and failure notes are retained,
- limitations are explicit,
- non-external evidence explicitly states that external, field, or operational validation is not established,
- forbidden claims are absent,
- founder approval is recorded.

`source.rights_status: unknown` is valid as an internal drafting state, but it does not pass the public verifier. Resolve it before promotion.

---

## 4. Verifier v2 integrity and resource gates

The standard-library verifier additionally fails closed when:

- the capsule contains duplicate JSON keys or invalid UTF-8,
- a path is absolute, uses backslashes, escapes the repository root, or is non-canonical,
- duplicate manifest paths or aliases resolve to the same artifact,
- a referenced artifact is missing, not a regular file, too large, or changes while being hashed,
- a SHA-256 or manifest digest is malformed or mismatched,
- enumerated source, baseline, evidence, run, or pilot values are unsupported,
- the timestamp is invalid or not UTC,
- list fields contain blank, non-string, or duplicate entries,
- a capsule or artifact exceeds the configured resource budget,
- public summary language contains a prohibited performance, endorsement, certification, revenue, or deployment claim.

Default resource budgets are 1 MiB for the capsule JSON and 512 MiB per referenced artifact. They may be raised explicitly by a reviewer; they are resource-safety limits, not evidence-quality thresholds.

---

## 5. Forbidden promotion language

Do not promote a Proof Capsule using language that implies:

- audited revenue,
- guaranteed ROI,
- field-validated savings,
- certified aircraft capability,
- certified suit capability,
- weapons capability,
- autonomous physical control,
- medical diagnosis,
- agency endorsement,
- grant award likelihood,
- customer deployment.

---

## 6. Safe capsule sentence

> This Proof Capsule is a bounded evidence unit. It identifies source, baseline, locked metric, run type, manifest status, result, and limitations so reviewers can decide the next validation gate without treating internal evidence as field certification.
