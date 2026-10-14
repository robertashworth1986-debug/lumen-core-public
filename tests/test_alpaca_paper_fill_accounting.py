"""Offline broker responses cannot turn acknowledgments into paper fills."""
import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import multi_exchange_paper_ticker as ticker


@pytest.fixture
def paper(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "offline-fixture")
    monkeypatch.setenv("ALPACA_API_SECRET", "offline-fixture")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    monkeypatch.setattr(ticker, "ALPACA_TRUE_PAPER_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(ticker, "ALPACA_TRUE_PAPER_LEDGER_FILE", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(ticker.requests, "request", lambda *a, **k: pytest.fail("network forbidden"))
    return tmp_path


def run_broker(monkeypatch, response, positions=(), candidates=True):
    posts = []

    def request(method, base, endpoint, key, secret, **kwargs):
        if method == "POST":
            posts.append(kwargs["payload"])
            data = dict(response)
            data.setdefault("client_order_id", kwargs["payload"].get("client_order_id"))
            return {"ok": True, "data": data}
        return {"ok": True, "data": {
            "/v2/account": {"cash": "1000", "equity": "1000"},
            "/v2/positions": list(positions),
            "/v2/assets": [{"symbol": "BTC/USD", "tradable": True}],
        }[endpoint]}

    monkeypatch.setattr(ticker, "_alpaca_request", request)
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {
        "hybrid_top": [{"symbol": "BTCUSDT", "price": 100, "hybrid_score": 1}]
        if candidates else []
    })
    return result, posts


def seed_long():
    state = {"accounting_schema": "alpaca_paper_accounting.v2", "trade_count": 0,
             "realized_pnl_usd": 0, "wins": 0, "losses": 0,
             "open_positions": {"BTC/USD": {"qty": 2, "entry_price": 100}},
             "booked_order_ids": []}
    ticker.ALPACA_TRUE_PAPER_STATE_FILE.write_text(json.dumps(state))


def lock_path():
    path = ticker.ALPACA_TRUE_PAPER_STATE_FILE
    return path.with_name(path.stem + ".order_lock.json")


def full_buy(**changes):
    return dict({"id": "order-1", "status": "filled", "symbol": "BTC/USD",
                 "side": "buy", "filled_qty": "2.5", "filled_avg_price": "100"}, **changes)


def child_run(tmp_path):
    source = """
import json, sys
from pathlib import Path
import multi_exchange_paper_ticker as t
t.ALPACA_TRUE_PAPER_STATE_FILE = Path(sys.argv[1]) / 'state.json'
t.ALPACA_TRUE_PAPER_LEDGER_FILE = Path(sys.argv[1]) / 'ledger.jsonl'
def forbidden(*args, **kwargs):
    raise AssertionError('broker I/O must remain blocked')
t._alpaca_request = forbidden
result = t.run_alpaca_true_paper_logic(2, 'hybrid', {}, {})
print(json.dumps({'ok': result['ok'], 'error': result['error']}))
"""
    return subprocess.run([sys.executable, "-c", source, str(tmp_path)],
        cwd=Path(ticker.__file__).parent, check=True, capture_output=True, text=True)


def test_accepted_buy_never_fabricates_quantity_or_fill(paper, monkeypatch):
    result, posts = run_broker(monkeypatch, {"id": "order-1", "status": "accepted",
        "symbol": "BTC/USD", "side": "buy", "filled_qty": "0", "filled_avg_price": None})
    assert len(posts) == 1
    assert result["state"]["open_positions"] == {}
    assert result["requires_operator_reconciliation"] is True
    assert result["event"]["event_type"] != "alpaca_true_paper_fill"
    assert lock_path().exists()
    assert json.loads(child_run(paper).stdout)["error"] == "unresolved_order_lock_requires_operator_reconciliation"


def test_accepted_sell_preserves_position_and_profit(paper, monkeypatch):
    seed_long()
    result, posts = run_broker(monkeypatch, {"id": "order-1", "status": "accepted",
        "symbol": "BTC/USD", "side": "sell", "filled_qty": "0", "filled_avg_price": None},
        [{"symbol": "BTCUSD", "qty": "2", "avg_entry_price": "100", "current_price": "110"}])
    assert len(posts) == 1
    assert result["state"]["open_positions"]["BTC/USD"]["qty"] == 2
    assert result["state"]["realized_pnl_usd"] == 0
    assert result["state"]["trade_count"] == 0


