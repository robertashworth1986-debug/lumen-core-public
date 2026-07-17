from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
PRIVATE_DIR = ROOT / "out" / "private"

ENV_PATHS = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]
BASELINE_PATH = PRIVATE_DIR / "sam_api_key_rotation_baseline.json"
OUT_JSON = SPRINT_DIR / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json"
OUT_MD = SPRINT_DIR / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.md"
INSTALLER_PATH = ROOT / "code" / "ops" / "INSTALL_SAM_PUBLIC_CREDENTIAL.py"
INSTALLER_TARGET = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"

KEY_NAMES = ("SAM_API_KEY", "SAM_GOV_API_KEY", "DATA_GOV_API_KEY_PRIMARY")
ROTATION_DEADLINE_LOCAL = date(2026, 7, 16)
LOCAL_TIMEZONE = ZoneInfo("America/Chicago")
OPPORTUNITIES_API = "https://api.sam.gov/opportunities/v2/search"
OPPORTUNITY_PROBE_SCOPE = "RECENT_30_DAY_FIRST_RECORD"
OFFICIAL_ACCOUNT_URL = "https://sam.gov/profile/details"
OFFICIAL_API_DOCUMENTATION = "https://open.gsa.gov/api/get-opportunities-public-api/"

EMAIL_EVIDENCE = {
    "sender": "donotreply@sam.gov",
    "subject": "<sam.gov> | [Final Reminder]: Rotate your Individual Account API Key today",
    "received_utc": "2026-07-16T08:07:36Z",
    "instruction": (
        "Retrieve the already-generated replacement under Public API Key in the SAM.gov "
        "account profile and update connected API clients before the current key becomes out of date."
    ),
}

CLAIM_BOUNDARY = (
    "This control proves only bounded local secret-discovery state, fingerprint comparison, and the "
    "recorded API probe result. It never stores or publishes an API key. A changed fingerprint proves "
    "that the configured secret changed, not that SAM.gov accepted it. Only a successful authenticated "
    "probe can establish live API acceptance, and no browser, account, submission, or opportunity state "
    "is changed by this control."
)

