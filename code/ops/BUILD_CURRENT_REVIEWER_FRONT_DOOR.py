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
PUBLIC_RELEASE_POLICY = ROOT / "config" / "public_release_sync_policy_v1.json"

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
MARKET_SIGNAL_KRAKEN_PANEL = (
    ROOT / "out" / "ops" / "market_signal_kraken_panel_benchmark_latest.json"
)
PROSPECTIVE_STATUS = (
    ROOT
    / "docs"
    / "receipts"
    / "TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE_V3_STATUS_2026-08-04.json"
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
PRODUCT_PRIORITY = ROOT / "out" / "ops" / "product_lane_priority_engine_latest.json"
VPS_PUBLIC_RELEASE_AUDIT = (
    ROOT / "out" / "ops" / "vps_public_release_security_audit_latest.json"
)
WHITEHOLE_AUDIT = ROOT / "docs" / "WHITEHOLE_WHITEHOLELAB_AUDIT_2026-08-02.md"

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
PUBLIC_RELEASE_ITEM_BY_ARTIFACT_ID = {
    "current_capability_statement": "federal_capability_statement_pdf",
    "current_evidence_to_pilot_deck": None,
    "current_evidence_to_pilot_deck_pdf": "current_evidence_to_pilot_deck_pdf",
    "current_source_native_whitepaper": "source_native_benchmark_whitepaper_pdf",
}


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


def dependency_freshness(
    dependencies: list[dict[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise FrontDoorError(f"{label} dependency {index} is invalid")
        relative = dependency.get("path")
        expected_sha = str(dependency.get("sha256", "")).upper()
        if not isinstance(relative, str) or not relative:
            raise FrontDoorError(f"{label} dependency {index} has no path")
        path = ROOT / relative
        try:
            path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise FrontDoorError(
                f"{label} dependency is missing or outside the repository: {relative}"
            ) from exc
        observed_sha = sha256_file(path) if path.is_file() else None
        expected_bytes = dependency.get("bytes")
        observed_bytes = path.stat().st_size if path.is_file() else None
        fresh = (
            path.is_file()
            and observed_sha == expected_sha
            and (
                expected_bytes is None
                or observed_bytes == expected_bytes
            )
        )
        records.append(
            {
                "path": relative,
                "expected_sha256": expected_sha,
                "observed_sha256": observed_sha,
                "expected_bytes": expected_bytes,
                "observed_bytes": observed_bytes,
                "fresh": fresh,
            }
        )
    stale = [row["path"] for row in records if not row["fresh"]]
    result = {
        "label": label,
        "dependency_count": len(records),
        "fresh_dependency_count": len(records) - len(stale),
        "stale_dependency_count": len(stale),
        "stale_dependency_paths": stale,
        "all_fresh": not stale,
        "dependencies": records,
    }
    if stale:
        raise FrontDoorError(
            f"{label} has stale governance dependencies: {', '.join(stale)}"
        )
    return result


def public_release_bindings(
    artifacts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    policy = read_json(PUBLIC_RELEASE_POLICY)
    if (
        policy.get("schema") != "lumencore.public_release_sync_policy.v1"
        or policy.get("status") != "frozen"
        or policy.get("mode") != "DRY_RUN_ONLY"
    ):
        raise FrontDoorError("Public-release policy is missing or not fail closed")
    release_items = {
        str(row.get("id")): row
        for row in policy.get("allowlist", [])
        if isinstance(row, dict)
    }
    by_id = {row["id"]: row for row in artifacts}
    bindings: dict[str, dict[str, Any]] = {}
    for artifact_id in PUBLIC_ARTIFACT_IDS:
        artifact = by_id[artifact_id]
        release_item_id = PUBLIC_RELEASE_ITEM_BY_ARTIFACT_ID[artifact_id]
        if release_item_id is None:
            bindings[artifact_id] = {
                "release_item_id": None,
                "immutable_target_path": None,
                "public_url": None,
                "publication_state": "LOCAL_ONLY_SOURCE_NOT_PUBLICATION_CANDIDATE",
                "local_only": True,
                "network_verification_performed": False,
            }
            continue
        release_item = release_items.get(release_item_id)
        if release_item is None:
            raise FrontDoorError(
                f"Public-release item is missing: {release_item_id}"
            )
        if (
            release_item.get("source_path") != artifact["path"]
            or str(release_item.get("expected_source_sha256", "")).upper()
            != artifact["sha256"]
        ):
            raise FrontDoorError(
                f"Public-release item is stale for {artifact_id}"
            )
        target_path = release_item.get("target_path")
        public_url = release_item.get("public_url")
        if not isinstance(target_path, str) or not isinstance(public_url, str):
            raise FrontDoorError(
                f"Public-release binding is incomplete for {artifact_id}"
            )
        target = ROOT / target_path
        if target.is_file():
            publication_state = (
                "LOCAL_STAGE_PRESENT_PUBLIC_URL_UNVERIFIED"
                if sha256_file(target) == artifact["sha256"]
                else "LOCAL_STAGE_HASH_MISMATCH_BLOCKED"
            )
        else:
            publication_state = "LOCAL_TARGET_ABSENT_NOT_PUBLISHED"
        bindings[artifact_id] = {
            "release_item_id": release_item_id,
            "immutable_target_path": target_path,
            "public_url": public_url,
            "publication_state": publication_state,
            "local_only": False,
            "network_verification_performed": False,
        }
    return bindings


def build_payload(as_of_utc: str) -> dict[str, Any]:
    capability = read_json(CAPABILITY_GOVERNANCE)
    pitch = read_json(PITCH_GOVERNANCE)
    whitepaper = read_json(WHITEPAPER_MANIFEST)
    source_native = read_json(SOURCE_NATIVE_LEDGER)
    market_signal = read_json(MARKET_SIGNAL_BENCHMARK)
    market_signal_panel = read_json(MARKET_SIGNAL_KRAKEN_PANEL)
    prospective = read_json(PROSPECTIVE_STATUS)
    command_board = read_json(COMMAND_BOARD)
    external_actions = read_json(EXTERNAL_ACTION_LEDGER)
    product_priority = read_json(PRODUCT_PRIORITY)
    vps_public_release = read_json(VPS_PUBLIC_RELEASE_AUDIT)

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
    capability_dependency_freshness = dependency_freshness(
        capability_current.get("dependencies", []),
        label="capability_statement_governance",
    )

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
    pitch_dependency_freshness = dependency_freshness(
        pitch_current.get("dependencies", []),
        label="pitch_deck_governance",
    )

    if whitepaper.get("schema") != "lumencore.source_native_research_whitepaper.v2":
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
    whitepaper_dependency_freshness = dependency_freshness(
        whitepaper.get("canonical_source_receipts", []),
        label="whitepaper_manifest",
    )

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
    panel_counts = {
        "market_signal_panel_pair_count": 12,
        "market_signal_panel_comparison_count": 16,
        "market_signal_panel_global_holm_positive_count": 1,
        "market_signal_panel_all_baseline_mean_winner_count": 0,
        "market_signal_panel_promoted_candidate_count": 0,
    }
    if any(summary.get(key) != value for key, value in expected_counts.items()):
        raise FrontDoorError("Source-native evidence snapshot changed; refresh review")
    if (
        source_native.get("summary", {}).get("public_performance_claim_allowed")
        is not False
        or prospective.get("schema")
        != "time_series_source_native_prospective_status.v3"
        or prospective.get("state") != "SEALED_AWAITING_FUTURE_OBSERVATIONS"
        or prospective.get("eligible_future_observation_count") != 0
        or prospective.get("primary_inference_complete") is not False
        or any(
            prospective.get(key) is not False
            for key in (
                "performance_claim_allowed",
                "trading_alpha_claim_allowed",
                "field_validation_claim_allowed",
                "real_dollar_claim_allowed",
            )
        )
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
    market_panel_summary = market_signal_panel.get("result_summary", {})
    market_panel_claim_controls = market_signal_panel.get("claim_controls")
    if (
        market_signal_panel.get("schema")
        != "market_signal_kraken_panel_benchmark_v1"
        or market_signal_panel.get("status")
        != "RETROSPECTIVE_PANEL_SCREEN_NO_PROMOTION"
        or market_signal_panel.get("external_actions") != []
        or not isinstance(market_panel_claim_controls, dict)
        or not market_panel_claim_controls
        or any(
            bool(value)
            for value in market_panel_claim_controls.values()
        )
        or market_signal_panel.get("implementation_summary", {}).get(
            "source_series_count"
        )
        != 12
        or market_panel_summary.get(
            "candidate_source_baseline_comparison_count"
        )
        != 16
        or market_panel_summary.get(
            "exploratory_global_holm_positive_count"
        )
        != 1
        or market_panel_summary.get(
            "candidate_beats_every_baseline_on_mean_count"
        )
        != 0
        or market_panel_summary.get("promotion_count") != 0
        or market_panel_summary.get("confirmatory_inference_allowed")
        is not False
    ):
        raise FrontDoorError(
            "Kraken-panel market-signal evidence is not fail closed"
        )

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

    ranking = product_priority.get("ranking")
    recommendation = product_priority.get("recommendation")
    if (
        product_priority.get("schema") != "product_lane_priority_engine_v1"
        or not isinstance(ranking, list)
        or len(ranking) < 2
        or not isinstance(recommendation, dict)
    ):
        raise FrontDoorError("Product-lane priority evidence is missing or stale")
    ranked_by_id = {
        str(row.get("id")): row
        for row in ranking
        if isinstance(row, dict)
    }
    commercial_lane = ranked_by_id.get("prooflock_opportunity_ops")
    hypercore_lane = ranked_by_id.get(
        "hypercore_readonly_resilience_evaluation"
    )
    if (
        commercial_lane is None
        or commercial_lane.get("rank") != 1
        or recommendation.get("commercial_lane")
        != "prooflock_opportunity_ops"
        or hypercore_lane is None
        or hypercore_lane.get("rank") != 4
    ):
        raise FrontDoorError("Product-lane ranking no longer matches the review contract")
    buyer_ready_lane_count = sum(
        row.get("buyer_readiness_gate", {}).get("passed") is True
        for row in ranking
        if isinstance(row, dict)
    )
    if buyer_ready_lane_count != 0:
        raise FrontDoorError(
            "A buyer-ready product claim requires a new external validation review"
        )

    release_summary = vps_public_release.get("summary")
    if (
        vps_public_release.get("schema")
        != "lumencore.vps_public_release_security_audit.v1"
        or not isinstance(release_summary, dict)
        or release_summary.get("public_release_allowed") is not False
        or release_summary.get("vps_mutation_allowed") is not False
        or release_summary.get("status") != "BLOCKED"
    ):
        raise FrontDoorError(
            "VPS public-release state requires a new release-authority review"
        )
    if not WHITEHOLE_AUDIT.is_file():
        raise FrontDoorError("WhiteHole archive-boundary audit is missing")
    whitehole_text = WHITEHOLE_AUDIT.read_text(encoding="utf-8")
    for marker in (
        "WhiteHole is useful as historical custody",
        "Neither currently establishes forecasting",
        "Keep WhiteHole frozen as an archive.",
    ):
        if marker not in whitehole_text:
            raise FrontDoorError("WhiteHole archive-boundary audit is stale")

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
            "market_signal_kraken_panel_benchmark",
            "retrospective_multi_series_challenger_screen",
            MARKET_SIGNAL_KRAKEN_PANEL,
            str(market_signal_panel.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "prospective_protocol_status",
            "future_only_validation_gate",
            PROSPECTIVE_STATUS,
            str(prospective.get("state", "UNKNOWN")),
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
        artifact_row(
            "product_lane_priority_engine",
            "commercialization_priority_and_buyer_gate",
            PRODUCT_PRIORITY,
            "INTERNAL_PRIORITY_ONLY_EXTERNAL_BUYER_VALIDATION_REQUIRED",
        ),
        artifact_row(
            "vps_public_release_security_audit",
            "publication_and_transport_gate",
            VPS_PUBLIC_RELEASE_AUDIT,
            str(release_summary.get("status", "UNKNOWN")),
        ),
        artifact_row(
            "whitehole_archive_boundary_audit",
            "historical_archive_and_claim_boundary",
            WHITEHOLE_AUDIT,
            "HISTORICAL_ARCHIVE_ONLY_DO_NOT_PROMOTE",
        ),
    ]
    release_bindings = public_release_bindings(artifacts)
    upstream_dependency_freshness = {
        "current_capability_statement": capability_dependency_freshness,
        "current_evidence_to_pilot_deck": pitch_dependency_freshness,
        "current_evidence_to_pilot_deck_pdf": pitch_dependency_freshness,
        "current_source_native_whitepaper": whitepaper_dependency_freshness,
    }
    for artifact in artifacts:
        artifact_id = artifact["id"]
        if artifact_id in upstream_dependency_freshness:
            artifact["upstream_dependency_fresh"] = (
                upstream_dependency_freshness[artifact_id]["all_fresh"]
            )

    payload = {
        "schema": SCHEMA,
        "as_of_utc": as_of_utc,
        "status": STATUS,
        "summary": {
            **expected_counts,
            **panel_counts,
            "eligible_future_observation_count": 0,
            "promoted_champion_count": 0,
            "artifact_count": len(artifacts),
            "external_release_authorized_count": 0,
            "product_lane_count": len(ranking),
            "buyer_ready_product_lane_count": buyer_ready_lane_count,
            "commercial_lane_id": commercial_lane["id"],
            "commercial_lane_internal_strategy_score": commercial_lane[
                "strategy_score"
            ],
            "hypercore_rank": hypercore_lane["rank"],
            "hypercore_internal_strategy_score": hypercore_lane[
                "strategy_score"
            ],
            "public_endpoint_count": release_summary.get(
                "public_endpoint_count"
            ),
            "public_endpoint_passed_count": release_summary.get(
                "public_endpoint_passed_count"
            ),
            "public_release_allowed": False,
            "public_artifact_upstream_dependency_fresh_count": sum(
                result["all_fresh"]
                for result in upstream_dependency_freshness.values()
            ),
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
            "product_lane_priority_engine",
            "vps_public_release_security_audit",
            "whitehole_archive_boundary_audit",
            "source_native_family_baseline_ledger",
            "market_signal_source_native_benchmark",
            "market_signal_kraken_panel_benchmark",
            "prospective_protocol_status",
            "near_deadline_submission_command_board",
            "portfolio_external_action_ledger",
        ],
        "artifacts": artifacts,
        "public_release_bindings": release_bindings,
        "upstream_dependency_freshness": upstream_dependency_freshness,
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
            "vps_public_release_allowed": False,
            "external_release_authorized": False,
            "autonomous_send_or_submit_allowed": False,
        },
        "safest_next_action": (
            "Select only the artifacts required by a verified recipient or official "
            "notice, recheck the current requirements and duplicate-send ledger, and "
            "obtain action-time founder review before any upload, send, certification, "
            "agreement acceptance, payment, gateway mutation, or publication. The "
            "current minimum honest commercial offer is a fixed-scope ProofLock "
            "Opportunity Operations proof sprint with buyer-owned acceptance gates."
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
        f"- Kraken-panel pairs: `{summary['market_signal_panel_pair_count']}`",
        f"- Kraken-panel comparisons: `{summary['market_signal_panel_comparison_count']}`",
        f"- Kraken-panel exploratory Holm positives: `{summary['market_signal_panel_global_holm_positive_count']}`",
        f"- Kraken-panel all-baseline mean winners: `{summary['market_signal_panel_all_baseline_mean_winner_count']}`",
        f"- Promoted champions: `{summary['promoted_champion_count']}`",
        f"- Eligible future observations: `{summary['eligible_future_observation_count']}`",
        f"- Stage-ready opportunity lanes: `{summary['open_stage_ready_lane_count']}`",
        f"- Human actions due: `{summary['human_action_due_count']}`",
        "",
        "## Commercialization State",
        "",
        f"- Ranked product lanes: `{summary['product_lane_count']}`",
        f"- Buyer-ready product lanes: `{summary['buyer_ready_product_lane_count']}`",
        f"- First commercial lane: `{summary['commercial_lane_id']}`",
        "- Internal strategy score: "
        f"`{summary['commercial_lane_internal_strategy_score']}` "
        "(prioritization only; not valuation or buyer acceptance)",
        f"- HyperCore rank: `{summary['hypercore_rank']}`",
        "- HyperCore internal strategy score: "
        f"`{summary['hypercore_internal_strategy_score']}` "
        "(read-only evaluation candidate; not a promoted champion)",
        "",
        "## Publication State",
        "",
        f"- Public endpoints passing: `{summary['public_endpoint_passed_count']}` "
        f"of `{summary['public_endpoint_count']}`",
        f"- Public release allowed: `{str(summary['public_release_allowed']).lower()}`",
        "- WhiteHole posture: historical archive and provenance only; do not deploy "
        "the legacy site or promote its heuristic ranks.",
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
        binding = payload["public_release_bindings"][artifact_id]
        artifacts.append(
            {
                "id": row["id"],
                "path": row["path"],
                "bytes": row["bytes"],
                "sha256": row["sha256"],
                "status": row["status"],
                "release_item_id": binding["release_item_id"],
                "immutable_target_path": binding["immutable_target_path"],
                "public_url": binding["public_url"],
                "publication_state": binding["publication_state"],
                "local_only": binding["local_only"],
                "upstream_dependency_fresh": row[
                    "upstream_dependency_fresh"
                ],
                "external_release_authorized": False,
            }
        )
    manifest: dict[str, Any] = {
        "schema": PUBLIC_ARTIFACT_MANIFEST_SCHEMA,
        "receipt_time_semantics": "artifact_set_only_observation_time_excluded",
        "status": "SEALED_LOCAL_ARTIFACT_MANIFEST_HUMAN_RELEASE_REQUIRED",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "all_upstream_dependencies_fresh": all(
            row["upstream_dependency_fresh"] for row in artifacts
        ),
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