@pytest.mark.parametrize("changes", [
    {"status": "partially_filled", "filled_qty": "1"},
    {"status": "accepted"}, {"status": "canceled"}, {"filled_qty": None},
    {"filled_qty": "0"}, {"filled_qty": "nan"}, {"filled_qty": "1e-4000"},
    {"filled_qty": True}, {"filled_avg_price": None}, {"filled_avg_price": "inf"},
    {"filled_avg_price": "0"}, {"filled_qty": "1"}, {"filled_qty": "3"},
    {"id": ""}, {"side": "sell"}, {"symbol": "ETH/USD"},
    {"client_order_id": "some-other-request"},
])
def test_unconfirmed_or_inconsistent_buys_never_book(paper, monkeypatch, changes):
    result, posts = run_broker(monkeypatch, full_buy(**changes))
    assert len(posts) == 1
    assert result["ok"] is False and result["requires_operator_reconciliation"] is True
    assert result["state"]["open_positions"] == {}
    assert result["state"]["realized_pnl_usd"] == 0
    assert lock_path().exists()
    assert not ticker.ALPACA_TRUE_PAPER_LEDGER_FILE.exists()


def test_confirmed_fills_book_exact_quantity_and_only_one_order_per_cycle(paper, monkeypatch):
    buy, posts = run_broker(monkeypatch, full_buy())
    assert buy["ok"] and len(posts) == 1 and not lock_path().exists()
    assert buy["state"]["open_positions"]["BTC/USD"]["qty"] == "2.5"
    assert buy["event"]["truth"] == "confirmed_broker_paper_fill"
    sell, posts = run_broker(monkeypatch, {
        "id": "order-2", "status": "filled", "symbol": "BTCUSD", "side": "sell",
        "filled_qty": "2.5", "filled_avg_price": "110"},
        [{"symbol": "BTCUSD", "qty": "2.5", "current_price": "110"}])
    assert sell["ok"] and len(posts) == 1
    assert posts[0]["side"] == "sell"  # No re-entry using pre-sale cash.
    assert sell["state"]["open_positions"] == {}
    assert sell["state"]["realized_pnl_usd"] == 25
    assert sell["state"]["trade_count"] == sell["state"]["wins"] == 1
    assert sell["state"]["realized_pnl_basis"] == "confirmed_fill_gross_excludes_fees"
    assert len(ticker.ALPACA_TRUE_PAPER_LEDGER_FILE.read_text().splitlines()) == 2


@pytest.mark.parametrize("qty", ["1", "3"])
def test_filled_close_with_wrong_quantity_is_held_without_full_position_profit(paper, monkeypatch, qty):
    seed_long()
    result, posts = run_broker(monkeypatch, {"id": "order-1", "status": "filled",
        "symbol": "BTCUSD", "side": "sell", "filled_qty": qty, "filled_avg_price": "110"},
        [{"symbol": "BTCUSD", "qty": "2", "current_price": "110"}])
    assert len(posts) == 1 and result["ok"] is False
    assert result["state"]["open_positions"]["BTC/USD"]["qty"] == 2
    assert result["state"]["realized_pnl_usd"] == 0


def test_transport_timeout_leaves_durable_intent_and_blocks_competing_process(paper, monkeypatch):
    posts = []

    def transport(*, method, url, **kwargs):
        if method == "POST":
            posts.append(kwargs["json"])
            intent = json.loads(lock_path().read_text())
            persisted = json.loads(ticker.ALPACA_TRUE_PAPER_STATE_FILE.read_text())
            assert intent["request"] == kwargs["json"]
            assert persisted["unresolved_order"]["request"] == kwargs["json"]
            assert json.loads(child_run(paper).stdout)["ok"] is False
            raise ticker.requests.Timeout("response lost after possible acceptance")
        endpoint = url.removeprefix("https://paper-api.alpaca.markets")
        data = {"/v2/account": {"cash": "1000", "equity": "1000"}, "/v2/positions": [],
                "/v2/assets": [{"symbol": "BTC/USD", "tradable": True}]}[endpoint]
        return SimpleNamespace(status_code=200, text="json", json=lambda: data)

    monkeypatch.setattr(ticker.requests, "request", transport)
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {
        "hybrid_top": [{"symbol": "BTCUSDT", "price": 100, "hybrid_score": 1}]})
    assert len(posts) == 1 and result["ok"] is False and lock_path().exists()
    assert result["state"]["open_positions"] == {}
    assert json.loads(child_run(paper).stdout)["error"] == "unresolved_order_lock_requires_operator_reconciliation"


