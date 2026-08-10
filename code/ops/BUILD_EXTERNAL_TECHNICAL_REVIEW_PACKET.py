from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "external_technical_review_packet_v1.json"
TEMPLATE_CONFIG = ROOT / "config" / "outreach_response_templates_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "external_technical_review_packet.json"
MD_OUT = ROOT / "docs" / "EXTERNAL_TECHNICAL_REVIEW_PACKET_2026-07-28.md"

CONFIG_SCHEMA = "lumencore.external_technical_review_packet_config.v1"
OUTPUT_SCHEMA = "lumencore.external_technical_review_packet.v1"
MAX_PUBLIC_SURFACE_BYTES = 1_048_576
RETIRED_PUBLIC_SURFACE_PATHS = frozenset(
    {
        "/anomalies.html",
        "/explain.html",
        "/forecast.html",
        "/grants.html",
        "/kraken_execution_dashboard.html",
        "/lab.html",
        "/mission_control.html",
        "/quant_lab.html",
    }
)


class ReviewPacketError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReviewPacketError(f"EXPECTED_OBJECT:{path}")
    return payload


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_file_bytes(path: Path) -> bytes:
    content = path.read_bytes()
    if b"\x00" in content:
        return content
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(canonical_file_bytes(path)).hexdigest()


def safe_repo_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReviewPacketError(f"UNSAFE_EVIDENCE_PATH:{value}")
    resolved = (ROOT / relative).resolve()
    if ROOT.resolve() not in resolved.parents:
        raise ReviewPacketError(f"EVIDENCE_PATH_OUTSIDE_REPO:{value}")
    return resolved


