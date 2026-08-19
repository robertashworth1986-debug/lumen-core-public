from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PAPER_LEDGER_RECONCILIATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paper_ledger_reconciliation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_reconciliation_keeps_raw_and_builds_unique_canonical_views(monkeypatch, tmp_path):
    module = load_module()
    raw_a = tmp_path / "raw_a.jsonl"
    raw_b = tmp_path / "raw_b.jsonl"
    canonical_a = tmp_path / "canonical_a.jsonl"
    canonical_b = tmp_path / "canonical_b.jsonl"
    receipt = tmp_path / "receipt.json"
    fill = {
        "timestamp": "2026-08-19T10:00:00+00:00",
        "event_type": "alpaca_fill",
        "fill_id": "private-fill-id",
    }
    snapshot = {
        "timestamp": "2026-08-19T10:01:00+00:00",
        "event_type": "account_snapshot",
        "trade_count": 1,
    }
    write_jsonl(raw_a, [fill, fill])
    write_jsonl(raw_b, [fill, fill, snapshot])
    raw_a_before = raw_a.read_bytes()
    raw_b_before = raw_b.read_bytes()

    monkeypatch.setattr(module, "PAPER_LEDGER", raw_a)
    monkeypatch.setattr(module, "REAL_API_LEDGER", raw_b)
    monkeypatch.setattr(module, "PAPER_CANONICAL", canonical_a)
    monkeypatch.setattr(module, "REAL_API_CANONICAL", canonical_b)
    monkeypatch.setattr(module, "RECEIPT_FILE", receipt)

    result = module.build_reconciliation()

    assert result["status"] == "PASS"
    assert raw_a.read_bytes() == raw_a_before
    assert raw_b.read_bytes() == raw_b_before
    assert len(canonical_a.read_text(encoding="utf-8").splitlines()) == 1
    assert len(canonical_b.read_text(encoding="utf-8").splitlines()) == 2
    assert result["ledgers"]["paper_ledger"]["source_duplicate_fill_rows"] == 1
    assert result["ledgers"]["real_api_ledger"]["canonical_duplicate_fill_rows"] == 0
    assert "private-fill-id" not in receipt.read_text(encoding="utf-8")


def test_reconciliation_fails_closed_on_missing_fill_id(monkeypatch, tmp_path):
    module = load_module()
    raw_a = tmp_path / "raw_a.jsonl"
    raw_b = tmp_path / "raw_b.jsonl"
    write_jsonl(raw_a, [{"event_type": "alpaca_fill"}])
    write_jsonl(raw_b, [{"event_type": "alpaca_fill"}])
    monkeypatch.setattr(module, "PAPER_LEDGER", raw_a)
    monkeypatch.setattr(module, "REAL_API_LEDGER", raw_b)
    monkeypatch.setattr(module, "PAPER_CANONICAL", tmp_path / "canonical_a.jsonl")
    monkeypatch.setattr(module, "REAL_API_CANONICAL", tmp_path / "canonical_b.jsonl")
    monkeypatch.setattr(module, "RECEIPT_FILE", tmp_path / "receipt.json")

    result = module.build_reconciliation()

    assert result["status"] == "FAIL"
    assert result["ledgers"]["paper_ledger"]["source_missing_fill_id_rows"] == 1
