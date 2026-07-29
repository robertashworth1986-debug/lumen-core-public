from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "economic_relief_gate_audit_v1.json"
DEFAULT_OUT_DIR = ROOT / "out" / "economic_relief_gate_audit"
DEFAULT_OUT_JSON = DEFAULT_OUT_DIR / "economic_relief_gate_audit.json"
DEFAULT_OUT_MD = DEFAULT_OUT_DIR / "economic_relief_gate_audit.md"

CONFIG_SCHEMA = "lumencore.economic_relief_gate_audit_config.v1"
REPORT_SCHEMA = "lumencore.economic_relief_gate_audit.v1"

CLASSIFICATIONS = (
    "LOCALLY_FIXABLE_NOW",
    "DOCUMENTARY_RETRIEVAL_NEEDED",
    "OFFICIAL_PORTAL_OR_HUMAN_ACTION",
    "LEGAL_OR_CERTIFICATION_DECISION",
    "EXPIRED_OR_CLOSED_ROUTE",
    "UNSUPPORTED_ASSUMPTION",
)
REQUIRED_DOMAINS = (
    "SAM_LOGIN",
    "GRANTS_GOV",
    "RESEARCH_GOV",
    "DSIP_SBIR_STTR",
    "DLA_JCP_DD2345",
    "CMMC_FRE_ITAR",
    "CORPORATE_LEGAL_FOUNDER",
    "BUDGET_CEILINGS",
    "PORTAL_RECEIPTS",
    "DUPLICATE_SUBMISSION_CONTROLS",
)
SOURCE_CLASSES = (
    "OFFICIAL_SOURCE",
    "PORTAL_OBSERVED",
    "PORTAL_ISSUED",
    "AGENCY_DETERMINATION",
    "LEGAL_REVIEW",
    "FOUNDER_ATTESTATION",
    "LOCAL_CONTROL",
    "LOCAL_DRAFT",
    "LOCAL_QUEUE",
)
AUTHORITATIVE_CLEARANCE_CLASSES = {
    "PORTAL_ISSUED",
    "AGENCY_DETERMINATION",
    "LEGAL_REVIEW",
}
LOCAL_PROCESS_CLEARANCE_CLASSES = {"LOCAL_CONTROL"}
STATES = {
    "OPEN",
    "PARTIAL",
    "CLOSED_ROUTE",
    "NOT_A_GATE",
    "CLEARED",
}
BLOCKING_STATES = {"OPEN", "PARTIAL", "EVIDENCE_MISMATCH_FAIL_CLOSED"}
CHECK_KINDS = {
    "json_array_contains",
    "json_equals",
    "json_number_equals_pointer",
    "json_number_gt",
    "json_number_gt_pointer",
    "text_contains",
    "text_regex_count_gt",
    "timestamp_age_days_gt",
    "timestamp_before_as_of",
}
ALLOWED_SOURCE_PREFIXES = (
    "config/",
    "grant_submissions/",
    "out/grants/",
    "out/portfolio_external_action_ledger/",
)
ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRIORITY_RE = re.compile(r"^P[0-3]$")
PRIVATE_REF_RE = re.compile(r"^private-ref:[a-z][a-z0-9_.-]{2,95}$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")

CLAIM_BOUNDARY = (
    "This audit reports source-backed readiness blockers and remediation ownership. It does not "
    "log in, authenticate, attest, certify, upload, submit, or establish eligibility, compliance, "
    "agency acceptance, award, contract, licensing, economic relief, or legal sufficiency. A local "
    "receipt, boolean, hash, draft, queue state, or portal observation is not an agency-issued "
    "determination."
)


class AuditConfigError(ValueError):
    """Raised when the audit configuration cannot be evaluated safely."""


