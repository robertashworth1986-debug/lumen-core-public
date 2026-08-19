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
    assert "live_arm_write" not in full_truth["signals"]
    assert full_truth["classification"] == "guarded_review"
    assert {"runtime_gate", "human_approval"}.issubset(full_truth["protections"])

    launcher = by_path["code/execution/RUN_LIVE_COMPOUNDING_STACK.ps1"]
    assert "live_arm_write" in launcher["signals"]
    assert {"human_approval", "runtime_gate"}.issubset(launcher["protections"])

    autofire = by_path["code/execution/approval_autofire_daemon.py"]
    assert autofire["classification"] == "guarded_review"
    assert "automatic_approval" in autofire["signals"]
    assert {"runtime_gate", "human_approval"}.issubset(autofire["protections"])

    gateway = by_path["code/luma_experience_gateway.py"]
    assert gateway["classification"] == "guarded_review"
    assert "automatic_approval" in gateway["signals"]
    assert {"runtime_gate", "human_approval"}.issubset(gateway["protections"])

    for path in (
        "code/REBUILD_FULL_ADAPTIVE_LIVE_STACK.py",
        "code/DISCOVER_AND_ROUTE_ALL_LIVE_KEYS.py",
    ):
        if path not in by_path:
            continue
        writer = by_path[path]
        assert writer["classification"] == "guarded_review"
        assert "live_arm_write" not in writer["signals"]
        assert {"runtime_gate", "human_approval"}.issubset(writer["protections"])

    assert "code/BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py" not in by_path


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


def test_live_write_signals_do_not_treat_comparisons_as_mutations():
    module = load_module()
    comparison_text = """
if mode == "live":
    allowed = allow_live_orders == True
    stopped = kill_switch is False
"""

    hits = module.pattern_hits(comparison_text)

    assert "live_mode_write" not in hits
    assert "live_arm_write" not in hits
    assert "kill_switch_off_write" not in hits


def test_live_write_signals_cover_python_powershell_and_json_mutations():
    module = load_module()
    mutation_text = """
runtime["mode"] = "live"
$runtime.allow_live_orders = $true
{"kill_switch": false}
"""

    hits = module.pattern_hits(mutation_text)

    assert "live_mode_write" in hits
    assert "live_arm_write" in hits
    assert "kill_switch_off_write" in hits
