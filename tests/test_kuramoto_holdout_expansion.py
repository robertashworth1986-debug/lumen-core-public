from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_HOLDOUT_EXPANSION.py"
REPRO_AUDIT = ROOT / "evidence" / "reproducibility" / "kuramoto_public_reproducibility_audit_20260721.json"


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_holdout_expansion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_manifest(tmp_path: Path, count: int = 20) -> dict:
    systems = ("energy_grid", "market_data", "macro_rates_labor", "weather")
    rows = []
    for index in range(count):
        source = tmp_path / f"source_{index:02d}.csv"
        values = [f"{step},{(index + 1) * 0.5 + step * 0.07 + (step % 5) * 0.11}" for step in range(160)]
        source.write_text("step,value\n" + "\n".join(values) + "\n", encoding="utf-8")
        rows.append(
            {
                "source_path": str(source),
                "system": systems[index % len(systems)],
                "estimated_rows": 50_000 + index,
                "lane": "wave_resonance_timing",
                "candidate_family": "kuramoto_phase_coupling",
                "baseline_family": "kalman_filter",
                "ready_for_benchmark": True,
            }
        )
    return {"schema": "geometry_live_source_manifest_v1", "manifest_rows": rows}


def test_kuramoto_holdout_expansion_runs_20_plus_source_conditioned_routes(tmp_path):
    module = load_module()
    payload = module.build_payload(manifest=fixture_manifest(tmp_path), max_routes=20, sample_limit=750)
    summary = payload["summary"]

    assert payload["schema"] == "kuramoto_holdout_expansion_v1"
    assert summary["candidate"] == "kuramoto_phase_coupling"
    assert summary["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 20
    assert summary["estimated_rows_replayed"] > 0
    assert summary["numeric_samples_read"] > 0
    assert summary["input_integrity_passed"] is True
    assert summary["missing_source_file_count"] == 0
    assert summary["fallback_source_count"] == 0
    assert summary["git_tracked_source_count"] == 0
    assert summary["public_clean_checkout_replay_ready"] is False
    assert summary["independent_reproduction_completed"] is False
    assert 0.0 <= summary["win_rate_vs_kalman"] <= 1.0
    assert 0.0 <= summary["wilson_95_win_rate_lower"] <= summary["wilson_95_win_rate_upper"] <= 1.0
    assert len(summary["holdout_chain_sha256"]) == 64


def test_kuramoto_holdout_expansion_hashes_sources_and_keeps_gates_closed(tmp_path):
    module = load_module()
    payload = module.build_payload(manifest=fixture_manifest(tmp_path), max_routes=20, sample_limit=750)
    gates = payload["claim_gates"]

    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert gates["buyer_authorized_field_pilot_required"] is True

    for row in payload["holdout_results"]:
        assert row["lane"] == "wave_resonance_timing"
        assert row["candidate_family"] == "kuramoto_phase_coupling"
        assert row["named_baseline"] == "kalman_filter"
        assert len(row["source_sha256"]) == 64
        assert row["source_sha256_is_full_file"] is True
        assert row["source_sha256_scope_bytes"] == row["source_size_bytes"]
        assert row["source_available"] is True
        assert row["evidence_eligible"] is True
        assert row["source_path_publication_allowed"] is False
        assert row["source_ref"].startswith("source://")
        assert len(row["holdout_sha256"]) == 64
        assert row["delta_vs_kalman"] is not None


def test_kuramoto_holdout_markdown_is_reviewer_safe(tmp_path):
    module = load_module()
    payload = module.build_payload(manifest=fixture_manifest(tmp_path), max_routes=20, sample_limit=750)
    public = module.build_public_projection(payload)
    rendered = module.render_markdown(public)
    dumped = json.dumps(public).lower()

    assert "Kuramoto Holdout Expansion" in rendered
    assert "not field validation" in rendered
    assert "field_validation_claim_allowed: `false`" in rendered
    assert "real_dollar_savings_claim_allowed: `false`" in rendered
    assert "public clean-checkout replay ready: `false`" in rendered.lower()
    assert "private_source_paths_included" in dumped
    assert str(tmp_path).lower().replace("\\", "/") not in dumped.replace("\\", "/")
    assert all("source_path" not in row for row in public["holdout_results"])
    assert "guaranteed" not in dumped
    assert "money printer" not in dumped


def test_kuramoto_holdout_fails_closed_without_manifest_rows():
    module = load_module()
    payload = module.build_payload(
        manifest={"schema": "geometry_live_source_manifest_v1", "manifest_rows": []},
        max_routes=20,
        sample_limit=750,
    )
    summary = payload["summary"]

    assert summary["route_count"] == 0
    assert summary["holdout_count"] == 0
    assert summary["passes_internal_20_holdout_gate"] is False
    assert summary["ready_for_buyer_authorized_field_replay_request"] is False
    assert summary["public_clean_checkout_replay_ready"] is False


def test_tracked_geometry_replay_docs_do_not_publish_workstation_paths():
    documents = (
        ROOT / "docs" / "KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md",
        ROOT / "docs" / "GEOMETRY_READY_SOURCE_REPLAY_2026-06-26.md",
    )
    for path in documents:
        text = path.read_text(encoding="utf-8").lower().replace("\\", "/")
        assert "c:/users/" not in text
        assert "c:/lumatrader/" not in text
        assert "e:/lumaproofvault/" not in text


def test_public_reproducibility_audit_stays_fail_closed():
    audit = json.loads(REPRO_AUDIT.read_text(encoding="utf-8"))
    local = audit["local_cached_manifest_probe"]
    validation = audit["validation_state"]

    assert audit["schema"] == "kuramoto_public_reproducibility_audit_v1"
    assert local["configured_route_count"] == 24
    assert local["evidence_eligible_holdout_count"] == 5
    assert local["excluded_holdout_count"] == 19
    assert local["git_tracked_eligible_source_count"] == 0
    assert local["input_integrity_passed"] is False
    assert local["public_clean_checkout_replay_ready"] is False
    assert validation["independent_reproduction_completed"] is False
    assert validation["external_validation_completed"] is False
    assert validation["field_validation_claim_allowed"] is False