def test_ledger_failure_after_fill_holds_booked_state_without_rebooking(paper, monkeypatch):
    monkeypatch.setattr(ticker, "_append_alpaca_paper_event", lambda *args: (_ for _ in ()).throw(OSError("disk full")))
    result, posts = run_broker(monkeypatch, full_buy())
    assert len(posts) == 1 and result["ok"] is False
    persisted = json.loads(ticker.ALPACA_TRUE_PAPER_STATE_FILE.read_text())
    assert persisted["unresolved_order"]["accounting_applied"] is True
    assert persisted["booked_order_ids"] == ["order-1"]
    assert persisted["open_positions"]["BTC/USD"]["qty"] == "2.5"
    assert lock_path().exists()
    assert json.loads(child_run(paper).stdout)["ok"] is False


def test_state_write_failure_after_fill_keeps_pre_submit_intent(paper, monkeypatch):
    original = ticker._save_alpaca_paper_state
    saves = []

    def save(state):
        saves.append(1)
        if len(saves) > 1:
            raise OSError("disk full after response")
        original(state)

    monkeypatch.setattr(ticker, "_save_alpaca_paper_state", save)
    result, posts = run_broker(monkeypatch, full_buy())
    assert len(posts) == 1 and result["ok"] is False and lock_path().exists()
    persisted = json.loads(ticker.ALPACA_TRUE_PAPER_STATE_FILE.read_text())
    assert persisted["open_positions"] == {} and persisted["booked_order_ids"] == []
    assert persisted["unresolved_order"]["request"]["side"] == "buy"
    assert not ticker.ALPACA_TRUE_PAPER_LEDGER_FILE.exists()
    assert json.loads(child_run(paper).stdout)["ok"] is False


def test_thrown_order_transport_does_not_release_uncertain_intent(paper, monkeypatch):
    def request(method, base, endpoint, *args, **kwargs):
        if method == "POST":
            raise RuntimeError("transport interrupted")
        return {"ok": True, "data": {"/v2/account": {"cash": "1000", "equity": "1000"},
            "/v2/positions": [], "/v2/assets": [{"symbol": "BTC/USD", "tradable": True}]}[endpoint]}

    monkeypatch.setattr(ticker, "_alpaca_request", request)
    with pytest.raises(RuntimeError, match="transport interrupted"):
        ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {
            "hybrid_top": [{"symbol": "BTCUSDT", "price": 100, "hybrid_score": 1}]})
    assert lock_path().exists()
    assert json.loads(child_run(paper).stdout)["ok"] is False


def test_process_exit_during_submission_retains_restart_lock(paper):
    source = """
import os, sys
from pathlib import Path
import multi_exchange_paper_ticker as t
t.ALPACA_TRUE_PAPER_STATE_FILE = Path(sys.argv[1]) / 'state.json'
t.ALPACA_TRUE_PAPER_LEDGER_FILE = Path(sys.argv[1]) / 'ledger.jsonl'
def request(method, base, endpoint, *args, **kwargs):
    if method == 'POST':
        os._exit(23)
    return {'ok': True, 'data': {'/v2/account': {'cash': '1000', 'equity': '1000'},
        '/v2/positions': [], '/v2/assets': [{'symbol': 'BTC/USD', 'tradable': True}]}[endpoint]}
t._alpaca_request = request
t.run_alpaca_true_paper_logic(1, 'hybrid', {}, {'hybrid_top': [
    {'symbol': 'BTCUSDT', 'price': 100, 'hybrid_score': 1}]})
"""
    process = subprocess.run([sys.executable, "-c", source, str(paper)], cwd=Path(ticker.__file__).parent,
        capture_output=True, text=True)
    assert process.returncode == 23
    assert lock_path().exists() and ticker.ALPACA_TRUE_PAPER_STATE_FILE.exists()
    assert json.loads(child_run(paper).stdout)["ok"] is False


