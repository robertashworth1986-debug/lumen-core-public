from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_BRANCHING_LIVE_BREADTH_REPLAY.py"


def load_module():
    spec = importlib.util.spec_from_file_location("branching_live_breadth_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def seed_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    live = tmp_path / "live_breadth.json"
    queue = tmp_path / "queue.json"
    intake = tmp_path / "intake.json"
    write_json(
        live,
        {
            "source_rows": [
                {
                    "primary_live_evidence": True,
                    "source": "EIA",
                    "sector": "power_grid",
                    "constraint": "default",
                    "evidence_source": "infra_frozen_delta_ledger",
                    "provenance": "live_measured_source",
                    "baseline_loss_rate_usd_per_hour": 125000,
                    "optimization_gain_pct": 3.1,
                    "estimated_hourly_value_usd": 3875,
                    "estimated_annual_value_usd": 33945000,
                    "generated_utc": "2026-06-03T15:21:27+00:00",
                },
                {
                    "primary_live_evidence": True,
                    "source": "NREL",
                    "sector": "power_grid",
                    "constraint": "default",
                    "evidence_source": "infra_frozen_delta_ledger",
                    "provenance": "live_measured_source",
                    "baseline_loss_rate_usd_per_hour": 125000,
                    "optimization_gain_pct": 1.35,
                    "estimated_hourly_value_usd": 1687.5,
                    "estimated_annual_value_usd": 14782500,
                    "generated_utc": "2026-06-03T15:21:27+00:00",
                },
                {
                    "primary_live_evidence": False,
                    "source": "ISO_NE",
                    "sector": "energy_grid",
                    "constraint": "frequency_stability",
                    "evidence_source": "infra_frozen_delta_ledger",
                    "provenance": "unmeasured_or_registry_unmatched_source",
                    "baseline_loss_rate_usd_per_hour": 1150000,
                    "optimization_gain_pct": 91.2,
                    "estimated_hourly_value_usd": 1598960,
                    "estimated_annual_value_usd": 14006889600,
                    "generated_utc": "2026-06-16T15:05:39+00:00",
                },
            ]
        },
    )
    write_json(
        queue,
        {
            "top_next_runs": [
                {
                    "family_id": "crack_propagation_paths",
                    "lane": "branching_transport",
                    "target_live_sources": ["EIA", "NREL", "ISO_NE"],
                    "live_measured_sources": ["EIA", "NREL"],
                    "baselines": ["minimum_spanning_tree", "steiner_approximation", "min_cost_flow"],
                    "metrics": ["delivered_flow", "energy_proxy", "material_proxy", "failure_tolerance", "runtime_ms"],
                }
            ]
        },
    )
    write_json(
        intake,
        {
            "valuation_bridge": {
                "candidate_count": 3,
                "top_candidates": [
                    {"path": "C:/WhiteHole/_SOURCE_OF_TRUTH/ARTIFACTS/ROI_CANON.sha256.txt"}
                ],
            }
        },
    )
    return live, queue, intake


def test_build_payload_runs_live_breadth_branching_replay_without_overclaiming(tmp_path, monkeypatch):
    module = load_module()
    live, queue, intake = seed_inputs(tmp_path)
    monkeypatch.setattr(module, "LIVE_BREADTH", live)
    monkeypatch.setattr(module, "GEOMETRY_QUEUE", queue)
    monkeypatch.setattr(module, "LOCAL_INTAKE", intake)

    payload = module.build_payload(run_tag="TEST")

    assert payload["schema"] == "branching_live_breadth_replay_v1"
    assert payload["family_id"] == "crack_propagation_paths"
    assert payload["lane"] == "branching_transport"
    assert payload["source_summary"]["live_source_manifest"]["sources"] == ["EIA", "NREL"]
    assert payload["source_summary"]["live_source_manifest"]["sha256"]
    assert payload["source_summary"]["live_measured_estimated_annual_value_usd"] == 48_727_500
    assert payload["validation_replay"]["scenario_manifest"]["scenario_count"] == 10
    assert payload["context_only_replay"]["scenario_manifest"]["scenario_count"] == 2

    strategies = {row["strategy"] for row in payload["validation_replay"]["leaderboard"]}
    assert {"minimum_spanning_tree", "steiner_approximation", "min_cost_flow"}.issubset(strategies)
    assert "crack_propagation_paths" in strategies

    gate = payload["promotion_gate"]
    assert gate["bounded_live_breadth_replay_complete"] is True
    assert gate["ready_for_real_dollar_claim"] is False
    assert gate["field_validation"] is False
    assert gate["grant_or_portal_submit_proof"] is False
    assert "minimum three representative live/authorized source families" in gate["requirements_missing"]
    assert "not raw operational topology" in payload["evidence_boundary"]
    assert payload["historical_valuation_bridge"]["candidate_count"] == 3


def test_write_outputs_creates_hashable_run_packet(tmp_path, monkeypatch):
    module = load_module()
    live, queue, intake = seed_inputs(tmp_path)
    monkeypatch.setattr(module, "LIVE_BREADTH", live)
    monkeypatch.setattr(module, "GEOMETRY_QUEUE", queue)
    monkeypatch.setattr(module, "LOCAL_INTAKE", intake)
    monkeypatch.setattr(module, "RUN_ROOT", tmp_path / "runs")
    monkeypatch.setattr(module, "OUT_JSON", tmp_path / "latest.json")
    monkeypatch.setattr(module, "DASHBOARD_JSON", tmp_path / "dashboard.json")
    monkeypatch.setattr(module, "OUT_MD", tmp_path / "report.md")

    written = module.write_outputs(module.build_payload(run_tag="TEST_RUN"))

    assert (tmp_path / "runs" / "TEST_RUN" / "summary.json").exists()
    assert (tmp_path / "runs" / "TEST_RUN" / "manifest.sha256.json").exists()
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["run_tag"] == "TEST_RUN"
    assert json.loads((tmp_path / "dashboard.json").read_text(encoding="utf-8"))["run_tag"] == "TEST_RUN"
    assert "Branching Live-Breadth Replay" in (tmp_path / "report.md").read_text(encoding="utf-8")
    assert written["artifact_manifest"]["schema"] == "branching_live_breadth_replay_manifest_v1"
