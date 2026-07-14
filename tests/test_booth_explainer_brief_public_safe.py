from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
SCRIPT = CODE / "build_booth_explainer_brief.py"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import luma_experience_gateway as gateway  # noqa: E402
from booth_public_contract import (  # noqa: E402
    public_booth_contains_forbidden_value,
    public_booth_projection,
)


SYNTHETIC_TRANSACTION = "OABCDE-FGHIJK-LMNOPQ"
SYNTHETIC_ABSOLUTE_PATH = r"C:\SyntheticPrivate\execution.jsonl"
SYNTHETIC_TAX_IDENTIFIER = "12-3456789"
SYNTHETIC_PATENT_APPLICATION = "12/345,678"
TRANSACTION_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9]{5,}-[A-Z0-9]{5,}-[A-Z0-9]{5,}\b",
    re.IGNORECASE,
)


def load_builder():
    spec = importlib.util.spec_from_file_location("build_booth_explainer_brief_public_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def raw_booth_payload() -> dict:
    event = {
        "timestamp": "2026-01-01T00:00:00Z",
        "txid": SYNTHETIC_TRANSACTION,
        "symbol": "SYNTH",
        "pair": "SYNTHUSD",
        "side": "buy",
        "status": "placed",
        "size_usd": 123.45,
    }
    return {
        "generated_utc": "2026-01-01T01:00:00Z",
        "schema": "luma_booth_explainer_brief_v1",
        "founder_profile": {
            "founder": "Synthetic Founder",
            "ein": SYNTHETIC_TAX_IDENTIFIER,
            "uspto_non_provisional_application": SYNTHETIC_PATENT_APPLICATION,
            "private_identifiers_embedded": True,
        },
        "indexing": {"files_indexed": 7, "roots_present": 2, "roots_total": 3, "scan_capped": False},
        "catalog": {"engine_count": 4, "assets_source_rows": 9, "top_engines": []},
        "live_execution": {
            "heartbeat": {
                "status": "running",
                "reason": "internal detail",
                "symbol": "SYNTH",
                "universe_candidate_count": 5,
                "timestamp_utc": "2026-01-01T00:30:00Z",
            },
            "latest_trade": dict(event),
            "recent_trade_count": 1,
            "recent_trades": [dict(event)],
        },
        "premium_mirror": {
            "generated_utc": "2026-01-01T00:15:00Z",
            "destination_root": SYNTHETIC_ABSOLUTE_PATH,
            "total_sources": 2,
            "total_files_seen": 8,
            "total_files_copied": 3,
            "total_bytes_seen": 55,
            "chain_of_custody_sha256": "a" * 64,
        },
        "autonomous_grant_win": {
            "master_valuation_generated_utc": "2026-01-01T00:10:00Z",
            "master_valuation_proxy_usd": 456789.0,
            "valuation_increment_usd": 12345.0,
            "ip_entry_sha256": "b" * 64,
            "event_id": "synthetic-event",
            "explainer_generated_utc": "2026-01-01T00:11:00Z",
            "explainer_entry_sha256": "c" * 64,
            "public_truth_status": "synthetic",
            "public_truth_generated_utc": "2026-01-01T00:12:00Z",
            "public_truth_chain_entry_sha256": "d" * 64,
        },
        "artifacts": {
            "universe_map_json": SYNTHETIC_ABSOLUTE_PATH,
            "live_trade_ledger_jsonl": SYNTHETIC_ABSOLUTE_PATH,
        },
        "private_reference_notes": {
            "tax_reference": SYNTHETIC_TAX_IDENTIFIER,
            "patent_application_reference": SYNTHETIC_PATENT_APPLICATION,
        },
    }


def assert_public_safe(payload: dict) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    assert TRANSACTION_PATTERN.search(serialized) is None
    assert SYNTHETIC_TRANSACTION not in serialized
    assert SYNTHETIC_ABSOLUTE_PATH not in serialized
    assert SYNTHETIC_TAX_IDENTIFIER not in serialized
    assert SYNTHETIC_PATENT_APPLICATION not in serialized
    assert public_booth_contains_forbidden_value(payload) is False
    assert payload["details_redacted"] is True
    assert payload["public_claim_allowed"] is False
    assert payload["profit_claim_allowed"] is False
    assert payload["live_execution_authority"] is False
    assert payload["supported_maturity_level"] == 3
    assert "Level 3" in payload["claim_boundary"]


def test_public_projection_preserves_safe_aggregates_and_redacts_details() -> None:
    raw = raw_booth_payload()
    projected = public_booth_projection(raw)

    assert projected["indexing"] == raw["indexing"]
    assert projected["catalog"] == raw["catalog"]
    heartbeat = projected["live_execution"]["heartbeat"]
    assert heartbeat["status"] == "running"
    assert heartbeat["timestamp_utc"] == "2026-01-01T00:30:00Z"
    assert heartbeat["universe_candidate_count"] == 5
    assert heartbeat["reason"] == ""
    assert heartbeat["symbol"] == ""
    assert projected["live_execution"]["recent_trade_count"] == 1
    assert projected["live_execution"]["recent_trades"] == []
    assert projected["live_execution"]["latest_trade"]["txid"] == ""
    assert projected["live_execution"]["latest_trade"]["size_usd"] is None
    assert projected["autonomous_grant_win"]["master_valuation_proxy_usd"] is None
    assert projected["autonomous_grant_win"]["event_id"] == ""
    assert projected["premium_mirror"]["destination_root"] == ""
    assert "ein" not in projected["founder_profile"]
    assert "uspto_non_provisional_application" not in projected["founder_profile"]
    assert projected["founder_profile"]["private_identifiers_embedded"] is False
    assert projected["private_reference_notes"]["tax_reference"] == ""
    assert projected["private_reference_notes"]["patent_application_reference"] == ""
    assert raw["live_execution"]["latest_trade"]["txid"] == SYNTHETIC_TRANSACTION
    assert_public_safe(projected)
    assert public_booth_projection(projected) == projected
    for forbidden in (
        SYNTHETIC_TRANSACTION,
        SYNTHETIC_ABSOLUTE_PATH,
        SYNTHETIC_TAX_IDENTIFIER,
        SYNTHETIC_PATENT_APPLICATION,
    ):
        assert public_booth_contains_forbidden_value(forbidden) is True


def test_cli_writes_only_projected_json_markdown_and_history(tmp_path, monkeypatch) -> None:
    builder = load_builder()
    primary_dir = tmp_path / "primary"
    upload_ready_root = tmp_path / "upload_ready"
    proof_dir = upload_ready_root / "proof_validation"
    pilot_dir = upload_ready_root / "pilot_briefs"
    outside_dir = tmp_path / "outside_upload_ready"

    copy_sets = (
        (proof_dir, ""),
        (pilot_dir, "__2"),
    )
    for directory, variant in copy_sets:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"booth_explainer_brief{variant}.json").write_text(
            json.dumps(
                {
                    "txid": SYNTHETIC_TRANSACTION,
                    "ein": SYNTHETIC_TAX_IDENTIFIER,
                    "application": SYNTHETIC_PATENT_APPLICATION,
                    "path": SYNTHETIC_ABSOLUTE_PATH,
                }
            ),
            encoding="utf-8",
        )
        (directory / f"booth_explainer_brief{variant}.md").write_text(
            " ".join(
                (
                    SYNTHETIC_TRANSACTION,
                    SYNTHETIC_TAX_IDENTIFIER,
                    SYNTHETIC_PATENT_APPLICATION,
                    SYNTHETIC_ABSOLUTE_PATH,
                )
            ),
            encoding="utf-8",
        )
        (directory / f"booth_explainer_brief_sha256{variant}.json").write_text(
            json.dumps({"files": {SYNTHETIC_ABSOLUTE_PATH: SYNTHETIC_TRANSACTION}}),
            encoding="utf-8",
        )

    outside_dir.mkdir(parents=True, exist_ok=True)
    outside_copy = outside_dir / "booth_explainer_brief.json"
    outside_copy.write_text(SYNTHETIC_TRANSACTION, encoding="utf-8")

    monkeypatch.setattr(builder, "_build_payload", lambda recent_trade_rows: raw_booth_payload())
    monkeypatch.setattr(builder, "OUTPUT_JSON", primary_dir / "booth_explainer_brief.json")
    monkeypatch.setattr(builder, "OUTPUT_MD", primary_dir / "booth_explainer_brief.md")
    monkeypatch.setattr(builder, "OUTPUT_SHA", primary_dir / "booth_explainer_brief_sha256.json")
    monkeypatch.setattr(builder, "OUTPUT_HISTORY", primary_dir / "booth_explainer_brief_history.jsonl")
    monkeypatch.setattr(builder, "UPLOAD_READY_ROOT", upload_ready_root)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--recent-trade-rows", "3"])

    builder.OUTPUT_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    builder.OUTPUT_HISTORY.write_text(
        json.dumps(
            {
                "generated_utc": "2025-12-31T00:00:00Z",
                "files_indexed": 2,
                "engine_count": 1,
                "heartbeat_status": (
                    f"private {SYNTHETIC_TAX_IDENTIFIER} {SYNTHETIC_PATENT_APPLICATION}"
                ),
                "latest_trade_txid": SYNTHETIC_TRANSACTION,
                "local_path": SYNTHETIC_ABSOLUTE_PATH,
                "mirror_files_seen": 4,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    builder.main()

    payload = json.loads(builder.OUTPUT_JSON.read_text(encoding="utf-8"))
    markdown = builder.OUTPUT_MD.read_text(encoding="utf-8")
    history_rows = [
        json.loads(line)
        for line in builder.OUTPUT_HISTORY.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(builder.OUTPUT_SHA.read_text(encoding="utf-8"))
    assert_public_safe(payload)
    assert SYNTHETIC_TRANSACTION not in markdown
    assert SYNTHETIC_ABSOLUTE_PATH not in markdown
    assert SYNTHETIC_TAX_IDENTIFIER not in markdown
    assert SYNTHETIC_PATENT_APPLICATION not in markdown
    assert "Autonomous Grant Win" not in markdown
    assert "latest_trade" not in markdown
    assert "valuation_" not in markdown
    assert "Level 3" in markdown

    assert len(history_rows) == 2
    assert history_rows[0]["heartbeat_status"] == ""
    assert all("latest_trade_txid" not in row for row in history_rows)
    assert all(row["details_redacted"] is True for row in history_rows)
    assert all(row["public_claim_allowed"] is False for row in history_rows)
    assert public_booth_contains_forbidden_value(history_rows) is False

    assert manifest["public_copy"] is True
    assert manifest["details_redacted"] is True
    assert set(manifest["files"]) == {
        "booth_explainer_brief.json",
        "booth_explainer_brief.md",
    }
    assert manifest["files"][builder.OUTPUT_JSON.name] == builder.read_sha256(builder.OUTPUT_JSON)
    assert manifest["files"][builder.OUTPUT_MD.name] == builder.read_sha256(builder.OUTPUT_MD)
    assert all("/" not in name and "\\" not in name for name in manifest["files"])

    for directory, variant in copy_sets:
        json_copy = directory / f"booth_explainer_brief{variant}.json"
        md_copy = directory / f"booth_explainer_brief{variant}.md"
        sha_copy = directory / f"booth_explainer_brief_sha256{variant}.json"
        copied_payload = json.loads(json_copy.read_text(encoding="utf-8"))
        copied_manifest = json.loads(sha_copy.read_text(encoding="utf-8"))

        assert copied_payload == payload
        assert md_copy.read_text(encoding="utf-8") == markdown
        assert_public_safe(copied_payload)
        assert copied_manifest["public_copy"] is True
        assert copied_manifest["details_redacted"] is True
        assert set(copied_manifest["files"]) == {json_copy.name, md_copy.name}
        assert copied_manifest["files"][json_copy.name] == builder.read_sha256(json_copy)
        assert copied_manifest["files"][md_copy.name] == builder.read_sha256(md_copy)
        assert all("/" not in name and "\\" not in name for name in copied_manifest["files"])
        assert public_booth_contains_forbidden_value(copied_manifest) is False

    assert outside_copy.read_text(encoding="utf-8") == SYNTHETIC_TRANSACTION


def test_api_prebuilt_and_fallback_share_the_same_public_contract(monkeypatch) -> None:
    raw = raw_booth_payload()
    monkeypatch.setattr(gateway, "load_json", lambda path, default: raw)
    prebuilt = gateway.master_booth_brief()

    monkeypatch.setattr(gateway, "load_json", lambda path, default: {})
    monkeypatch.setattr(gateway, "_build_booth_explainer_brief_payload", lambda: raw)
    fallback = gateway.master_booth_brief()

    assert prebuilt["source"] == "prebuilt"
    assert fallback["source"] == "live_fallback"
    assert_public_safe(prebuilt)
    assert_public_safe(fallback)
    for payload in (prebuilt, fallback):
        payload.pop("source")
        payload.pop("served_utc")
    assert prebuilt == fallback
