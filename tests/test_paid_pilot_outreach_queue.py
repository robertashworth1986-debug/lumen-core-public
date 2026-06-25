from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PAID_PILOT_OUTREACH_QUEUE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_pilot_outreach_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_paid_pilot_queue_builds_ranked_actionable_rows():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    queue = payload["queue"]

    assert payload["schema"] == "paid_pilot_outreach_queue_v1"
    assert summary["proof_card_count"] == 2
    assert summary["ready_proof_card_count"] == 2
    assert summary["queue_count"] == 12
    assert summary["top_ranked_target"] == "utility_grid_analytics"
    assert summary["unique_lanes"] == ["optimal_curve_transport", "wave_resonance_timing"]
    assert len(summary["queue_chain_sha256"]) == 64

    ranks = [row["rank"] for row in queue]
    assert ranks == list(range(1, 13))
    assert queue[0]["family_id"] == "brachistochrone_descent"
    assert queue[0]["buyer_role"] == "Director of Grid Analytics"
    assert "20-minute technical fit call" in queue[0]["primary_ask"]
    assert "positive frozen replay windows" in queue[0]["proof_line"]
    assert len(queue[0]["row_sha256"]) == 64


def test_paid_pilot_queue_has_both_current_champion_lanes():
    module = load_module()
    payload = module.build_payload()
    rows_by_family = {}
    for row in payload["queue"]:
        rows_by_family.setdefault(row["family_id"], []).append(row)

    assert set(rows_by_family) == {"brachistochrone_descent", "kuramoto_phase_coupling"}
    assert len(rows_by_family["brachistochrone_descent"]) == 6
    assert len(rows_by_family["kuramoto_phase_coupling"]) == 6
    assert any(row["target_segment"] == "datacenter_cooling_optimization" for row in rows_by_family["brachistochrone_descent"])
    assert any(row["target_segment"] == "energy_forecasting" for row in rows_by_family["kuramoto_phase_coupling"])

    for row in payload["queue"]:
        assert row["manual_review_required"] is True
        assert row["send_now_allowed"] is False
        assert row["organization_search_phrase"]
        assert row["measured_outcome"]
        assert row["data_room_artifacts"]


def test_paid_pilot_queue_blocks_bulk_outreach_and_overclaims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    gate = payload["send_gate"]

    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["bulk_email_allowed"] is False
    assert summary["contact_scraping_allowed"] is False
    assert summary["send_without_user_review_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False

    assert gate["manual_reviewed_outreach_allowed"] is True
    assert gate["bulk_email_allowed"] is False
    assert gate["contact_scraping_allowed"] is False
    assert gate["send_without_user_review_allowed"] is False
    assert gate["requires_valid_physical_address"] is True
    assert gate["requires_opt_out_language"] is True
    assert gate["requires_per_recipient_fit_review"] is True

    for row in payload["queue"]:
        blocked = " ".join(row["blocked_positioning"]).lower()
        assert "guaranteed savings" in blocked
        assert "field validated" in blocked
        assert "$10k per frozen delta" in blocked


def test_paid_pilot_queue_markdown_and_csv_are_safe_surfaces(tmp_path):
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    csv_path = tmp_path / "queue.csv"
    module.write_csv(csv_path, payload["queue"])
    csv_text = csv_path.read_text(encoding="utf-8")

    assert "Paid Pilot Outreach Queue" in rendered
    assert "Queue rows: `12`" in rendered
    assert "Bulk email allowed: `false`" in rendered
    assert "Contact scraping allowed: `false`" in rendered
    assert "Fixed-dollar delta claim allowed: `false`" in rendered
    assert "Send now allowed: `false`" in rendered
    assert "utility_grid_analytics" in csv_text
    assert "energy_forecasting" in csv_text
    assert "row_sha256" in csv_text

    rendered_lower = rendered.lower()
    assert "guaranteed alpha" in rendered_lower
    assert "contact scraping" in rendered_lower
    assert ("api" + "_key") not in rendered_lower
    assert "client" + "_sec" + "ret" not in rendered_lower
    assert "live_order_placement" not in rendered_lower
