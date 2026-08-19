import ast
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
GO_LIVE = CODE / "go_live_paper_trader.py"
PAPER_LIVE_WRAPPER = CODE / "RUN_ALPACA_PAPER_LIVE.ps1"
UNIVERSAL = CODE / "run_universal_meta_orchestrator.py"
FULL_TRUTH = CODE / "FULL_TRUTH_ORCHESTRATOR.py"


def load_module(name: str, path: Path):
    sys.path.insert(0, str(CODE))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_retired_live_arming_api_always_raises_without_writing():
    module = load_module("go_live_paper_trader_test", GO_LIVE)

    for action in (
        module.arm_live_mode,
        module.arm_paper_runtime,
        module.create_live_arm_confirm,
    ):
        with pytest.raises(module.LegacyLiveArmingRetired):
            action()

    assert module.main() == 2


def test_legacy_powershell_wrapper_is_explicitly_paper_only():
    source = PAPER_LIVE_WRAPPER.read_text(encoding="utf-8")

    assert "go_live_paper_trader.py" not in source
    assert '$env:PAPER_MODE = "true"' in source
    assert '$env:LIVE_MODE = "false"' in source
    assert '$env:FORCE_LIVE = "false"' in source
    assert "Start-Process" not in source


def test_universal_meta_orchestrator_has_no_direct_order_transport():
    source = UNIVERSAL.read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_calls = [
        node
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    ]

    assert "requests.post" not in source
    assert "_private_post" not in source
    assert '"validate": "false"' not in source
    assert "legacy_live_execution_quarantined" in source
    assert not any(node.value.func.id == "_hydrate_live_keys" for node in top_level_calls)


def configure_full_truth_paths(module, tmp_path: Path) -> None:
    module.RUNTIME_CONTROL_PATH = tmp_path / "config" / "runtime_control.json"
    module.PAPER_RUNTIME_PATH = tmp_path / "config" / "paper_trader_runtime.json"
    module.INFRA_RUNTIME_PATH = tmp_path / "config" / "infra_live_runtime.json"
    module.EXECUTION_RUNTIME_JSON = tmp_path / "out" / "execution_runtime.json"
    module.EXECUTION_STATUS_JSON = tmp_path / "out" / "execution_status.json"
    module.APPROVAL_QUEUE_JSON = tmp_path / "out" / "execution_approval_queue.json"
    module.LIVE_ACTION_RECEIPT_PATH = (
        tmp_path / "out" / "execution" / "live_action_time_approval_receipt_latest.json"
    )
    module.DATASET_CATALOG_CSV = tmp_path / "out" / "dataset_catalog_live.csv"
    module.DATASET_SCAN_SUMMARY_CSV = tmp_path / "out" / "data_scan_summary_live.csv"
    module.DATA_INGEST_PROOF_JSON = tmp_path / "out" / "data_ingest_proof_live.json"
    module.SOURCE_TRUTH_TABLE_JSON = tmp_path / "out" / "source_truth_table.json"
    module.LIVE_SOURCE_REGISTRY_PATH = tmp_path / "config" / "live_source_registry.json"
    module.DATA_ROOTS = []


def live_runtime() -> dict:
    return {
        "mode": "live",
        "allow_live_orders": True,
        "paper_enabled": False,
        "kill_switch": False,
        "strict_live_only": True,
    }


def test_full_truth_disarms_live_flags_without_fresh_authority(tmp_path):
    module = load_module("full_truth_disarm_test", FULL_TRUTH)
    configure_full_truth_paths(module, tmp_path)
    module.save_json(module.RUNTIME_CONTROL_PATH, live_runtime())

    module.sync_runtime_files()

    runtime = json.loads(module.RUNTIME_CONTROL_PATH.read_text(encoding="utf-8"))
    status = json.loads(module.EXECUTION_STATUS_JSON.read_text(encoding="utf-8"))
    assert runtime["mode"] == "paper"
    assert runtime["allow_live_orders"] is False
    assert runtime["paper_enabled"] is True
    assert runtime["kill_switch"] is True
    assert status["live_action_time_authority"]["authorized"] is False
    assert status["canonical_runtime_rewritten"] is True


def test_full_truth_does_not_rewrite_hash_bound_authorized_runtime(tmp_path):
    module = load_module("full_truth_authorized_test", FULL_TRUTH)
    configure_full_truth_paths(module, tmp_path)
    module.save_json(module.RUNTIME_CONTROL_PATH, live_runtime())
    runtime_sha = hashlib.sha256(module.RUNTIME_CONTROL_PATH.read_bytes()).hexdigest()
    module.save_json(
        module.LIVE_ACTION_RECEIPT_PATH,
        {
            "schema": "live_action_time_approval_receipt_v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "controller": "test-controller",
            "human_unlock_verified": True,
            "exact_action_time_phrase_verified": True,
            "authorization_scope": "single_live_stack_start",
            "reusable_for_restart": False,
            "runtime_control_path": "config/runtime_control.json",
            "armed_runtime_sha256": runtime_sha,
        },
    )

    module.sync_runtime_files()

    status = json.loads(module.EXECUTION_STATUS_JSON.read_text(encoding="utf-8"))
    assert hashlib.sha256(module.RUNTIME_CONTROL_PATH.read_bytes()).hexdigest() == runtime_sha
    assert status["live_action_time_authority"]["authorized"] is True
    assert status["canonical_runtime_rewritten"] is False
