"""Build the fail-closed current reviewer front door."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_JSON = ROOT / "out" / "ops" / "current_reviewer_front_door_latest.json"
OUT_MD = SPRINT_DIR / "CURRENT_REVIEWER_FRONT_DOOR_2026-07-29.md"
PUBLIC_ARTIFACT_MANIFEST = (
    ROOT
    / "docs"
    / "receipts"
    / "CURRENT_REVIEWER_PUBLIC_ARTIFACT_MANIFEST_2026-07-29.json"
)

CAPABILITY_PDF = ROOT / "output" / "pdf" / "LumenCore_Federal_Capability_Statement_CURRENT.pdf"
CAPABILITY_GOVERNANCE = SPRINT_DIR / "CAPABILITY_ARTIFACT_GOVERNANCE_2026-07-26.json"
PITCH_DECK = (
    ROOT
    / "output"
    / "pptx"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pptx"
)
PITCH_DECK_PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf"
)
PITCH_GOVERNANCE = ROOT / "out" / "ops" / "pitch_deck_governance_latest.json"
WHITEPAPER_PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_Source_Native_Benchmark_Whitepaper_CURRENT.pdf"
)
WHITEPAPER_MANIFEST = (
    ROOT / "out" / "ops" / "source_native_research_whitepaper_manifest_latest.json"
)
SOURCE_NATIVE_LEDGER = (
    ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
)
MARKET_SIGNAL_BENCHMARK = (
    ROOT / "out" / "ops" / "market_signal_source_native_benchmark_latest.json"
)
PROSPECTIVE_STATUS = (
    ROOT / "out" / "ops" / "time_series_source_native_prospective_protocol_status.json"
)
COMMAND_BOARD = (
    ROOT / "out" / "ops" / "near_deadline_submission_command_board_latest.json"
)
EXTERNAL_ACTION_LEDGER = (
    ROOT
    / "out"
    / "portfolio_external_action_ledger"
    / "portfolio_external_action_ledger_latest.json"
)

SCHEMA = "lumencore.current_reviewer_front_door.v1"
STATUS = "CURRENT_REVIEWER_FRONT_DOOR_READY_HUMAN_RELEASE_REQUIRED"
PUBLIC_ARTIFACT_MANIFEST_SCHEMA = (
    "lumencore.current_reviewer_public_artifact_manifest.v1"
)
PUBLIC_ARTIFACT_IDS = (
    "current_capability_statement",
    "current_evidence_to_pilot_deck",
    "current_evidence_to_pilot_deck_pdf",
    "current_source_native_whitepaper",
)


class FrontDoorError(ValueError):
    """Raised when a current reviewer artifact fails reconciliation."""


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontDoorError(f"Unreadable JSON: {rel(path)}") from exc
    if not isinstance(payload, dict):
        raise FrontDoorError(f"Expected JSON object: {rel(path)}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def artifact_row(
    artifact_id: str,
    role: str,
    path: Path,
    status: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise FrontDoorError(f"Missing current reviewer artifact: {rel(path)}")
    return {
        "id": artifact_id,
        "role": role,
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "status": status,
        "external_release_authorized": False,
    }


def find_artifact(
    artifacts: list[dict[str, Any]],
    artifact_id: str,
) -> dict[str, Any]:
    matches = [row for row in artifacts if row.get("id") == artifact_id]
    if len(matches) != 1:
        raise FrontDoorError(f"Expected one governed artifact: {artifact_id}")
    return matches[0]


def build_payload(as_of_utc: str) -> dict[str, Any]:
    capability = read_json(CAPABILITY_GOVERNANCE)
    pitch = read_json(PITCH_GOVERNANCE)
    whitepaper = read_json(WHITEPAPER_MANIFEST)
    source_native = read_json(SOURCE_NATIVE_LEDGER)
    market_signal = read_json(MARKET_SIGNAL_BENCHMARK)
    prospective = read_json(PROSPECTIVE_STATUS)
    command_board = read_json(COMMAND_BOARD)
    external_actions = read_json(EXTERNAL_ACTION_LEDGER)

    if capability.get("schema") != "lumencore.capability_statement_governance.v1":
        raise FrontDoorError("Capability-statement governance schema mismatch")
    if capability.get("status") != "GOVERNED_CURRENT_PACKET_WITH_ARCHIVED_LEGACY":
        raise FrontDoorError("Capability-statement governance is not current")
    capability_current = find_artifact(
        capability.get("artifacts", []),
        "federal_capability_statement_current",
    )
    if (
        capability_current.get("status")
        != "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED"
        or capability_current.get("external_release_authorized") is not False
        or capability_current.get("sha256") != sha256_file(CAPABILITY_PDF)
    ):
        raise FrontDoorError("Current capability statement failed governance")

    if pitch.get("schema") != "lumencore.pitch_deck_governance.v1":
        raise FrontDoorError("Pitch-deck governance schema mismatch")
    pitch_current = pitch.get("current_deck", {})
    pitch_pdf = pitch.get("current_pdf_companion", {})
    if (
        pitch_current.get("status") != "CURRENT_HUMAN_REVIEW_REQUIRED"
        or pitch_current.get("external_release_authorized") is not False
        or pitch_current.get("sha256") != sha256_file(PITCH_DECK)
    ):
        raise FrontDoorError("Current pitch deck failed governance")
    if (
        pitch_pdf.get("status")
        != "CURRENT_PDF_COMPANION_HUMAN_REVIEW_REQUIRED"
        or pitch_pdf.get("external_release_authorized") is not False
        or pitch_pdf.get("send_eligible") is not False
        or pitch_pdf.get("source_pptx_sha256") != pitch_current.get("sha256")
        or pitch_pdf.get("sha256") != sha256_file(PITCH_DECK_PDF)
    ):
        raise FrontDoorError("Current pitch-deck PDF companion failed governance")

    if whitepaper.get("schema") != "lumencore.source_native_research_whitepaper.v1":
        raise FrontDoorError("Whitepaper manifest schema mismatch")
    whitepaper_artifact = next(
        (
            row
            for row in whitepaper.get("generated_artifacts", [])
            if row.get("path") == rel(WHITEPAPER_PDF)
        ),
        None,
    )
    if (
        whitepaper.get("status") != "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED"
        or whitepaper.get("external_release_authorized") is not False
        or whitepaper_artifact is None
        or str(whitepaper_artifact.get("sha256", "")).upper()
        != sha256_file(WHITEPAPER_PDF)
    ):
        raise FrontDoorError("Current whitepaper failed governance")

    summary = source_native.get("summary", {})
    expected_counts = {
        "registered_family_count": 140,
        "implementation_present_count": 35,
        "implementation_required_count": 105,
        "executed_direct_source_baseline_comparison_count": 126,
        "individual_comparison_global_holm_positive_count": 0,
        "internal_source_native_promotion_gate_pass_count": 0,
        "market_signal_candidate_count": 4,
        "market_signal_source_count": 3,
        "market_signal_comparison_count": 48,
        "market_signal_inference_insufficient_count": 48,
        "market_signal_global_holm_positive_count": 0,
        "market_signal_promoted_candidate_count": 0,
    }
    if any(summary.get(key) != value for key, value in expected_counts.items()):
        raise FrontDoorError("Source-native evidence snapshot changed; refresh review")
    if (
        source_native.get("summary", {}).get("public_performance_claim_allowed")
        is not False
        or prospective.get("eligible_future_observation_count") != 0
    ):
        raise FrontDoorError("Evidence boundary is not fail closed")
    market_negative = market_signal.get("negative_result_summary", {})
    if (
        market_signal.get("schema")
        != "market_signal_source_native_benchmark_v1"
        or market_signal.get("status")
        != "EXPLORATORY_RETROSPECTIVE_NEGATIVE_OR_INSUFFICIENT_EVIDENCE"
        or market_signal.get("external_actions") != []
        or any(
            bool(value)
            for value in market_signal.get("claim_controls", {}).values()
        )
        or market_negative.get("candidate_source_baseline_comparison_count")
        != 48
        or market_negative.get("inference_insufficient_comparison_count")
        != 48
        or market_negative.get("global_holm_positive_count") != 0
    ):
        raise FrontDoorError("Market-signal evidence is not fail closed")

    board_summary = command_board.get("summary", {})
    if (
        command_board.get("status")
        != "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_FAIL_CLOSED_FRESHNESS_BLOCKERS"
        or board_summary.get("final_submit_allowed_without_human") is not False
        or board_summary.get("external_send_allowed_without_human") is not False
    ):
        raise FrontDoorError("Near-deadline command board is not fail closed")
    if (
        external_actions.get("status")
        != "RECONCILED_FAIL_CLOSED_LEDGER_READY"
    ):
        raise FrontDoorError("External-action ledger is not reconciled")

    artifacts = [
        artifact_row(
            "current_capability_statement",
            "recipient_specific_capability_overview",
            CAPABILITY_PDF,
            "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED",
        ),
        artifact_row(
            "current_evidence_to_pilot_deck",
            "technical_and_commercial_review_deck",
            PITCH_DECK,
            "CURRENT_HUMAN_REVIEW_REQUIRED",
        ),
        artifact_row(
            "current_evidence_to_pilot_deck_pdf",
            "portable_technical_and_commercial_review_deck",
            PITCH_DECK_PDF,
            "CURRENT_PDF_COMPANION_HUMAN_REVIEW_REQUIRED",
        ),
        artifact_row(
            "current_source_native_whitepaper",
            "technical_method_and_limitations",
            WHITEPAPER_PDF,
            "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED",
        ),
        artifact_row(
            "source_native_family_baseline_ledger",
            "machine_readable_benchmark_evidence",
            SOURCE_NATIVE_LEDGER,
            "INTERNAL_EVIDENCE_REVIEW_REQUIRED",
        ),
        artifact_row(
            "market_signal_source_native_benchmark",
            "cost_aware_source_specific_market_replay",
            MARKET_SIGNAL_BENCHMARK,
            str(market_signal.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "prospective_protocol_status",
            "future_only_validation_gate",
            PROSPECTIVE_STATUS,
            str(prospective.get("protocol_status", "UNKNOWN")),
        ),
        artifact_row(
            "near_deadline_submission_command_board",
            "current_opportunity_and_action_router",
            COMMAND_BOARD,
            str(command_board.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "portfolio_external_action_ledger",
            "duplicate_suppression_and_receipt_state",
            EXTERNAL_ACTION_LEDGER,
            str(external_actions.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "capability_statement_governance",
            "capability_release_control",
            CAPABILITY_GOVERNANCE,
            str(capability.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "pitch_deck_governance",
            "deck_release_control",
            PITCH_GOVERNANCE,
            str(pitch.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "whitepaper_manifest",
            "whitepaper_release_control",
            WHITEPAPER_MANIFEST,
            str(whitepaper.get("status", "UNKNOWN")),
        ),
    ]

    payload = {
        "schema": SCHEMA,
        "as_of_utc": as_of_utc,
        "status": STATUS,
        "summary": {
            **expected_counts,
            "eligible_future_observation_count": 0,
            "promoted_champion_count": 0,
            "artifact_count": len(artifacts),
            "external_release_authorized_count": 0,
            "human_release_review_required": True,
            "open_stage_ready_lane_count": board_summary.get(
                "stage_ready_count"
            ),
            "human_action_due_count": board_summary.get(
                "human_action_due_count"
            ),
        },
        "recommended_reading_order": [
            "current_capability_statement",
            "current_evidence_to_pilot_deck",
            "current_evidence_to_pilot_deck_pdf",
            "current_source_native_whitepaper",
            "source_native_family_baseline_ledger",
            "market_signal_source_native_benchmark",
            "prospective_protocol_status",
            "near_deadline_submission_command_board",
            "portfolio_external_action_ledger",
        ],
        "artifacts": artifacts,
        "claim_boundary": (
            "This front door proves the presence and hashes of current local review "
            "artifacts plus their fail-closed governance state. It does not establish "
            "model superiority, alpha, field performance, savings, revenue, valuation, "
            "customer adoption, agency endorsement, award, contract, legal sufficiency, "
            "or external-release authority."
        ),
        "release_controls": {
            "recipient_and_venue_specific_review_required": True,
            "official_opportunity_source_recheck_required": True,
            "duplicate_send_check_required": True,
            "legal_identity_and_certification_human_only": True,
            "pricing_and_payment_human_only": True,
            "external_release_authorized": False,
            "autonomous_send_or_submit_allowed": False,
        },
        "safest_next_action": (
            "Select only the artifacts required by a verified recipient or official "
            "notice, recheck the current requirements and duplicate-send ledger, and "
            "obtain action-time founder review before any upload, send, certification, "
            "agreement acceptance, or payment."
        ),
        "outputs": {
            "json": rel(OUT_JSON),
            "markdown": rel(OUT_MD),
            "public_artifact_manifest": rel(PUBLIC_ARTIFACT_MANIFEST),
        },
    }
    payload["front_door_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# LumenCore Current Reviewer Front Door",
        "",
        f"As of UTC: `{payload['as_of_utc']}`",
        f"Status: `{payload['status']}`",
        "",
        "This is the current review entry point. Legacy decks, capability packets, "
        "whitepapers, and speculative archives are not substitutes for these governed "
        "artifacts.",
        "",
        "## Evidence State",
        "",
        f"- Registered families: `{summary['registered_family_count']}`",
        f"- Implementations present: `{summary['implementation_present_count']}`",
        f"- Implementations missing: `{summary['implementation_required_count']}`",
        f"- Direct source-native comparisons: `{summary['executed_direct_source_baseline_comparison_count']}`",
        f"- Global Holm-positive comparisons: `{summary['individual_comparison_global_holm_positive_count']}`",
        f"- Market-signal comparisons: `{summary['market_signal_comparison_count']}`",
        f"- Market-signal inferentially insufficient: `{summary['market_signal_inference_insufficient_count']}`",
        f"- Promoted champions: `{summary['promoted_champion_count']}`",
        f"- Eligible future observations: `{summary['eligible_future_observation_count']}`",
        f"- Stage-ready opportunity lanes: `{summary['open_stage_ready_lane_count']}`",
        f"- Human actions due: `{summary['human_action_due_count']}`",
        "",
        "## Reading Order",
        "",
    ]
    by_id = {row["id"]: row for row in payload["artifacts"]}
    for artifact_id in payload["recommended_reading_order"]:
        row = by_id[artifact_id]
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Role: `{row['role']}`",
                f"- Path: `{row['path']}`",
                f"- Status: `{row['status']}`",
                f"- SHA-256: `{row['sha256']}`",
                f"- External release authorized: `{str(row['external_release_authorized']).lower()}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Release Controls",
            "",
        ]
    )
    for key, value in payload["release_controls"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
            f"Front-door SHA-256: `{payload['front_door_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def serialized(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_public_artifact_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["id"]: row for row in payload["artifacts"]}
    artifacts = []
    for artifact_id in PUBLIC_ARTIFACT_IDS:
        row = by_id.get(artifact_id)
        if row is None:
            raise FrontDoorError(
                f"Missing public artifact manifest member: {artifact_id}"
            )
        artifacts.append(
            {
                "id": row["id"],
                "path": row["path"],
                "bytes": row["bytes"],
                "sha256": row["sha256"],
                "status": row["status"],
                "external_release_authorized": False,
            }
        )
    manifest: dict[str, Any] = {
        "schema": PUBLIC_ARTIFACT_MANIFEST_SCHEMA,
        "as_of_utc": payload["as_of_utc"],
        "status": "SEALED_LOCAL_ARTIFACT_MANIFEST_HUMAN_RELEASE_REQUIRED",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "external_release_authorized": False,
        "network_action_performed": False,
        "claim_boundary": (
            "This manifest binds exact local reviewer-artifact paths, byte counts, "
            "and SHA-256 values. It does not authorize publication or sending and "
            "does not establish external validation, model superiority, field "
            "performance, award, contract, revenue, savings, or valuation."
        ),
        "manifest_sha256": "",
    }
    manifest["manifest_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in manifest.items()
            if key != "manifest_sha256"
        }
    )
    return manifest


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_ARTIFACT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(serialized(payload), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    PUBLIC_ARTIFACT_MANIFEST.write_text(
        serialized(build_public_artifact_manifest(payload)),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        published = read_json(OUT_JSON)
        payload = build_payload(str(published["as_of_utc"]))
        expected = {
            OUT_JSON: serialized(payload),
            OUT_MD: render_markdown(payload),
            PUBLIC_ARTIFACT_MANIFEST: serialized(
                build_public_artifact_manifest(payload)
            ),
        }
        stale = [
            rel(path)
            for path, text in expected.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            raise FrontDoorError(f"Stale outputs: {', '.join(stale)}")
        print("current reviewer front door outputs are current")
        return 0

    as_of_utc = args.as_of_utc or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    payload = build_payload(as_of_utc)
    write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "artifacts": payload["summary"]["artifact_count"],
                "sha256": payload["front_door_sha256"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
