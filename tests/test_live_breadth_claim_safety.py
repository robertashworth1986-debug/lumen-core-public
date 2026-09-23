from __future__ import annotations

import importlib.util
import hashlib
import csv
import json
from pathlib import Path

import pytest


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
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "pytest==9.1.0" in workflow
    for test_path in (
        "tests/test_public_live_breadth_provenance_gate.py",
        "tests/test_public_visibility_packet.py",
        "tests/test_public_support_readiness_packet.py",
        "tests/test_live_breadth_claim_safety.py",
        "tests/test_live_breadth_governance_worklist.py",
        "tests/test_public_live_breadth_manifest.py",
        "tests/test_canonical_surface_design.py",
    ):
        assert test_path in workflow


def load_producer(filename: str):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "code" / "ops" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def model_row(source="sample", gain=10, **overrides):
    return {
        "source": source, "sector": "cooling", "constraint": "repeat_work",
        "generated_utc": "2026-09-22T12:00:00Z",
        "baseline_loss_rate_usd_per_hour": 100,
        "optimization_gain_pct": gain,
        **overrides,
    }


@pytest.mark.parametrize("gain,reported,modeled", [(-10, 500, -10), (0, 500, 0), (10, -5, 10)])
def test_signed_models_preserve_losses_and_conflicts_without_savings(gain, reported, modeled):
    module = load_module()
    sectors, rows = module.build_sector_rollup(
        [model_row(gain=gain, estimated_hourly_value_usd=reported)],
        {"SAMPLE": {"enabled": True, "measured": True}},
    )
    row = rows[0]
    assert row["modeled_hourly_value_usd"] == modeled
    assert row["reported_estimated_hourly_value_usd"] == reported
    assert row["reported_hourly_value_conflict"] is True
    assert row["estimated_annual_value_usd"] is None
    assert row["primary_live_evidence"] is False
    assert row["recommended_action"] == "review_invalid_input"
    assert sectors[0]["total_estimated_annual_value_usd"] is None


@pytest.mark.parametrize("gain", [None, float("nan"), float("inf"), True, "not measured"])
def test_invalid_or_missing_gain_cannot_be_replaced_by_reported_dollars(gain):
    module = load_module()
    sectors, rows = module.build_sector_rollup(
        [model_row(gain=gain, estimated_hourly_value_usd=900)], {}
    )
    assert rows[0]["modeled_annual_value_usd"] is None
    assert sectors[0]["modeled_annual_value_usd"] is None
    assert rows[0]["estimated_annual_value_usd"] is None
    json.dumps([sectors, rows], allow_nan=False)


def test_registry_intake_flags_do_not_become_measured_economics(tmp_path):
    module = load_module()
    source = tmp_path / "registry.json"
    write_json(source, {"sources": [
        {"source": "disabled", "enabled": False, "measured": False, "status": "LIVE", "rows": 100},
        {"source": "intake", "enabled": True, "measured": True, "translated_value": {"year": 123456}},
    ]})
    summary = module.build_registry_summary(source)
    assert summary["enabled_sources"] == 1
    assert summary["measured_sources"] == 1
    assert summary["translated_annual_value_usd"] is None
    assert summary["reported_translated_annual_value_usd"] == 123456


def panel_inputs(tmp_path, rows):
    frozen = tmp_path / "frozen.jsonl"
    frozen.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    empty = tmp_path / "empty.json"
    write_json(empty, {})
    reference = tmp_path / "reference.csv"
    reference.write_text("source,sector,optimization_gain_pct,estimated_hourly_value_usd\n", encoding="utf-8")
    return dict(
        stack_root=tmp_path, workspace_root=tmp_path,
        frozen_deltas_path=frozen, optimization_report_path=empty,
        top_sectors_csv_path=reference, source_registry_path=empty,
        lumascout_summary_path=empty, runtime_control_path=empty,
        controller_status_path=empty, vps_growth_proof_path=empty,
        evidence_roots=[], top_n=1,
    )


def test_full_panel_preserves_nonwins_and_unknowns_beyond_display_limit(tmp_path):
    module = load_module()
    report, csv_rows = module.build_panel(**panel_inputs(tmp_path, [
        model_row("positive", 10), model_row("negative", -20), model_row("zero", 0),
    ]))
    assert len(report["source_rows"]) == 3
    assert sorted(row["optimization_gain_pct"] for row in report["source_rows"]) == [-20, 0, 10]
    assert report["headline"]["modeled_annual_value_usd"] == -87600
    assert report["headline"]["total_estimated_annual_value_usd"] is None
    assert report["claim_gate"]["accepted_annual_savings_usd"] is None
    assert report["lanes"]["live_source_translation"]["translated_annual_value_usd"] is None
    assert csv_rows[0]["total_estimated_annual_value_usd"] is None
    assert "overhead" in csv_rows[0]["model_boundary"]
    json.dumps(report, allow_nan=False)


