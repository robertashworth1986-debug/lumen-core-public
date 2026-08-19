import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TRADING_STACK_SAFETY_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trading_stack_safety_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def configure_fixture(monkeypatch, module, tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "stack"
    config = root / "config"
    out_execution = root / "out" / "execution"
    paths = {
        "root": root,
        "runtime": config / "runtime_control.json",
        "legacy_runtime": root / "code" / "execution" / "runtime_control.json",
        "alpaca_runtime": config / "accounts" / "ALPACA_PRIMARY" / "runtime_control.json",
        "kraken_runtime": config / "accounts" / "KRAKEN_PRIMARY" / "runtime_control.json",
        "control_flags": root / "control_flags.json",
        "out_control_flags": root / "out" / "control_flags.json",
        "policy": config / "multi_account_policy.json",
        "live_flag": root / "control" / "LIVE.flag",
        "live_arm": config / "live_arm.confirm",
        "multi_arm": config / "multi_live_arm.confirm",
        "lightning_arm": config / "lightning_live_arm.confirm",
        "paper_ledger": root / "out" / "paper_trade_ledger.jsonl",
        "real_ledger": root / "out" / "paper_trade_real_api_ledger.jsonl",
        "paper_canonical": out_execution / "paper_trade_ledger_canonical.jsonl",
        "real_canonical": out_execution / "paper_trade_real_api_ledger_canonical.jsonl",
        "reconciliation": out_execution / "paper_ledger_reconciliation.json",
        "executor": out_execution / "live_executor_heartbeat.json",
        "autofire": out_execution / "approval_autofire_heartbeat.json",
        "growth": out_execution / "vps_growth_controller_status.json",
        "queue": out_execution / "live_operator_approval_queue.json",
        "code": root / "code",
    }
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "RUNTIME_FILE", paths["runtime"])
    monkeypatch.setattr(module, "LEGACY_RUNTIME_FILE", paths["legacy_runtime"])
    monkeypatch.setattr(module, "ACCOUNT_RUNTIME_FILES", [paths["alpaca_runtime"], paths["kraken_runtime"]])
    monkeypatch.setattr(module, "CONTROL_FLAG_FILES", [paths["control_flags"], paths["out_control_flags"]])
    monkeypatch.setattr(module, "MULTI_ACCOUNT_POLICY_FILE", paths["policy"])
    monkeypatch.setattr(
        module,
        "LIVE_MARKER_FILES",
        [paths["live_flag"], paths["live_arm"], paths["multi_arm"], paths["lightning_arm"]],
    )
    monkeypatch.setattr(module, "PAPER_LEDGER_FILE", paths["paper_ledger"])
    monkeypatch.setattr(module, "REAL_PAPER_LEDGER_FILE", paths["real_ledger"])
    monkeypatch.setattr(module, "PAPER_CANONICAL_LEDGER_FILE", paths["paper_canonical"])
    monkeypatch.setattr(module, "REAL_PAPER_CANONICAL_LEDGER_FILE", paths["real_canonical"])
    monkeypatch.setattr(module, "PAPER_RECONCILIATION_FILE", paths["reconciliation"])
    monkeypatch.setattr(module, "STATE_WRITER_SCAN_ROOTS", [paths["code"]])
    monkeypatch.setattr(module, "EXEC_HEARTBEAT", paths["executor"])
    monkeypatch.setattr(module, "AUTOFIRE_HEARTBEAT", paths["autofire"])
    monkeypatch.setattr(module, "GROWTH_STATUS", paths["growth"])
    monkeypatch.setattr(module, "QUEUE_FILE", paths["queue"])
    return paths


def seed_safe_runtime_inputs(paths: dict[str, Path]) -> None:
    runtime = {
        "mode": "paper",
        "allow_live_orders": False,
        "paper_enabled": True,
        "kill_switch": False,
        "force_live_mode": False,
    }
    write_json(paths["runtime"], runtime)
    write_json(paths["alpaca_runtime"], runtime)
    write_json(paths["kraken_runtime"], runtime)
    now = datetime.now(timezone.utc).isoformat()
    write_json(paths["executor"], {"timestamp_utc": now, "status": "running"})
    write_json(paths["autofire"], {"generated_utc": now, "status": "running"})
    write_json(
        paths["growth"],
        {
            "mode": "SAFE_DRY_RUN",
            "guard": {"heartbeat_ok": True},
            "summary": {"actionable_candidates": 1, "auto_fired_count": 0},
        },
    )
    write_json(paths["queue"], {"tickets": []})


def seed_state_writer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'from pathlib import Path\nSTATE_FILE = Path("paper_trade_state.json")\n'
        'def write_json(path, payload):\n    path.write_text("{}", encoding="utf-8")\n'
        'write_json(STATE_FILE, {})\n',
        encoding="utf-8",
    )


