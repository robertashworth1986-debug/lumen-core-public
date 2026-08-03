from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "product_lane_priority_v1.json"
OUT_JSON = ROOT / "dashboard" / "data" / "product_lane_priority_engine_20260718.json"
OUT_MD = ROOT / "docs" / "PRODUCT_LANE_PRIORITY_ENGINE_2026-07-18.md"
MINDWISE_MD = ROOT / "docs" / "MINDWISE_PAID_DESIGN_PARTNER_PILOT_2026-07-18.md"
MINDWISE_EMAIL = ROOT / "docs" / "MINDWISE_DESIGN_PARTNER_FOLLOWUP_EMAIL_2026-07-18.txt"
BUNDLE_MANIFEST = ROOT / "docs" / "receipts" / "PRODUCT_LANE_PRIORITY_BUNDLE_MANIFEST_2026-07-18.json"
MINDWISE_DEMO_FEED = ROOT / "dashboard" / "data" / "mindwise_healthcare_candidate_feed_20260718.json"
PILOT_CONFIG = ROOT / "config" / "prooflock_opportunity_ops_pilot_v1.json"
GOLDEN_REPLAY = (
    ROOT
    / "dashboard"
    / "data"
    / "prooflock_opportunity_ops_golden_replay_v1.json"
)

RUN_IDS = (
    "20260505T082948Z",
    "20260505T104706Z",
    "20260505T121657Z",
    "20260511T175644Z",
    "20260526T050639Z",
)
RUN_ROOT = ROOT / "dashboard" / "evidence" / "runs"
RAW_RUN_ROOT = ROOT / "out" / "master_universe_v2"
HEALTHCARE_FEED = ROOT / "out" / "ops" / "healthcare_grants_engine" / "healthcare_website_feed_latest.json"