class LoadedSource:
    __slots__ = (
        "source_id",
        "path",
        "relative_path",
        "source_class",
        "sensitivity",
        "raw",
        "text",
        "json_payload",
    )

    def __init__(
        self,
        *,
        source_id: str,
        path: Path,
        relative_path: str,
        source_class: str,
        sensitivity: str,
        raw: bytes,
        text: str,
        json_payload: Any | None,
    ) -> None:
        self.source_id = source_id
        self.path = path
        self.relative_path = relative_path
        self.source_class = source_class
        self.sensitivity = sensitivity
        self.raw = raw
        self.text = text
        self.json_payload = json_payload


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AuditConfigError(f"{field} must be a non-empty timestamp")
    candidate = value.strip()
    if re.fullmatch(r"\d{8}T\d{6}Z", candidate):
        parsed = datetime.strptime(candidate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return parsed
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditConfigError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise AuditConfigError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_relative_path(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditConfigError(f"{field} must be a repository-relative path")
    normalized = Path(value.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise AuditConfigError(f"{field} must stay repository-relative")
    posix = normalized.as_posix()
    if not posix.startswith(ALLOWED_SOURCE_PREFIXES):
        raise AuditConfigError(f"{field} is outside the allowed evidence roots")
    return posix


def _require_safe_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditConfigError(f"{field} must be a non-empty string")
    text = value.strip()
    if "\x00" in text or EMAIL_RE.search(text):
        raise AuditConfigError(f"{field} contains prohibited private contact data")
    return text


def _json_pointer_get(payload: Any, pointer: str) -> Any:
    if pointer == "":
        return payload
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise KeyError("JSON pointer must begin with '/'")
    current = payload
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(pointer)
    return current


def _load_sources(
    config: dict[str, Any],
    *,
    root: Path,
) -> tuple[dict[str, LoadedSource], list[dict[str, Any]]]:
    loaded: dict[str, LoadedSource] = {}
    inventory: list[dict[str, Any]] = []
    root_resolved = root.resolve()
    for source_id in sorted(config["sources"]):
        source = config["sources"][source_id]
        relative_path = _safe_relative_path(source["path"], f"sources.{source_id}.path")
        path = (root_resolved / relative_path).resolve()
        if not path.is_relative_to(root_resolved):
            raise AuditConfigError(f"sources.{source_id}.path escapes the repository")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise AuditConfigError(f"required source is unavailable: {source_id}") from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AuditConfigError(f"source is not UTF-8 text: {source_id}") from exc
        json_payload: Any | None = None
        if path.suffix.lower() == ".json":
            try:
                json_payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise AuditConfigError(f"source is not valid JSON: {source_id}") from exc
        item = LoadedSource(
            source_id=source_id,
            path=path,
            relative_path=relative_path,
            source_class=source["source_class"],
            sensitivity=source["sensitivity"],
            raw=raw,
            text=text,
            json_payload=json_payload,
        )
        loaded[source_id] = item
        display_ref = (
            relative_path
            if item.sensitivity == "PUBLIC"
            else f"private-ref:{source_id}"
        )
        inventory.append(
            {
                "source_id": source_id,
                "source_ref": display_ref,
                "source_class": item.source_class,
                "sensitivity": item.sensitivity,
                "bytes": len(raw),
                "sha256": bytes_sha256(raw),
            }
        )
    return loaded, inventory


def _evaluate_check(
    check: dict[str, Any],
    source: LoadedSource,
    *,
    as_of: datetime,
) -> dict[str, Any]:
    kind = check["kind"]
    matched = False
    error_code = ""
    try:
        if kind == "text_contains":
            matched = check["expected"] in source.text
        elif kind == "text_regex_count_gt":
            count = len(re.findall(check["pattern"], source.text, flags=re.MULTILINE))
            matched = count > int(check["threshold"])
        else:
            if source.json_payload is None:
                raise TypeError("JSON check applied to non-JSON source")
            pointer = check["pointer"]
            observed = _json_pointer_get(source.json_payload, pointer)
            if kind == "json_equals":
                matched = observed == check["expected"]
            elif kind == "json_array_contains":
                matched = isinstance(observed, list) and check["expected"] in observed
            elif kind == "json_number_gt":
                matched = (
                    isinstance(observed, (int, float))
                    and not isinstance(observed, bool)
                    and observed > check["threshold"]
                )
            elif kind in {"json_number_equals_pointer", "json_number_gt_pointer"}:
                other = _json_pointer_get(source.json_payload, check["other_pointer"])
                numeric = (
                    isinstance(observed, (int, float))
                    and not isinstance(observed, bool)
                    and isinstance(other, (int, float))
                    and not isinstance(other, bool)
                )
                if kind == "json_number_equals_pointer":
                    matched = numeric and observed == other
                else:
                    matched = numeric and observed > other
            elif kind == "timestamp_before_as_of":
                matched = parse_utc(str(observed), check["label"]) < as_of
            elif kind == "timestamp_age_days_gt":
                observed_at = parse_utc(str(observed), check["label"])
                matched = as_of - observed_at > timedelta(days=int(check["days"]))
            else:
                raise AuditConfigError(f"unsupported check kind: {kind}")
        if not matched:
            error_code = "EXPECTED_EVIDENCE_NOT_MATCHED"
    except (AuditConfigError, KeyError, TypeError, ValueError):
        matched = False
        error_code = "EVIDENCE_CHECK_ERROR"
    return {
        "source_id": source.source_id,
        "label": check["label"],
        "kind": kind,
        "matched": matched,
        "error_code": error_code,
    }


def _validate_check(check: dict[str, Any], field: str, source_ids: set[str]) -> None:
    if not isinstance(check, dict):
        raise AuditConfigError(f"{field} must be an object")
    required = {"source_id", "kind", "label"}
    missing = sorted(required - set(check))
    if missing:
        raise AuditConfigError(f"{field} missing keys: {', '.join(missing)}")
    if check["source_id"] not in source_ids:
        raise AuditConfigError(f"{field}.source_id is not declared")
    if check["kind"] not in CHECK_KINDS:
        raise AuditConfigError(f"{field}.kind is not supported")
    _require_safe_text(check["label"], f"{field}.label")
    kind = check["kind"]
    if kind == "text_contains":
        _require_safe_text(check.get("expected"), f"{field}.expected")
    elif kind == "text_regex_count_gt":
        pattern = _require_safe_text(check.get("pattern"), f"{field}.pattern")
        if len(pattern) > 160:
            raise AuditConfigError(f"{field}.pattern is too long")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise AuditConfigError(f"{field}.pattern is invalid") from exc
        if not isinstance(check.get("threshold"), int) or check["threshold"] < 0:
            raise AuditConfigError(f"{field}.threshold must be a non-negative integer")
    else:
        pointer = check.get("pointer")
        if not isinstance(pointer, str) or not pointer.startswith("/"):
            raise AuditConfigError(f"{field}.pointer must be a JSON pointer")
        if kind in {"json_equals", "json_array_contains"} and "expected" not in check:
            raise AuditConfigError(f"{field}.expected is required")
        if kind == "json_number_gt":
            if not isinstance(check.get("threshold"), (int, float)):
                raise AuditConfigError(f"{field}.threshold must be numeric")
        if kind in {"json_number_equals_pointer", "json_number_gt_pointer"}:
            other = check.get("other_pointer")
            if not isinstance(other, str) or not other.startswith("/"):
                raise AuditConfigError(f"{field}.other_pointer must be a JSON pointer")
        if kind == "timestamp_age_days_gt":
            days = check.get("days")
            if not isinstance(days, int) or days < 0:
                raise AuditConfigError(f"{field}.days must be a non-negative integer")


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise AuditConfigError("config root must be an object")
    if config.get("schema") != CONFIG_SCHEMA:
        raise AuditConfigError(f"config schema must be {CONFIG_SCHEMA}")
    parse_utc(str(config.get("audit_as_of_utc", "")), "audit_as_of_utc")
    if tuple(config.get("classifications", [])) != CLASSIFICATIONS:
        raise AuditConfigError("config classifications must match the frozen v1 list")
    if tuple(config.get("required_domains", [])) != REQUIRED_DOMAINS:
        raise AuditConfigError("config required_domains must match the frozen v1 list")
    sources = config.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise AuditConfigError("config sources must be a non-empty object")
    source_ids = set(sources)
    for source_id, source in sources.items():
        if not ID_RE.fullmatch(source_id):
            raise AuditConfigError(f"invalid source id: {source_id}")
        if not isinstance(source, dict):
            raise AuditConfigError(f"sources.{source_id} must be an object")
        _safe_relative_path(source.get("path", ""), f"sources.{source_id}.path")
        if source.get("source_class") not in SOURCE_CLASSES:
            raise AuditConfigError(f"sources.{source_id}.source_class is invalid")
        if source.get("sensitivity") not in {"PUBLIC", "PRIVATE"}:
            raise AuditConfigError(f"sources.{source_id}.sensitivity is invalid")

    gates = config.get("gates")
    if not isinstance(gates, list) or not gates:
        raise AuditConfigError("config gates must be a non-empty list")
    gate_ids: set[str] = set()
    observed_domains: set[str] = set()
    for index, gate in enumerate(gates):
        field = f"gates[{index}]"
        if not isinstance(gate, dict):
            raise AuditConfigError(f"{field} must be an object")
        required = {
            "gate_id",
            "domain",
            "classification",
            "state",
            "priority",
            "reviewer_question",
            "current_answer",
            "proof_required_to_clear",
            "safest_next_action",
            "actionable_now",
            "checks",
        }
        missing = sorted(required - set(gate))
        if missing:
            raise AuditConfigError(f"{field} missing keys: {', '.join(missing)}")
        gate_id = gate["gate_id"]
        if not isinstance(gate_id, str) or not ID_RE.fullmatch(gate_id):
            raise AuditConfigError(f"{field}.gate_id is invalid")
        if gate_id in gate_ids:
            raise AuditConfigError(f"duplicate gate_id: {gate_id}")
        gate_ids.add(gate_id)
        domain = gate["domain"]
        if domain not in REQUIRED_DOMAINS:
            raise AuditConfigError(f"{field}.domain is invalid")
        observed_domains.add(domain)
        classification = gate["classification"]
        state = gate["state"]
        if classification not in CLASSIFICATIONS:
            raise AuditConfigError(f"{field}.classification is invalid")
        if state not in STATES:
            raise AuditConfigError(f"{field}.state is invalid")
        if classification == "EXPIRED_OR_CLOSED_ROUTE" and state != "CLOSED_ROUTE":
            raise AuditConfigError(f"{field} closed-route classification requires CLOSED_ROUTE")
        if classification == "UNSUPPORTED_ASSUMPTION" and state != "NOT_A_GATE":
            raise AuditConfigError(f"{field} unsupported assumptions require NOT_A_GATE")
        if not PRIORITY_RE.fullmatch(str(gate["priority"])):
            raise AuditConfigError(f"{field}.priority is invalid")
        for text_field in (
            "reviewer_question",
            "current_answer",
            "proof_required_to_clear",
            "safest_next_action",
        ):
            _require_safe_text(gate[text_field], f"{field}.{text_field}")
        if not isinstance(gate["actionable_now"], bool):
            raise AuditConfigError(f"{field}.actionable_now must be boolean")
        checks = gate["checks"]
        if not isinstance(checks, list) or not checks:
            raise AuditConfigError(f"{field}.checks must be a non-empty list")
        for check_index, check in enumerate(checks):
            _validate_check(check, f"{field}.checks[{check_index}]", source_ids)
        if state == "CLEARED":
            clearance_ids = gate.get("clearance_evidence_source_ids")
            if not isinstance(clearance_ids, list) or not clearance_ids:
                raise AuditConfigError(
                    f"{field} CLEARED requires clearance_evidence_source_ids"
                )
            for source_id in clearance_ids:
                if source_id not in source_ids:
                    raise AuditConfigError(f"{field} has unknown clearance source")
                source_class = sources[source_id]["source_class"]
                permitted = set(AUTHORITATIVE_CLEARANCE_CLASSES)
                if classification == "LOCALLY_FIXABLE_NOW":
                    permitted.update(LOCAL_PROCESS_CLEARANCE_CLASSES)
                if source_class not in permitted:
                    raise AuditConfigError(
                        f"{field} cannot be cleared by {source_class}"
                    )
    missing_domains = sorted(set(REQUIRED_DOMAINS) - observed_domains)
    if missing_domains:
        raise AuditConfigError(
            "config does not cover required domains: " + ", ".join(missing_domains)
        )
    rules = config.get("rules")
    if not isinstance(rules, list) or not rules:
        raise AuditConfigError("config rules must be a non-empty list")
    for index, rule in enumerate(rules):
        _require_safe_text(rule, f"rules[{index}]")


def build_report(
    config: dict[str, Any],
    *,
    root: Path = ROOT,
    as_of_utc: str | None = None,
    config_sha256: str | None = None,
    generator_sha256: str | None = None,
) -> dict[str, Any]:
    validate_config(config)
    as_of = parse_utc(
        as_of_utc or str(config["audit_as_of_utc"]),
        "audit_as_of_utc",
    )
    sources, source_inventory = _load_sources(config, root=root)
    gates: list[dict[str, Any]] = []
    for configured in config["gates"]:
        check_results = [
            _evaluate_check(check, sources[check["source_id"]], as_of=as_of)
            for check in configured["checks"]
        ]
        evidence_matches = all(item["matched"] for item in check_results)
        effective_state = (
            configured["state"]
            if evidence_matches
            else "EVIDENCE_MISMATCH_FAIL_CLOSED"
        )
        if effective_state == "CLEARED":
            clearance_classes = {
                config["sources"][source_id]["source_class"]
                for source_id in configured["clearance_evidence_source_ids"]
            }
            clearance_status = (
                "CLEARED_BY_LOCAL_CONTROL"
                if clearance_classes & LOCAL_PROCESS_CLEARANCE_CLASSES
                else "CLEARED_BY_AUTHORITATIVE_EVIDENCE"
            )
        else:
            clearance_status = {
                "NOT_A_GATE": "NOT_A_GATE",
                "CLOSED_ROUTE": "ROUTE_CLOSED_NO_LATE_ACTION",
            }.get(effective_state, "NOT_CLEARED")
        gates.append(
            {
                "gate_id": configured["gate_id"],
                "domain": configured["domain"],
                "classification": configured["classification"],
                "priority": configured["priority"],
                "configured_state": configured["state"],
                "effective_state": effective_state,
                "clearance_status": clearance_status,
                "blocks_current_pursuit": effective_state in BLOCKING_STATES
                or effective_state == "CLOSED_ROUTE",
                "actionable_now": configured["actionable_now"]
                and effective_state in BLOCKING_STATES,
                "reviewer_question": configured["reviewer_question"],
                "current_answer": configured["current_answer"],
                "proof_required_to_clear": configured["proof_required_to_clear"],
                "safest_next_action": configured["safest_next_action"],
                "evidence_status": (
                    "MATCHED_CONFIGURED_FINDING"
                    if evidence_matches
                    else "MISMATCH_FAIL_CLOSED"
                ),
                "checks": check_results,
            }
        )

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    class_order = {name: index for index, name in enumerate(CLASSIFICATIONS)}
    gates.sort(
        key=lambda item: (
            priority_order[item["priority"]],
            class_order[item["classification"]],
            item["domain"],
            item["gate_id"],
        )
    )
    evidence_mismatch_count = sum(
        item["effective_state"] == "EVIDENCE_MISMATCH_FAIL_CLOSED" for item in gates
    )
    summary = {
        "gate_count": len(gates),
        "open_blocker_count": sum(
            item["effective_state"] in BLOCKING_STATES for item in gates
        ),
        "closed_route_count": sum(
            item["effective_state"] == "CLOSED_ROUTE" for item in gates
        ),
        "unsupported_assumption_count": sum(
            item["effective_state"] == "NOT_A_GATE" for item in gates
        ),
        "cleared_gate_count": sum(
            item["effective_state"] == "CLEARED" for item in gates
        ),
        "evidence_mismatch_count": evidence_mismatch_count,
        "actionable_now_count": sum(item["actionable_now"] for item in gates),
        "by_classification": {
            classification: sum(
                item["classification"] == classification for item in gates
            )
            for classification in CLASSIFICATIONS
        },
        "by_domain": {
            domain: sum(item["domain"] == domain for item in gates)
            for domain in REQUIRED_DOMAINS
        },
    }
    source_set_sha256 = stable_hash(source_inventory)
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "audit_as_of_utc": format_utc(as_of),
        "report_state": (
            "EVIDENCE_MISMATCH_FAIL_CLOSED"
            if evidence_mismatch_count
            else "BLOCKERS_IDENTIFIED"
            if summary["open_blocker_count"] or summary["closed_route_count"]
            else "NO_OPEN_BLOCKERS"
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "required_domains": list(REQUIRED_DOMAINS),
        "classifications": list(CLASSIFICATIONS),
        "rules": deepcopy(config["rules"]),
        "summary": summary,
        "gates": gates,
        "source_inventory": source_inventory,
        "integrity": {
            "hash_algorithm": "SHA-256",
            "config_sha256": config_sha256 or stable_hash(config),
            "generator_sha256": generator_sha256 or file_sha256(Path(__file__)),
            "source_set_sha256": source_set_sha256,
            "report_sha256": "",
        },
    }
    unhashed = deepcopy(report)
    unhashed["integrity"]["report_sha256"] = ""
    report["integrity"]["report_sha256"] = stable_hash(unhashed)
    return report


def verify_report_hash(report: dict[str, Any]) -> bool:
    candidate = deepcopy(report)
    expected = str(candidate.get("integrity", {}).get("report_sha256", ""))
    if not SHA256_RE.fullmatch(expected):
        return False
    candidate["integrity"]["report_sha256"] = ""
    return stable_hash(candidate) == expected


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Economic Relief and Award Readiness Gate Audit",
        "",
        f"Audit snapshot: `{report['audit_as_of_utc']}`",
        f"Report state: `{report['report_state']}`",
        f"Report SHA-256: `{report['integrity']['report_sha256']}`",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Gates audited: `{summary['gate_count']}`",
        f"- Open or partial blockers: `{summary['open_blocker_count']}`",
        f"- Closed routes: `{summary['closed_route_count']}`",
        f"- Unsupported assumptions removed: `{summary['unsupported_assumption_count']}`",
        f"- Gates cleared by authoritative evidence: `{summary['cleared_gate_count']}`",
        f"- Evidence mismatches: `{summary['evidence_mismatch_count']}`",
        f"- Safe actions available now: `{summary['actionable_now_count']}`",
        "",
        "## Classification Counts",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for classification in CLASSIFICATIONS:
        lines.append(
            f"| `{classification}` | {summary['by_classification'][classification]} |"
        )
    lines.append("")

    for classification in CLASSIFICATIONS:
        items = [
            item for item in report["gates"] if item["classification"] == classification
        ]
        lines.extend(
            [
                f"## {classification.replace('_', ' ').title()}",
                "",
                "| Gate | State | Priority | Reviewer question | Current answer | Safest next action |",
                "|---|---|---|---|---|---|",
            ]
        )
        for item in items:
            lines.append(
                "| `{gate}` | `{state}` | `{priority}` | {question} | {answer} | {action} |".format(
                    gate=item["gate_id"],
                    state=item["effective_state"],
                    priority=item["priority"],
                    question=_md_escape(item["reviewer_question"]),
                    answer=_md_escape(item["current_answer"]),
                    action=_md_escape(item["safest_next_action"]),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Clearance Proof Required",
            "",
            "| Gate | Required proof | Evidence checks |",
            "|---|---|---:|",
        ]
    )
    for item in report["gates"]:
        matched = sum(check["matched"] for check in item["checks"])
        lines.append(
            "| `{gate}` | {proof} | {matched}/{total} |".format(
                gate=item["gate_id"],
                proof=_md_escape(item["proof_required_to_clear"]),
                matched=matched,
                total=len(item["checks"]),
            )
        )
    lines.extend(
        [
            "",
            "## Evidence Inventory",
            "",
            "| Source | Class | Sensitivity | Bytes | SHA-256 |",
            "|---|---|---|---:|---|",
        ]
    )
    for source in report["source_inventory"]:
        lines.append(
            "| `{ref}` | `{source_class}` | `{sensitivity}` | {bytes} | `{sha}` |".format(
                ref=source["source_ref"],
                source_class=source["source_class"],
                sensitivity=source["sensitivity"],
                bytes=source["bytes"],
                sha=source["sha256"],
            )
        )
    lines.extend(
        [
            "",
            "## Frozen Rules",
            "",
            *[f"- {rule}" for rule in report["rules"]],
            "",
        ]
    )
    return "\n".join(lines)


def output_bytes(report: dict[str, Any]) -> tuple[bytes, bytes]:
    if not verify_report_hash(report):
        raise RuntimeError("refusing to serialize a report with an invalid hash")
    json_bytes = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8")
        + b"\n"
    )
    markdown_bytes = (render_markdown(report) + "\n").encode("utf-8")
    return json_bytes, markdown_bytes


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
    temporary.replace(path)


def write_outputs(report: dict[str, Any], out_json: Path, out_md: Path) -> None:
    json_bytes, markdown_bytes = output_bytes(report)
    atomic_write(out_json, json_bytes)
    atomic_write(out_md, markdown_bytes)


def check_outputs(report: dict[str, Any], out_json: Path, out_md: Path) -> list[str]:
    expected_json, expected_md = output_bytes(report)
    stale: list[str] = []
    for path, expected in ((out_json, expected_json), (out_md, expected_md)):
        try:
            actual = path.read_bytes()
        except OSError:
            stale.append(str(path))
            continue
        if actual != expected:
            stale.append(str(path))
    return stale


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditConfigError(f"unable to read config: {path}") from exc
    if not isinstance(payload, dict):
        raise AuditConfigError("config root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic economic-relief and award-readiness gate audit"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--as-of-utc", default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated outputs differ; do not write files",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    report = build_report(
        load_config(config_path),
        root=ROOT,
        as_of_utc=args.as_of_utc,
        config_sha256=file_sha256(config_path),
        generator_sha256=file_sha256(Path(__file__)),
    )
    out_json = args.out_json.resolve()
    out_md = args.out_md.resolve()
    if args.check:
        stale = check_outputs(report, out_json, out_md)
        if stale:
            print(
                json.dumps(
                    {
                        "status": "STALE",
                        "stale_outputs": stale,
                    },
                    sort_keys=True,
                )
            )
            return 1
    else:
        write_outputs(report, out_json, out_md)
    print(
        json.dumps(
            {
                "status": "CURRENT" if args.check else "BUILT",
                "report_state": report["report_state"],
                "gate_count": report["summary"]["gate_count"],
                "open_blocker_count": report["summary"]["open_blocker_count"],
                "closed_route_count": report["summary"]["closed_route_count"],
                "report_sha256": report["integrity"]["report_sha256"],
                "out_json": str(out_json),
                "out_md": str(out_md),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
