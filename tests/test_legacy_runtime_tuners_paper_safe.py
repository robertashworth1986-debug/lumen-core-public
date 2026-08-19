import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


def load_module(name: str, filename: str):
    sys.path.insert(0, str(CODE))
    try:
        spec = importlib.util.spec_from_file_location(name, CODE / filename)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(CODE))


def test_beast_tuner_cannot_transition_runtime_to_live(monkeypatch):
    module = load_module("beast_mode_paper_safe", "beast_mode.py")
    monkeypatch.setattr(module, "_live_guard_passes", lambda _cfg: (True, []))

    patched = module.apply_super_sniper(
        runtime_cfg={"mode": "paper", "allow_live_orders": False},
        sniper_cfg={"candidate_hunter": {"sharp_trigger": 0.0}},
        top_candidates=[],
        sharp_value=99.0,
        dry_run=False,
    )

    assert patched["mode"] == "paper"
    assert patched["allow_live_orders"] is False
    assert "legacy_runtime_tuner_live_transition_retired" in patched["super_sniper_guard_reasons"]


def test_lightning_tuner_cannot_transition_runtime_to_live(monkeypatch):
    module = load_module("lightning_paper_safe", "lightning.py")
    monkeypatch.setattr(module, "_live_guard_passes", lambda _cfg: (True, []))

    patched = module.apply_upgrades(
        runtime={"mode": "paper", "allow_live_orders": False},
        health={},
        guardrails={"upgrades": {}},
        dry_run=False,
    )

    assert patched["mode"] == "paper"
    assert patched["allow_live_orders"] is False
    assert "legacy_runtime_tuner_live_transition_retired" in patched["lightning_live_guard_reasons"]


def test_multi_account_rollout_is_paper_only_even_when_legacy_guards_pass(monkeypatch):
    module = load_module("multi_account_rollout_paper_safe", "multi_account_universe_rollout.py")
    monkeypatch.setattr(module, "_live_guard", lambda _policy: (True, []))
    monkeypatch.setattr(
        module,
        "read_json",
        lambda _path, _default: {
            "mode": "live",
            "allow_live_orders": True,
            "paper_enabled": False,
            "kill_switch": False,
        },
    )

    plan = module.build_account_plan(
        accounts=[{"account_id": "KRAKEN_TEST", "provider": "KRAKEN", "status": "ready"}],
        universe=[{"symbol": "BTCUSD", "asset_class": "crypto"}],
        policy={"providers": {"KRAKEN": {"supports_asset_classes": ["crypto"]}}},
        apply_live=True,
    )

    runtime = plan["plan_accounts"][0]["runtime_patch"]
    assert runtime["mode"] == "paper"
    assert runtime["allow_live_orders"] is False
    assert runtime["paper_enabled"] is True
    assert plan["allow_live_effective"] is False
    assert "legacy_multi_account_live_transition_retired" in plan["live_guard_reasons"]
