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
    "timestamp_utc": "ISO-8601 string",
    "code_commit": "git SHA or unknown",
    "dependency_lock": "path or unknown",
    "seed_or_window": "string"
  },
  "manifest": {
    "input_hashes": [],
    "output_hashes": [],
    "manifest_hash": "string or pending",
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
- data rights are labeled,
- baseline/comparator is named,
- metric is locked before scoring,
- run type is labeled,
- manifest or hash plan exists,
- limitations are explicit,
- forbidden claims are absent,
- founder approval is recorded.

---

## 4. Forbidden promotion language

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

## 5. Safe capsule sentence

> This Proof Capsule is a bounded evidence unit. It identifies source, baseline, locked metric, run type, manifest status, result, and limitations so reviewers can decide the next validation gate without treating internal evidence as field certification.
