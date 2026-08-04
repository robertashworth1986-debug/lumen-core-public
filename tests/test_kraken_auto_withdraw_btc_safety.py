import importlib.util
import json
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "kraken_auto_withdraw_btc.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kraken_auto_withdraw_btc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def live_root(tmp_path: Path) -> Path:
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    (config / "runtime_control.json").write_text(
        json.dumps(
            {
                "mode": "live",
                "allow_live_orders": True,
                "paper_enabled": False,
                "kill_switch": False,
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def approved_environment(module):
    return {
        module.HUMAN_APPROVAL_ENV: "x" * 32,
        module.DESTINATION_ENV: "configured-at-execution",
        module.API_KEY_ENV: "test-key",
        module.API_SECRET_ENV: "test-secret",
    }


def test_import_and_default_mode_do_not_load_credentials_or_contact_exchange():
    module = load_module()
    args = Namespace(execute=False, amount=None, confirmation="")

    assert module.execution_block_reason(args, {}, ROOT) == "--execute is required; no exchange request was made"
    assert module.main([]) == 0


def test_execution_requires_exact_amount_confirmation_human_unlock_and_live_runtime(tmp_path):
    module = load_module()
    args = Namespace(execute=True, amount=module.Decimal("0.001"), confirmation=module.CONFIRMATION_PHRASE)
    env = approved_environment(module)

    assert "runtime is not fully live-armed" in module.execution_block_reason(args, env, ROOT)
    assert module.execution_block_reason(args, env, live_root(tmp_path)) is None

    missing_human = dict(env)
    missing_human.pop(module.HUMAN_APPROVAL_ENV)
    assert "human action-time approval" in module.execution_block_reason(args, missing_human, live_root(tmp_path))

    wrong_confirmation = Namespace(execute=True, amount=module.Decimal("0.001"), confirmation="no")
    assert "exact --confirmation" in module.execution_block_reason(wrong_confirmation, env, live_root(tmp_path))

    no_amount = Namespace(execute=True, amount=None, confirmation=module.CONFIRMATION_PHRASE)
    assert "--amount is required" in module.execution_block_reason(no_amount, env, live_root(tmp_path))


def test_execute_withdrawal_never_builds_client_before_a_gate_passes(monkeypatch):
    module = load_module()
    args = Namespace(execute=True, amount=module.Decimal("0.001"), confirmation=module.CONFIRMATION_PHRASE)
    called = False

    def fail_if_called(_environ):
        nonlocal called
        called = True
        raise AssertionError("exchange client must not be built when runtime is blocked")

    monkeypatch.setattr(module, "build_kraken_client", fail_if_called)
    try:
        module.execute_withdrawal(args, approved_environment(module), ROOT)
    except RuntimeError as exc:
        assert "runtime is not fully live-armed" in str(exc)
    else:
        raise AssertionError("blocked execution must raise")
    assert not called
