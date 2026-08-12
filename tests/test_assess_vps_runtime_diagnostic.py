import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "ASSESS_VPS_RUNTIME_DIAGNOSTIC.py"
COMMIT = "a" * 40

SPEC = importlib.util.spec_from_file_location("assess_vps_runtime_diagnostic", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
assess = MODULE.assess


def _diagnostic(*, healthy: bool) -> str:
    gateway_user = "lumencore" if healthy else ""
    lock_owner = "lumencore:lumencore" if healthy else "root:root"
    lock_mode = "640" if healthy else "644"
    ticker_active = "active" if healthy else "activating"
    ticker_state = "active" if healthy else "activating"
    ticker_substate = "running" if healthy else "auto-restart"
    ledger_owner = "lumencore" if healthy else "opc"
    ledger_group = "lumencore" if healthy else "opc"
    ledger_mode = "640" if healthy else "644"
    writable = "true" if healthy else "false"
    match_count = 20 if healthy else 19
    mismatch_count = 0 if healthy else 1
    failure = "" if healthy else "PermissionError: [Errno 13] Permission denied: ledger\n"
    return f"""=== identity ===
2026-08-12T05:36:12Z
=== public and loopback endpoint probes (status only; no bodies) ===
public_root rc=0 code=200 remote=example
public_nginx_health rc=0 code=200 remote=example
public_gateway_health rc=0 code=200 remote=example
public_gateway_snapshot rc=0 code=503 remote=example
loopback_nginx_health rc=0 code=200 remote=127.0.0.1
loopback_gateway_via_nginx rc=0 code=200 remote=127.0.0.1
loopback_gateway_direct rc=0 code=200 remote=127.0.0.1
=== canonical and related service states ===
--- luma-gateway ---
active=active
NRestarts=0
User={gateway_user}
Group={gateway_user}
ActiveState=active
SubState=running
--- luma-paper-ticker ---
active={ticker_active}
NRestarts=42
User=lumencore
Group=lumencore
ActiveState={ticker_state}
SubState={ticker_substate}
=== systemd failed units ===
=== gateway singleton-lock identity ===
lock_exists=true
lock_mode={lock_mode} lock_owner={lock_owner} lock_bytes=6
lock_pid_matches_systemd_main=true
=== gateway executable and source preflight ===
=== paper ticker output-path access (metadata only) ===
--- paper_ticker_ledger ---
symlink=false
exists=true type=regular empty file mode={ledger_mode} owner={ledger_owner} group={ledger_group} bytes=0
lumencore_test_w={writable}
=== runtime allowlisted failure signatures (redacted) ===
--- luma-paper-ticker failures since 5 minutes ago ---
journal_lines_in_window={1 if healthy else 4}
{failure}--- luma-symbol-awareness failures since 5 minutes ago ---
journal_lines_in_window=1
=== approved gateway closure comparison ===
source_commit={COMMIT}
expected_file_count=20
closure_match_count={match_count}
closure_mismatch_count={mismatch_count}
closure_missing_count=0
closure_symbolic_count=0
closure_unreadable_count=0
=== end approved gateway closure comparison ===
"""


def test_pass_requires_every_declared_runtime_contract() -> None:
    result = assess(
        _diagnostic(healthy=True),
        run_id="123",
        source_commit=COMMIT,
        source_url="https://example.invalid/run/123",
    )

    assert result["verdict"] == "PASS"
    assert result["summary"] == {
        "pass_count": 7,
        "fail_count": 0,
        "unknown_count": 0,
        "failed_check_ids": [],
        "unknown_check_ids": [],
        "required_repair_controls": [],
    }
    assert result["source"]["observed_at_utc"] == "2026-08-12T05:36:12Z"
    assert len(result["source"]["diagnostic_sha256"]) == 64


def test_runtime_defects_are_action_required_not_a_green_diagnostic() -> None:
    result = assess(
        _diagnostic(healthy=False),
        run_id="456",
        source_commit=COMMIT,
        source_url="https://example.invalid/run/456",
    )

    assert result["verdict"] == "ACTION_REQUIRED"
    assert set(result["summary"]["failed_check_ids"]) == {
        "gateway_service_identity",
        "gateway_lock_identity",
        "gateway_source_closure",
        "paper_ticker_service",
        "paper_ticker_ledger",
        "paper_ticker_recent_failures",
    }
    assert result["summary"]["required_repair_controls"] == [
        "DEPLOY_REVIEWED_NON_ROOT_GATEWAY_SERVICE_IDENTITY",
        "REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP",
        "REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE",
    ]


def test_missing_observations_fail_closed_as_indeterminate() -> None:
    result = assess(
        "2026-08-12T05:36:12Z\n",
        run_id="789",
        source_commit=COMMIT,
        source_url="https://example.invalid/run/789",
    )

    assert result["verdict"] == "INDETERMINATE"
    assert result["summary"]["fail_count"] == 0
    assert result["summary"]["unknown_count"] == 7


def test_source_closure_must_name_the_exact_assessed_commit() -> None:
    result = assess(
        _diagnostic(healthy=True),
        run_id="999",
        source_commit="b" * 40,
        source_url="https://example.invalid/run/999",
    )

    assert result["verdict"] == "ACTION_REQUIRED"
    closure = next(
        item for item in result["checks"] if item["id"] == "gateway_source_closure"
    )
    assert closure["status"] == "FAIL"
    assert closure["observed"]["declared_source_commit"] == "b" * 40
    assert closure["observed"]["observed_source_commit"] == COMMIT


def test_cli_writes_hash_bound_json_and_bounded_summary(tmp_path: Path) -> None:
    source = tmp_path / "diagnostic.txt"
    output = tmp_path / "assessment.json"
    summary = tmp_path / "summary.md"
    source.write_text(_diagnostic(healthy=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(source),
            "--output",
            str(output),
            "--summary-output",
            str(summary),
            "--run-id",
            "456",
            "--source-commit",
            COMMIT,
            "--source-url",
            "https://example.invalid/run/456",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert completed.stdout.strip() == "ACTION_REQUIRED"
    assert payload["schema_version"] == "lumencore.vps_runtime_assessment.v1"
    assert payload["verdict"] == "ACTION_REQUIRED"
    summary_text = summary.read_text(encoding="utf-8")
    assert "**Verdict:** `ACTION_REQUIRED`" in summary_text
    assert "first-party point-in-time evidence" in summary_text
    assert "Permission denied" not in summary_text
