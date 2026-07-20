# Proof Capsule Schema

**Purpose:** Standardize how LumenCore promotes evidence from internal artifacts into public-safe reviewer reports.

A Proof Capsule is a bounded evidence unit. It is not a sales claim, revenue claim, certification claim, or field-validation claim unless external validation is attached.

---

## 1. Required fields

```json
{
  "schema_version": "3.0",
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
    "run_type": "measured | replay | synthetic | bench | modeled | estimated | conceptual",
    "timestamp_utc": "ISO-8601 UTC string",
    "code_commit": "git SHA or explicit unknown value",
    "dependency_lock": "path or unknown",
    "seed_or_window": "string"
  },
  "manifest": {
    "manifest_format": "proof-capsule-manifest-v3",
    "input_hashes": [],
    "output_hashes": [],
    "manifest_hash": "64-character SHA-256 digest",
    "public_safe": true
  },
  "external_validation": {
    "status": "not_established | established",
    "validator_name": "string | null",
    "validator_organization": "string | null",
    "scope": "string | null",
    "completed_at_utc": "ISO-8601 UTC string | null",
    "report_path": "canonical manifest path | null",
    "report_sha256": "manifest-bound SHA-256 digest | null"
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
| externally_validated | outside report is declared and manifest-bound | requires human authentication and scope review |

---

## 3. Promotion gate

A capsule may be public only when:

- source/dataset is named,
- data rights are resolved and labeled,
- baseline/comparator is named and selected before scoring,
- metric is locked before scoring,
- evidence type and run type are compatible,
- externally validated evidence names the validator and binds its report path and
  digest to a verified manifest record,
- a human reviewer authenticates the validator, independence, scope, and conclusion,
- the run timestamp is explicit UTC,
- manifest paths are canonical repository-relative POSIX paths,
- at least one artifact hash is verified,
- manifest and artifact hashes are valid SHA-256 digests,
- negative or neutral findings and failure notes are retained,
- limitations are explicit,
- non-external evidence explicitly states that external, field, or operational validation is not established,
- forbidden claims are absent,
- action-time founder approval is obtained separately from the verifier receipt.

`source.rights_status: unknown` is valid as an internal drafting state, but it does not pass the public verifier. Resolve it before promotion.

---

## 4. Verifier v3 integrity and resource gates

The standard-library verifier additionally fails closed when:

- the capsule contains duplicate JSON keys or invalid UTF-8,
- the capsule uses an unsupported schema or manifest format,
- any object contains missing or unknown fields,
- a string contains surrounding whitespace, control characters, or hidden Unicode
  format controls,
- a path is absolute, uses backslashes, escapes the repository root, or is non-canonical,
- duplicate manifest paths, symlinks, or hardlink aliases resolve to the same artifact,
- a referenced artifact is missing, not a regular file, too large, or changes while being hashed,
- a SHA-256 or manifest digest is malformed or mismatched,
- enumerated source, baseline, evidence, run, or pilot values are unsupported,
- the timestamp is invalid or not UTC,
- list fields contain blank, non-string, or duplicate entries,
- a capsule, artifact, or aggregate manifest exceeds the configured resource budget,
- an external-validation label lacks a manifest-bound validator report,
- any public-facing positive claim field contains normalized prohibited performance,
  endorsement, certification, revenue, deployment, ranking, or valuation language.

Default resource budgets are 1 MiB for the capsule JSON, 512 MiB per referenced
artifact, and 1 GiB across the complete manifest. They may be raised explicitly by
a reviewer; they are resource-safety limits, not evidence-quality thresholds.

The v3 manifest hash is the SHA-256 digest of canonical JSON containing
`manifest_format`, `input_hashes`, and `output_hashes`. Input/output roles are therefore
part of the digest; moving a record between those arrays changes the manifest hash.

The v3 machine receipt binds both the exact capsule file bytes and a canonical JSON
representation. `capsule_file_custody_complete: true` is emitted only when the stable
file-loading path supplies that exact-byte metadata. Receipt fields deliberately call
the evidence type and external-validation status **declared** metadata. For an
`externally_validated` capsule, `external_report_manifest_bound: true` means only that
the declared report path and digest match a verified manifest record. The verifier emits
`external_validator_identity_evaluated: false`,
`external_validator_independence_evaluated: false`, and
`external_validation_conclusion_evaluated: false`; a hash cannot establish those facts.
The receipt also reports `release_authorization_evaluated: false` and
`human_unlock_required: true`. A valid receipt verifies schema, custody, hashes, and
bounded claim rules; it does not authenticate a validator or authorize publication,
submission, certification, or external contact.

---

## 5. Verifier v2 to v3 migration

Verifier v3 intentionally has no permissive v2 fallback. To migrate a capsule:

1. add `schema_version: "3.0"`,
2. add `manifest_format: "proof-capsule-manifest-v3"`,
3. add the complete `external_validation` object, using `not_established` and null
   detail fields unless a real validator report exists,
4. remove every field that is not defined by this schema,
5. recompute `manifest_hash` from canonical role-separated manifest JSON, and
6. run verifier v3 to create a receipt that binds the exact capsule bytes.

Do not relabel old receipts as v3. The verifier and receipt versions are part of the
custody record.

---

## 6. Forbidden promotion language

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

## 7. Safe capsule sentence

> This Proof Capsule is a bounded evidence unit. It identifies source, baseline, locked metric, run type, manifest status, result, and limitations so reviewers can decide the next validation gate without treating internal evidence as field certification.
