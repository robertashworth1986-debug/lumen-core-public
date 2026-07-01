from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_live_breadth_panel_provenance_separates_measured_and_reference_rows() -> None:
    module = load_module(
        "live_breadth_value_panel",
        ROOT / "code" / "ops" / "build_live_breadth_value_panel.py",
    )

    summary = module.summarize_evidence_provenance(
        source_rows=[
            {"source": "LIVE_A", "measured_source": True, "estimated_hourly_value_usd": 5.0},
            {"source": "ARCHIVE_B", "measured_source": False, "estimated_hourly_value_usd": 90.0},
        ],
        sector_rows=[
            {"evidence_source": "live_measured_frozen_delta", "total_estimated_hourly_value_usd": 5.0},
            {"evidence_source": "reference_fallback_csv", "total_estimated_hourly_value_usd": 30.0},
        ],
        reference_rows=[{"source": "REF"}],
        fallback_used=True,
    )

    assert summary["primary_evidence_mode"] == "live_measured_delta_rows"
    assert summary["live_measured_source_rows"] == 1
    assert summary["unmeasured_source_rows"] == 1
    assert summary["reference_fallback_used"] is True
    assert summary["live_measured_estimated_hourly_value_usd"] == 5.0
    assert summary["unmeasured_estimated_hourly_value_usd"] == 90.0
    assert summary["reference_fallback_estimated_hourly_value_usd"] == 30.0
    assert "Only rows marked live_measured_source" in summary["claim_boundary"]


