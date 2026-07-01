from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_EVIDENCE_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_evidence_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_measured_rows_promote_only_hashable_live_sources() -> None:
    module = load_module()
    payload = {
        "provider_rows": [
            {
                "source": "EIA",
                "sector": "energy",
                "status": "MEASURED",
                "rows": 2,
                "measured": True,
                "snapshot_json": "data/live_measured/eia/eia.json",
                "snapshot_sha256": "abc123",
            },
            {
                "source": "PAPER_ONLY",
                "sector": "market_data",
                "status": "MEASURED",
                "rows": 4,
                "measured": True,
                "snapshot_json": "paper.json",
                "snapshot_sha256": "",
            },
            {
                "source": "NREL",
                "sector": "energy_lab",
                "status": "PROBE_FAILED_OR_THIN",
                "rows": 0,
                "measured": False,
                "snapshot_sha256": "def456",
            },
        ]
    }

    promoted = module.measured_rows(payload)

    assert [row["source"] for row in promoted] == ["EIA"]
    assert promoted[0]["claim_use"] == "LIVE_MEASURED_REFERENCE"


def test_blocked_rows_excludes_measured_sources() -> None:
    module = load_module()
    payload = {
        "provider_rows": [
            {"source": "EIA", "sector": "energy", "status": "MEASURED", "rows": 1, "measured": True},
            {"source": "EPA_AQS", "sector": "air_quality", "status": "PROBE_FAILED_OR_THIN", "rows": 0, "measured": False},
        ]
    }

    blocked = module.blocked_rows(payload)

    assert [row["source"] for row in blocked] == ["EPA_AQS"]
    assert blocked[0]["claim_use"] == "EXCLUDED_UNTIL_MEASURED"


def test_geometry_gate_keeps_claim_readiness_false() -> None:
    module = load_module()
    payload = {
        "summary": {
            "lane_count": 12,
            "family_count": 75,
            "live_source_measured_count": 18,
            "total_measured_rows": 418,
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
        },
        "priority_queue": [
            {
                "lane": "time_series_model_routing",
                "proof_build_priority_rank": 1,
                "live_wiring_score": 123.4,
                "lane_ready_for_live_replay_build": True,
                "ready_for_live_geometry_claim": False,
                "ready_for_real_dollar_claim": False,
                "proof_value_champion": {"label": "Fractal Brownian surface"},
            }
        ],
    }

    gate = module.geometry_gate(payload)

    assert gate["classification"] == "LIVE_WIRED_NOT_CLAIM_READY"
    assert gate["summary"]["ready_for_live_geometry_claim"] is False
    assert gate["lanes"][0]["ready_for_live_replay_build"] is True
