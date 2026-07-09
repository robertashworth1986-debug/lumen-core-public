from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KRAKEN_PAPER_INNOVATION_CONTROL_ROOM.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kraken_paper_innovation_control_room", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_kraken_control_room_is_paper_ready_and_live_blocked():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "kraken_paper_innovation_control_room_v1"
    assert payload["status"] == "KRAKEN_PAPER_INNOVATION_READY_LIVE_BLOCKED"
    assert summary["public_alpha_map_present"] is True
    assert summary["paper_research_card_count"] > 0
    assert summary["global_runtime_paper"] is True
    assert summary["kraken_runtime_paper"] is True
    assert summary["global_live_orders_disabled"] is True
    assert summary["kraken_live_orders_disabled"] is True
    assert summary["live_arm_off"] is True
    assert summary["live_promotion_blocked"] is True
    assert summary["private_api_use_allowed_without_human"] is False
    assert summary["validate_only_allowed_without_action_time_approval"] is False
    assert summary["order_placement_allowed"] is False
    assert summary["capital_movement_allowed"] is False
    assert summary["keys_loaded_by_this_packet"] is False
    assert len(payload["kraken_paper_innovation_sha256"]) == 64


def test_research_cards_are_paper_only_with_hashes():
    module = load_module()
    payload = module.build_payload()

    for card in payload["paper_research_cards"]:
        assert card["allowed_next_step"] == "paper_replay_ticket_only"
        assert "no_live_order" in card["blocked_next_steps"]
        assert "no_private_api_order" in card["blocked_next_steps"]
        assert "no_capital_movement" in card["blocked_next_steps"]
        assert card["paper_research_mode"].startswith("paper_")
        assert card["alpha_edge_score"] != 0
        assert len(card["research_card_sha256"]) == 64


def test_rendered_control_room_has_no_secret_or_live_authority_language():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Kraken Paper Innovation Control Room" in rendered
    assert "Order placement allowed: `false`" in rendered
    assert "Capital movement allowed: `false`" in rendered
    assert "Keys loaded by this packet: `false`" in rendered
    assert "not investment advice" in lowered
    assert "no live trading" in lowered
    assert "password" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
    assert "sk-" not in lowered