@pytest.mark.parametrize("content", ["", "garbage", "{}", '{"partial":'])
def test_existing_invalid_intent_is_never_aged_out_or_bypassed(paper, monkeypatch, content):
    lock_path().write_text(content)
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and lock_path().read_text() == content


def test_symlink_intent_fails_closed_without_touching_target(paper, monkeypatch):
    target = paper / "must-remain.txt"
    target.write_text("unchanged")
    lock_path().symlink_to(target)
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and lock_path().is_symlink() and target.read_text() == "unchanged"


def test_owned_partial_intent_write_failure_is_cleaned_before_any_io(paper, monkeypatch):
    monkeypatch.setattr(ticker, "_write_alpaca_paper_intent", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and not lock_path().exists()
    assert not ticker.ALPACA_TRUE_PAPER_STATE_FILE.exists()


def test_cleanup_never_unlinks_a_replaced_intent(paper, monkeypatch):
    target = paper / "other-owner"
    target.write_text("unchanged")

    def replace_then_fail(*args):
        lock_path().unlink()
        lock_path().symlink_to(target)
        raise OSError("intent replaced")

    monkeypatch.setattr(ticker, "_write_alpaca_paper_intent", replace_then_fail)
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and lock_path().is_symlink() and target.read_text() == "unchanged"


@pytest.mark.parametrize("content", ["{}", "not-json", '{"accounting_schema": "legacy"}',
    '{"accounting_schema":"alpaca_paper_accounting.v2","open_positions":{},"booked_order_ids":[],"extra":NaN}',
    '{"accounting_schema":"alpaca_paper_accounting.v2","open_positions":{},"booked_order_ids":[],"extra":Infinity}',
    '{"accounting_schema":"alpaca_paper_accounting.v2","open_positions":{},"booked_order_ids":[],"extra":1e9999}',
    '{"accounting_schema":"alpaca_paper_accounting.v2","open_positions":{},"booked_order_ids":[],"open_positions":{}}',
    '{"accounting_schema":"alpaca_paper_accounting.v2","open_positions":{"BTC/USD":{"qty":1,"qty":2,"entry_price":100}},"booked_order_ids":[]}',
])
def test_legacy_or_corrupt_state_never_resets_into_new_orders(paper, monkeypatch, content):
    ticker.ALPACA_TRUE_PAPER_STATE_FILE.write_text(content)
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and ticker.ALPACA_TRUE_PAPER_STATE_FILE.read_text() == content


def test_broker_snapshot_failure_never_becomes_empty_position_permission(paper, monkeypatch):
    monkeypatch.setattr(ticker, "_alpaca_request", lambda method, base, endpoint, *a, **k:
        {"ok": False} if endpoint == "/v2/positions" else {"ok": True, "data": {"cash": "1000", "equity": "1000"}})
    result = ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})
    assert not result["ok"] and result["error"] == "positions_fetch_failed"


def test_nonpaper_origin_never_reaches_transport(paper, monkeypatch):
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets")
    monkeypatch.setattr(ticker, "_alpaca_request", lambda *a, **k: pytest.fail("broker I/O forbidden"))
    assert ticker.run_alpaca_true_paper_logic(1, "hybrid", {}, {})["error"] == "paper_origin_required"


def paper_report(monkeypatch, **changes):
    monkeypatch.setattr(ticker, "save_json", lambda *args: None)
    monkeypatch.setattr(ticker, "sha256_file", lambda *args: "")
    state = dict({"accounting_schema": "alpaca_paper_accounting.v2", "initial_cash_usd": 1000,
        "cash_usd": 750, "equity_usd": 1000, "realized_pnl_usd": 0,
        "realized_pnl_basis": "confirmed_fill_gross_excludes_fees",
        "account_snapshot_utc": "2026-10-14T12:00:00Z", "account_snapshot_precedes_order": False,
        "open_positions": {"BTC/USD": {"qty": "2.5", "entry_price": "100"}}}, **changes)
    return ticker.build_institutional_crypto_paper_report({"alpaca_true_paper_engine": {
        "ok": True, "requires_operator_reconciliation": False, "state": state}}, 1000, False)