BOUNDARY = (
    "Product-lane priority engine. Scores are a transparent founder strategy heuristic, not market valuation, "
    "patentability, customer acceptance, award probability, field validation, or guaranteed revenue."
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_pilot_config() -> dict[str, Any]:
    config = read_json(PILOT_CONFIG)
    if config.get("schema") != "prooflock_opportunity_ops_pilot_config_v1":
        raise ValueError("ProofLock pilot config is missing or uses the wrong schema")
    required_sections = {
        "minimum_sample",
        "permitted_sources",
        "prohibited_inputs",
        "deliverables",
        "exclusions",
        "event_schema",
        "receipt_schema",
        "acceptance_metrics",
        "acceptance_thresholds",
        "raci",
        "retention_and_security",
        "support_boundary",
        "pricing",
        "human_gates",
    }
    missing = sorted(required_sections - set(config))
    if missing:
        raise ValueError(f"ProofLock pilot config missing sections: {missing}")
    if config["pricing"].get("founder_approved") is not False:
        raise ValueError("Pilot pricing must remain unapproved until exact scope review")
    return config


def build_golden_replay(config: dict[str, Any]) -> dict[str, Any]:
    genesis = "0" * 64
    fixtures = [
        {
            "opportunity_id": "SYNTH-QUALIFIED",
            "decision": "QUALIFIED_FOR_BUYER_REVIEW",
            "blockers": [],
            "evidence": {
                "eligibility_rule": "synthetic_entity_type_allowed",
                "deadline_state": "synthetic_open_verified",
                "source_state": "synthetic_official_fixture",
            },
        },
        {
            "opportunity_id": "SYNTH-DISQUALIFIED",
            "decision": "DISQUALIFIED",
            "blockers": ["synthetic_entity_type_not_eligible"],
            "evidence": {
                "eligibility_rule": "synthetic_entity_type_excluded",
                "deadline_state": "synthetic_open_verified",
                "source_state": "synthetic_official_fixture",
            },
        },
        {
            "opportunity_id": "SYNTH-INSUFFICIENT",
            "decision": "ABSTAIN_INSUFFICIENT_EVIDENCE",
            "blockers": ["missing_synthetic_deadline_receipt"],
            "evidence": {
                "eligibility_rule": "synthetic_rule_present",
                "deadline_state": "unverified",
                "source_state": "synthetic_incomplete_fixture",
            },
        },
    ]
    events: list[dict[str, Any]] = []
    previous = genesis
    for index, fixture in enumerate(fixtures, start=1):
        event = {
            "event_id": f"GOLDEN-{index:03d}",
            "event_utc": f"2026-07-18T00:0{index}:00Z",
            "opportunity_id": fixture["opportunity_id"],
            "source_id": "synthetic_fixture_v1",
            "action_type": "eligibility_and_deadline_review",
            "actor_role": "system_draft_for_human_review",
            "evidence_sha256": stable_hash(fixture["evidence"]),
            "decision": fixture["decision"],
            "blockers": fixture["blockers"],
            "human_authority_state": "not_requested",
            "previous_event_sha256": previous,
        }
        event["event_sha256"] = stable_hash(event)
        previous = event["event_sha256"]
        events.append(event)

    receipt = {
        "protocol_id": config["protocol_id"],
        "event_count": len(events),
        "genesis_sha256": genesis,
        "terminal_event_sha256": previous,
        "chain_valid": True,
    }
    receipt["receipt_sha256"] = stable_hash(receipt)
    replay = {
        "schema": "prooflock_opportunity_ops_golden_replay_v1",
        "protocol_id": config["protocol_id"],
        "fixture_data_class": "synthetic_no_phi_no_credentials",
        "events": events,
        "receipt": receipt,
        "boundary": (
            "This replay proves deterministic decision-state and receipt-chain "
            "behavior for synthetic fixtures only. It does not prove eligibility, "
            "customer outcomes, awards, savings, or production readiness."
        ),
    }
    replay["replay_sha256"] = stable_hash(replay)
    return replay


def verify_golden_replay(replay: dict[str, Any]) -> bool:
    replay_without_hash = dict(replay)
    observed_replay_hash = replay_without_hash.pop("replay_sha256", None)
    if observed_replay_hash != stable_hash(replay_without_hash):
        return False

    events = replay.get("events")
    receipt = replay.get("receipt")
    if not isinstance(events, list) or not isinstance(receipt, dict):
        return False
    previous = str(receipt.get("genesis_sha256") or "")
    if previous != "0" * 64:
        return False
    for event_value in events:
        if not isinstance(event_value, dict):
            return False
        event = dict(event_value)
        observed_hash = event.pop("event_sha256", None)
        if event.get("previous_event_sha256") != previous:
            return False
        if observed_hash != stable_hash(event):
            return False
        previous = str(observed_hash)
    receipt_without_hash = dict(receipt)
    observed_receipt_hash = receipt_without_hash.pop("receipt_sha256", None)
    return (
        receipt.get("event_count") == len(events)
        and receipt.get("terminal_event_sha256") == previous
        and receipt.get("chain_valid") is True
        and observed_receipt_hash == stable_hash(receipt_without_hash)
    )


def file_receipt(path: Path) -> dict[str, Any]:
    relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
    if not path.is_file():
        return {"path": relative_path, "exists": False, "bytes": 0, "sha256": None}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": relative_path,
        "exists": True,
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def build_bundle_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    paths = (
        CONFIG,
        Path(__file__).resolve(),
        OUT_JSON,
        OUT_MD,
        MINDWISE_MD,
        MINDWISE_EMAIL,
        ROOT / "dashboard" / "js" / "luma_healthcare_grants_embed.js",
        ROOT / "dashboard" / "embed" / "healthcare_grants_widget_example.html",
        ROOT / "dashboard" / "embed" / "mindwise_premium_flow_demo.html",
        ROOT / "code" / "ops" / "HEALTHCARE_WEBSITE_EMBED_PLAYBOOK.md",
        ROOT / "tests" / "test_product_lane_priority_engine.py",
        MINDWISE_DEMO_FEED,
        PILOT_CONFIG,
        GOLDEN_REPLAY,
    )
    receipts = [file_receipt(path) for path in paths]
    manifest: dict[str, Any] = {
        "schema": "product_lane_priority_bundle_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "product_lane_priority_sha256": payload["product_lane_priority_sha256"],
        "all_artifacts_present": all(receipt["exists"] for receipt in receipts),
        "artifact_count": len(receipts),
        "artifacts": receipts,
        "boundary": (
            "File receipts prove byte identity and presence only. They do not prove eligibility, correctness, "
            "independent validation, customer acceptance, award probability, or commercial value."
        ),
    }
    manifest["manifest_payload_sha256"] = stable_hash(manifest)
    return manifest


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def parse_utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_evidence_contract(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {
            "path": value,
            "required": True,
            "kind": "legacy_untyped_artifact",
            "claim_scope": "",
            "min_bytes": 1,
            "expected_schema": None,
            "required_keys": [],
            "max_age_hours": None,
            "legacy_untyped": True,
        }
    if not isinstance(value, dict):
        return {
            "path": "",
            "required": True,
            "kind": "invalid_contract",
            "claim_scope": "",
            "min_bytes": 1,
            "expected_schema": None,
            "required_keys": [],
            "max_age_hours": None,
            "legacy_untyped": False,
        }

    required_keys = value.get("required_keys")
    if not isinstance(required_keys, list):
        required_keys = []
    return {
        "path": str(value.get("path") or "").strip(),
        "required": bool(value.get("required", True)),
        "kind": str(value.get("kind") or "artifact").strip(),
        "claim_scope": str(value.get("claim_scope") or "").strip(),
        "min_bytes": value.get("min_bytes", 1),
        "expected_schema": value.get("expected_schema"),
        "required_keys": [str(item) for item in required_keys if str(item).strip()],
        "max_age_hours": value.get("max_age_hours"),
        "legacy_untyped": False,
    }


def validate_evidence_contract(value: Any, at: datetime | None = None) -> dict[str, Any]:
    at = (at or now_utc()).astimezone(timezone.utc)
    contract = normalize_evidence_contract(value)
    path_text = contract["path"]
    reasons: list[str] = []

    min_bytes = parse_float(contract["min_bytes"])
    if min_bytes is None or min_bytes < 1:
        reasons.append("contract_invalid_min_bytes")
        min_bytes = 1.0
    max_age_hours = parse_float(contract["max_age_hours"])
    if contract["max_age_hours"] is not None and (
        max_age_hours is None or max_age_hours <= 0
    ):
        reasons.append("contract_invalid_max_age_hours")
        max_age_hours = None
    expected_schema = contract["expected_schema"]
    if expected_schema is not None and not isinstance(expected_schema, str):
        reasons.append("contract_invalid_expected_schema")
        expected_schema = None
    if contract["legacy_untyped"]:
        reasons.append("contract_legacy_untyped")
    if not contract["claim_scope"]:
        reasons.append("contract_missing_claim_scope")
    if not path_text:
        reasons.append("contract_missing_path")

    target: Path | None = None
    if path_text:
        try:
            target = (ROOT / path_text).resolve()
            target.relative_to(ROOT.resolve())
        except (OSError, ValueError):
            reasons.append("contract_path_outside_root")
            target = None

    exists = bool(target and target.exists())
    is_file = bool(target and target.is_file())
    size = 0
    modified_utc: str | None = None
    sha256: str | None = None
    age_hours: float | None = None
    age_source: str | None = None
    observed_schema: Any = None
    observed_keys: list[str] = []
    missing_keys: list[str] = []
    json_payload: dict[str, Any] | None = None

    if target is not None and not exists:
        reasons.append("artifact_missing")
    elif target is not None and not is_file:
        reasons.append("artifact_not_file")
    elif target is not None:
        stat = target.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        modified_utc = modified.isoformat()
        age_reference = modified
        age_source = "file_modified_utc"
        if size < min_bytes:
            reasons.append("artifact_below_min_bytes")

        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()

        needs_json = (
            expected_schema is not None
            or bool(contract["required_keys"])
            or target.suffix.lower() == ".json"
        )
        if needs_json:
            try:
                candidate = json.loads(target.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                reasons.append("artifact_invalid_json")
            else:
                if isinstance(candidate, dict):
                    json_payload = candidate
                    observed_schema = candidate.get("schema")
                    observed_keys = sorted(str(key) for key in candidate)
                    generated = parse_utc_datetime(candidate.get("generated_utc"))
                    if generated is not None:
                        age_reference = generated
                        age_source = "json_generated_utc"
                else:
                    reasons.append("artifact_json_not_object")

        if expected_schema is not None and json_payload is not None:
            if observed_schema != expected_schema:
                reasons.append("artifact_schema_mismatch")
        if contract["required_keys"] and json_payload is not None:
            missing_keys = sorted(set(contract["required_keys"]) - set(json_payload))
            if missing_keys:
                reasons.append("artifact_missing_required_keys")
        else:
            missing_keys = []

        if max_age_hours is not None:
            age_hours = (at - age_reference).total_seconds() / 3600
            if age_hours < -0.25:
                reasons.append("artifact_timestamp_in_future")
            elif age_hours > max_age_hours:
                reasons.append("artifact_stale")
    contract_complete = not any(reason.startswith("contract_") for reason in reasons)
    valid = not reasons
    return {
        "path": path_text,
        "required": contract["required"],
        "kind": contract["kind"],
        "claim_scope": contract["claim_scope"],
        "contract_complete": contract_complete,
        "valid": valid,
        "status": "valid" if valid else "invalid",
        "reasons": reasons,
        "exists": exists,
        "is_file": is_file,
        "bytes": size,
        "min_bytes": int(min_bytes),
        "sha256": sha256,
        "modified_utc": modified_utc,
        "expected_schema": expected_schema,
        "observed_schema": observed_schema,
        "required_keys": contract["required_keys"],
        "missing_required_keys": missing_keys,
        "observed_keys": observed_keys,
        "max_age_hours": max_age_hours,
        "age_hours": round(age_hours, 4) if age_hours is not None else None,
        "age_source": age_source,
    }


def audit_run(run_id: str) -> dict[str, Any]:
    run_dir = RUN_ROOT / run_id
    summary = read_json(run_dir / "summary.json")
    scorecard_path = run_dir / "UNDENIABLE_SCORECARD_V2.md"
    scorecard = scorecard_path.read_text(encoding="utf-8", errors="replace") if scorecard_path.exists() else ""

    model_rows: Counter[str] = Counter()
    valid_rows: Counter[str] = Counter()
    error_rows: Counter[str] = Counter()
    results_path = run_dir / "results.csv"
    if results_path.exists():
        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                model = str(row.get("model") or "unknown")
                model_rows[model] += 1
                if parse_float(row.get("rmse")) is not None:
                    valid_rows[model] += 1
                else:
                    error_rows[model] += 1

    failures = {
        model: {
            "invalid_rows": int(error_rows[model]),
            "total_rows": int(model_rows[model]),
        }
        for model in sorted(model_rows)
        if error_rows[model]
    }
    all_models_complete = bool(model_rows) and not failures
    raw_dir = RAW_RUN_ROOT / run_id / "raw"
    raw_count = len(list(raw_dir.glob("*.csv"))) if raw_dir.exists() else 0
    scorecard_calls_walk_forward = "walk-forward" in scorecard.lower()

    return {
        "run_id": run_id,
        "datasets_succeeded": int(summary.get("n_datasets_succeeded") or 0),
        "attempted_datasets": int(summary.get("n_datasets_in_universe") or 0),
        "models_reported": sorted(model_rows),
        "model_count": len(model_rows),
        "all_models_complete": all_models_complete,
        "model_failures": failures,
        "raw_csv_count": raw_count,
        "dashboard_manifest_note": (
            "Dashboard copy hashes six summary artifacts; raw CSVs remain in the canonical out/master_universe_v2 run."
        ),
        "evaluation_design": "single_chronological_80_20_holdout",
        "scorecard_calls_method_walk_forward": scorecard_calls_walk_forward,
        "method_language_status": "stale_overstatement" if scorecard_calls_walk_forward else "bounded",
        "reviewer_use": (
            "bounded_exploratory_reference"
            if all_models_complete
            else "blocked_from_comparative_headline"
        ),
    }


def audit_healthcare_feed(at: datetime) -> dict[str, Any]:
    feed = read_json(HEALTHCARE_FEED)
    generated_text = str(feed.get("generated_utc") or "")
    generated: datetime | None = None
    try:
        generated = datetime.fromisoformat(generated_text.replace("Z", "+00:00"))
    except ValueError:
        pass
    if generated is not None and generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    age_hours = (at - generated).total_seconds() / 3600 if generated is not None else None
    records = feed.get("records") if isinstance(feed.get("records"), list) else []
    is_fresh = age_hours is not None and 0 <= age_hours <= 24
    return {
        "path": str(HEALTHCARE_FEED.relative_to(ROOT)).replace("\\", "/"),
        "generated_utc": generated_text,
        "record_count": len(records),
        "freshness_sla_hours": 24,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "freshness_label_allowed": is_fresh,
        "eligibility_label_allowed": False,
        "submission_ready_label_allowed": False,
        "status": "fresh" if is_fresh else "stale_or_unverifiable",
        "boundary": (
            "Freshness applies only to the candidate source feed. Relevance scores do not establish applicant "
            "eligibility, current requirements, submission readiness, or award probability."
        ),
    }


def build_mindwise_demo_feed() -> dict[str, Any]:
    source = read_json(HEALTHCARE_FEED)
    source_records = source.get("records") if isinstance(source.get("records"), list) else []
    records = [row for row in source_records[:6] if isinstance(row, dict)]

    def closes_within(row: dict[str, Any], days: int) -> bool:
        value = parse_float(row.get("days_to_close"))
        return value is not None and 0 <= value <= days

    snapshot: dict[str, Any] = {
        "schema": "mindwise_healthcare_candidate_feed_demo_v1",
        "generated_utc": source.get("generated_utc"),
        "source": source.get("source", {}),
        "summary": {
            "close_7_days": sum(1 for row in records if closes_within(row, 7)),
            "close_14_days": sum(1 for row in records if closes_within(row, 14)),
            "urgent_or_expedited_review": sum(
                1
                for row in records
                if str(row.get("action") or "").upper()
                in {"URGENT_REVIEW", "EXPEDITED_REVIEW"}
            ),
            "snapshot_records": len(records),
        },
        "records": records,
        "boundary": (
            "Frozen demonstration snapshot from a source-linked candidate feed. Scores and queue labels reflect "
            "configured relevance and urgency only; they do not establish organizational eligibility, current "
            "requirements, submission readiness, or award probability."
        ),
    }
    snapshot["snapshot_payload_sha256"] = stable_hash(snapshot)
    return snapshot


def rank_lanes(
    config: dict[str, Any],
    at: datetime | None = None,
) -> list[dict[str, Any]]:
    at = at or now_utc()
    weights = config.get("weights") if isinstance(config.get("weights"), dict) else {}
    if round(sum(float(value) for value in weights.values()), 8) != 100:
        raise ValueError("product-lane weights must sum to 100")

    ranked: list[dict[str, Any]] = []
    for lane in config.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        scores = lane.get("scores") if isinstance(lane.get("scores"), dict) else {}
        missing_dimensions = sorted(set(weights) - set(scores))
        if missing_dimensions:
            raise ValueError(f"{lane.get('id')} missing score dimensions: {missing_dimensions}")
        weighted = sum(float(scores[key]) * float(weight) for key, weight in weights.items()) / 100
        evidence_checks = [
            validate_evidence_contract(value, at)
            for value in lane.get("evidence_paths", [])
        ]
        required_checks = [item for item in evidence_checks if item["required"]]
        validated_count = sum(1 for item in required_checks if item["valid"])
        evidence_coverage = (
            validated_count / len(required_checks)
            if required_checks
            else 0.0
        )
        internal_evidence_gate_passed = bool(required_checks) and all(
            item["valid"] for item in required_checks
        )
        evidence_blockers = [
            {
                "path": item["path"],
                "reasons": item["reasons"],
            }
            for item in required_checks
            if not item["valid"]
        ]
        buyer_gate_status = (
            "requires_external_buyer_validation"
            if internal_evidence_gate_passed
            else "blocked_internal_evidence"
        )
        ranked.append(
            {
                **lane,
                "strategy_score": round(weighted, 2),
                "evidence_coverage": round(evidence_coverage, 4),
                "validated_evidence_coverage": round(evidence_coverage, 4),
                "validated_evidence_count": validated_count,
                "required_evidence_count": len(required_checks),
                "evidence_checks": evidence_checks,
                "internal_evidence_gate_passed": internal_evidence_gate_passed,
                "buyer_readiness_gate": {
                    "passed": False,
                    "status": buyer_gate_status,
                    "internal_evidence_gate_passed": internal_evidence_gate_passed,
                    "evidence_blockers": evidence_blockers,
                    "next_required_validation": lane.get("first_validation"),
                    "boundary": (
                        "Internal artifact validation cannot establish buyer acceptance, "
                        "organizational eligibility, external validation, or commercial readiness."
                    ),
                },
            }
        )
    ranked.sort(key=lambda row: (-float(row["strategy_score"]), str(row["id"])))
    for index, lane in enumerate(ranked, start=1):
        lane["rank"] = index
    return ranked


def mindwise_pilot(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "ProofLock Opportunity Operations - 30-day paid pilot",
        "buyer_selected": False,
        "buyer": None,
        "status": config["status"],
        "protocol_id": config["protocol_id"],
        "duration_days": config["duration_days"],
        "scope_boundary": config["scope_boundary"],
        "minimum_sample": config["minimum_sample"],
        "permitted_sources": config["permitted_sources"],
        "prohibited_inputs": config["prohibited_inputs"],
        "deliverables": config["deliverables"],
        "exclusions": config["exclusions"],
        "event_schema": config["event_schema"],
        "receipt_schema": config["receipt_schema"],
        "commercial_posture": (
            "Paid pilot after exact buyer scope, baseline, acceptance thresholds, "
            "data terms, price, and recipient are approved."
        ),
        "week_1_baseline": [
            "Measure current time from opportunity discovery to pursue/no-pursue decision.",
            "Measure current time from pursue decision to reviewer-ready draft.",
            "Count eligibility reversals, missing attachments, and missed internal review dates.",
            "Freeze source permissions, eligibility rules, metric denominators, thresholds, roles, and human gates.",
        ],
        "weeks_2_to_4": [
            "Refresh permitted opportunity sources and rank candidates with evidence links.",
            "Generate source-grounded draft structures and an attachment/blocker ledger.",
            "Route unresolved facts to named owners; abstain instead of guessing.",
            "Emit a replayable receipt for every shortlist, draft, and preflight decision.",
        ],
        "acceptance_metrics": config["acceptance_metrics"],
        "acceptance_thresholds": config["acceptance_thresholds"],
        "raci": config["raci"],
        "retention_and_security": config["retention_and_security"],
        "support_boundary": config["support_boundary"],
        "pricing": config["pricing"],
        "human_gates": config["human_gates"],
        "go_no_go": (
            "Convert only when the frozen sample rule is met and the buyer confirms "
            "that every accepted metric passes its prospectively approved threshold. "
            "Otherwise stop, extend under a documented alternate sample rule, or abstain."
        ),
    }


def build_payload(at: datetime | None = None) -> dict[str, Any]:
    at = at or now_utc()
    config = read_json(CONFIG)
    pilot_config = load_pilot_config()
    golden_replay = build_golden_replay(pilot_config)
    if not verify_golden_replay(golden_replay):
        raise ValueError("ProofLock golden replay failed receipt-chain verification")
    ranked = rank_lanes(config, at)
    run_audits = [audit_run(run_id) for run_id in RUN_IDS]
    comparable = [row for row in run_audits if row["all_models_complete"]]
    best_exploratory = max(comparable, key=lambda row: row["datasets_succeeded"], default={})
    pilot = mindwise_pilot(pilot_config)
    feed_audit = audit_healthcare_feed(at)
    allowed_now = [
        "working grant-ranking, draft-assembly, preflight, and receipt components exist",
        "five historical benchmark runs and raw source directories exist",
        "the 673-dataset run is a bounded exploratory single-holdout reference",
        "a paid design-partner pilot can measure workflow improvement",
    ]
    if feed_audit["freshness_label_allowed"]:
        allowed_now.append(
            "the healthcare candidate feed was refreshed within its 24-hour SLA; freshness does not establish eligibility"
        )
    blocked_now = [
        "organizational eligibility from relevance scores alone",
        "urgent or priority labels as authorization to apply or submit",
        "prospective router superiority until train-only features pass",
        "field validation or realized savings",
        "guaranteed awards or autonomous final submission",
        "patentability",
    ]
    if not feed_audit["freshness_label_allowed"]:
        blocked_now.insert(0, "current-feed language until the candidate feed is refreshed within the freshness SLA")

    payload: dict[str, Any] = {
        "schema": "product_lane_priority_engine_v1",
        "generated_utc": at.isoformat(),
        "boundary": BOUNDARY,
        "evidence_contract_version": "typed_evidence_contract_v1",
        "weights": config.get("weights", {}),
        "ranking": ranked,
        "recommendation": {
            "commercial_lane": ranked[0]["id"] if ranked else None,
            "commercial_offer": ranked[0]["offer"] if ranked else None,
            "technical_wedge": "prooflock_evidence_router_api",
            "technical_wedge_boundary": (
                "The defensible target is not generic grant search or AI writing. It is a constrained router that "
                "uses train-only or source-available features, abstains when eligibility or evidence gates fail, "
                "and emits replayable policy/source receipts. Patentability still requires a dedicated search."
            ),
            "first_design_partner": "unselected_requires_current_validated_target",
            "why_now": (
                (
                    "Typed internal evidence contracts pass for the top lane. Buyer selection, "
                    "workflow baseline, acceptance thresholds, eligibility review, and measured "
                    "pilot outcomes remain external gates."
                )
                if ranked and ranked[0]["internal_evidence_gate_passed"]
                else (
                    "The top strategy lane has unresolved typed-evidence blockers. Repair those "
                    "internal artifacts before selecting a buyer or describing the offer as ready."
                )
            ),
        },
        "evidence_audit": {
            "runs": run_audits,
            "best_bounded_exploratory_run": best_exploratory.get("run_id"),
            "best_bounded_exploratory_dataset_count": best_exploratory.get("datasets_succeeded"),
            "router_risk": (
                "The historical meta-router extracts features from each full series, including the benchmark test "
                "window. Cross-dataset CV does not remove that within-series look-ahead. Rebuild features from each "
                "training window as train-only inputs before making prospective routing claims."
            ),
            "latest_run_blocker": (
                "Run 20260526T050639Z is blocked from comparative headline use because i_sarima has no valid RMSE "
                "on all 1,118 datasets while the scorecard still describes a classical comparison."
            ),
            "healthcare_feed": feed_audit,
        },
        "market_boundary": {
            "crowded_features": [
                "grant matching and tracking",
                "AI-assisted proposal drafting",
                "grant database search and APIs",
                "grantmaker workflow and review management",
            ],
            "official_product_sources_checked_2026_07_18": [
                "https://www.instrumentl.com/product-overview",
                "https://grantable.co/",
                "https://ops.opengrants.io/api-docs",
                "https://www.submittable.com/solutions/grants",
            ],
            "inference": (
                "Generic grant finding/filling is not a defensible category claim. Lead with evidence-bound "
                "eligibility, deterministic abstention, deadline controls, and replayable submission receipts."
            ),
        },
        "prooflock_opportunity_ops_pilot": pilot,
        "mindwise_pilot": pilot,
        "pilot_protocol_receipts": {
            "config_path": str(PILOT_CONFIG.relative_to(ROOT)).replace("\\", "/"),
            "config_sha256": stable_hash(pilot_config),
            "golden_replay_path": str(GOLDEN_REPLAY.relative_to(ROOT)).replace("\\", "/"),
            "golden_replay_sha256": golden_replay["replay_sha256"],
            "golden_replay_verified": True,
            "golden_replay_event_count": len(golden_replay["events"]),
            "golden_replay_decisions": [
                event["decision"] for event in golden_replay["events"]
            ],
            "boundary": golden_replay["boundary"],
        },
        "claim_controls": {
            "allowed_now": allowed_now,
            "blocked_now": blocked_now,
        },
    }
    payload["product_lane_priority_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Product Lane Priority Engine",
        "",
        f"Generated: `{payload['generated_utc']}`",
        "",
        f"> {payload['boundary']}",
        "",
        "## Decision",
        "",
        "Build and sell **ProofLock Opportunity Operations** first. Use the **ProofLock Evidence Router API** as the narrower technical wedge. Keep LumaScout as a later vertical after a forward outcome study.",
        "",
        "## Ranked Lanes",
        "",
        "| Rank | Lane | Strategy score | Validated evidence | Buyer gate | First validation |",
        "|---:|---|---:|---:|---|---|",
    ]
    for lane in payload["ranking"]:
        lines.append(
            f"| {lane['rank']} | {lane['name']} | {lane['strategy_score']:.2f} | "
            f"{lane['validated_evidence_coverage'] * 100:.0f}% | "
            f"{lane['buyer_readiness_gate']['status']} | {lane['first_validation']} |"
        )

    audit = payload["evidence_audit"]
    feed = audit["healthcare_feed"]
    lines.extend(
        [
            "",
            "## Evidence Audit",
            "",
            f"- Best bounded exploratory run: `{audit['best_bounded_exploratory_run']}` with `{audit['best_bounded_exploratory_dataset_count']}` datasets.",
            f"- Latest-run blocker: {audit['latest_run_blocker']}",
            f"- Router blocker: {audit['router_risk']}",
            f"- Healthcare candidate feed: `{feed['status']}`; age `{feed['age_hours']}` hours; freshness label allowed `{str(feed['freshness_label_allowed']).lower()}`; eligibility label allowed `{str(feed['eligibility_label_allowed']).lower()}`.",
            f"- Feed boundary: {feed['boundary']}",
            "",
            "## Commercial Wedge",
            "",
            payload["recommendation"]["technical_wedge_boundary"],
            "",
            "The first recurring product is an organization subscription for monitored opportunities, controlled collaboration, evidence storage, and preflight. Final certifications and submissions remain with the authorized human.",
            "",
            "## Buyer-Neutral Pilot",
            "",
            f"- Scope: {payload['mindwise_pilot']['scope_boundary']}",
            f"- Commercial posture: {payload['mindwise_pilot']['commercial_posture']}",
            f"- Go/no-go: {payload['mindwise_pilot']['go_no_go']}",
            "",
            "Acceptance metrics:",
        ]
    )
    for item in payload["mindwise_pilot"]["acceptance_metrics"]:
        lines.append(
            f"- **{item['metric']}**: numerator = {item['numerator']}; "
            f"denominator = {item['denominator']}"
        )
    lines.extend(
        [
            "",
            "## Claim Gates",
            "",
            "Allowed now:",
        ]
    )
    lines.extend(f"- {value}" for value in payload["claim_controls"]["allowed_now"])
    lines.extend(["", "Blocked now:"])
    lines.extend(f"- {value}" for value in payload["claim_controls"]["blocked_now"])
    lines.extend(["", "## Receipt", "", f"SHA-256: `{payload['product_lane_priority_sha256']}`"])
    return "\n".join(lines)


def render_mindwise_brief(payload: dict[str, Any]) -> str:
    pilot = payload["mindwise_pilot"]
    lines = [
        "# ProofLock Opportunity Operations",
        "",
        "## Buyer-Neutral 30-Day Paid Pilot Protocol",
        "",
        "### Objective",
        "",
        "Measure whether an evidence-bound opportunity workflow can reduce administrative cycle time and package defects without making unsupported eligibility, award, or savings claims.",
        "",
        "### Boundary",
        "",
        pilot["scope_boundary"],
        "",
        "### Buyer And Commercial State",
        "",
        "- Buyer selected: `false`",
        f"- Protocol status: `{pilot['status']}`",
        f"- Pricing status: `{pilot['pricing']['status']}`",
        "- No fee, subscription price, recipient, or external communication is approved by this document.",
        "",
        "### Minimum Sample",
        "",
        f"- Reviewed opportunities: `{pilot['minimum_sample']['reviewed_opportunities']}`",
        f"- Pursued packages: `{pilot['minimum_sample']['pursued_packages']}`",
        f"- Alternate rule: {pilot['minimum_sample']['alternate_sample_rule']}",
        "",
        "### Week 1: Lock the Baseline",
        "",
    ]
    lines.extend(f"- {item}" for item in pilot["week_1_baseline"])
    lines.extend(["", "### Weeks 2-4: Run the Pilot", ""])
    lines.extend(f"- {item}" for item in pilot["weeks_2_to_4"])
    lines.extend(["", "### Acceptance Metrics", ""])
    lines.extend(
        (
            f"- **{item['metric']}**: numerator = {item['numerator']}; "
            f"denominator = {item['denominator']}"
        )
        for item in pilot["acceptance_metrics"]
    )
    lines.extend(
        [
            "",
            "Threshold rule:",
            "",
            f"- {pilot['acceptance_thresholds']['rule']}",
            "",
            "### Permitted Sources",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in pilot["permitted_sources"])
    lines.extend(["", "### Prohibited Inputs", ""])
    lines.extend(f"- {item}" for item in pilot["prohibited_inputs"])
    lines.extend(["", "### Deliverables", ""])
    lines.extend(f"- {item}" for item in pilot["deliverables"])
    lines.extend(["", "### Exclusions", ""])
    lines.extend(f"- {item}" for item in pilot["exclusions"])
    lines.extend(["", "### RACI", ""])
    lines.extend(f"- **{role}**: {duty}" for role, duty in pilot["raci"].items())
    lines.extend(
        [
            "",
            "### Retention And Security",
            "",
            f"- Default post-pilot retention: `{pilot['retention_and_security']['default_retention_days_after_pilot']}` days",
            f"- Deletion: {pilot['retention_and_security']['deletion_rule']}",
            f"- Access: {pilot['retention_and_security']['access_rule']}",
            f"- Incident response: {pilot['retention_and_security']['incident_rule']}",
            "",
            "### Support Boundary",
            "",
            f"- Included: {pilot['support_boundary']['included']}",
            f"- Excluded: {pilot['support_boundary']['excluded']}",
        ]
    )
    lines.extend(["", "### Human Authority Gates", ""])
    lines.extend(f"- {item}" for item in pilot["human_gates"])
    lines.extend(
        [
            "",
            "### Commercial Path",
            "",
            pilot["commercial_posture"],
            "",
            "No value, savings, performance, or price figure is quoted until a selected buyer approves the baseline inputs and prospective thresholds and the pilot produces a traceable measurement.",
            "",
            "### Golden Replay",
            "",
            f"- Verified: `{str(payload['pilot_protocol_receipts']['golden_replay_verified']).lower()}`",
            f"- Synthetic events: `{payload['pilot_protocol_receipts']['golden_replay_event_count']}`",
            f"- Replay SHA-256: `{payload['pilot_protocol_receipts']['golden_replay_sha256']}`",
            f"- Boundary: {payload['pilot_protocol_receipts']['boundary']}",
        ]
    )
    return "\n".join(lines)


def render_mindwise_email(payload: dict[str, Any]) -> str:
    pilot = payload["mindwise_pilot"]
    return "\n".join(
        [
            "DRAFT ONLY - RECIPIENT NOT SELECTED - DO NOT SEND",
            "",
            "Subject: Bounded 30-day opportunity-operations pilot",
            "",
            "Hi [Name],",
            "",
            "I am reaching out only after confirming that your current workflow and source permissions fit a bounded pilot.",
            "",
            "The strongest next step is not another broad AI-writing demo. It is a bounded 30-day design-partner pilot for opportunity operations: permitted-source monitoring, evidence-linked eligibility review, reviewer-ready draft structure, attachment/blocker preflight, and a replayable receipt for every material decision. Final certifications and submissions remain with your authorized team.",
            "",
            (
                "In week one, we would freeze your baseline, denominators, thresholds, "
                f"and cutoff. The default minimum sample is {pilot['minimum_sample']['reviewed_opportunities']} "
                f"reviewed opportunities and {pilot['minimum_sample']['pursued_packages']} pursued packages. "
                "The pilot excludes PHI, credentials, legal advice, and autonomous submission."
            ),
            "",
            "If the prospectively approved metrics do not justify continuing, we stop or document why the sample was insufficient. If they do, we can discuss a separately approved subscription under terms agreed after measurement.",
            "",
            "Would you be open to a 20-minute scoping call next week to choose one workflow and one baseline?",
            "",
            "Respectfully,",
            "Robert Ashworth",
        ]
    )


def main() -> int:
    payload = build_payload()
    pilot_config = load_pilot_config()
    golden_replay = build_golden_replay(pilot_config)
    if not verify_golden_replay(golden_replay):
        raise ValueError("ProofLock golden replay failed before artifact write")
    demo_feed = build_mindwise_demo_feed()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    write_text(MINDWISE_MD, render_mindwise_brief(payload))
    write_text(MINDWISE_EMAIL, render_mindwise_email(payload))
    write_json(MINDWISE_DEMO_FEED, demo_feed)
    write_json(GOLDEN_REPLAY, golden_replay)
    manifest = build_bundle_manifest(payload)
    write_json(BUNDLE_MANIFEST, manifest)
    print(json.dumps({
        "output_json": str(OUT_JSON),
        "output_markdown": str(OUT_MD),
        "mindwise_brief": str(MINDWISE_MD),
        "mindwise_email_draft": str(MINDWISE_EMAIL),
        "mindwise_demo_feed": str(MINDWISE_DEMO_FEED),
        "bundle_manifest": str(BUNDLE_MANIFEST),
        "top_lane": payload["recommendation"]["commercial_lane"],
        "sha256": payload["product_lane_priority_sha256"],
        "bundle_manifest_sha256": manifest["manifest_payload_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
