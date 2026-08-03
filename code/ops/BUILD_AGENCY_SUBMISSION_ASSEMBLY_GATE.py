from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
CONCIERGE_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
FEDERAL_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
AGENCY_JSON = OUT_OPS / "agency_account_activation_docket_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
CONFORMANCE_JSON = OUT_OPS / "submission_conformance_gate_latest.json"

OUT_JSON = OUT_OPS / "agency_submission_assembly_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "agency_submission_assembly_gate.json"
OUT_MD = SPRINT_DIR / "AGENCY_SUBMISSION_ASSEMBLY_GATE_2026-07-09.md"

FEDERAL_AND_IP_CHANNELS = {
    "federal_registration",
    "federal_lab_tech_transfer",
    "federal_baa",
    "federal_contract",
    "federal_rfi",
    "federal_sbir",
    "federal_market_research",
    "federal_sources_sought",
    "ip_readiness",
}

SUPPLEMENTAL_CHANNEL_BY_LANE_ID = {
    "cdc_ai_acquisition_rfi": "federal_rfi",
    "darpa_falcon_dpa26bz04_dv016": "federal_sbir",
    "erdc_sovereign_cloud_cso": "federal_contract",
    "launchtn_3686_pitch_2026": "venture_pitch",
}

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.I),
]

COMMON_COMPONENTS = [
    {
        "component": "official_source_and_instructions",
        "gate": "Official opportunity instructions, amendments, due date, format, and submission route checked by a human.",
    },
    {
        "component": "capability_or_technical_narrative",
        "gate": "Human-approved narrative or technical volume aligned to the opportunity.",
    },
    {
        "component": "evidence_annex_and_proof_boundary",
        "gate": "Evidence artifacts are present, hashed, and claim-bounded.",
    },
    {
        "component": "program_fit_and_argument_trace",
        "gate": "Official objectives, novelty, named baseline, metrics, mission experiment, evidence applicability, execution plan, and falsifiers pass a source-bound conformance review.",
    },
    {
        "component": "eligibility_account_and_signer_authority",
        "gate": "SAM/UEI/CAGE, portal account, organization linkage, role, and signer authority verified.",
    },
    {
        "component": "cost_price_or_budget_basis",
        "gate": "Cost, price, budget, or ROM language is reviewed and permitted by the opportunity.",
    },
    {
        "component": "cyber_export_and_protected_data_boundary",
        "gate": "FCI/CUI/export/CMMC/SPRS/ATO/FedRAMP implications are checked before representation.",
    },
    {
        "component": "ip_disclosure_and_counsel_boundary",
        "gate": "Patent, ownership, disclosure, and claim-scope language remains counsel-gated.",
    },
    {
        "component": "human_final_action_authority",
        "gate": "Robert or named human authority approves send, upload, certification, filing, signature, pricing, or term action.",
    },
]

COMPONENT_GATE_PASSED_STATES = {
    "primary_artifact_ready",
    "hashable_artifacts_claim_bounded",
    "invention_family_summary_ready",
    "not_applicable_for_current_route",
    "not_primary_gate",
    "source_bound_argument_conformance_pass",
    "watch_only",
}

MODE_BLOCKERS = {
    "FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING": [
        "SAM.gov submission is not the same as Active status.",
        "External IRS/CAGE/DLA or SAM validation must clear before eligibility language is promoted.",
    ],
    "LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED": [
        "No lab license, partnership, or technology-transfer relationship is claimed.",
        "Human approves any follow-up content and disclosure boundary.",
    ],
    "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED": [
        "Official BAA/RFI instructions, attachment limits, and submission channel must be checked at action time.",
        "Cost, team, compliance, and upload preview remain human-gated.",
    ],
    "RFI_DRAFT_READY_SEND_BLOCKED": [
        "Official RFI send route, page limits, and attachment rules must be verified.",
        "Human must approve response wording before send.",
    ],
    "SBIR_DRAFT_READY_PORTAL_BLOCKED": [
        "DSIP firm linkage, Firm PIN, topic workspace, forms, cost volume, and certifications remain human-gated.",
        "No DSIP submit or certification action is authorized by local files.",
    ],
    "ROLLING_GATE_READY_RULE_CHECK_REQUIRED": [
        "NSF account, pending-pitch status, invitation state, and one-pending-pitch rule must be checked.",
        "No Research.gov or NSF final action is authorized by local files.",
    ],
    "ROUTING_SENT_WAIT_FOR_RESPONSE": [
        "Wait for official routing response before claiming a submission path or agency interest.",
    ],
    "PARTNER_REQUIRED_NO_SOLO_SUBMISSION": [
        "Qualified prime, jurisdictional owner, lab, testbed, or domain partner is required before any solo package is promoted.",
    ],
    "TOPIC_SCOUT_READY_SELECTION_REQUIRED": [
        "Topic fit and official package requirements must be selected before drafting becomes submission assembly.",
    ],
    "PARKED_NO_SOLO_ACTION": [
        "This lane should not be pursued solo without a qualified partner or lead organization.",
    ],
    "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL": [
        "Only intro material is ready; no solo proposal, pricing, or certification should be sent.",
    ],
    "IP_PACKET_READY_COUNSEL_REQUIRED": [
        "Licensed counsel must verify status, support, disclosure limits, and exact wording before IP claim expansion.",
    ],
}