def test_report_never_counts_invested_market_value_as_profit(monkeypatch):
    report = paper_report(monkeypatch)
    assert report["portfolio"]["gross_position_value_usd"] == 250
    assert report["portfolio"]["unrealized_pnl_usd"] is None
    assert report["portfolio"]["unrealized_pnl_status"] == "unknown_not_captured_in_snapshot"


def test_report_separates_pre_order_snapshot_from_post_fill_positions(monkeypatch):
    portfolio = paper_report(monkeypatch, account_snapshot_precedes_order=True)["portfolio"]
    assert portfolio["account_snapshot_precedes_order"] is True
    assert portfolio["account_snapshot_utc"] == "2026-10-14T12:00:00Z"
    assert portfolio["positions_open"] is None
    assert portfolio["local_confirmed_positions_open"] == 1
    assert portfolio["realized_pnl_basis"] == "confirmed_fill_gross_excludes_fees"


def test_report_preserves_losses_and_does_not_call_equity_change_strategy_return(monkeypatch):
    portfolio = paper_report(monkeypatch, equity_usd=950, realized_pnl_usd=-10)["portfolio"]
    assert portfolio["realized_pnl_usd"] == -10
    assert portfolio["unrealized_pnl_usd"] is None
    assert portfolio["return_pct"] is None
    assert portfolio["equity_change_pct"] == -.05
    assert portfolio["equity_change_pct_basis"] == "includes_external_flows_not_strategy_return"
    assert portfolio["return_pct_status"] == "unknown_cash_flows_not_reconciled"


def test_deposit_is_not_reported_as_trading_profit(monkeypatch):
    portfolio = paper_report(monkeypatch, equity_usd=2000, cash_usd=1750)["portfolio"]
    assert portfolio["return_pct"] is None
    assert portfolio["equity_change_pct"] == 1
    assert portfolio["unrealized_pnl_usd"] is None


def test_separate_manifest_hashes_final_report_bytes_and_survives_readback(tmp_path, monkeypatch):
    names = ["STATUS_FILE", "BINANCEUS_PAPER_LEDGER_FILE", "BINANCEUS_PAPER_STATE_FILE",
             "BINANCEUS_PAPER_SCOREBOARD_FILE", "ALPACA_TRUE_PAPER_STATE_FILE",
             "ALPACA_TRUE_PAPER_LEDGER_FILE", "INSTITUTIONAL_PAPER_REPORT_FILE",
             "INSTITUTIONAL_PAPER_HASH_FILE"]
    for name in names:
        path = tmp_path / (name.lower() + ".json")
        monkeypatch.setattr(ticker, name, path)
        if name not in ("INSTITUTIONAL_PAPER_REPORT_FILE", "INSTITUTIONAL_PAPER_HASH_FILE"):
            path.write_text('{"fixture":"offline"}')
    original_save = ticker.save_json
    report_writes = []

    def save(path, data):
        if path == ticker.INSTITUTIONAL_PAPER_REPORT_FILE:
            report_writes.append(1)
        original_save(path, data)

    monkeypatch.setattr(ticker, "save_json", save)
    monkeypatch.setattr(ticker.requests, "request", lambda *a, **k: pytest.fail("network forbidden"))
    returned = ticker.build_institutional_crypto_paper_report({}, 1000, False)
    report_bytes = ticker.INSTITUTIONAL_PAPER_REPORT_FILE.read_bytes()
    saved_report = json.loads(report_bytes)
    manifest_path = Path(saved_report["artifact_hash_file"])
    assert manifest_path == ticker.INSTITUTIONAL_PAPER_HASH_FILE
    manifest = json.loads(manifest_path.read_bytes())
    report_entry = next(entry for entry in manifest["files"]
                        if entry["path"] == str(ticker.INSTITUTIONAL_PAPER_REPORT_FILE))
    assert report_entry["sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert returned == saved_report
    assert "artifact_hashes" not in saved_report  # No self-referential hash copies.
    assert report_writes == [1]
