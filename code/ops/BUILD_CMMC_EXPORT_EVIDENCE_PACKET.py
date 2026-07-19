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
DEFAULT_CONFIG = ROOT / "config" / "cmmc_export_evidence_packet_v1.json"
DEFAULT_OUT_DIR = ROOT / "grant_submissions" / "compliance_evidence"
DEFAULT_OUT_JSON = DEFAULT_OUT_DIR / "CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json"
DEFAULT_OUT_MD = DEFAULT_OUT_DIR / "CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.md"

CONFIG_SCHEMA = "lumencore.cmmc_export_evidence_packet_config.v1"
PACKET_SCHEMA = "lumencore.cmmc_export_evidence_packet.v1"
ALLOWED_SOURCE_CLASSES = (
    "FOUNDER_ATTESTATION",
    "LEGAL_REVIEW",
    "TECHNICAL_CONTROL_EVIDENCE",
    "PORTAL_OBSERVED",
    "PORTAL_ISSUED",
    "AGENCY_DETERMINATION",
)
PROOF_STATES_BY_SOURCE_CLASS = {
    "FOUNDER_ATTESTATION": {"ATTESTED"},
    "LEGAL_REVIEW": {"REVIEWED"},
    "TECHNICAL_CONTROL_EVIDENCE": {"VERIFIED"},
    "PORTAL_OBSERVED": {"OBSERVED"},
    "PORTAL_ISSUED": {"ISSUED"},
    "AGENCY_DETERMINATION": {"DETERMINED", "ISSUED"},
}
NON_AUTHORITATIVE_CLASSES = {"FOUNDER_ATTESTATION", "PORTAL_OBSERVED"}
APPLICABILITY_STATES = {"APPLIES", "NOT_APPLICABLE", "UNKNOWN"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_REF_RE = re.compile(r"^(?:private-ref|official-source):[a-z0-9][a-z0-9._:/-]{1,180}$")
SAFE_SUBJECT_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
NAMED_REVIEW_ROLE_RE = re.compile(r"(?:legal|counsel|contracting)", re.IGNORECASE)
PROHIBITED_CONCLUSIONS = (
    "compliant",
    "certified",
    "award_eligible",
)
CLAIM_BOUNDARY = (
    "Evidence inventory only. This packet does not determine or claim compliance, certification, "
    "award eligibility, export authorization, JCP approval, or satisfaction of any solicitation. "
    "Only the named authoritative issuer, contracting authority, or qualified reviewer can make "
    "the corresponding determination."
)
EVALUATION_LIMIT = (
    "The builder validates only supplied metadata, chronology, scope markers, source-class policy, "
    "and deterministic integrity. It does not open referenced private evidence or authenticate an "
    "issuer, signature, portal session, legal opinion, or agency determination."
)


class PacketConfigError(ValueError):
    """Raised when the packet configuration cannot be evaluated safely."""


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PacketConfigError(f"{field} must be a non-empty ISO-8601 timestamp")
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise PacketConfigError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PacketConfigError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def require_safe_reference(value: str, field: str) -> str:
    if not isinstance(value, str) or not SAFE_REF_RE.fullmatch(value):
        raise PacketConfigError(
            f"{field} must be an opaque private-ref: or official-source: reference"
        )
    if ".." in value or "@" in value or "\\" in value:
        raise PacketConfigError(f"{field} contains a prohibited path or identifier fragment")
    return value


def validate_source_path(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketConfigError(f"{field} must be a non-empty repository-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise PacketConfigError(f"{field} must stay repository-relative")
    return path.as_posix()


def _evidence_issue(evidence_id: str, code: str) -> dict[str, str]:
    return {"evidence_id": evidence_id, "code": code}


def evaluate_evidence(
    evidence: dict[str, Any],
    requirement: dict[str, Any],
    *,
    as_of: datetime,
    max_age_days: int,
) -> tuple[dict[str, Any], list[dict[str, str]], bool]:
    evidence_id = str(evidence.get("evidence_id", "")).strip()
    if not evidence_id:
        evidence_id = "unnamed-evidence"
    issues: list[dict[str, str]] = []

    source_class = str(evidence.get("source_class", "")).strip().upper()
    if source_class not in ALLOWED_SOURCE_CLASSES:
        issues.append(_evidence_issue(evidence_id, "SOURCE_CLASS_NOT_ALLOWED"))

    proof_state = str(evidence.get("proof_state", "")).strip().upper()
    if proof_state not in PROOF_STATES_BY_SOURCE_CLASS.get(source_class, set()):
        issues.append(_evidence_issue(evidence_id, "PROOF_STATE_SOURCE_CLASS_MISMATCH"))

    issuer = str(evidence.get("issuer", "")).strip().upper()
    required_issuers = {str(item).strip().upper() for item in requirement["accepted_issuers"]}
    if not issuer or issuer not in required_issuers:
        issues.append(_evidence_issue(evidence_id, "ISSUER_NOT_ACCEPTED"))

    artifact_sha256 = str(evidence.get("artifact_sha256", "")).strip().lower()
    if not SHA256_RE.fullmatch(artifact_sha256):
        issues.append(_evidence_issue(evidence_id, "ARTIFACT_SHA256_MALFORMED"))

    artifact_ref = str(evidence.get("artifact_ref", "")).strip()
    try:
        require_safe_reference(artifact_ref, f"evidence[{evidence_id}].artifact_ref")
    except PacketConfigError:
        issues.append(_evidence_issue(evidence_id, "ARTIFACT_REFERENCE_UNSAFE_OR_MISSING"))

    entity_match = str(evidence.get("entity_match", "UNKNOWN")).strip().upper()
    scope_match = str(evidence.get("scope_match", "UNKNOWN")).strip().upper()
    if entity_match != "MATCH":
        issues.append(_evidence_issue(evidence_id, "ENTITY_NOT_MATCHED"))
    if scope_match != "MATCH":
        issues.append(_evidence_issue(evidence_id, "SCOPE_NOT_MATCHED"))
    if evidence.get("conflict") is not False:
        issues.append(_evidence_issue(evidence_id, "CONFLICT_PRESENT_OR_UNRESOLVED"))

    issued_at: datetime | None = None
    try:
        issued_at = parse_utc(
            str(evidence.get("issued_utc", "")),
            f"evidence[{evidence_id}].issued_utc",
        )
    except PacketConfigError:
        issues.append(_evidence_issue(evidence_id, "ISSUED_TIMESTAMP_INVALID"))

    expires_raw = evidence.get("expires_utc")
    if expires_raw:
        try:
            expires_at = parse_utc(str(expires_raw), f"evidence[{evidence_id}].expires_utc")
            if expires_at < as_of:
                issues.append(_evidence_issue(evidence_id, "EVIDENCE_EXPIRED"))
            if issued_at is not None and expires_at < issued_at:
                issues.append(_evidence_issue(evidence_id, "EXPIRY_PRECEDES_ISSUE"))
        except PacketConfigError:
            issues.append(_evidence_issue(evidence_id, "EXPIRY_TIMESTAMP_INVALID"))
    elif issued_at is not None and as_of - issued_at > timedelta(days=max_age_days):
        issues.append(_evidence_issue(evidence_id, "EVIDENCE_STALE"))

    accepted_classes = {
        str(item).strip().upper() for item in requirement["accepted_source_classes"]
    }
    if source_class not in accepted_classes:
        issues.append(_evidence_issue(evidence_id, "SOURCE_CLASS_INSUFFICIENT_FOR_REQUIREMENT"))
    if source_class in NON_AUTHORITATIVE_CLASSES:
        issues.append(_evidence_issue(evidence_id, "LOCAL_OR_OBSERVED_EVIDENCE_NOT_AUTHORITATIVE"))

    usable = not issues
    safe_summary = {
        "evidence_id": evidence_id,
        "source_class": source_class or "UNKNOWN",
        "proof_state": proof_state or "UNKNOWN",
        "issuer": issuer or "UNKNOWN",
        "artifact_ref": artifact_ref if SAFE_REF_RE.fullmatch(artifact_ref) else "REDACTED_INVALID_REF",
        "artifact_sha256": artifact_sha256 if SHA256_RE.fullmatch(artifact_sha256) else "",
        "entity_match": entity_match,
        "scope_match": scope_match,
        "conflict": evidence.get("conflict") is not False,
        "evaluation": "ACCEPTED_PROOF_METADATA" if usable else "REJECTED_FAIL_CLOSED",
    }
    return safe_summary, issues, usable


def evaluate_not_applicable(
    applicability: dict[str, Any], fact_id: str
) -> tuple[dict[str, Any], list[dict[str, str]], bool]:
    issues: list[dict[str, str]] = []
    decided_by = str(applicability.get("decided_by_source_class", "")).strip().upper()
    reviewer_name = str(applicability.get("reviewer_name", "")).strip()
    reviewer_role = str(applicability.get("reviewer_role", "")).strip()
    decision_ref = str(applicability.get("decision_ref", "")).strip()
    decision_sha256 = str(applicability.get("decision_sha256", "")).strip().lower()
    if decided_by not in {"LEGAL_REVIEW", "AGENCY_DETERMINATION"}:
        issues.append(_evidence_issue(fact_id, "NOT_APPLICABLE_REQUIRES_QUALIFIED_SOURCE"))
    if not reviewer_name or not reviewer_role or not NAMED_REVIEW_ROLE_RE.search(reviewer_role):
        issues.append(_evidence_issue(fact_id, "NOT_APPLICABLE_REQUIRES_NAMED_REVIEW"))
    try:
        require_safe_reference(decision_ref, f"applicability[{fact_id}].decision_ref")
    except PacketConfigError:
        issues.append(_evidence_issue(fact_id, "NOT_APPLICABLE_DECISION_REFERENCE_INVALID"))
    if not SHA256_RE.fullmatch(decision_sha256):
        issues.append(_evidence_issue(fact_id, "NOT_APPLICABLE_DECISION_HASH_INVALID"))
    try:
        parse_utc(str(applicability.get("decided_utc", "")), f"applicability[{fact_id}].decided_utc")
    except PacketConfigError:
        issues.append(_evidence_issue(fact_id, "NOT_APPLICABLE_DECISION_TIMESTAMP_INVALID"))
    safe = {
        "state": "NOT_APPLICABLE",
        "decided_by_source_class": decided_by or "UNKNOWN",
        "named_reviewer_present": bool(reviewer_name),
        "reviewer_role": reviewer_role,
        "decision_ref": decision_ref if SAFE_REF_RE.fullmatch(decision_ref) else "",
        "decision_sha256": decision_sha256 if SHA256_RE.fullmatch(decision_sha256) else "",
    }
    return safe, issues, not issues


def evaluate_requirement(
    requirement: dict[str, Any], *, as_of: datetime, max_age_days: int
) -> dict[str, Any]:
    required_keys = {
        "fact_id",
        "control",
        "applicability",
        "accepted_source_classes",
        "accepted_issuers",
        "evidence",
    }
    missing = sorted(required_keys - set(requirement))
    if missing:
        raise PacketConfigError(f"requirement missing keys: {', '.join(missing)}")
    fact_id = str(requirement["fact_id"]).strip()
    if not fact_id:
        raise PacketConfigError("requirement fact_id must not be empty")

    accepted_classes = [str(item).strip().upper() for item in requirement["accepted_source_classes"]]
    if not accepted_classes or any(item not in ALLOWED_SOURCE_CLASSES for item in accepted_classes):
        raise PacketConfigError(f"{fact_id} has an invalid accepted_source_classes list")
    if any(item in NON_AUTHORITATIVE_CLASSES for item in accepted_classes):
        raise PacketConfigError(
            f"{fact_id} cannot accept founder attestations or portal observations as proof"
        )
    accepted_issuers = [str(item).strip().upper() for item in requirement["accepted_issuers"]]
    if not accepted_issuers or any(not item for item in accepted_issuers):
        raise PacketConfigError(f"{fact_id} must name at least one accepted issuer")

    applicability = requirement["applicability"]
    if not isinstance(applicability, dict):
        raise PacketConfigError(f"{fact_id}.applicability must be an object")
    applicability_state = str(applicability.get("state", "UNKNOWN")).strip().upper()
    if applicability_state not in APPLICABILITY_STATES:
        raise PacketConfigError(f"{fact_id} has invalid applicability state")

    result: dict[str, Any] = {
        "fact_id": fact_id,
        "control": str(requirement["control"]).strip(),
        "applicability": {
            "state": applicability_state,
            "basis": str(applicability.get("basis", "")).strip(),
        },
        "accepted_source_classes": accepted_classes,
        "accepted_issuers": accepted_issuers,
        "evidence": [],
        "issues": [],
        "authoritative_proof_count": 0,
        "evidence_state": "MISSING_OFFICIAL_PROOF",
        "prohibited_conclusions": list(PROHIBITED_CONCLUSIONS),
    }

    if applicability_state == "UNKNOWN":
        result["evidence_state"] = "APPLICABILITY_UNRESOLVED"
        result["issues"].append(_evidence_issue(fact_id, "APPLICABILITY_UNRESOLVED"))
        return result

    if applicability_state == "NOT_APPLICABLE":
        safe_applicability, issues, valid = evaluate_not_applicable(applicability, fact_id)
        result["applicability"] = safe_applicability
        result["issues"].extend(issues)
        result["evidence_state"] = (
            "NOT_APPLICABLE_REVIEW_INVENTORIED" if valid else "NOT_APPLICABLE_UNSUPPORTED"
        )
        return result

    evidence_rows = requirement["evidence"]
    if not isinstance(evidence_rows, list):
        raise PacketConfigError(f"{fact_id}.evidence must be a list")
    observed_evidence_ids: set[str] = set()
    for evidence in evidence_rows:
        if not isinstance(evidence, dict):
            raise PacketConfigError(f"{fact_id}.evidence entries must be objects")
        evidence_id = str(evidence.get("evidence_id", "")).strip()
        if evidence_id and evidence_id in observed_evidence_ids:
            raise PacketConfigError(f"{fact_id} contains duplicate evidence_id {evidence_id}")
        observed_evidence_ids.add(evidence_id)
        safe_evidence, issues, usable = evaluate_evidence(
            evidence,
            {
                "accepted_source_classes": accepted_classes,
                "accepted_issuers": accepted_issuers,
            },
            as_of=as_of,
            max_age_days=max_age_days,
        )
        result["evidence"].append(safe_evidence)
        result["issues"].extend(issues)
        if usable:
            result["authoritative_proof_count"] += 1

    if result["authoritative_proof_count"] > 0 and not result["issues"]:
        result["evidence_state"] = "AUTHORITATIVE_PROOF_INVENTORIED"
    elif not any(issue["code"] == "MISSING_OFFICIAL_PROOF" for issue in result["issues"]):
        result["issues"].append(_evidence_issue(fact_id, "MISSING_OFFICIAL_PROOF"))
    return result


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA:
        raise PacketConfigError(f"config schema must be {CONFIG_SCHEMA}")
    if tuple(config.get("source_classes", [])) != ALLOWED_SOURCE_CLASSES:
        raise PacketConfigError("config source_classes must match the frozen v1 source-class list")
    subject_ref = str(config.get("subject_ref", ""))
    if not SAFE_SUBJECT_RE.fullmatch(subject_ref):
        raise PacketConfigError("subject_ref must be an opaque lowercase token, not an entity identifier")
    max_age_days = config.get("max_evidence_age_days")
    if not isinstance(max_age_days, int) or not 1 <= max_age_days <= 3660:
        raise PacketConfigError("max_evidence_age_days must be an integer from 1 through 3660")
    programs = config.get("programs")
    if not isinstance(programs, list) or not programs:
        raise PacketConfigError("config must contain at least one program")
    expected_programs = {"DICE", "HarborSentinel", "MissionWeave"}
    observed_programs = {str(program.get("program_id", "")) for program in programs}
    if observed_programs != expected_programs:
        raise PacketConfigError("config must contain exactly DICE, HarborSentinel, and MissionWeave")


def build_packet(
    config: dict[str, Any], *, as_of_utc: str | None = None, config_sha256: str | None = None
) -> dict[str, Any]:
    validate_config(config)
    as_of = parse_utc(as_of_utc or str(config.get("as_of_utc", "")), "as_of_utc")
    max_age_days = int(config["max_evidence_age_days"])

    programs: list[dict[str, Any]] = []
    all_requirements: list[dict[str, Any]] = []
    observed_fact_ids: set[str] = set()
    for program in config["programs"]:
        program_id = str(program.get("program_id", "")).strip()
        sources = []
        for index, source in enumerate(program.get("requirements_sources", [])):
            if not isinstance(source, dict):
                raise PacketConfigError(f"{program_id}.requirements_sources entries must be objects")
            reference = str(source.get("reference", "")).strip()
            if not reference:
                raise PacketConfigError(
                    f"{program_id}.requirements_sources[{index}].reference must not be empty"
                )
            sources.append(
                {
                    "path": validate_source_path(
                        str(source.get("path", "")),
                        f"{program_id}.requirements_sources[{index}].path",
                    ),
                    "reference": reference,
                }
            )
        if not sources:
            raise PacketConfigError(f"{program_id} must include at least one requirements source")
        requirements = [
            evaluate_requirement(item, as_of=as_of, max_age_days=max_age_days)
            for item in program.get("requirements", [])
        ]
        if not requirements:
            raise PacketConfigError(f"{program_id} must include at least one requirement")
        for requirement in requirements:
            if requirement["fact_id"] in observed_fact_ids:
                raise PacketConfigError(
                    f"duplicate fact_id across programs: {requirement['fact_id']}"
                )
            observed_fact_ids.add(requirement["fact_id"])
        programs.append(
            {
                "program_id": program_id,
                "requirements_sources": sources,
                "requirements": requirements,
            }
        )
        all_requirements.extend(requirements)

    ready_states = {
        "AUTHORITATIVE_PROOF_INVENTORIED",
        "NOT_APPLICABLE_REVIEW_INVENTORIED",
    }
    complete = all(item["evidence_state"] in ready_states for item in all_requirements)
    issue_count = sum(len(item["issues"]) for item in all_requirements)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "generated_utc": format_utc(as_of),
        "claim_boundary": CLAIM_BOUNDARY,
        "evaluation_limit": EVALUATION_LIMIT,
        "packet_state": (
            "AUTHORITATIVE_EVIDENCE_INVENTORIED" if complete and issue_count == 0
            else "EVIDENCE_INCOMPLETE"
        ),
        "subject_ref": config["subject_ref"],
        "source_classes": list(ALLOWED_SOURCE_CLASSES),
        "rules": deepcopy(config.get("rules", [])),
        "summary": {
            "program_count": len(programs),
            "requirement_count": len(all_requirements),
            "authoritative_requirement_count": sum(
                item["evidence_state"] == "AUTHORITATIVE_PROOF_INVENTORIED"
                for item in all_requirements
            ),
            "supported_not_applicable_count": sum(
                item["evidence_state"] == "NOT_APPLICABLE_REVIEW_INVENTORIED"
                for item in all_requirements
            ),
            "open_requirement_count": sum(
                item["evidence_state"] not in ready_states for item in all_requirements
            ),
            "issue_count": issue_count,
        },
        "programs": programs,
        "prohibited_conclusions": list(PROHIBITED_CONCLUSIONS),
        "integrity": {
            "hash_algorithm": "SHA-256",
            "config_sha256": config_sha256 or stable_hash(config),
            "generator_sha256": file_sha256(Path(__file__)),
            "packet_sha256": "",
        },
    }
    unhashed = deepcopy(packet)
    unhashed["integrity"]["packet_sha256"] = ""
    packet["integrity"]["packet_sha256"] = stable_hash(unhashed)
    return packet


def verify_packet_hash(packet: dict[str, Any]) -> bool:
    candidate = deepcopy(packet)
    expected = str(candidate.get("integrity", {}).get("packet_sha256", ""))
    if not SHA256_RE.fullmatch(expected):
        return False
    candidate["integrity"]["packet_sha256"] = ""
    return stable_hash(candidate) == expected


def render_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# CMMC and Export Evidence Packet",
        "",
        f"Packet state: `{packet['packet_state']}`",
        f"Generated UTC: `{packet['generated_utc']}`",
        f"Packet SHA-256: `{packet['integrity']['packet_sha256']}`",
        "",
        "## Claim Boundary",
        "",
        packet["claim_boundary"],
        "",
        "## Evaluation Limit",
        "",
        packet["evaluation_limit"],
        "",
        "## Inventory Summary",
        "",
        f"- Programs: `{summary['program_count']}`",
        f"- Requirements: `{summary['requirement_count']}`",
        f"- Authoritative proof inventoried: `{summary['authoritative_requirement_count']}`",
        f"- Supported not-applicable reviews: `{summary['supported_not_applicable_count']}`",
        f"- Open requirements: `{summary['open_requirement_count']}`",
        f"- Fail-closed issues: `{summary['issue_count']}`",
        "",
    ]
    for program in packet["programs"]:
        lines.extend(
            [
                f"## {program['program_id']}",
                "",
                "Requirements sources:",
            ]
        )
        for source in program["requirements_sources"]:
            lines.append(f"- `{source['path']}` - {source['reference']}")
        lines.extend(
            [
                "",
                "| Fact | Control | Applicability | Evidence state | Proofs | Issues |",
                "|---|---|---|---|---:|---:|",
            ]
        )
        for item in program["requirements"]:
            lines.append(
                "| `{fact}` | `{control}` | `{app}` | `{state}` | {proofs} | {issues} |".format(
                    fact=item["fact_id"],
                    control=item["control"],
                    app=item["applicability"]["state"],
                    state=item["evidence_state"],
                    proofs=item["authoritative_proof_count"],
                    issues=len(item["issues"]),
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Frozen Rules",
            "",
            *[f"- {rule}" for rule in packet["rules"]],
            "",
            "## Prohibited Conclusions",
            "",
            *[f"- `{item}`" for item in packet["prohibited_conclusions"]],
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
    temporary.replace(path)


def write_outputs(packet: dict[str, Any], out_json: Path, out_md: Path) -> None:
    if not verify_packet_hash(packet):
        raise RuntimeError("refusing to write a packet with an invalid integrity hash")
    json_bytes = json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n"
    markdown_bytes = render_markdown(packet).encode("utf-8")
    atomic_write(out_json, json_bytes)
    atomic_write(out_md, markdown_bytes)


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketConfigError(f"unable to read config: {path}") from exc
    if not isinstance(payload, dict):
        raise PacketConfigError("config root must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the bounded CMMC/export evidence inventory")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--as-of-utc", default=None)
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = load_config(config_path)
    packet = build_packet(
        config,
        as_of_utc=args.as_of_utc,
        config_sha256=file_sha256(config_path),
    )
    write_outputs(packet, args.out_json.resolve(), args.out_md.resolve())
    print(
        json.dumps(
            {
                "packet_state": packet["packet_state"],
                "open_requirement_count": packet["summary"]["open_requirement_count"],
                "packet_sha256": packet["integrity"]["packet_sha256"],
                "out_json": str(args.out_json.resolve()),
                "out_md": str(args.out_md.resolve()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
