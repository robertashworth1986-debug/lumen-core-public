import importlib.util
import json
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "LIQUIDATE_ALL_TO_USD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("liquidate_all_to_usd", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def live_root(tmp_path: Path) -> Path:
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    (config / "runtime_control.json").write_text(
        json.dumps({"mode": "live", "allow_live_orders": True, "paper_enabled": False, "kill_switch": False}),
        encoding="utf-8",
    )
    return tmp_path


def approved_environment(module):
    return {module.HUMAN_APPROVAL_ENV: "x" * 32}


def test_default_mode_is_local_only_and_does_not_import_exchange_clients():
    module = load_module()
    assert module.main([]) == 0
    source = SCRIPT.read_text(encoding="utf-8")
    assert "get_balance(" not in source
    assert "arm_deadman_switch" not in source
    assert "fetch_asset_pairs()" not in source.split("def main", maxsplit=1)[1].split("try:", maxsplit=1)[0]


def test_live_request_requires_named_asset_exact_amount_confirmation_human_unlock_and_runtime(tmp_path):
    module = load_module()
    args = Namespace(
        execute=True,
        asset="BTC",
        amount=module.Decimal("0.001"),
        confirmation=module.CONFIRMATION_PHRASE,
    )
    env = approved_environment(module)

    assert "runtime is not fully live-armed" in module.execution_block_reason(args, env, ROOT)
    assert module.execution_block_reason(args, env, live_root(tmp_path)) is None

    no_asset = Namespace(execute=True, asset="", amount=module.Decimal("0.001"), confirmation=module.CONFIRMATION_PHRASE)
    assert "--asset is required" in module.execution_block_reason(no_asset, env, live_root(tmp_path))
    no_amount = Namespace(execute=True, asset="BTC", amount=None, confirmation=module.CONFIRMATION_PHRASE)
    assert "--amount is required" in module.execution_block_reason(no_amount, env, live_root(tmp_path))
    no_human = {}
    assert "human action-time approval" in module.execution_block_reason(args, no_human, live_root(tmp_path))


def test_execute_never_discovers_pairs_or_submits_before_local_gates(monkeypatch):
    module = load_module()
    args = Namespace(
        execute=True,
        asset="BTC",
        amount=module.Decimal("0.001"),
        confirmation=module.CONFIRMATION_PHRASE,
    )
    called = False

    def fail_if_called():
        nonlocal called
        called = True
        raise AssertionError("network pair discovery must not run while runtime is blocked")

    monkeypatch.setattr(module, "fetch_asset_pairs", fail_if_called)
    try:
        module.execute_liquidation(args, approved_environment(module), ROOT)
    except RuntimeError as exc:
        assert "runtime is not fully live-armed" in str(exc)
    else:
        raise AssertionError("blocked execution must raise")
    assert not called
