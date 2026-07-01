from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LOCAL_ICLOUD_EVIDENCE_INTAKE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("local_icloud_evidence_intake", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_intake_includes_requested_historical_roots():
    module = load_module()
    roots = {str(path).replace("\\", "/") for path in module.SCAN_ROOTS}

    for expected in [
        "C:/WhiteHole",
        "C:/WhiteHoleLab",
        "C:/Users",
        "C:/LumenLab_Demo_Pack",
        "C:/LumenMacro",
        "C:/LumenOrchestrator",
        "C:/NovaCore",
        "C:/LumenFinanceLab",
        "C:/LumenHybrid",
        "C:/LumenLab",
    ]:
        assert expected in roots


def test_valuation_and_benchmark_artifacts_are_candidates_not_money_claims():
    module = load_module()
    categories, score = module.classify(Path("C:/LumenLab/value_leaderboard_benchmark_annual_value.json"))

    assert "benchmark_evidence" in categories
    assert "valuation_broadening" in categories
    assert score >= 8
    assert (
        module.recommended_use(categories, Path("C:/LumenLab/value_leaderboard_benchmark_annual_value.json"))
        == "usable_as_candidate_value_signal_after_replay_and_claim_gate"
    )

    bridge = module.valuation_bridge(
        [
            {
                "root": "C:/LumenLab",
                "path": "C:/LumenLab/value_leaderboard_benchmark_annual_value.json",
                "categories": categories,
                "score": score,
                "bytes": 100,
                "last_write_utc": "2026-06-22T00:00:00+00:00",
                "recommended_use": "usable_as_candidate_value_signal_after_replay_and_claim_gate",
                "grant_lanes": ["valuation_broadening", "benchmark_reproduction"],
            }
        ]
    )

    assert bridge["candidate_count"] == 1
    assert "No realized revenue" in bridge["blocked_claims"][0]


def test_write_outputs_creates_dashboard_and_docs_feeds(tmp_path, monkeypatch):
    module = load_module()

    out_json = tmp_path / "out" / "local_icloud_evidence_intake_latest.json"
    dash_json = tmp_path / "dashboard" / "local_icloud_evidence_intake.json"
    md_out = tmp_path / "grants" / "LOCAL_ICLOUD_EVIDENCE_INTAKE_2026-06-21.md"
    docs_out = tmp_path / "docs" / "ROOT_EVIDENCE_VALUATION_BRIDGE_2026-06-22.md"

    monkeypatch.setattr(module, "JSON_OUT", out_json)
    monkeypatch.setattr(module, "DASHBOARD_JSON", dash_json)
    monkeypatch.setattr(module, "MD_OUT", md_out)
    monkeypatch.setattr(module, "DOCS_OUT", docs_out)

    payload = {
        "schema": "local_icloud_evidence_intake_v1",
        "generated_utc": "2026-06-22T00:00:00+00:00",
        "roots": [],
        "summary": {"records": 0, "by_recommended_use": {}, "by_grant_lane": {}},
        "top_records": [],
        "valuation_bridge": {
            "candidate_count": 0,
            "safe_use": [],
            "blocked_claims": [],
            "top_candidates": [],
        },
        "records": [],
    }

    module.write_outputs(payload)

    assert json.loads(out_json.read_text(encoding="utf-8"))["schema"] == "local_icloud_evidence_intake_v1"
    assert json.loads(dash_json.read_text(encoding="utf-8"))["schema"] == "local_icloud_evidence_intake_v1"
    assert "Valuation Bridge" in md_out.read_text(encoding="utf-8")
    assert "Valuation Bridge" in docs_out.read_text(encoding="utf-8")