PROHIBITED_PUBLIC_PATTERNS = (
    r"(?i)SAM_API_KEY\s*=",
    r"(?i)SAM_GOV_API_KEY\s*=",
    r"(?i)DATA_GOV_API_KEY_PRIMARY\s*=",
    r"(?i)[?&]api_key=",
    r"(?i)fingerprint_sha256",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def secret_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def parse_env_file(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    records: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        name = name.strip()
        if name not in KEY_NAMES:
            continue
        value = raw_value.strip().strip('"').strip("'")
        if not value:
            continue
        records.append(
            {
                "name": name,
                "value": value,
                "source_kind": "env_file",
                "source": rel(path),
            }
        )
    return records


def discover_key_records(
    *,
    environ: dict[str, str] | os._Environ[str] | None = None,
    env_paths: list[Path] | None = None,
) -> list[dict[str, str]]:
    env = os.environ if environ is None else environ
    records: list[dict[str, str]] = []
    for name in KEY_NAMES:
        value = str(env.get(name) or "").strip()
        if value:
            records.append(
                {
                    "name": name,
                    "value": value,
                    "source_kind": "process_environment",
                    "source": f"process:{name}",
                }
            )
    for path in env_paths or ENV_PATHS:
        records.extend(parse_env_file(path))
    return records


def select_key_record(records: list[dict[str, str]]) -> dict[str, str] | None:
    source_rank = {"process_environment": 0, "env_file": 1}
    name_rank = {name: idx for idx, name in enumerate(KEY_NAMES)}
    candidates = [row for row in records if row.get("value")]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda row: (
            name_rank.get(row.get("name", ""), len(name_rank)),
            source_rank.get(row.get("source_kind", ""), 99),
            row.get("source", ""),
        ),
    )


def public_source_summary(records: list[dict[str, str]]) -> dict[str, Any]:
    fingerprints = {secret_fingerprint(row["value"]) for row in records if row.get("value")}
    entries = [
        {
            "name": row["name"],
            "source_kind": row["source_kind"],
            "source": row["source"],
        }
        for row in records
    ]
    return {
        "configured_entry_count": len(entries),
        "distinct_secret_value_count": len(fingerprints),
        "aliases_consistent": len(fingerprints) <= 1 if entries else False,
        "entries": entries,
        "secret_values_exposed": False,
        "secret_hashes_exposed": False,
    }


def classify_probe(status: int | None, body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace") if body else ""
    key_rejection_detected = bool(
        re.search(r"(?i)(invalid|missing|no)\s+(?:api[_ -]?key|key)", text)
    )
    shape_valid = False
    if status == 200 and text:
        try:
            payload = json.loads(text)
            shape_valid = (
                isinstance(payload, dict)
                and isinstance(payload.get("opportunitiesData"), list)
                and isinstance(payload.get("totalRecords"), int)
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            shape_valid = False

    if status == 200 and shape_valid:
        classification = "LIVE_AUTHENTICATED_RESPONSE"
        live = True
    elif status in {401, 403} or key_rejection_detected:
        classification = "KEY_REJECTED_OR_MISSING"
        live = False
    elif status == 404 and not body:
        classification = "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"
        live = False
    elif status is None:
        classification = "NETWORK_OR_UPSTREAM_FAILURE_INCONCLUSIVE"
        live = False
    else:
        classification = f"HTTP_{status}_INCONCLUSIVE"
        live = False

    return {
        "classification": classification,
        "http_status": status,
        "response_shape_valid": shape_valid,
        "live_authenticated_response": live,
        "response_body_published": False,
    }


def probe_sam_api_key(
    api_key: str,
    *,
    as_of_date: date | None = None,
    timeout_seconds: float = 20.0,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    posted_to = as_of_date or datetime.now(LOCAL_TIMEZONE).date()
    posted_from = posted_to - timedelta(days=30)
    query = urllib.parse.urlencode(
        {
            "api_key": api_key,
            "limit": 1,
            "offset": 0,
            "postedFrom": posted_from.strftime("%m/%d/%Y"),
            "postedTo": posted_to.strftime("%m/%d/%Y"),
        }
    )
    request = urllib.request.Request(
        f"{OPPORTUNITIES_API}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "LumenCore-SAM-Rotation-Verifier/1.0",
        },
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", response.getcode()))
            body = response.read(2_000_000)
    except urllib.error.HTTPError as error:
        status = int(error.code)
        body = error.read(2_000_000)
    except Exception:  # noqa: BLE001 - public result intentionally suppresses secret-bearing errors
        status = None
        body = b""

    result = classify_probe(status, body)
    result.update(
        {
            "endpoint": "SAM_GET_OPPORTUNITIES_PUBLIC_API",
            "probe_scope": OPPORTUNITY_PROBE_SCOPE,
            "probe_listing_id": None,
            "posted_from": posted_from.isoformat(),
            "posted_to": posted_to.isoformat(),
            "official_documentation": OFFICIAL_API_DOCUMENTATION,
            "request_url_published": False,
            "secret_value_published": False,
        }
    )
    return result


def read_private_baseline(path: Path = BASELINE_PATH) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "lumencore.sam_api_key_rotation_private_baseline.v1":
        raise ValueError("Unexpected SAM key rotation baseline schema")
    fingerprint = payload.get("fingerprint_sha256")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9A-F]{64}", fingerprint):
        raise ValueError("Invalid SAM key rotation private fingerprint")
    return payload


def capture_private_baseline(
    selected: dict[str, str],
    *,
    path: Path = BASELINE_PATH,
    captured_utc: str | None = None,
) -> dict[str, Any]:
    if path.exists():
        return read_private_baseline(path) or {}
    payload = {
        "schema": "lumencore.sam_api_key_rotation_private_baseline.v1",
        "captured_utc": captured_utc or now_utc(),
        "fingerprint_sha256": secret_fingerprint(selected["value"]),
        "selected_name": selected["name"],
        "selected_source": selected["source"],
        "claim_boundary": (
            "Private fingerprint only. This file is excluded from Git and must never be published. "
            "It proves comparison identity, not API validity or SAM.gov acceptance."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def operational_date(generated_utc: str) -> date:
    parsed = datetime.fromisoformat(generated_utc.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TIMEZONE).date()


def build_payload(
    *,
    records: list[dict[str, str]],
    baseline: dict[str, Any] | None,
    probe: dict[str, Any],
    generated_utc: str | None = None,
) -> dict[str, Any]:
    generated = generated_utc or now_utc()
    selected = select_key_record(records)
    selected_fingerprint = secret_fingerprint(selected["value"]) if selected else None
    baseline_fingerprint = baseline.get("fingerprint_sha256") if baseline else None
    fingerprint_changed = bool(
        selected_fingerprint
        and baseline_fingerprint
        and selected_fingerprint != baseline_fingerprint
    )
    live = bool(probe.get("live_authenticated_response"))
    today = operational_date(generated)

    if today > ROTATION_DEADLINE_LOCAL:
        deadline_state = "PAST_DUE"
    elif today == ROTATION_DEADLINE_LOCAL:
        deadline_state = "DUE_TODAY"
    else:
        deadline_state = "UPCOMING"

    if not selected:
        status = "SAM_API_KEY_MISSING"
    elif not baseline:
        status = "PRIVATE_BASELINE_REQUIRED_BEFORE_REPLACEMENT_INSTALL"
    elif fingerprint_changed and live:
        status = "ROTATION_VERIFIED_NEW_KEY_LIVE"
    elif fingerprint_changed:
        status = "ROTATION_CHANGE_DETECTED_API_PROBE_INCONCLUSIVE"
    elif today > ROTATION_DEADLINE_LOCAL:
        status = "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED"
    else:
        status = "ROTATION_DUE_REPLACEMENT_NOT_DETECTED"

    selected_public = None
    if selected:
        selected_public = {
            "name": selected["name"],
            "source_kind": selected["source_kind"],
            "source": selected["source"],
        }

    payload: dict[str, Any] = {
        "schema": "lumencore.sam_public_credential_rotation_control.v1",
        "generated_utc": generated,
        "operational_timezone": "America/Chicago",
        "operational_date": today.isoformat(),
        "status": status,
        "deadline": {
            "date_local": ROTATION_DEADLINE_LOCAL.isoformat(),
            "state": deadline_state,
            "source": EMAIL_EVIDENCE,
        },
        "local_configuration": {
            **public_source_summary(records),
            "selected": selected_public,
            "private_baseline_present": baseline is not None,
            "configured_fingerprint_changed_from_private_baseline": fingerprint_changed,
            "replacement_installation_detected": fingerprint_changed,
        },
        "api_probe": probe,
        "rotation_verified": bool(fingerprint_changed and live),
        "human_action_gate": {
            "browser_navigation_performed_by_control": False,
            "external_account_change_performed_by_control": False,
            "steps": [
                "Keep the existing signed-in in-app browser tab on SAM.gov.",
                "Open Account Details and locate Public API Key.",
                "Use the SAM.gov one-time-password flow to reveal the already-generated replacement.",
                "Run `python code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py` in a private terminal and paste the replacement only at its hidden prompt.",
                "Rerun this verifier and require a changed private fingerprint; require a live authenticated response when the upstream API is observable.",
            ],
            "official_account_url": OFFICIAL_ACCOUNT_URL,
            "final_confirmation_required": True,
        },
        "private_installer": {
            "path": rel(INSTALLER_PATH),
            "target": rel(INSTALLER_TARGET),
            "hidden_prompt_input": True,
            "command_line_secret_argument_supported": False,
            "target_must_be_git_ignored": True,
            "atomic_replace_required": True,
            "plaintext_backup_created": False,
            "browser_navigation_performed": False,
        },
        "decision": (
            "No configured SAM public API credential was found; install the replacement only in the ignored private secret store."
            if not selected
            else (
                "Capture a private write-once fingerprint baseline before installing the replacement."
                if not baseline
                else (
                    "Do not claim the SAM key is rotated yet. The current local aliases are consistent, but "
                    "the private fingerprint has not changed and the API probe is inconclusive."
                    if not fingerprint_changed
                    else "A replacement secret is detected locally; API acceptance remains bounded by the probe result."
                )
            )
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["control_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    local = payload["local_configuration"]
    probe = payload["api_probe"]
    lines = [
        "# SAM.gov API-Key Rotation Control - 2026-07-16",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Direct Answer",
        "",
        payload["decision"],
        "",
        "## Evidence",
        "",
        f"- Official reminder sender: `{payload['deadline']['source']['sender']}`",
        f"- Official reminder received UTC: `{payload['deadline']['source']['received_utc']}`",
        f"- Rotation deadline, America/Chicago: `{payload['deadline']['date_local']}`",
        f"- Local configured aliases: `{local['configured_entry_count']}`",
        f"- Distinct configured secret values: `{local['distinct_secret_value_count']}`",
        f"- Aliases consistent: `{str(local['aliases_consistent']).lower()}`",
        f"- Private baseline present: `{str(local['private_baseline_present']).lower()}`",
        f"- Replacement installation detected: `{str(local['replacement_installation_detected']).lower()}`",
        f"- API probe: `{probe['classification']}`",
        f"- API HTTP status: `{probe['http_status']}`",
        f"- Rotation verified: `{str(payload['rotation_verified']).lower()}`",
        f"- Control SHA-256: `{payload['control_sha256']}`",
        "",
        "No secret value, request URL, response body, or secret fingerprint is published.",
        f"The guarded local installer is `{payload['private_installer']['path']}`; it accepts the replacement only through a hidden prompt.",
        "",
        "## Human Action Gate",
        "",
    ]
    for index, step in enumerate(payload["human_action_gate"]["steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Official References",
            "",
            f"- SAM.gov Account Details: {payload['human_action_gate']['official_account_url']}",
            f"- GSA API documentation: {probe['official_documentation']}",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def ensure_public_safe(text: str, secrets: list[str]) -> None:
    for pattern in PROHIBITED_PUBLIC_PATTERNS:
        if re.search(pattern, text):
            raise ValueError(f"Public SAM rotation control matched prohibited pattern: {pattern}")
    for secret in secrets:
        if secret and secret in text:
            raise ValueError("Public SAM rotation control contains a configured secret")
        fingerprint = secret_fingerprint(secret) if secret else ""
        if fingerprint and fingerprint in text:
            raise ValueError("Public SAM rotation control contains a secret fingerprint")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a secret-safe SAM.gov API-key rotation control")
    parser.add_argument(
        "--capture-baseline",
        action="store_true",
        help="Capture the current private fingerprint only when no baseline exists",
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Skip the live API probe and record an explicit inconclusive result",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = discover_key_records()
    selected = select_key_record(records)
    if args.capture_baseline and selected:
        capture_private_baseline(selected)
    baseline = read_private_baseline()

    if selected and not args.no_probe:
        probe = probe_sam_api_key(selected["value"])
    else:
        probe = {
            "classification": "PROBE_SKIPPED_INCONCLUSIVE",
            "http_status": None,
            "response_shape_valid": False,
            "live_authenticated_response": False,
            "response_body_published": False,
            "endpoint": "SAM_GET_OPPORTUNITIES_PUBLIC_API",
            "probe_scope": OPPORTUNITY_PROBE_SCOPE,
            "probe_listing_id": None,
            "posted_from": None,
            "posted_to": None,
            "official_documentation": OFFICIAL_API_DOCUMENTATION,
            "request_url_published": False,
            "secret_value_published": False,
        }

    payload = build_payload(records=records, baseline=baseline, probe=probe)
    markdown = render_markdown(payload)
    secrets = [row["value"] for row in records]
    ensure_public_safe(json.dumps(payload, sort_keys=True), secrets)
    ensure_public_safe(markdown, secrets)
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "configured_aliases": payload["local_configuration"]["configured_entry_count"],
                "aliases_consistent": payload["local_configuration"]["aliases_consistent"],
                "replacement_detected": payload["local_configuration"]["replacement_installation_detected"],
                "api_probe": payload["api_probe"]["classification"],
                "rotation_verified": payload["rotation_verified"],
                "secret_values_printed": False,
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
