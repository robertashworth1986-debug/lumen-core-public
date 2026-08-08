from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "build_live_breadth_value_panel.py"
WORKFLOW = ROOT / ".github" / "workflows" / "live-breadth-claim-gate.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("live_breadth_value_panel", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_metric_readiness_never_recommends_live_capital_or_claims_validation(
    tmp_path: Path,
) -> None:
    module = load_module()
    runtime = tmp_path / "runtime.json"
    controller = tmp_path / "controller.json"
    proof = tmp_path / "proof.json"
    write_json(
        runtime,
        {
            "mode": "paper",
            "allow_live_orders": False,
            "kill_switch": True,
            "max_notional_per_trade_usd": 70,
            "max_daily_loss_usd": 65,
        },
    )
    write_json(
        controller,
        {
            "mode": "SAFE_DRY_RUN",
            "guard": {
                "allow_live": False,
                "live_requested": False,
                "trade_rows_total": 37,
                "portfolio_est_usd": 101.53,
            },
        },
    )
    write_json(
        proof,
        {
            "live_trade_performance": {
                "closed_live_count": 37,
                "win_rate_pct": 0,
                "realized_net_usd": -2.58,
                "max_drawdown_pct": 17.54,
            }
        },
    )

    readiness = module.build_metric_readiness(runtime, controller, proof)
    serialized = json.dumps(readiness).lower()

    assert "first-party diagnostics" in readiness["explanation"]
    assert "do not validate alpha" in readiness["explanation"]
    assert "paper/replay mode" in readiness["thursday_plan"][0]
    assert "non-author execution" in serialized
    for unsafe in (
        "signal quality is validated",
        "fund incremental capital",
        "switch runtime",
        "funded live window",
    ):
        assert unsafe not in serialized


def test_investor_readiness_omits_economic_estimates_and_alpha_claims(
    tmp_path: Path,
) -> None:
    module = load_module()
    report = {
        "generated_utc": "2026-08-08T00:00:00+00:00",
        "headline": {
            "total_estimated_annual_value_usd": 52_000_000_000,
            "translated_source_annual_value_usd": 7_000_000_000,
            "measured_sources": 14,
            "enabled_sources": 17,
            "measured_coverage_pct": 82.35,
            "router_edge_pct": 49.48,
            "harmonic_win_rate_pct": 24.51,
            "kalisha_prediction_score": 50.94,
            "top_sector": "financial_market_infra",
            "top_sector_hourly_value_usd": 3_647_280,
        },
        "metric_readiness": {
            "status": "capital_and_risk_guarded",
            "provisional_label": "provisional_under_guardrails",
            "explanation": "First-party diagnostics; performance is not validated.",
            "closed_live_trades": 37,
            "metrics_stable_threshold": 200,
            "stability_progress_pct": 18.5,
            "provisional_due_to": ["sample_depth_below_institutional_threshold"],
            "provisional_metrics": {},
            "runtime_gates": {"runtime_mode": "paper", "allow_live_orders": False},
            "controller_gates": {"mode": "SAFE_DRY_RUN", "allow_live": False},
            "thursday_plan": ["keep execution in paper/replay mode"],
        },
        "proof_refs": {},
    }

    payload = module.build_investor_metric_readiness_payload(
        report,
        tmp_path,
        tmp_path / "panel.json",
        tmp_path / "panel-tagged.json",
    )
    markdown = module.render_investor_metric_readiness_markdown(payload)
    signal = payload["summary"]["signal_evidence"]

    assert signal["economic_estimates_included"] is False
    assert signal["performance_validated"] is False
    assert "annual_value_usd" not in signal
    assert "top_sector_hourly_value_usd" not in signal
    assert "52,000,000,000" not in markdown
    assert "7,000,000,000" not in markdown
    assert "already proving" not in markdown.lower()
    assert "funded metric" not in markdown.lower()


def test_current_planning_docs_retire_the_unfrozen_29_25_target() -> None:
    paths = (
        ROOT / "docs" / "CURRENT_PROOF_PROMOTION_BACKLOG.md",
        ROOT / "docs" / "LUMENCORE_CURRENT_PROOF_STATUS_2026-07-09.md",
        ROOT / "docs" / "EVTIT_LUMENCORE_BUILD_SCOPE.md",
        ROOT / "docs" / "NEXT_ACTIONS_BOARD.md",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()

    assert "retired as a current-state claim" in combined
    assert "never frozen" in combined
    assert "not current proof" in combined
    assert "dataset fitness" in combined
    assert "numeric breadth headline" in combined


def test_live_breadth_claim_gate_runs_the_exact_focused_suite() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Live Breadth Claim Gate" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in workflow
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in workflow
    assert "pytest==9.1.0" in workflow
    for test_path in (
        "tests/test_public_live_breadth_provenance_gate.py",
        "tests/test_public_visibility_packet.py",
        "tests/test_public_support_readiness_packet.py",
        "tests/test_live_breadth_claim_safety.py",
        "tests/test_canonical_surface_design.py",
    ):
        assert test_path in workflow