def test_panel_reference_fallback_does_not_recreate_savings():
    module = load_module()
    rows = module.fallback_sectors_from_reference([
        {"source": "old", "sector": "cooling", "estimated_hourly_value_usd": 12345}
    ])
    assert rows[0]["total_estimated_annual_value_usd"] is None
    assert rows[0]["modeled_annual_value_usd"] is None
    assert rows[0]["recommended_action"] == "review_invalid_input"


@pytest.mark.parametrize("flags", [False, True, "true"])
def test_multiasset_cannot_promote_self_asserted_flags_or_legacy_dollar_values(flags):
    module = load_producer("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py")
    row = model_row(gain=-5, measured_source=flags, primary_live_evidence=flags,
                    estimated_hourly_value_usd=10000, estimated_annual_value_usd=87600000)
    payload = module.build_payload({"source_rows": [row], "claim_gate": {"public_economic_value_claim_allowed": flags}}, [])
    lane = payload["top_lanes"][0]
    assert lane["modeled_annual_value_usd"] == -43800
    assert lane["estimated_annual_value_usd"] is None
    assert lane["reported_estimated_annual_value_usd"] == 87600000
    assert lane["primary_live_evidence"] is False
    assert payload["headline"]["estimated_annual_value_usd"] is None
    assert payload["claim_gate"]["public_economic_value_claim_allowed"] is False
    markdown = module.build_markdown(payload)
    assert "Accepted annual savings: **UNKNOWN**" in markdown
    assert "-43,800.00" in markdown


def test_panel_to_pack_preserves_null_and_distinguishes_zero(tmp_path):
    panel = load_module()
    multi = load_producer("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py")
    report, _ = panel.build_panel(**panel_inputs(tmp_path, [model_row("zero", 0), model_row("unknown", None)]))
    payload = multi.build_payload(report, [])
    assert payload["headline"]["estimated_annual_value_usd"] is None
    assert payload["headline"]["modeled_annual_value_usd"] is None
    lanes = {row["source"]: row for row in payload["top_lanes"]}
    assert lanes["zero"]["modeled_annual_value_usd"] == 0
    assert lanes["unknown"]["modeled_annual_value_usd"] is None


@pytest.mark.parametrize("filename,function", [
    ("build_live_breadth_value_panel.py", "pick_latest_frozen_deltas"),
    ("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py", "pick_latest_rows"),
])
def test_latest_frozen_rows_use_utc_and_reject_ambiguous_conflicts(filename, function):
    module = load_producer(filename)
    choose = getattr(module, function)
    older = model_row(gain=20, generated_utc="2026-09-22T12:00:00+02:00")
    newer = model_row(gain=-5, generated_utc="2026-09-22T11:00:00Z")
    assert choose([newer, older])[0]["optimization_gain_pct"] == -5
    assert len(choose([newer, newer])) == 1
    with pytest.raises(ValueError, match="Conflicting"):
        choose([newer, dict(newer, optimization_gain_pct=20)])
    with pytest.raises(ValueError, match="timezone"):
        choose([dict(newer, generated_utc="2026-09-22T11:00:00")])