COMPONENT_OVERRIDES = {
    "federal_registration": {
        "capability_or_technical_narrative": "not_required_for_registration_watch",
        "cost_price_or_budget_basis": "not_required_for_registration_watch",
        "cyber_export_and_protected_data_boundary": "watch_only",
        "ip_disclosure_and_counsel_boundary": "watch_only",
    },
    "federal_lab_tech_transfer": {
        "cost_price_or_budget_basis": "not_required_for_initial_followup",
        "eligibility_account_and_signer_authority": "human_followup_authority_required",
    },
    "ip_readiness": {
        "official_source_and_instructions": "counsel_or_official_record_required",
        "capability_or_technical_narrative": "invention_family_summary_ready",
        "cost_price_or_budget_basis": "not_required_for_counsel_packet",
        "cyber_export_and_protected_data_boundary": "not_primary_gate",
        "eligibility_account_and_signer_authority": "inventor_and_assignment_facts_required",
    },
    "federal_sources_sought": {
        "cost_price_or_budget_basis": "not_required_until_partner_or_sources_sought_response",
        "eligibility_account_and_signer_authority": "partner_authority_required",
    },
    "federal_market_research": {
        "cost_price_or_budget_basis": "not_required_for_routing_watch",
        "eligibility_account_and_signer_authority": "human_routing_authority_required",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def by_lane(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lane_id", "")): row for row in rows}


def artifact_status(path_text: str) -> dict[str, Any]:
    path = ROOT / path_text
    return {
        "path": path_text,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def component_state(
    component: str,
    lane: dict[str, Any],
    authority: dict[str, Any],
    concierge: dict[str, Any],
    conformance: dict[str, Any],
) -> str:
    channel = str(lane.get("channel", ""))
    override = COMPONENT_OVERRIDES.get(channel, {}).get(component)
    if override:
        return override

    readiness = str(authority.get("readiness_mode", ""))
    if component == "official_source_and_instructions":
        return "source_identified_human_recheck_required" if lane.get("source_refs") else "missing_source_reference"
    if component == "capability_or_technical_narrative":
        return "primary_artifact_ready" if int(concierge.get("artifact_missing_count", 0)) == 0 else "missing_primary_artifact"
    if component == "evidence_annex_and_proof_boundary":
        return "hashable_artifacts_claim_bounded" if int(concierge.get("artifact_missing_count", 0)) == 0 else "evidence_artifact_missing"
    if component == "program_fit_and_argument_trace":
        if not conformance:
            return "missing_submission_conformance_record"
        if str(conformance.get("status", "")) == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
            return "closed_official_decision_postmortem_only"
        if not bool(conformance.get("technical_argument_required", False)):
            return "not_applicable_for_current_route"
        if bool(conformance.get("argument_conformance_pass", False)):
            return "source_bound_argument_conformance_pass"
        return "argument_conformance_blocked"
    if component == "eligibility_account_and_signer_authority":
        if channel == "federal_sbir":
            return "dsip_or_sbir_authority_required"
        if channel in {"federal_contract", "federal_rfi", "federal_baa"}:
            return "sam_portal_and_signer_authority_required"
        return "human_authority_required"
    if component == "cost_price_or_budget_basis":
        if readiness in {"RFI_DRAFT_READY_SEND_BLOCKED", "LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED"}:
            return "not_required_for_initial_response"
        return "cost_or_price_review_required"
    if component == "cyber_export_and_protected_data_boundary":
        return "fci_cui_export_cyber_check_required"
    if component == "ip_disclosure_and_counsel_boundary":
        return "counsel_boundary_required"
    if component == "human_final_action_authority":
        return "blocked_until_human_approval"
    return "review_required"


def component_gate_passed(state: str) -> bool:
    return state in COMPONENT_GATE_PASSED_STATES or state.startswith("not_required_")


def package_status(row: dict[str, Any], conformance: dict[str, Any]) -> str:
    conformance_status = str(conformance.get("status", ""))
    if conformance_status == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
        return "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    if conformance_status == "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED":
        return "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    if conformance_status == "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY":
        return "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"
    if conformance_status == "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION":
        return "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION"
    if conformance_status in {
        "NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE",
        "NON_SUBMISSION_ROUTE",
    }:
        return "NO_CURRENT_SUBMISSION_ROUTE"
    if bool(conformance.get("submission_candidate_active", False)) and not bool(
        conformance.get("argument_conformance_pass", False)
    ):
        return "ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW"
    readiness = str(row.get("readiness_mode", ""))
    if readiness == "FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING":
        return "VALIDATION_WATCH_NOT_SUBMISSION"
    if readiness in {"PARKED_NO_SOLO_ACTION", "PARTNER_REQUIRED_NO_SOLO_SUBMISSION", "INTRO_MATERIAL_READY_NO_SOLO_PROPOSAL"}:
        return "PARTNER_OR_NO_SOLO_BLOCKED"
    if readiness == "IP_PACKET_READY_COUNSEL_REQUIRED":
        return "COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED"
    if readiness == "LAB_POC_FOLLOWUP_READY_HUMAN_SEND_REQUIRED":
        return "FOLLOWUP_PACKET_READY_HUMAN_SEND_REQUIRED"
    if readiness == "ROUTING_SENT_WAIT_FOR_RESPONSE":
        return "WAIT_FOR_RESPONSE"
    if readiness == "TOPIC_SCOUT_READY_SELECTION_REQUIRED":
        return "SCOUT_READY_NOT_ASSEMBLED"
    if readiness in {"FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED", "RFI_DRAFT_READY_SEND_BLOCKED", "SBIR_DRAFT_READY_PORTAL_BLOCKED", "ROLLING_GATE_READY_RULE_CHECK_REQUIRED"}:
        return "ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED"
    return "REVIEW_PACKET_READY_HUMAN_ACTION_BLOCKED"


def conformance_first_artifact(conformance: dict[str, Any]) -> str:
    for field in ("candidate_artifact", "official_source", "postmortem"):
        receipt = conformance.get(field)
        if (
            isinstance(receipt, dict)
            and receipt.get("present") is True
            and str(receipt.get("path") or "").strip()
        ):
            return str(receipt["path"])
    return ""


def build_rows() -> list[dict[str, Any]]:
    traction = read_json(TRACTION_JSON)
    authority_payload = read_json(AUTHORITY_JSON)
    docket_payload = read_json(DOCKET_JSON)
    concierge_payload = read_json(CONCIERGE_JSON)
    conformance_payload = read_json(CONFORMANCE_JSON)

    authority_rows = by_lane(authority_payload.get("authority_rows", []))
    docket_rows = by_lane(docket_payload.get("docket_items", []))
    concierge_rows = by_lane(concierge_payload.get("concierge_cards", []))
    conformance_rows = by_lane(conformance_payload.get("lanes", []))

    traction_lanes = [
        lane
        for lane in traction.get("lanes", [])
        if isinstance(lane, dict)
        and str(lane.get("channel", "")) in FEDERAL_AND_IP_CHANNELS
    ]
    traction_lane_ids = {
        str(lane.get("lane_id", ""))
        for lane in traction_lanes
        if str(lane.get("lane_id", "")).strip()
    }
    supplemental_lanes = []
    for index, conformance in enumerate(
        sorted(conformance_rows.values(), key=lambda item: str(item.get("lane_id", "")))
    ):
        lane_id = str(conformance.get("lane_id", ""))
        if (
            lane_id in traction_lane_ids
            or conformance.get("technical_argument_required") is not True
        ):
            continue
        official_source = conformance.get("official_source")
        source_refs = []
        if (
            isinstance(official_source, dict)
            and official_source.get("present") is True
            and str(official_source.get("path") or "").strip()
        ):
            source_refs = [str(official_source["path"])]
        supplemental_lanes.append(
            {
                "lane_id": lane_id,
                "name": conformance.get("name", lane_id),
                "priority": 900 + index,
                "channel": SUPPLEMENTAL_CHANNEL_BY_LANE_ID.get(
                    lane_id,
                    "supplemental_technical_submission",
                ),
                "effective_status": conformance.get("status", ""),
                "status": conformance.get("status", ""),
                "effective_source": "submission_conformance_supplement",
                "source_refs": source_refs,
                "effective_claim_boundary": conformance.get("claim_boundary", ""),
                "claim_boundary": conformance.get("claim_boundary", ""),
                "_conformance_first_artifact": conformance_first_artifact(conformance),
            }
        )

    rows = []
    for lane in sorted(
        [*traction_lanes, *supplemental_lanes],
        key=lambda item: int(item.get("priority", 999)),
    ):
        lane_id = str(lane.get("lane_id", ""))
        authority = authority_rows.get(lane_id, {})
        docket = docket_rows.get(lane_id, {})
        concierge = concierge_rows.get(lane_id, {})
        conformance = conformance_rows.get(lane_id, {})
        first_artifact = str(
            authority.get("first_artifact")
            or concierge.get("best_first_read")
            or lane.get("_conformance_first_artifact")
            or ""
        )
        if not authority and lane.get("_conformance_first_artifact"):
            authority = {
                "readiness_mode": "CONFORMANCE_SUPPLEMENT_ONLY",
                "first_artifact": first_artifact,
                "can_prepare_internal": True,
                "claim_boundary": lane.get("claim_boundary", ""),
                "required_authority": "Human action-time authority",
                "decision_question": conformance.get("next_action", ""),
            }
        if not concierge and first_artifact:
            concierge = {
                "artifact_missing_count": 0,
                "best_first_read": first_artifact,
            }
        artifact = artifact_status(first_artifact) if first_artifact else {
            "path": "",
            "present": False,
            "bytes": 0,
            "sha256": "",
        }
        components = []
        for component in COMMON_COMPONENTS:
            state = component_state(component["component"], lane, authority, concierge, conformance)
            components.append(
                {
                    **component,
                    "state": state,
                    "ready_for_review": component_gate_passed(state),
                    "gate_passed": component_gate_passed(state),
                    "final_action_blocked": True,
                }
            )
        blockers = list(MODE_BLOCKERS.get(str(authority.get("readiness_mode", "")), []))
        conformance_status = str(conformance.get("status", "MISSING_SUBMISSION_CONFORMANCE_RECORD"))
        if conformance_status == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
            blockers.insert(
                0,
                str(
                    conformance.get(
                        "next_action",
                        "Preserve the closed route and postmortem; do not recycle the packet as an active submission.",
                    )
                ),
            )
        elif bool(conformance.get("technical_argument_required", False)) and not bool(
            conformance.get("argument_conformance_pass", False)
        ):
            blockers.insert(
                0,
                str(
                    conformance.get(
                        "next_action",
                        "Complete the source-bound submission conformance review before calling the package reviewer-ready.",
                    )
                ),
            )
        if not blockers:
            blockers.append("Human approval remains required before external send, portal action, certification, filing, or term action.")
        row = {
            "lane_id": lane_id,
            "name": lane.get("name", ""),
            "priority": int(lane.get("priority", 999)),
            "channel": lane.get("channel", ""),
            "status": lane.get("effective_status", lane.get("status", "")),
            "legacy_intake_status": lane.get("status", ""),
            "state_source": lane.get("effective_source", "legacy_intake_baseline"),
            "readiness_mode": authority.get("readiness_mode", ""),
            "package_status": package_status(authority, conformance),
            "submission_conformance_status": conformance_status,
            "submission_candidate_active": bool(conformance.get("submission_candidate_active", False)),
            "technical_argument_required": bool(conformance.get("technical_argument_required", False)),
            "argument_conformance_pass": bool(conformance.get("argument_conformance_pass", False)),
            "argument_criterion_pass_count": int(conformance.get("criterion_pass_count", 0) or 0),
            "argument_criterion_count": int(conformance.get("criterion_count", 0) or 0),
            "urgency": docket.get("urgency", ""),
            "action_due": docket.get("action_due"),
            "first_artifact": artifact,
            "component_count": len(components),
            "review_ready_component_count": sum(1 for item in components if item["ready_for_review"]),
            "components": components,
            "assembly_blockers": blockers,
            "pre_action_checks": authority.get("pre_action_checks", []),
            "required_authority": authority.get("required_authority", ""),
            "next_human_action": docket.get("docket_action", authority.get("decision_question", "")),
            "claim_boundary": authority.get(
                "claim_boundary",
                lane.get("effective_claim_boundary", lane.get("claim_boundary", "")),
            ),
            "can_prepare_internal": bool(authority.get("can_prepare_internal", False)),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "legal_or_certification_action_allowed_without_human": False,
        }
        row["assembly_row_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()
        rows.append(row)
    return rows


def build_payload() -> dict[str, Any]:
    gate = read_json(REVIEWER_GATE_JSON)
    federal = read_json(FEDERAL_JSON)
    agency = read_json(AGENCY_JSON)
    authority = read_json(AUTHORITY_JSON)
    conformance = read_json(CONFORMANCE_JSON)
    rows = build_rows()

    gate_clear = (
        bool(gate.get("reviewer_gate_clear"))
        and int(gate["summary"]["unsafe_secret_count"]) == 0
        and int(gate["summary"]["unsafe_claim_count"]) == 0
    )
    all_final_actions_blocked = bool(authority["summary"]["all_final_actions_blocked_without_human"])
    all_artifacts_present = all(row["first_artifact"]["present"] for row in rows)
    active_submission_candidate_count = sum(1 for row in rows if row["submission_candidate_active"])
    active_argument_pass_count = sum(
        1 for row in rows if row["submission_candidate_active"] and row["argument_conformance_pass"]
    )
    active_argument_blocked_count = active_submission_candidate_count - active_argument_pass_count
    argument_gate_clear = (
        active_submission_candidate_count > 0
        and active_submission_candidate_count == active_argument_pass_count
    )
    conformance_active_lane_ids = {
        str(row.get("lane_id", ""))
        for row in conformance.get("lanes", [])
        if isinstance(row, dict)
        and row.get("submission_candidate_active") is True
        and row.get("technical_argument_required") is True
    }
    assembly_lane_ids = {str(row.get("lane_id", "")) for row in rows}
    unrepresented_active_conformance_lane_ids = sorted(
        conformance_active_lane_ids - assembly_lane_ids
    )
    assembly_conformance_coverage_clear = (
        bool(conformance.get("summary", {}).get("all_current_lanes_covered", False))
        and not unrepresented_active_conformance_lane_ids
    )
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[str(row["package_status"])] = status_counts.get(str(row["package_status"]), 0) + 1

    payload = {
        "generated_utc": now_utc(),
        "schema": "agency_submission_assembly_gate_v2",
        "status": "AGENCY_SUBMISSION_ASSEMBLY_READY_HUMAN_GATED"
        if (
            gate_clear
            and all_final_actions_blocked
            and all_artifacts_present
            and argument_gate_clear
            and assembly_conformance_coverage_clear
        )
        else "AGENCY_SUBMISSION_ASSEMBLY_BLOCKED",
        "purpose": "Convert near-term federal, SBIR, RFI, lab, and IP lanes into a fail-closed assembly checklist that separates artifact presence from source-bound argument conformance and human final authority.",
        "summary": {
            "assembly_lane_count": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "first_artifacts_present": all_artifacts_present,
            "reviewer_gate_clear": gate_clear,
            "submission_conformance_status": conformance.get("status", "MISSING"),
            "submission_conformance_all_current_lanes_covered": bool(
                conformance.get("summary", {}).get("all_current_lanes_covered", False)
            ),
            "assembly_conformance_coverage_clear": (
                assembly_conformance_coverage_clear
            ),
            "unrepresented_active_conformance_lane_count": len(
                unrepresented_active_conformance_lane_ids
            ),
            "unrepresented_active_conformance_lane_ids": (
                unrepresented_active_conformance_lane_ids
            ),
            "active_submission_candidate_count": active_submission_candidate_count,
            "active_argument_pass_count": active_argument_pass_count,
            "active_argument_blocked_count": active_argument_blocked_count,
            "argument_gate_clear": argument_gate_clear,
            "federal_protocol_status": federal.get("status", ""),
            "agency_activation_status": agency.get("status", ""),
            "agency_activation_item_count": int(agency["summary"]["activation_item_count"]),
            "agency_blocked_item_count": int(agency["summary"]["blocked_item_count"]),
            "authority_lane_count": int(authority["summary"]["lane_count"]),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "legal_or_certification_action_allowed_without_human": False,
            "live_trading_allowed": False,
            "capital_movement_allowed": False,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
        },
        "assembly_rows": rows,
        "global_stop_rule": "No federal, SBIR, RFI, lab, IP, certification, legal, pricing, portal, trading, or capital-impacting final action is authorized by this packet. It is an assembly and review gate only.",
        "source_ledgers": {
            "traction": rel(TRACTION_JSON),
            "authority": rel(AUTHORITY_JSON),
            "docket": rel(DOCKET_JSON),
            "concierge": rel(CONCIERGE_JSON),
            "federal_protocol": rel(FEDERAL_JSON),
            "agency_activation": rel(AGENCY_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
            "submission_conformance": rel(CONFORMANCE_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["assembly_gate_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Agency Submission Assembly Gate - 2026-07-09",
        "",
        f"Purpose: {payload['purpose']}",
        "",
        payload["global_stop_rule"],
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Assembly lanes: `{summary['assembly_lane_count']}`",
        f"- First artifacts present: `{str(summary['first_artifacts_present']).lower()}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Submission conformance status: `{summary['submission_conformance_status']}`",
        f"- Submission conformance covers all current lanes: `{str(summary['submission_conformance_all_current_lanes_covered']).lower()}`",
        f"- Assembly represents every active conformance lane: `{str(summary['assembly_conformance_coverage_clear']).lower()}`",
        f"- Unrepresented active conformance lanes: `{summary['unrepresented_active_conformance_lane_count']}`",
        f"- Active submission candidates: `{summary['active_submission_candidate_count']}`",
        f"- Active argument passes: `{summary['active_argument_pass_count']}`",
        f"- Active argument blocks: `{summary['active_argument_blocked_count']}`",
        f"- Argument gate clear: `{str(summary['argument_gate_clear']).lower()}`",
        f"- Federal protocol status: `{summary['federal_protocol_status']}`",
        f"- Agency activation status: `{summary['agency_activation_status']}`",
        f"- Agency activation items: `{summary['agency_activation_item_count']}`",
        f"- Agency blocked items: `{summary['agency_blocked_item_count']}`",
        f"- Authority lanes: `{summary['authority_lane_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Legal/certification action without human: `{str(summary['legal_or_certification_action_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Assembly gate SHA-256: `{payload['assembly_gate_sha256']}`",
        "",
        "## Package Status Counts",
        "",
    ]
    for key, value in summary["status_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Assembly Rows", ""])
    for row in payload["assembly_rows"]:
        lines.extend(
            [
                f"### {row['priority']}. {row['lane_id']}",
                "",
                f"- Name: {row['name']}",
                f"- Channel: `{row['channel']}`",
                f"- Status: `{row['status']}`",
                f"- Legacy intake status: `{row['legacy_intake_status']}`",
                f"- State source: `{row['state_source']}`",
                f"- Readiness mode: `{row['readiness_mode']}`",
                f"- Package status: `{row['package_status']}`",
                f"- Submission conformance: `{row['submission_conformance_status']}`",
                f"- Argument conformance pass: `{str(row['argument_conformance_pass']).lower()}`",
                f"- Argument criteria passed: `{row['argument_criterion_pass_count']}/{row['argument_criterion_count']}`",
                f"- Urgency: `{row['urgency']}`",
                f"- Action due: `{row['action_due']}`",
                f"- First artifact: `{row['first_artifact']['path']}` sha256=`{row['first_artifact']['sha256']}`",
                f"- Component gates passed: `{row['review_ready_component_count']}/{row['component_count']}`",
                f"- Can prepare internally: `{str(row['can_prepare_internal']).lower()}`",
                f"- External send without human: `{str(row['external_send_allowed_without_human']).lower()}`",
                f"- Final submission without human: `{str(row['final_submission_allowed_without_human']).lower()}`",
                f"- Legal/certification action without human: `{str(row['legal_or_certification_action_allowed_without_human']).lower()}`",
                f"- Required authority: {row['required_authority']}",
                f"- Next human action: {row['next_human_action']}",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Row SHA-256: `{row['assembly_row_sha256']}`",
                "",
                "Components:",
            ]
        )
        for component in row["components"]:
            lines.append(
                f"- `{component['component']}` state=`{component['state']}` gate_passed=`{str(component['gate_passed']).lower()}`"
            )
        lines.extend(["", "Assembly blockers:"])
        for blocker in row["assembly_blockers"]:
            lines.append(f"- {blocker}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    hits = {marker for marker in SENSITIVE_MARKERS if marker in lowered}
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.add(pattern.pattern)
    return sorted(hits)


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive assembly gate markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "assembly_lanes": payload["summary"]["assembly_lane_count"],
                "first_artifacts_present": payload["summary"]["first_artifacts_present"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