def test_audit_blocks_conflicting_live_authority_and_duplicate_evidence(monkeypatch, tmp_path):
    module = load_module()
    paths = configure_fixture(monkeypatch, module, tmp_path)
    seed_safe_runtime_inputs(paths)

    write_json(paths["legacy_runtime"], {"mode": "live", "allow_live_orders": True})
    write_json(paths["control_flags"], {"live_enabled": True, "runtime_mode": "live"})
    write_json(paths["policy"], {"allow_live": True, "default_mode": "live"})
    paths["live_arm"].parent.mkdir(parents=True, exist_ok=True)
    paths["live_arm"].write_text("DO_NOT_DISCLOSE_THIS_VALUE", encoding="utf-8")
    seed_state_writer(paths["code"] / "writer_a.py")
    seed_state_writer(paths["code"] / "writer_b.py")
    (paths["code"] / "reader_only.py").write_text(
        'from pathlib import Path\n'
        'def load_json(path):\n    return {}\n'
        'def write_json(path, payload):\n    path.write_text("{}", encoding="utf-8")\n'
        'paper_state = load_json(Path("paper_trade_state.json"))\n'
        'write_json(Path("audit.json"), paper_state)\n',
        encoding="utf-8",
    )

    fill = {
        "timestamp": "2026-07-19T12:00:00+00:00",
        "event_type": "alpaca_fill",
        "mode": "ALPACA_PAPER",
        "source": "alpaca_api",
        "fill_id": "fill-1",
    }
    write_jsonl(paths["paper_ledger"], [fill, fill])
    write_jsonl(
        paths["real_ledger"],
        [
            {"timestamp": "2026-07-19T12:00:00+00:00", "event_type": "account_snapshot", "trade_count": 2},
            fill,
            fill,
        ],
    )

    audit = module.build_audit()
    blockers = "\n".join(audit["blockers"])

    assert audit["posture"] == "BLOCK_LIVE"
    assert audit["execution_authorized"] is False
    assert "legacy runtime contradicts canonical paper authority" in blockers
    assert "control flag contradicts canonical paper authority" in blockers
    assert "multi-account policy permits live execution" in blockers
    assert "stale live-arm marker" in blockers
    assert "paper state has 2 write-capable implementations" in blockers
    assert "unreconciled duplicate fill identities" in blockers
    assert "snapshot trade_count exceeds" in blockers
    assert audit["paper_evidence_integrity"]["paper_ledger"]["duplicate_fill_rows"] == 1
    assert "DO_NOT_DISCLOSE_THIS_VALUE" not in json.dumps(audit)


def test_clean_paper_fixture_is_bounded_and_never_authorizes_execution(monkeypatch, tmp_path):
    module = load_module()
    paths = configure_fixture(monkeypatch, module, tmp_path)
    seed_safe_runtime_inputs(paths)
    seed_state_writer(paths["code"] / "canonical_writer.py")

    fill = {
        "timestamp": "2026-07-19T12:00:00+00:00",
        "event_type": "alpaca_fill",
        "mode": "ALPACA_PAPER",
        "source": "alpaca_api",
        "fill_id": "fill-1",
    }
    write_jsonl(paths["paper_ledger"], [fill])
    write_jsonl(
        paths["real_ledger"],
        [
            {"timestamp": "2026-07-19T12:00:00+00:00", "event_type": "account_snapshot", "trade_count": 1},
            fill,
        ],
    )

    audit = module.build_audit()

    assert audit["posture"] == "PAPER_OK"
    assert audit["blockers"] == []
    assert audit["execution_authorized"] is False
    assert audit["claim_status"] == "NOT_VALIDATED_FOR_ALPHA_OR_LIVE_EXECUTION"
    assert audit["authority"]["paper_state_writer_count"] == 1
    assert audit["paper_evidence_integrity"]["real_api_ledger"]["duplicate_fill_rows"] == 0
    assert "human operator" in audit["promotion_rule"]


def test_current_reconciliation_preserves_raw_duplicates_without_blocking_canonical_view(
    monkeypatch, tmp_path
):
    module = load_module()
    paths = configure_fixture(monkeypatch, module, tmp_path)
    seed_safe_runtime_inputs(paths)
    seed_state_writer(paths["code"] / "canonical_writer.py")

    fill = {
        "timestamp": "2026-07-19T12:00:00+00:00",
        "event_type": "alpaca_fill",
        "mode": "ALPACA_PAPER",
        "source": "alpaca_api",
        "fill_id": "fill-1",
    }
    snapshot = {
        "timestamp": "2026-07-19T12:01:00+00:00",
        "event_type": "account_snapshot",
        "trade_count": 1,
    }
    write_jsonl(paths["paper_ledger"], [fill, fill])
    write_jsonl(paths["real_ledger"], [fill, fill, snapshot])
    write_jsonl(paths["paper_canonical"], [fill])
    write_jsonl(paths["real_canonical"], [fill, snapshot])
    write_json(
        paths["reconciliation"],
        {
            "schema": "paper_ledger_reconciliation_v1",
            "status": "PASS",
            "raw_evidence_preserved": True,
            "ledgers": {
                "paper_ledger": {
                    "status": "PASS",
                    "source_sha256": module.sha256_file(paths["paper_ledger"]),
                    "canonical_sha256": module.sha256_file(paths["paper_canonical"]),
                },
                "real_api_ledger": {
                    "status": "PASS",
                    "source_sha256": module.sha256_file(paths["real_ledger"]),
                    "canonical_sha256": module.sha256_file(paths["real_canonical"]),
                },
            },
        },
    )

    audit = module.build_audit()
    blockers = "\n".join(audit["blockers"])

    assert audit["posture"] == "PAPER_OK"
    assert "duplicate fill identities" not in blockers
    assert audit["paper_evidence_integrity"]["reconciliation"]["current"] is True
    assert any("duplicate historical rows" in warning for warning in audit["warnings"])
