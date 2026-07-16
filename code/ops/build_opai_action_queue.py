from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROGRAM = ROOT / "config" / "opai_entry_program.json"
DEFAULT_INTELLIGENCE = ROOT / "dashboard" / "data" / "opai_consortium_intelligence.json"
DEFAULT_INTELLIGENCE_SEED = (
    ROOT / "dashboard" / "data" / "opai_consortium_intelligence_seed.json"
)
DEFAULT_OUT = ROOT / "out" / "opai" / "opai_action_queue_latest.json"
DEFAULT_DASHBOARD_OUT = ROOT / "dashboard" / "data" / "opai_action_queue.json"


class ConfigurationError(ValueError):
    """Raised when the public-safe program configuration is incomplete."""


def parse_utc(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ConfigurationError("expected a UTC timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ConfigurationError(f"invalid ISO date: {value!r}") from exc


def canonical_json_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError(f"expected a JSON object in {path}")
    return payload


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def resolve_intelligence(path: Path) -> tuple[dict[str, Any], str]:
    if path.exists():
        return read_json(path), str(path)
    if DEFAULT_INTELLIGENCE_SEED.exists():
        return read_json(DEFAULT_INTELLIGENCE_SEED), str(DEFAULT_INTELLIGENCE_SEED)
    return {}, "unavailable"


def validate_program(program: Mapping[str, Any]) -> None:
    if program.get("schema") != "opai_entry_program_v1":
        raise ConfigurationError("unsupported or missing program schema")
    membership = program.get("membership")
    challenge = program.get("ai_for_power_2026")
    opportunities = program.get("opportunities")
    if not isinstance(membership, dict):
        raise ConfigurationError("membership must be an object")
    if not isinstance(challenge, dict):
        raise ConfigurationError("ai_for_power_2026 must be an object")
    if not isinstance(opportunities, list) or not opportunities:
        raise ConfigurationError("opportunities must be a non-empty list")
    parse_utc(str(membership.get("last_contact_utc", "")))
    parse_utc(str(membership.get("next_contact_not_before_utc", "")))
    parse_date(str(challenge.get("pitch_day_date", "")))


def membership_action(
    membership: Mapping[str, Any],
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    status = str(membership.get("status", "unknown"))
    not_before = parse_utc(str(membership.get("next_contact_not_before_utc", "")))
    suppress = bool(membership.get("suppress_new_contact", False))

    if status in {"accepted", "declined", "withdrawn"}:
        return {
            "id": "membership_follow_up",
            "priority": "closed",
            "state": "closed",
            "action": "No outreach action required.",
            "reason": f"Membership state is {status}.",
            "not_before_utc": not_before.isoformat(),
            "contact_mode": str(membership.get("contact_mode", "existing_thread_only")),
        }

    if suppress or now_utc < not_before:
        return {
            "id": "membership_follow_up",
            "priority": "blocked",
            "state": "wait",
            "action": str(membership.get("next_action", "Wait for a response.")),
            "reason": "A membership-interest request is already pending; duplicate standalone outreach is suppressed.",
            "not_before_utc": not_before.isoformat(),
            "contact_mode": str(membership.get("contact_mode", "existing_thread_only")),
        }

    return {
        "id": "membership_follow_up",
        "priority": "high",
        "state": "ready",
        "action": "Send one concise follow-up in the existing membership thread, then reset the cooldown.",
        "reason": "The contact cooldown has expired and no accepted/declined state is recorded.",
        "not_before_utc": not_before.isoformat(),
        "contact_mode": str(membership.get("contact_mode", "existing_thread_only")),
    }


def challenge_action(
    challenge: Mapping[str, Any],
    *,
    today: date,
) -> dict[str, Any]:
    pitch_day = parse_date(str(challenge.get("pitch_day_date", "")))
    days_to_pitch = (pitch_day - today).days
    application_state = str(challenge.get("application_state", "unknown"))

    if application_state in {"submitted", "selected", "not_selected", "closed"}:
        priority = "closed" if application_state in {"not_selected", "closed"} else "high"
        state = "closed" if priority == "closed" else "monitor"
    elif application_state == "requires_program_confirmation":
        priority = "critical" if days_to_pitch <= 30 else "high"
        state = "verify"
    else:
        priority = "high" if days_to_pitch <= 30 else "medium"
        state = "review"

    return {
        "id": "ai_for_power_window",
        "priority": priority,
        "state": state,
        "application_state": application_state,
        "days_to_pitch_day": days_to_pitch,
        "pitch_day_date": pitch_day.isoformat(),
        "public_application_evaluation_window": str(
            challenge.get("public_application_evaluation_window", "unknown")
        ),
        "page_still_displays_submit_application": bool(
            challenge.get("page_still_displays_submit_application", False)
        ),
        "action": str(challenge.get("next_action", "Verify the current program window.")),
        "reason": (
            "The public page still exposes a submission section, but its published timeline places "
            "application and evaluation in May/June. The portal state must be confirmed rather than inferred."
        ),
    }


def evidence_readiness(root: Path, paths: Sequence[str]) -> dict[str, Any]:
    present: list[str] = []
    missing: list[str] = []
    for raw_path in paths:
        normalized = str(raw_path).strip().replace("\\", "/")
        if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
            missing.append(normalized or "(blank path)")
            continue
        if (root / normalized).is_file():
            present.append(normalized)
        else:
            missing.append(normalized)
    total = len(present) + len(missing)
    ratio = round(len(present) / total, 4) if total else 0.0
    return {
        "present": present,
        "missing": missing,
        "present_count": len(present),
        "total_count": total,
        "ratio": ratio,
    }


def opportunity_rows(
    opportunities: Sequence[Mapping[str, Any]],
    *,
    root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in opportunities:
        evidence_paths = item.get("repo_evidence_paths", [])
        if not isinstance(evidence_paths, list):
            evidence_paths = []
        evidence = evidence_readiness(root, [str(path) for path in evidence_paths])
        fit_score = int(item.get("fit_score", 0) or 0)
        external_gates = item.get("external_gates", [])
        if not isinstance(external_gates, list):
            external_gates = []

        readiness_score = round((fit_score * 0.7) + (evidence["ratio"] * 3.0), 4)
        rows.append(
            {
                "id": str(item.get("id", "")),
                "title": str(item.get("title", "")),
                "category": str(item.get("category", "")),
                "public_source": str(item.get("public_source", "")),
                "fit_score_10": fit_score,
                "readiness_score_10": readiness_score,
                "entry_claim": str(item.get("entry_claim", "")),
                "repo_evidence": evidence,
                "external_gates": [str(gate) for gate in external_gates],
                "promotion_state": "external_review_required",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["readiness_score_10"]),
            -int(row["fit_score_10"]),
            str(row["title"]).casefold(),
        ),
    )


def source_health(intelligence: Mapping[str, Any]) -> dict[str, Any]:
    summary = intelligence.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    schema = str(intelligence.get("schema", "unavailable"))
    pages = int(summary.get("pages_fetched", 0) or 0)
    failures = int(summary.get("pages_failed", 0) or 0)
    if schema.endswith("_seed_v1"):
        state = "seed_only"
    elif pages and not failures:
        state = "live_clean"
    elif pages:
        state = "live_partial"
    else:
        state = "unavailable"
    return {
        "state": state,
        "schema": schema,
        "pages_fetched": pages,
        "pages_failed": failures,
        "intelligence_hash_sha256": str(
            intelligence.get("intelligence_hash_sha256", "")
        ),
    }


def build_action_queue(
    program: Mapping[str, Any],
    intelligence: Mapping[str, Any],
    *,
    root: Path = ROOT,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    validate_program(program)
    generated = parse_utc(generated_utc) if generated_utc else datetime.now(timezone.utc)
    today = generated.date()

    membership = membership_action(program["membership"], now_utc=generated)
    challenge = challenge_action(program["ai_for_power_2026"], today=today)
    opportunities = opportunity_rows(program["opportunities"], root=root)
    source = source_health(intelligence)

    action_queue = [challenge, membership]
    for index, lane in enumerate(opportunities[:3], start=1):
        action_queue.append(
            {
                "id": f"build_capsule_{lane['id']}",
                "priority": "high" if index == 1 else "medium",
                "state": "prepare",
                "action": (
                    f"Prepare a bounded Proof Capsule for {lane['title']} using only the listed "
                    "repository evidence; leave every external gate open until a consortium or utility reviewer owns it."
                ),
                "readiness_score_10": lane["readiness_score_10"],
            }
        )

    stable_core = {
        "schema": "opai_action_queue_v1",
        "program_source_checked_utc": str(program.get("source_checked_utc", "")),
        "source_health": source,
        "membership": membership,
        "ai_for_power_2026": challenge,
        "opportunities": opportunities,
        "action_queue": action_queue,
        "sources": program.get("sources", {}),
        "claim_boundary": str(program.get("claim_boundary", "")),
    }

    return {
        **stable_core,
        "generated_utc": generated.isoformat(),
        "action_queue_hash_sha256": canonical_json_hash(stable_core),
        "automation_boundary": {
            "emails_sent": False,
            "forms_submitted": False,
            "applications_submitted": False,
            "membership_claimed": False,
            "purpose": "rank public-source opportunities and enforce outreach cooldowns",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a public-safe OPAI membership and AI for Power action queue."
    )
    parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    parser.add_argument("--intelligence", type=Path, default=DEFAULT_INTELLIGENCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD_OUT)
    parser.add_argument("--no-dashboard", action="store_true")
    parser.add_argument(
        "--generated-utc",
        default=None,
        help="Optional deterministic UTC time for testing or frozen builds.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        program = read_json(args.program)
        intelligence, intelligence_source = resolve_intelligence(args.intelligence)
        payload = build_action_queue(
            program,
            intelligence,
            root=ROOT,
            generated_utc=args.generated_utc,
        )
        payload["input_files"] = {
            "program": str(args.program),
            "intelligence": intelligence_source,
        }
        write_json(args.out, payload)
        if not args.no_dashboard:
            write_json(args.dashboard_out, payload)
    except (ConfigurationError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "source_state": payload["source_health"]["state"],
                "membership_state": payload["membership"]["state"],
                "challenge_state": payload["ai_for_power_2026"]["state"],
                "top_opportunity": (
                    payload["opportunities"][0]["title"]
                    if payload["opportunities"]
                    else None
                ),
                "action_queue_hash_sha256": payload["action_queue_hash_sha256"],
                "out": str(args.out),
                "dashboard_out": None if args.no_dashboard else str(args.dashboard_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