@pytest.mark.parametrize("filename", ["build_live_breadth_value_panel.py", "BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py"])
def test_duplicate_or_malformed_frozen_rows_fail_instead_of_dropping_a_nonwin(tmp_path, filename):
    module = load_producer(filename)
    source = tmp_path / "deltas.jsonl"
    source.write_text('{"optimization_gain_pct":-10,"optimization_gain_pct":10}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        module.load_jsonl(source)
    source.write_text(json.dumps(model_row(gain=10)) + "\n{broken negative row\n", encoding="utf-8")
    with pytest.raises(ValueError):
        module.load_jsonl(source)


def chain_inputs(tmp_path, monkeypatch):
    module = load_producer("BUILD_FROZEN_DELTA_TRUTH_CHAIN.py")
    for name in ("LIVE_PANEL", "MASTER_VAL", "READINESS", "PUBLIC_TRUTH", "GRANTS_QUEUE", "JOBS_QUEUE", "OPP_TRACKER", "EXEC_EVENTS_A", "EXEC_EVENTS_B"):
        monkeypatch.setattr(module, name, tmp_path / (name.lower() + ".json"))
    return module


def test_truth_chain_never_uses_valuation_maximum_to_reopen_unknown_savings(tmp_path, monkeypatch):
    module = chain_inputs(tmp_path, monkeypatch)
    write_json(module.LIVE_PANEL, {"headline": {"total_estimated_annual_value_usd": None,
        "modeled_annual_value_usd": -200, "measured_sources": 1, "enabled_sources": 2}})
    write_json(module.MASTER_VAL, {"inputs": {"annual_value_signal_usd": 900000000, "measured_sources": 99},
                                   "valuation": {"master_valuation_proxy_usd": 8000000000}})
    state = module.collect_state()
    metrics = state["metrics"]
    assert metrics["annual_value_signal_usd"] is None
    assert metrics["valuation_proxy_usd"] is None
    assert metrics["modeled_annual_value_usd"] == -200
    assert metrics["measured_sources"] == 1
    assert metrics["reported_economic_context"]["master_valuation_annual_value_usd"] == 900000000
    assert metrics["public_economic_value_claim_allowed"] is False
    assert "Accepted annual savings: UNKNOWN" in module.build_markdown_report(state)


def test_truth_chain_deltas_skip_unknown_nonfinite_and_boolean_values():
    module = load_producer("BUILD_FROZEN_DELTA_TRUTH_CHAIN.py")
    result = module.build_numeric_deltas(
        {"savings": None, "model": -8, "missing": 20, "flag": True, "invalid": float("inf")},
        {"savings": 400, "model": 5, "flag": False, "invalid": 3},
    )
    assert result == {"model": -13}


def test_truth_chain_hashes_the_same_bytes_it_parsed(tmp_path, monkeypatch):
    module = chain_inputs(tmp_path, monkeypatch)
    original = b'{"headline":{"modeled_annual_value_usd":-50}}'
    module.LIVE_PANEL.write_bytes(original)
    read_bytes = Path.read_bytes
    def changing_source(path):
        data = read_bytes(path)
        if path == module.LIVE_PANEL:
            path.write_bytes(b'{"headline":{"modeled_annual_value_usd":999}}')
        return data
    monkeypatch.setattr(Path, "read_bytes", changing_source)
    state = module.collect_state()
    assert state["metrics"]["modeled_annual_value_usd"] == -50
    assert state["source_hashes"]["live_breadth_value_panel_latest"] == hashlib.sha256(original).hexdigest()
    assert state["source_bytes"]["live_breadth_value_panel_latest"] == len(original)


def test_truth_chain_rejects_duplicate_current_input_without_touching_ledger(tmp_path, monkeypatch):
    module = chain_inputs(tmp_path, monkeypatch)
    module.LIVE_PANEL.write_text('{"headline":{},"headline":{"total_estimated_annual_value_usd":123}}', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid frozen-chain input"):
        module.collect_state()


def test_multiasset_cli_exports_unknown_cells_and_negative_model(tmp_path, monkeypatch):
    module = load_producer("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py")
    monkeypatch.setattr(module, "OPS_OUT", tmp_path / "output")
    monkeypatch.setattr(module, "LIVE_BREADTH_PANEL", tmp_path / "panel.json")
    monkeypatch.setattr(module, "INFRA_FROZEN_DELTAS", tmp_path / "ledger.jsonl")
    write_json(module.LIVE_BREADTH_PANEL, {"source_rows": [model_row(gain=-5)]})
    assert module.main() == 0
    payload = json.loads((module.OPS_OUT / "multi_asset_frozen_delta_pack_latest.json").read_text())
    assert payload["headline"]["estimated_annual_value_usd"] is None
    with (module.OPS_OUT / "multi_asset_frozen_delta_pack_latest.csv").open(newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["estimated_annual_value_usd"] == ""
    assert float(row["modeled_annual_value_usd"]) == -43800


def test_new_chain_entry_preserves_legacy_snapshot_without_false_savings_delta(tmp_path, monkeypatch):
    module = chain_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OUT_OPS", tmp_path / "ops")
    monkeypatch.setattr(module, "CHAIN_DIR", tmp_path / "chain")
    monkeypatch.setattr(module, "DELTA_DIR", module.CHAIN_DIR / "deltas")
    for name in ("LEDGER_PATH", "LEDGER_LATEST_JSON", "SNAPSHOT_LATEST_JSON", "VERIFY_LATEST_JSON", "VERIFY_LATEST_MD", "HEARTBEAT_LATEST_JSON"):
        monkeypatch.setattr(module, name, module.CHAIN_DIR / getattr(module, name).name)
    module.CHAIN_DIR.mkdir()
    legacy = {"metrics": {"annual_value_signal_usd": 9000000, "valuation_proxy_usd": 80000000}}
    write_json(module.SNAPSHOT_LATEST_JSON, legacy)
    write_json(module.LIVE_PANEL, {"headline": {"modeled_annual_value_usd": -123}})
    assert module.build_chain(strict=True) == 0
    delta = json.loads((module.DELTA_DIR / "frozen_delta_live_surface_latest.json").read_text())
    assert delta["previous"]["annual_value_signal_usd"] == 9000000
    assert delta["current"]["annual_value_signal_usd"] is None
    assert "annual_value_signal_usd" not in delta["numeric_delta"]
    assert delta["public_economic_value_claim_allowed"] is False
    assert module.verify_chain(module.LEDGER_PATH)["status"] == "PASS"
