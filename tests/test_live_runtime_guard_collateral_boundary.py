import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "execution" / "live_runtime_guard.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_runtime_guard_collateral", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_collateral_conversion_is_disarmed_for_paper_runtime_even_when_requested():
    module = load_module()
    guard = module.LiveRuntimeGuard(ROOT)

    runtime = guard._normalize(
        {
            "mode": "paper",
            "allow_live_orders": False,
            "paper_enabled": True,
            "kill_switch": False,
            "auto_convert_collateral": True,
        }
    )

    assert runtime["auto_convert_collateral"] is False


def test_collateral_conversion_requires_every_live_arm_condition():
    module = load_module()
    guard = module.LiveRuntimeGuard(ROOT)

    conflicting = guard._normalize(
        {
            "mode": "live",
            "allow_live_orders": True,
            "paper_enabled": True,
            "kill_switch": False,
            "auto_convert_collateral": True,
        }
    )
    fully_armed = guard._normalize(
        {
            "mode": "live",
            "allow_live_orders": True,
            "paper_enabled": False,
            "kill_switch": False,
            "auto_convert_collateral": True,
        }
    )

    assert conflicting["auto_convert_collateral"] is False
    assert fully_armed["auto_convert_collateral"] is True