def test_registry_rows_with_measured_basis_are_counted_as_measured(tmp_path) -> None:
    module = load_module(
        "live_breadth_value_panel_registry",
        ROOT / "code" / "ops" / "build_live_breadth_value_panel.py",
    )

    registry = tmp_path / "live_source_registry.json"
    registry.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "source": "EIA",
                        "sector": "energy",
                        "status": "LIVE_KEY_PRESENT",
                        "rows": 5862,
                        "evidence_basis": "MEASURED_FILE_MATCH",
                        "dollar_basis": "MEASURED",
                        "enabled": True,
                    },
                    {
                        "source": "NOAA_NCEI",
                        "sector": "weather",
                        "status": "LIVE_KEY_PRESENT",
                        "rows": 0,
                        "evidence_basis": "KEY_ONLY",
                        "dollar_basis": "UNMEASURED",
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = module.build_registry_summary(registry)

    assert summary["enabled_sources"] == 2
    assert summary["measured_sources"] == 1
    assert summary["source_lookup"]["EIA"]["measured"] is True
    assert summary["source_lookup"]["NOAANCEI"]["measured"] is False


def test_multi_asset_pack_promotes_only_live_measured_primary_lanes() -> None:
    module = load_module(
        "multi_asset_frozen_delta_pack",
        ROOT / "code" / "ops" / "BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py",
    )

    lanes = module.build_top_lanes(
        [
            {
                "source": "LIVE_A",
                "sector": "energy",
                "estimated_hourly_value_usd": 12000,
                "estimated_annual_value_usd": 105120000,
                "measured_source": True,
                "primary_live_evidence": True,
                "enabled_source": True,
            },
            {
                "source": "ARCHIVE_BIG",
                "sector": "reference",
                "estimated_hourly_value_usd": 999999,
                "estimated_annual_value_usd": 8759991240,
                "measured_source": True,
                "primary_live_evidence": False,
                "enabled_source": True,
                "provenance": "reference_context",
            },
        ]
    )
    live, context = module.split_lanes_by_provenance(lanes)

    assert [row["source"] for row in live] == ["LIVE_A"]
    assert [row["source"] for row in context] == ["ARCHIVE_BIG"]

    markdown = module.build_markdown(
        {
            "generated_utc": "2026-06-21T00:00:00+00:00",
            "headline": {
                "primary_evidence_mode": "live_measured_delta_rows",
                "live_measured_hourly_value_usd": 12000,
                "live_measured_annual_value_usd": 105120000,
                "live_measured_lane_count": 1,
                "context_only_lane_count": 1,
                "live_measured_ten_k_plus_lane_count": 1,
                "enabled_source_count": 2,
                "measured_source_count": 1,
            },
            "claim_gate": {
                "boundary": "Headline values include only rows marked measured_source and primary_live_evidence."
            },
            "live_measured_top_lanes": live,
            "context_only_lanes": context,
        }
    )

    assert "Live-measured lanes in pack: 1" in markdown
    assert "ARCHIVE_BIG" in markdown
    assert "Context-Only Lanes" in markdown
    assert "Headline values include only rows marked measured_source" in markdown


def test_grant_evidence_delta_pack_prefers_provenance_gated_multi_asset_pack(tmp_path) -> None:
    module = load_module(
        "grant_evidence_delta_pack",
        ROOT / "code" / "ops" / "BUILD_GRANT_EVIDENCE_DELTA_PACK.py",
    )

    pack_path = tmp_path / "multi_asset_frozen_delta_pack_latest.json"
    pack_path.write_text(
        json.dumps(
            {
                "headline": {
                    "primary_evidence_mode": "live_measured_delta_rows",
                    "live_measured_hourly_value_usd": 42.5,
                    "context_only_lane_count": 3,
                },
                "claim_gate": {
                    "boundary": "live-measured only",
                },
                "live_measured_top_lanes": [
                    {
                        "source": "LIVE_A",
                        "sector": "energy",
                        "constraint": "latency",
                        "estimated_hourly_value_usd": 42.5,
                        "estimated_avoided_loss_usd": 10.0,
                        "trust_tier": "measured",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    old_pack = module.MULTI_ASSET_PACK
    try:
        module.MULTI_ASSET_PACK = pack_path
        deltas, summary = module.gather_multi_asset_deltas(tmp_path / "missing.jsonl")
    finally:
        module.MULTI_ASSET_PACK = old_pack

    assert len(deltas) == 1
    assert summary["source_mode"] == "live_measured_multi_asset_pack"
    assert summary["total_hourly_value_usd"] == 42.5
    assert summary["context_only_lane_count"] == 3
    assert summary["claim_boundary"] == "live-measured only"


def test_grant_evidence_pack_freshness_uses_promoted_pack_not_stale_raw_context(tmp_path) -> None:
    module = load_module(
        "grant_evidence_delta_pack_freshness",
        ROOT / "code" / "ops" / "BUILD_GRANT_EVIDENCE_DELTA_PACK.py",
    )

    pack_path = tmp_path / "multi_asset_frozen_delta_pack_latest.json"
    pack_path.write_text(
        json.dumps(
            {
                "headline": {
                    "primary_evidence_mode": "live_measured_delta_rows",
                    "live_measured_hourly_value_usd": 10.0,
                    "context_only_lane_count": 1,
                },
                "claim_gate": {"boundary": "live-measured only"},
                "live_measured_top_lanes": [
                    {
                        "source": "LIVE_A",
                        "sector": "energy",
                        "constraint": "latency",
                        "estimated_hourly_value_usd": 10.0,
                        "estimated_avoided_loss_usd": 3.0,
                        "trust_tier": "measured",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    raw_deltas = tmp_path / "infra_frozen_deltas.jsonl"
    raw_deltas.write_text("{}\n", encoding="utf-8")
    stale_time = time.time() - (48 * 3600)
    os.utime(raw_deltas, (stale_time, stale_time))
    truth_chain = tmp_path / "frozen_delta_truth_chain_latest.json"
    truth_chain.write_text(
        json.dumps({"run_tag": "TEST", "entry_sha256": "abc", "metrics": {}}),
        encoding="utf-8",
    )

    old_values = {
        "MULTI_ASSET_PACK": module.MULTI_ASSET_PACK,
        "INFRA_DELTAS": module.INFRA_DELTAS,
        "TRUTH_CHAIN_LATEST": module.TRUTH_CHAIN_LATEST,
        "SNAPSHOT_LATEST": module.SNAPSHOT_LATEST,
        "FROZEN_LEDGER": module.FROZEN_LEDGER,
        "PACK_ROOT": module.PACK_ROOT,
        "MEMO_PATH": module.MEMO_PATH,
    }
    try:
        module.MULTI_ASSET_PACK = pack_path
        module.INFRA_DELTAS = raw_deltas
        module.TRUTH_CHAIN_LATEST = truth_chain
        module.SNAPSHOT_LATEST = tmp_path / "missing_snapshot.json"
        module.FROZEN_LEDGER = tmp_path / "missing_ledger.jsonl"
        module.PACK_ROOT = tmp_path / "packs"
        module.MEMO_PATH = tmp_path / "missing_memo.md"

        result = module.build_pack(
            ticket={"ticket_id": "TEST", "title": "", "agency": "", "opp_num": "", "channel": "", "submit_url": "", "close_date": ""},
            snapshot={},
            sections={},
            freshness_hours=24,
        )
    finally:
        for name, value in old_values.items():
            setattr(module, name, value)

    assert result["freshness"]["state"] == "fresh"
    assert result["freshness"]["headline_source_mode"] == "live_measured_multi_asset_pack"
    assert result["freshness"]["infra_deltas_age_hours"] >= 48
    assert any("not promoted as headline proof" in note for note in result["freshness"]["notes"])
