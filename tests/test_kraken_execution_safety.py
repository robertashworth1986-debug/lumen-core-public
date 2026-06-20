import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "kraken_execution.py"
spec = importlib.util.spec_from_file_location("kraken_execution_under_test", MODULE_PATH)
kraken = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(kraken)


def test_validate_only_forces_kraken_validate_true(monkeypatch):
    flags = dict(kraken.DEFAULT_FLAGS)
    flags.update(
        {
            "kill_switch": False,
            "max_notional_per_trade_usd": 100.0,
            "max_open_positions": 10,
            "max_daily_loss_usd": 20.0,
        }
    )
    calls = []

    monkeypatch.setattr(kraken, "_ensure_flags", lambda: flags)
    monkeypatch.setattr(kraken, "_count_open_positions", lambda: 0)
    monkeypatch.setattr(kraken, "_todays_live_loss_usd", lambda: 0.0)
    monkeypatch.setattr(kraken, "get_last_price", lambda pair: 1000.0)
    monkeypatch.setattr(kraken, "arm_deadman_switch", lambda timeout: {"armed": True})
    monkeypatch.setattr(kraken, "queue_approval_ticket", lambda **kwargs: {"approval_state": "PENDING_HUMAN_APPROVAL"})
    monkeypatch.setattr(kraken, "_append_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(kraken, "_write_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(kraken, "_runtime_snapshot", lambda **kwargs: {})

    def fake_private_post(path, payload):
        calls.append((path, dict(payload)))
        return {"validated": True}

    monkeypatch.setattr(kraken, "_private_post", fake_private_post)

    result = kraken.submit_order_validate_only(
        controller="Robert",
        pair="XBTUSD",
        side="buy",
        notional_usd=10.0,
    )

    assert result["mode"] == "VALIDATE_ONLY"
    assert result["payload"]["validate"] == "true"
    assert calls == [(kraken.ADD_ORDER_PATH, result["payload"])]
    assert calls[0][1]["validate"] == "true"


def test_enforce_risk_blocks_notional_above_configured_cap(monkeypatch):
    flags = dict(kraken.DEFAULT_FLAGS)
    flags.update(
        {
            "kill_switch": False,
            "max_notional_per_trade_usd": 5.0,
            "max_open_positions": 10,
            "max_daily_loss_usd": 20.0,
        }
    )
    monkeypatch.setattr(kraken, "_ensure_flags", lambda: flags)
    monkeypatch.setattr(kraken, "_count_open_positions", lambda: 0)
    monkeypatch.setattr(kraken, "_todays_live_loss_usd", lambda: 0.0)

    with pytest.raises(kraken.KrakenExecutionError, match="notional exceeds per-trade cap"):
        kraken.enforce_risk(symbol="XBTUSD", side="buy", notional_usd=10.0)


def test_sandbox_dns_failure_refuses_live_endpoint_fallback(monkeypatch):
    calls = []

    monkeypatch.setenv("KRAKEN_API_TESTNET", "1")
    monkeypatch.delenv("KRAKEN_API_URL", raising=False)
    monkeypatch.setattr(kraken, "_env", lambda name: "dummy")
    monkeypatch.setattr(kraken, "_nonce", lambda: "123")
    monkeypatch.setattr(kraken, "_kraken_signature", lambda *args, **kwargs: "sig")

    def fake_post(url, **kwargs):
        calls.append(url)
        raise kraken.requests.RequestException("Failed to resolve 'api.sandbox.kraken.com'")

    monkeypatch.setattr(kraken.requests, "post", fake_post)

    with pytest.raises(kraken.KrakenExecutionError, match="refusing to fall back to the live endpoint"):
        kraken._private_post(kraken.BALANCE_PATH, {})

    assert calls == ["https://api.sandbox.kraken.com" + kraken.BALANCE_PATH]