def validate_https_url(value: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ReviewPacketError(f"UNSAFE_PUBLIC_URL:{value}")


def _nonempty_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ReviewPacketError(f"MISSING_NONEMPTY_LIST:{key}")
    return value


def validate_assurance_exercise(config: dict[str, Any]) -> dict[str, Any]:
    exercise = config.get("assurance_exercise")
    if not isinstance(exercise, dict):
        raise ReviewPacketError("ASSURANCE_EXERCISE_MISSING")
    if exercise.get("schema") != "lumencore.external_review_assurance_exercise.v1":
        raise ReviewPacketError("ASSURANCE_EXERCISE_SCHEMA_INVALID")
    if exercise.get("mode") != "REVIEWER_CONTROLLED_LOCAL_REPLAY_ONLY":
        raise ReviewPacketError("ASSURANCE_EXERCISE_MODE_INVALID")

    authority = exercise.get("authority_boundary")
    expected_authority = {
        "active_targeting_allowed": False,
        "private_system_access_allowed": False,
        "production_load_testing_allowed": False,
        "external_action_allowed": False,
    }
    if authority != expected_authority:
        raise ReviewPacketError("ASSURANCE_AUTHORITY_BOUNDARY_INVALID")

    roles = exercise.get("roles")
    if not isinstance(roles, dict) or set(roles) != {
        "red_team",
        "blue_team",
        "purple_team",
    }:
        raise ReviewPacketError("ASSURANCE_ROLES_INVALID")
    if any(not str(value).strip() for value in roles.values()):
        raise ReviewPacketError("ASSURANCE_ROLE_DESCRIPTION_MISSING")

    scenarios = _nonempty_list(exercise, "scenarios")
    if len(scenarios) < 6:
        raise ReviewPacketError("ASSURANCE_SCENARIO_SET_INCOMPLETE")
    scenario_ids: set[str] = set()
    required_fields = {
        "scenario_id",
        "target",
        "test_path",
        "red_team_action",
        "expected_blue_control",
        "pass_condition",
        "boundary",
    }
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != required_fields:
            raise ReviewPacketError("ASSURANCE_SCENARIO_INVALID")
        scenario_id = str(scenario["scenario_id"])
        if not scenario_id.startswith("RB-") or scenario_id in scenario_ids:
            raise ReviewPacketError("ASSURANCE_SCENARIO_ID_INVALID")
        scenario_ids.add(scenario_id)
        if any(not str(scenario[field]).strip() for field in required_fields):
            raise ReviewPacketError(f"ASSURANCE_SCENARIO_FIELD_MISSING:{scenario_id}")
        test_path = str(scenario["test_path"])
        if not test_path.startswith("tests/") or not test_path.endswith(".py"):
            raise ReviewPacketError(f"ASSURANCE_TEST_PATH_INVALID:{scenario_id}")
        if not safe_repo_path(test_path).is_file():
            raise ReviewPacketError(f"ASSURANCE_TEST_MISSING:{scenario_id}")

    receipt_fields = _nonempty_list(exercise, "receipt_fields")
    required_receipt_fields = {
        "evaluator_identity_or_pseudonymous_identifier",
        "independence_disclosure",
        "source_commit",
        "environment_fingerprint",
        "scenario_ids",
        "commands_executed",
        "started_utc",
        "completed_utc",
        "observed_results",
        "deviations",
        "negative_results",
        "remediation",
        "retest_results",
        "reviewer_recommendation",
    }
    if set(receipt_fields) != required_receipt_fields:
        raise ReviewPacketError("ASSURANCE_RECEIPT_FIELDS_INVALID")
    if not str(exercise.get("objective") or "").strip():
        raise ReviewPacketError("ASSURANCE_OBJECTIVE_MISSING")
    if not str(exercise.get("claim_boundary") or "").strip():
        raise ReviewPacketError("ASSURANCE_CLAIM_BOUNDARY_MISSING")
    return exercise


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema") != CONFIG_SCHEMA:
        raise ReviewPacketError("CONFIG_SCHEMA_INVALID")
    if config.get("status") != "MEETING_PREP_READY_NO_DUPLICATE_SEND":
        raise ReviewPacketError("CONFIG_STATUS_INVALID")
    if not str(config.get("generated_at_utc") or "").endswith("Z"):
        raise ReviewPacketError("GENERATED_AT_MUST_BE_UTC")
    if not str(config.get("claim_boundary") or "").strip():
        raise ReviewPacketError("CLAIM_BOUNDARY_MISSING")

    controls = config.get("controls")
    expected_controls = {
        "builder_can_send_email": False,
        "builder_can_create_calendar_event": False,
        "builder_can_accept_terms": False,
        "duplicate_invite_prohibited": True,
        "meeting_credentials_omitted": True,
        "recipient_identity_omitted": True,
        "private_identifiers_omitted": True,
    }
    if controls != expected_controls:
        raise ReviewPacketError("CONTROL_SET_INVALID")

    meeting = config.get("meeting")
    if not isinstance(meeting, dict):
        raise ReviewPacketError("MEETING_MISSING")
    if meeting.get("invite_state") != "ACCEPTED":
        raise ReviewPacketError("MEETING_NOT_ACCEPTED")
    if meeting.get("selected_template_id") != "NO_DUPLICATE_MEETING_PREP":
        raise ReviewPacketError("MEETING_TEMPLATE_INVALID")
    if meeting.get("duration_minutes") != 30:
        raise ReviewPacketError("MEETING_DURATION_INVALID")

    validate_assurance_exercise(config)

    templates = read_json(TEMPLATE_CONFIG).get("templates")
    selected = next(
        (
            row
            for row in templates
            if row.get("template_id") == meeting["selected_template_id"]
        ),
        None,
    )
    if (
        selected is None
        or selected.get("send_policy") != "MONITOR_NO_SEND"
        or selected.get("subject") != ""
        or selected.get("body") != ""
    ):
        raise ReviewPacketError("MEETING_TEMPLATE_NOT_FAIL_CLOSED")

    for surface in _nonempty_list(config, "public_surfaces"):
        if not isinstance(surface, dict):
            raise ReviewPacketError("PUBLIC_SURFACE_INVALID")
        url = str(surface.get("url") or "")
        validate_https_url(url)
        if urlsplit(url).path in RETIRED_PUBLIC_SURFACE_PATHS:
            raise ReviewPacketError(f"RETIRED_PUBLIC_SURFACE:{url}")
        if not isinstance(surface.get("observed_http_status"), int):
            raise ReviewPacketError("PUBLIC_SURFACE_STATUS_INVALID")
        if not str(surface.get("verified_at_utc") or "").endswith("Z"):
            raise ReviewPacketError("PUBLIC_SURFACE_TIME_INVALID")
        expected_content_type = str(
            surface.get("expected_content_type") or ""
        ).strip()
        if not expected_content_type:
            raise ReviewPacketError("PUBLIC_SURFACE_CONTENT_TYPE_MISSING")
        required_text = surface.get("required_text")
        required_json = surface.get("required_json")
        has_text_contract = isinstance(required_text, str) and bool(
            required_text.strip()
        )
        has_json_contract = isinstance(required_json, dict) and bool(required_json)
        if has_text_contract == has_json_contract:
            raise ReviewPacketError("PUBLIC_SURFACE_CONTRACT_INVALID")
        if has_json_contract and not all(
            isinstance(key, str) and key.strip() for key in required_json
        ):
            raise ReviewPacketError("PUBLIC_SURFACE_JSON_CONTRACT_INVALID")
        if not str(surface.get("limitation") or "").strip():
            raise ReviewPacketError("PUBLIC_SURFACE_LIMITATION_MISSING")

    for reference in _nonempty_list(config, "draft_references"):
        validate_https_url(str(reference.get("url") or ""))
        if reference.get("state") not in {
            "CLOSED_UNMERGED",
            "DRAFT_PR_NOT_MERGED",
        }:
            raise ReviewPacketError("REFERENCE_STATE_INVALID")

    for key in (
        "evidence_assets",
        "agenda",
        "reviewer_questions",
        "bounded_next_steps",
        "known_gaps",
        "claims_not_to_make",
        "note_capture_fields",
    ):
        _nonempty_list(config, key)
    return config


def evidence_record(item: dict[str, Any]) -> dict[str, Any]:
    relative = str(item.get("path") or "")
    path = safe_repo_path(relative)
    if not path.is_file():
        raise ReviewPacketError(f"EVIDENCE_MISSING:{relative}")
    canonical_bytes = canonical_file_bytes(path)
    record: dict[str, Any] = {
        "path": relative,
        "purpose": str(item.get("purpose") or ""),
        "bytes": len(canonical_bytes),
        "sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        "required_status": item.get("required_status"),
        "observed_status": None,
        "claim_boundary": None,
    }
    if item.get("required_status"):
        payload = read_json(path)
        record["observed_status"] = payload.get("status")
        record["claim_boundary"] = payload.get("claim_boundary")
        if record["observed_status"] != item["required_status"]:
            raise ReviewPacketError(f"EVIDENCE_STATUS_MISMATCH:{relative}")
        if not str(record["claim_boundary"] or "").strip():
            raise ReviewPacketError(f"EVIDENCE_BOUNDARY_MISSING:{relative}")
    return record


def assurance_exercise_record(config: dict[str, Any]) -> dict[str, Any]:
    exercise = validate_assurance_exercise(config)
    scenarios = []
    for item in exercise["scenarios"]:
        test_path = str(item["test_path"])
        path = safe_repo_path(test_path)
        scenarios.append(
            {
                **item,
                "test_bytes": len(canonical_file_bytes(path)),
                "test_sha256": sha256_file(path),
                "verification_command": f"python -m pytest -q {test_path}",
            }
        )
    return {**exercise, "scenarios": scenarios}


def build_payload(config: dict[str, Any]) -> dict[str, Any]:
    config = validate_config(config)
    evidence = [evidence_record(item) for item in config["evidence_assets"]]
    assurance_exercise = assurance_exercise_record(config)
    return {
        "schema": OUTPUT_SCHEMA,
        "generated_at_utc": config["generated_at_utc"],
        "status": config["status"],
        "source_config": CONFIG.relative_to(ROOT).as_posix(),
        "source_config_sha256": canonical_sha256(config),
        "template_config_sha256": canonical_sha256(read_json(TEMPLATE_CONFIG)),
        "claim_boundary": config["claim_boundary"],
        "controls": config["controls"],
        "meeting": config["meeting"],
        "summary": {
            "evidence_asset_count": len(evidence),
            "public_surface_count": len(config["public_surfaces"]),
            "demo_surface_count": sum(
                1 for row in config["public_surfaces"] if row["demo"]
            ),
            "degraded_surface_count": sum(
                1
                for row in config["public_surfaces"]
                if row["observed_http_status"] >= 400
            ),
            "reviewer_question_count": len(config["reviewer_questions"]),
            "assurance_scenario_count": len(assurance_exercise["scenarios"]),
            "active_targeting_allowed": assurance_exercise["authority_boundary"][
                "active_targeting_allowed"
            ],
            "known_gap_count": len(config["known_gaps"]),
            "duplicate_invite_blocked": True,
        },
        "evidence_assets": evidence,
        "public_surfaces": config["public_surfaces"],
        "public_surface_snapshot_sha256": canonical_sha256(config["public_surfaces"]),
        "draft_references": config["draft_references"],
        "agenda": config["agenda"],
        "reviewer_questions": config["reviewer_questions"],
        "assurance_exercise": assurance_exercise,
        "bounded_next_steps": config["bounded_next_steps"],
        "known_gaps": config["known_gaps"],
        "claims_not_to_make": config["claims_not_to_make"],
        "note_capture_fields": config["note_capture_fields"],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    meeting = payload["meeting"]
    lines = [
        "# External Technical Review Packet",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Decision",
        "",
        meeting["objective"],
        "",
        f"Opening: {meeting['opening_statement']}",
        "",
        f"Requested outcome: {meeting['requested_outcome']}",
        "",
        "One calendar invitation already exists and is accepted. Do not send another reply or invitation unless the schedule changes or the reviewer asks a new question.",
        "",
        "## Evidence Walkthrough",
        "",
        "| Artifact | Purpose | Observed status | SHA-256 |",
        "|---|---|---|---|",
    ]
    for row in payload["evidence_assets"]:
        status = row["observed_status"] or "FILE_PRESENT"
        lines.append(
            f"| `{row['path']}` | {row['purpose']} | `{status}` | `{row['sha256']}` |"
        )

    lines.extend(
        [
            "",
            "The receipt statuses above are bounded first-party or operator-controlled evidence. Their own claim boundaries remain controlling.",
            "",
            "## Public Surface Snapshot",
            "",
            "| Surface | HTTP | Demo | Limitation |",
            "|---|---:|---|---|",
        ]
    )
    for row in payload["public_surfaces"]:
        demo = "yes" if row["demo"] else "no"
        lines.append(
            f"| [{row['label']}]({row['url']}) | `{row['observed_http_status']}` | `{demo}` | {row['limitation']} |"
        )

    lines.extend(["", "## Agenda", ""])
    for row in payload["agenda"]:
        lines.append(
            f"- **{row['minutes']} - {row['purpose']}:** {row['content']}"
        )

    lines.extend(["", "## Reviewer Questions", ""])
    lines.extend(
        f"{index}. {question}"
        for index, question in enumerate(payload["reviewer_questions"], start=1)
    )

    exercise = payload["assurance_exercise"]
    lines.extend(
        [
            "",
            "## Reviewer-Controlled Red / Blue Assurance Exercise",
            "",
            f"Mode: `{exercise['mode']}`",
            "",
            exercise["objective"],
            "",
            f"- **Red team:** {exercise['roles']['red_team']}",
            f"- **Blue team:** {exercise['roles']['blue_team']}",
            f"- **Purple team:** {exercise['roles']['purple_team']}",
            "",
            "Active targeting, private-system access, production load testing, and external actions are prohibited.",
            "",
            "| Scenario | Target | Red-team action | Expected blue control | Replay command |",
            "|---|---|---|---|---|",
        ]
    )
    for row in exercise["scenarios"]:
        lines.append(
            f"| `{row['scenario_id']}` | {row['target']} | {row['red_team_action']} | "
            f"{row['expected_blue_control']} | `{row['verification_command']}` |"
        )
        lines.append(
            f"|  | **Pass condition** | {row['pass_condition']} | **Boundary** | {row['boundary']} |"
        )

    lines.extend(
        [
            "",
            "### Assurance Receipt Fields",
            "",
            ", ".join(f"`{field}`" for field in exercise["receipt_fields"]),
            "",
            f"**Exercise boundary:** {exercise['claim_boundary']}",
        ]
    )

    lines.extend(["", "## Bounded Next Steps", ""])
    lines.extend(f"- {item}" for item in payload["bounded_next_steps"])

    lines.extend(["", "## Known Gaps", ""])
    lines.extend(f"- {item}" for item in payload["known_gaps"])

    lines.extend(["", "## Claims Not To Make", ""])
    lines.extend(f"- `{item}`" for item in payload["claims_not_to_make"])

    lines.extend(
        [
            "",
            "## Notes To Capture",
            "",
            "| Field | Meeting note |",
            "|---|---|",
        ]
    )
    lines.extend(f"| `{field}` | |" for field in payload["note_capture_fields"])

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def observe_public_surface(surface: dict[str, Any]) -> dict[str, Any]:
    url = surface["url"]
    request = Request(
        url,
        method="GET",
        headers={"User-Agent": "LumenCoreReview/1.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type") or "")
            body = response.read(MAX_PUBLIC_SURFACE_BYTES + 1)
    except HTTPError as exc:
        status = int(exc.code)
        content_type = str((exc.headers or {}).get("Content-Type") or "")
        body = exc.read(MAX_PUBLIC_SURFACE_BYTES + 1)
    except URLError as exc:
        raise ReviewPacketError(f"LIVE_SURFACE_UNREACHABLE:{url}:{exc.reason}") from exc

    if len(body) > MAX_PUBLIC_SURFACE_BYTES:
        raise ReviewPacketError(f"LIVE_SURFACE_BODY_TOO_LARGE:{url}")

    observed_content_type = content_type.split(";", 1)[0].strip().lower()
    expected_content_type = surface["expected_content_type"].strip().lower()
    content_type_match = observed_content_type == expected_content_type
    contract_match = content_type_match
    if "required_text" in surface:
        try:
            decoded = body.decode("utf-8")
        except UnicodeDecodeError:
            contract_match = False
        else:
            contract_match = contract_match and surface["required_text"] in decoded
    else:
        try:
            decoded_json = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            contract_match = False
        else:
            contract_match = (
                contract_match
                and isinstance(decoded_json, dict)
                and all(
                    decoded_json.get(key) == value
                    for key, value in surface["required_json"].items()
                )
            )

    return {
        "observed_status": status,
        "observed_content_type": observed_content_type,
        "content_type_match": content_type_match,
        "contract_match": contract_match,
    }


def verify_live_surfaces(config: dict[str, Any]) -> list[dict[str, Any]]:
    observed = []
    for row in config["public_surfaces"]:
        result = observe_public_surface(row)
        observed.append(
            {
                "url": row["url"],
                "expected_status": row["observed_http_status"],
                "observed_status": result["observed_status"],
                "expected_content_type": row["expected_content_type"],
                "observed_content_type": result["observed_content_type"],
                "content_type_match": result["content_type_match"],
                "contract_match": result["contract_match"],
                "match": (
                    result["observed_status"] == row["observed_http_status"]
                    and result["contract_match"]
                ),
            }
        )
    mismatches = [row for row in observed if not row["match"]]
    if mismatches:
        raise ReviewPacketError(
            "LIVE_SURFACE_CONTRACT_DRIFT:"
            + ",".join(
                f"{row['url']}={row['observed_status']}"
                f"/{row['observed_content_type']}"
                f"/contract={str(row['contract_match']).lower()}"
                for row in mismatches
            )
        )
    return observed


def write_outputs(payload: dict[str, Any]) -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the no-duplicate external technical review packet."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-live", action="store_true")
    args = parser.parse_args()

    config = validate_config(read_json(CONFIG))
    live = verify_live_surfaces(config) if args.verify_live else []
    payload = build_payload(config)
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_md = render_markdown(payload)

    if args.check:
        stale = []
        if not JSON_OUT.is_file() or JSON_OUT.read_text(encoding="utf-8") != rendered_json:
            stale.append(JSON_OUT.relative_to(ROOT).as_posix())
        if not MD_OUT.is_file() or MD_OUT.read_text(encoding="utf-8") != rendered_md:
            stale.append(MD_OUT.relative_to(ROOT).as_posix())
        if stale:
            raise ReviewPacketError("STALE_OUTPUTS:" + ",".join(stale))
    else:
        write_outputs(payload)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "evidence_asset_count": payload["summary"]["evidence_asset_count"],
                "public_surface_count": payload["summary"]["public_surface_count"],
                "degraded_surface_count": payload["summary"][
                    "degraded_surface_count"
                ],
                "duplicate_invite_blocked": payload["summary"][
                    "duplicate_invite_blocked"
                ],
                "live_verified": bool(live),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
