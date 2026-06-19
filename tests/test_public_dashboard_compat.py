from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import multi_exchange_paper_ticker as paper_ticker


def test_gateway_public_compatibility_routes_are_declared() -> None:
    text = (ROOT / "code" / "luma_experience_gateway.py").read_text(encoding="utf-8")
    for route in (
        "/api/live_status.json",
        "/api/federal_brief.json",
        "/api/evidence_summary.json",
        "/api/executor_heartbeat.json",
    ):
        assert route in text
    assert "Queue presence is not portal submission" in text
    assert "No live execution authorization is implied" in text
    assert "field-performance or grant-award claim" in text


def test_gateway_exposes_public_compatibility_feeds() -> None:
    pytest.importorskip("fastapi")
    import luma_experience_gateway as gateway

    live_status = gateway.live_status_json()
    federal_brief = gateway.federal_brief_json()
    evidence_summary = gateway.evidence_summary_json()
    executor_heartbeat = gateway.executor_heartbeat_json()

    assert live_status["schema"] == "lumencore_live_status_compat_v1"
    assert "execution_gate" in live_status
    assert federal_brief["schema"] == "lumencore_federal_brief_compat_v1"
    assert "claim_boundary" in federal_brief
    assert evidence_summary["schema"] == "lumencore_evidence_summary_compat_v1"
    assert "claim_boundary" in evidence_summary
    assert executor_heartbeat["schema"] == "lumencore_executor_heartbeat_compat_v1"
    assert "source_meta" in executor_heartbeat


def test_paper_ticker_cycle_ledger_is_bounded() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "paper_ticker.jsonl"
        status = Path(tmp) / "paper_ticker_rotation.json"
        ledger.write_text(
            "".join(
                f'{{"row": {idx}, "payload": "{("x" * 30)}"}}\n'
                for idx in range(40)
            ),
            encoding="utf-8",
        )
        before = ledger.stat().st_size
        rotation = paper_ticker.append_bounded_jsonl(
            ledger,
            {"row": "new", "payload": "latest"},
            max_bytes=500,
            tail_bytes=180,
            status_path=status,
        )
        after = ledger.stat().st_size
        text = ledger.read_text(encoding="utf-8")

        assert before > 500
        assert rotation["rotated"] is True
        assert after < before
        assert '"row"' in text
        assert '"new"' in text
        assert status.exists()
