from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_INVESTOR_MISSION_CONTROL_PACK.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "investor_mission_control", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_review_only_grant_candidate_omits_private_autofill_content():
    module = load_module()
    fit_pack = {
        "opportunities": [
            {
                "opp_num": "SYNTH-001",
                "title": "Synthetic Review Candidate",
                "agency": "Synthetic Agency",
                "close_date": "2099-01-01",
                "submit_url": "https://example.invalid/submit",
                "fit_status": "FIT_LIKELY",
                "source_channel": "grants_gov",
                "award_ceiling_usd": 1000000,
            }
        ]
    }
    queue = [
        {
            "ticket_id": "PRIVATE-TICKET",
            "opportunity": {"opp_num": "SYNTH-001"},
            "organization": {"ein": "private"},
            "contacts": {"email": "private@example.invalid"},
            "abstract": "private proposal content",
        }
    ]

    candidate = module.select_autonomous_grant_live_fill(fit_pack, queue)

    assert candidate["status"] == "REVIEW_ONLY_OFFICIAL_SOURCE_REVERIFY_REQUIRED"
    assert candidate["grant_selected_automatically"] is False
    assert candidate["autofill_packet_ready"] is False
    assert candidate["submission_authorized"] is False
    assert candidate["deadline_actionable"] is False
    assert candidate["autofill_payload"] == {}
    assert "submit_url" not in candidate["selected_opportunity"]
    rendered = str(candidate)
    assert "private proposal content" not in rendered
    assert "private@example.invalid" not in rendered
    assert "'ein': 'private'" not in rendered


def test_three_minute_pitch_suppresses_legacy_value_and_performance_inputs():
    module = load_module()
    pitch = module.build_three_minute_pitch(
        annual_value_usd=999999999999,
        top_sector="synthetic-sector",
        measured_sources=999,
        enabled_sources=999,
        router_edge_pct=99.9,
        harmonic_win_rate_pct=99.9,
        readiness_status="ready",
        selected_grant_title="Synthetic Grant",
        top_problem="Synthetic Problem",
        grade_a_locks=999,
    )
    text = pitch["full_script"].lower()

    assert pitch["external_share_ready"] is False
    assert pitch["recipient_selected"] is False
    assert pitch["legacy_value_inputs_suppressed"] is True
    assert "$" not in text
    assert "government-grade" not in text
    assert "grade-a" not in text
    assert "autonomous grant" not in text
    assert "valuation" in text
    assert "no valuation" in text


def test_modeled_value_graphic_is_blocked_and_empty():
    module = load_module()
    pack = module.build_3d_graphics_pack(
        {
            "sector_value_matrix": [
                {
                    "sector": "synthetic",
                    "hour": 1000000,
                    "year": 999999999,
                }
            ]
        },
        top_n=10,
    )

    assert pack["status"] == "BLOCKED_FROM_INVESTOR_AND_REVIEWER_USE"
    assert pack["points"] == []
    assert pack["chart_type"] is None
    assert pack["legacy_row_count"] == 1
