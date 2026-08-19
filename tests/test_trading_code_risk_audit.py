import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TRADING_CODE_RISK_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trading_code_risk_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_audit_avoids_key_files_and_names_safe_spine():
    module = load_module()
    audit = module.build_audit()

    scanned = "\n".join(str(path) for path in module.iter_scan_paths()).lower().replace("\\", "/")
    assert ".env" not in scanned
    assert "live_keys.env" not in scanned
    assert "keys.env" not in scanned
    assert "code/_start_all_live_now.ps1" in scanned

    assert audit["secret_handling"].startswith("Scanner intentionally avoids env/key files")
    assert "code/kraken_execution.py" in audit["safe_spine"]
    assert "code/execution/live_runtime_guard.py" in audit["safe_spine"]
    assert audit["posture"] in {"BLOCK_LEGACY_LIVE", "GUARDED_REVIEW"}


def test_root_launchers_and_live_writers_are_inside_the_audit_boundary():
    module = load_module()
    audit = module.build_audit()
    by_path = {row["path"]: row for row in audit["files"]}

    full_truth = by_path["code/FULL_TRUTH_ORCHESTRATOR.py"]
    assert {"live_arm_write", "live_mode_write"}.issubset(full_truth["signals"])
    assert full_truth["classification"] == "high_review"

    launcher = by_path["code/execution/RUN_LIVE_COMPOUNDING_STACK.ps1"]
    assert "live_arm_write" in launcher["signals"]
    assert {"human_approval", "runtime_gate"}.issubset(launcher["protections"])

    autofire = by_path["code/execution/approval_autofire_daemon.py"]
    assert autofire["classification"] == "high_review"
    assert "automatic_approval" in autofire["signals"]


def test_withdrawal_and_validate_false_paths_are_not_marked_safe():
    module = load_module()
    audit = module.build_audit()
    by_path = {row["path"]: row for row in audit["files"]}

    auto_withdraw = by_path.get("code/kraken_auto_withdraw_btc.py")
    if auto_withdraw:
        assert auto_withdraw["classification"] == "guarded_review"
        assert {"execute_confirm", "runtime_gate", "human_approval"}.issubset(auto_withdraw["protections"])

    liquidate = by_path.get("code/ops/LIQUIDATE_ALL_TO_USD.py")
    if liquidate:
        assert liquidate["classification"] == "guarded_review"
        assert {"execute_confirm", "runtime_gate", "human_approval"}.issubset(liquidate["protections"])

    assert "code/micro_position_kraken_bot.py" not in by_path
    assert "code/kraken_swing_hunter.py" not in by_path

    history_reader = by_path.get("code/ops/LEARN_FROM_TRADE_HISTORY.py")
    if history_reader:
        assert history_reader["classification"] == "guarded_review"
        assert history_reader["signals"] == ["validate_false"]

    risky_validate_false = [
        row for row in audit["files"]
        if "validate_false" in row["signals"] and row["classification"] != "guarded_review"
    ]
    assert all(row["classification"] in {"high_review", "critical_legacy_quarantine"} for row in risky_validate_false)
