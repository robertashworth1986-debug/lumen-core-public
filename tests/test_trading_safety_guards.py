from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_secondary_execution_authorities_default_fail_closed():
    flags = json.loads((ROOT / "control_flags.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "config" / "multi_account_policy.json").read_text(encoding="utf-8"))

    assert flags["live_enabled"] is False
    assert flags["kill_switch"] is True
    assert flags["runtime_mode"] == "shadow"
    assert policy["allow_live"] is False
    assert policy["default_mode"] == "paper"
    assert not (ROOT / "config" / "live_arm.confirm").exists()
    assert not (ROOT / "config" / "multi_live_arm.confirm").exists()


def test_copilot_watch_fails_closed_instead_of_forcing_live():
    text = (ROOT / "code" / "ops" / "_copilot_watch.py").read_text(encoding="utf-8")

    assert "'mode': 'paper'" in text
    assert "'allow_live_orders': False" in text
    assert "'kill_switch': True" in text
    assert "allow_live_orders=True — forcing paper/safe mode" in text
    assert "enabling fail-closed guard" in text

    assert "forcing live" not in text
    assert "auto-clearing" not in text
    assert "fixes['allow_live_orders'] = True" not in text
    assert "fixes['kill_switch'] = False" not in text


def test_cancel_open_orders_requires_execute_and_confirmation():
    text = (ROOT / "code" / "ops" / "cancel_open_orders.py").read_text(encoding="utf-8")

    assert 'CONFIRM_PHRASE = "CANCEL_ALL_OPEN_ORDERS"' in text
    assert 'parser.add_argument("--execute"' in text
    assert 'parser.add_argument("--confirm"' in text
    assert 'args.execute and args.confirm != CONFIRM_PHRASE' in text
    assert "DRY RUN: no orders cancelled" in text
    assert 'kraken_private("/0/private/CancelAll"' in text
