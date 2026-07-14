from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "hybrid_agent_capability_registry_v1.json"


def test_hybrid_agent_registry_is_bounded_and_complete() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    agents = payload["agents"]
    ids = [row["id"] for row in agents]

    assert payload["schema"] == "lumencore.hybrid_agent_capability_registry.v1"
    assert len(agents) == 10
    assert len(ids) == len(set(ids))
    assert "universal programming-language expertise" in payload["claim_boundary"]
    assert all("autonomy" in row and "external_action" in row for row in agents)

    external = [row for row in agents if row["external_action"]]
    assert [row["id"] for row in external] == ["external_action_operator"]
    assert external[0]["autonomy"] == "human_unlock_required"


def test_registry_has_five_ordered_operational_cadences() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cadences = payload["coordination_cadences"]
    assert [row["order"] for row in cadences] == [1, 2, 3, 4, 5]
    assert [row["id"] for row in cadences] == [
        "event_ingest",
        "artifact_seal",
        "change_validation",
        "action_unlock",
        "release_promotion",
    ]


def test_language_support_requires_a_toolchain_specific_gate() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    adapters = payload["language_adapters"]
    assert all(row["gate"] for row in adapters)
    other = next(row for row in adapters if row["language"] == "Other")
    assert other["status"] == "on_demand_unverified"


def test_all_consequential_actions_are_registered_for_human_unlock() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    actions = set(payload["human_unlock_actions"])
    assert {
        "send_external_message",
        "submit_or_certify_form",
        "place_live_order",
        "move_or_spend_money",
        "execute_legal_document",
        "file_patent_or_other_legal_record",
    }.issubset(actions)
