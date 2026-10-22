from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from booth_public_contract import (  # noqa: E402
    public_booth_contains_forbidden_value,
    public_booth_projection,
)


SYNTHETIC_TRANSACTION = "OABCDE-FGHIJK-LMNOPQ"
SYNTHETIC_PATH = r"C:\SyntheticPrivate\execution.jsonl"
SYNTHETIC_TAX_ID = "12-3456789"
SYNTHETIC_PATENT_ID = "12/345,678"
SYNTHETIC_EMAIL = "private.person@example.invalid"


def _raw_payload() -> dict:
    trade = {
        "timestamp": "2026-01-01T00:00:00Z",
        "txid": SYNTHETIC_TRANSACTION,
        "symbol": "SYNTH",
        "pair": "SYNTHUSD",
        "side": "buy",
        "status": "placed",
        "size_usd": 123.45,
    }
    return {
        "founder_profile": {
            "founder": "Synthetic Founder",
            "ein": SYNTHETIC_TAX_ID,
            "uspto_non_provisional_application": SYNTHETIC_PATENT_ID,
        },
        "indexing": {"files_indexed": 7},
        "live_execution": {
            "heartbeat": {
                "status": "running",
                "reason": f"private {SYNTHETIC_TAX_ID}",
                "symbol": "SYNTH",
                "universe_candidate_count": 5,
                "timestamp_utc": "2026-01-01T00:30:00Z",
            },
            "latest_trade": copy.deepcopy(trade),
            "recent_trade_count": 1,
            "recent_trades": [copy.deepcopy(trade)],
        },
        "premium_mirror": {"destination_root": SYNTHETIC_PATH},
        "autonomous_grant_win": {
            "master_valuation_proxy_usd": 456789.0,
            "event_id": "synthetic-event",
        },
        "artifacts": {"live_trade_ledger_jsonl": SYNTHETIC_PATH},
        "private_notes": {
            "tax_reference": SYNTHETIC_TAX_ID,
            "patent_reference": SYNTHETIC_PATENT_ID,
            "transaction_reference": SYNTHETIC_TRANSACTION,
            "contact": SYNTHETIC_EMAIL,
            "api_key": "synthetic-not-a-real-key",
        },
    }


def test_public_projection_redacts_operational_details_and_claims() -> None:
    raw = _raw_payload()
    original = copy.deepcopy(raw)
    projected = public_booth_projection(raw)
    serialized = json.dumps(projected, sort_keys=True)

    for forbidden in (
        SYNTHETIC_TRANSACTION,
        SYNTHETIC_PATH,
        SYNTHETIC_TAX_ID,
        SYNTHETIC_PATENT_ID,
        SYNTHETIC_EMAIL,
    ):
        assert forbidden not in serialized
        assert public_booth_contains_forbidden_value(forbidden) is True

    assert raw == original
    assert projected["indexing"] == {
        "files_indexed": 7,
        "roots_present": 0,
        "roots_total": 0,
        "scan_capped": False,
    }
    assert projected["catalog"] == {
        "engine_count": 0,
        "assets_source_rows": 0,
    }
    assert set(projected) == {
        "schema",
        "generated_utc",
        "brand",
        "indexing",
        "catalog",
        "supported_maturity_level",
        "details_redacted",
        "public_claim_allowed",
        "profit_claim_allowed",
        "live_execution_authority",
        "level_5_attained",
        "claim_boundary",
    }
    assert projected["supported_maturity_level"] == 3
    assert projected["details_redacted"] is True
    assert projected["public_claim_allowed"] is False
    assert projected["profit_claim_allowed"] is False
    assert projected["live_execution_authority"] is False
    assert projected["level_5_attained"] is False
    assert "Level 3" in projected["claim_boundary"]
    assert public_booth_contains_forbidden_value(projected) is False
    assert public_booth_projection(projected) == projected


def test_public_contract_module_is_syntax_valid_and_fixed_schema() -> None:
    source = (CODE / "booth_public_contract.py").read_text(encoding="utf-8")
    ast.parse(source)
    projected = public_booth_projection({})
    assert projected["schema"] == "lumencore.public_booth_contract.v2"
    assert projected["supported_maturity_level"] == 3
    assert projected["public_claim_allowed"] is False


EXPECTED_GATEWAY_CLOSURE = {
    "application_context_resolver.py",
    "autonomous_agent_manifest.py",
    "booth_public_contract.py",
    "execution/__init__.py",
    "execution/order_safety_gate.py",
    "forecast_api.py",
    "grant_application_factory.py",
    "grant_hunter_v2.py",
    "grant_submission_kit.py",
    "grants_api.py",
    "linkedin_oauth.py",
    "linkedin_router.py",
    "luma_experience_gateway.py",
    "luma_experience_gateway_legacy.py",
    "master_universe_benchmark.py",
    "master_universe_benchmark_v2.py",
    "meta_router.py",
    "operator_api_access.py",
    "opportunities_api.py",
    "universe_v2_fetchers.py",
}


def _repair_script() -> str:
    return (
        ROOT / "code" / "ops" / "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh"
    ).read_text(encoding="utf-8")


def _declared_gateway_closure(script: str) -> set[str]:
    match = re.search(
        r"^BUNDLE_FILES=\(\n(?P<body>.*?)^\)\n",
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None
    return set(re.findall(r'^\s+"([^"]+)"$', match.group("body"), re.MULTILINE))


def _bash_function(script: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}\(\) \{{.*?^\}}\n",
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None
    return match.group(0)


def test_deployment_repairs_the_exact_gateway_dependency_closure() -> None:
    script = _repair_script()

    assert "Inspect-only by default" in script
    assert "--apply" in script
    assert "--print-files" in script
    assert "--bundle-sha" in script
    assert "--hardening-sha" in script
    assert "LUMENCORE_HUMAN_UNLOCK_FILE" in script
    assert "LUMA_HUMAN_UNLOCK_TOKEN" not in script
    assert '[[ "$HUMAN_UNLOCK_FILE" =~ ^/tmp/lumencore-gateway-repair-' in script
    assert '[[ "$(stat -c \'%U:%a\' "$HUMAN_UNLOCK_FILE")" == "opc:600" ]]' in script
    assert "${#human_unlock_token} -lt 32" in script
    assert "unset human_unlock_token" in script
    for marker in (
        '[[ "$TARGET_ROOT" == "/opt/lumencore/code"',
        '&& "$STACK_ROOT" == "/opt/lumencore"',
        '&& "$PYTHON_BIN" == "/opt/lumencore/.venv/bin/python"',
        '&& "$SERVICE" == "luma-gateway"',
        '&& "$SERVICE_USER" == "lumencore"',
        '&& "$SERVICE_GROUP" == "lumencore"',
        '&& "$RUN_DIR" == "/opt/lumencore/run"',
        '&& "$SERVICE_DROP_IN_DIR" == "/etc/systemd/system/luma-gateway.service.d"',
        '&& "$SERVICE_DROP_IN" == "/etc/systemd/system/luma-gateway.service.d/20-lumencore-runtime-hardening.conf"',
        '&& "$LOCK_FILE" == "/opt/lumencore/run/luma_experience_gateway.lock"',
        '&& "$LOCAL_HEALTH_URL" == "http://127.0.0.1:8787/health"',
        '&& "$PUBLIC_HEALTH_URL" == "https://lumen-core.ai/health"',
        '&& "$LOCAL_STATUS_URL" == "http://127.0.0.1:8787/api/public/status"',
        '&& "$PUBLIC_STATUS_URL" == "https://lumen-core.ai/api/public/status"',
        '&& "$LOCAL_GATEWAY_BASE_URL" == "http://127.0.0.1:8787"',
        '&& "$PUBLIC_GATEWAY_BASE_URL" == "https://lumen-core.ai"',
    ):
        assert marker in script
    assert _declared_gateway_closure(script) == EXPECTED_GATEWAY_CLOSURE
    assert "LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256" in script
    assert "LUMENCORE_EXPECTED_GATEWAY_HARDENING_SHA256" in script
    assert "source closure does not match the approved bundle SHA-256" in script
    assert "service hardening does not match the approved SHA-256" in script
    assert '[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]' in script
    assert "PYTHONDONTWRITEBYTECODE=1" in script
    assert 'PYTHONPATH="$STAGE_DIR:$TARGET_ROOT"' in script
    assert "blocked_live_order" in script
    assert "luma-gateway" in script
    assert 'systemctl stop "$SERVICE"' in script
    assert 'systemctl start "$SERVICE"' in script
    assert "Rolling back the complete gateway dependency closure" in script
    assert "/opt/lumencore/code" in script
    assert "singleton lock owner absence was not confirmed; refusing removal" in script
    assert 'require_absent_lock_owner "$lock_pid" || {' in script
    assert script.count('lock_pid="$(read_gateway_lock_pid)"') == 2
    assert "tr -d '[:space:]'" not in script
    lock_reader = _bash_function(script, "read_gateway_lock_pid")
    assert '[[ $# -eq 0 ]] || return 14' in lock_reader
    assert '"$PYTHON_BIN" - "$LOCK_FILE"' in lock_reader
    assert 'stream.read(13)' in lock_reader
    presence_reader = _bash_function(script, "read_gateway_lock_presence")
    assert '[[ $# -eq 0 ]] || return 14' in presence_reader
    assert '"$PYTHON_BIN" - "$LOCK_FILE"' in presence_reader
    assert 'if exc.errno != errno.ENOENT:' in presence_reader
    assert _bash_function(script, "remove_verified_dead_lock").count('lock_presence="$(read_gateway_lock_presence)" || return $?') == 2
    assert "Removed verified dead-PID gateway singleton lock" in script
    assert "POST_APPLY_SOURCE_SHA256" in script
    assert "POST_APPLY_TARGET_SHA256" in script
    assert "POST_APPLY_HASH_PARITY=" in script
    assert "post-apply source/target SHA-256 mismatch" in script
    for marker in (
        "User=lumencore",
        "Group=lumencore",
        "Restart=on-failure",
        "StartLimitIntervalSec=300",
        "StartLimitBurst=10",
        "UMask=0027",
        "NoNewPrivileges=true",
        "PrivateTmp=true",
        'install -d -o "$run_uid" -g "$run_gid" -m "$run_mode" -- "$RUN_DIR"',
        'install_gateway_runtime_directory\nsystemctl daemon-reload',
        'systemctl daemon-reload',
        'effective gateway service identity is not lumencore:lumencore',
        'gateway singleton lock did not bind to the systemd main PID',
        'gateway singleton lock identity is not bounded',
        'checked_restore_step dropin_copy service_drop_in bounded_recovery_copy "$BACKUP_DIR/service-drop-in.before" "$SERVICE_DROP_IN" || finish_rollback "$rc"',
        'chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$SERVICE_DROP_IN_DIR"',
        'chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$RUN_DIR"',
        'if [[ "$SERVICE_WAS_ACTIVE" == true ]]',
        "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK",
    ):
        assert marker in script
    copy_wrapper = _bash_function(script, "bounded_recovery_copy")
    assert '[[ $# -eq 2 ]] || return 125' in copy_wrapper
    assert '"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s' in copy_wrapper
    assert 'cp -a -- "$1" "$2"' in copy_wrapper
    assert "GATEWAY_DEPENDENCY_CLOSURE_REPAIR_OK" in script
    for path in ("/metrics", "/openapi.json", "/docs", "/redoc"):
        assert f'  "{path}"' in script
    for marker in (
        "PROTECTED_OPERATOR_HTTP_PATHS=(",
        'PROTECTED_OPERATOR_WEBSOCKET_PATH="/ws"',
        "probe_operator_http_boundary()",
        "probe_operator_websocket_boundary()",
        '[[ "$status" == "401" || "$status" == "503" ]]',
        "operator API authentication required",
        "operator API access unavailable",
        "^cache-control:",
        "^pragma:",
        "^www-authenticate:",
        "awk grep seq sleep tr",
        '[[ "$status" == "403" || ( "$allow_not_found" == "true" && "$status" == "404" ) ]]',
        "local anonymous operator boundary failed",
        "public anonymous operator boundary failed",
        "local anonymous WebSocket boundary failed",
        "public anonymous WebSocket boundary failed",
        "Local anonymous operator HTTP boundaries:",
        "Public anonymous operator HTTP boundaries:",
        "Local anonymous WebSocket boundary:",
        "Public anonymous WebSocket boundary:",
    ):
        assert marker in script
    assert "Authorization: Bearer" not in script
    assert "x-luma-operator-token" not in script.lower()
    assert "rm -rf -- \"$TARGET_ROOT\"" not in script
    assert '[[ "$STAGE_DIR" =~ ^/tmp/lumencore-gateway-stage\\.' in script
    assert 'RECOVERY_ROOT="/var/backups/lumencore-gateway-repair"' in script
    assert 'rm -rf -- "$BACKUP_DIR"' not in script
    assert "systemctl restart" not in script


def _gateway_rollback_test_bash() -> str:
    if Path("/bin/bash").is_file():
        return "/bin/bash"
    # Git Bash can exercise these subprocess cases on Windows without WSL.
    git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
    if git_bash.is_file():
        return str(git_bash)
    raise RuntimeError("Bash is required for gateway rollback regression tests")


def _gateway_external_postcheck_step() -> str:
    workflow = (ROOT / ".github/workflows/repair-gateway-dependency-closure.yml").read_text(encoding="utf-8")
    section = workflow.split("      - name: Verify public gateway contracts after repair\n", 1)[1]
    section = section.split("      - name: Remove local private unlock staging\n", 1)[0]
    return textwrap.dedent(section.split("        run: |\n", 1)[1])


def _run_gateway_external_postcheck(case: str) -> dict:
    """Execute the actual workflow body with inert curl/jq responses; never use network/SSH.

    jq is stubbed only to select a contract failure; these are workflow control-flow
    and receipt tests, not an integration test of jq or HTTP server behavior.
    """
    with tempfile.TemporaryDirectory(prefix="gateway-postcheck-") as temporary:
        root = Path(temporary)
        receipts = root / "receipts"
        receipts.mkdir()
        temporary_files = root / "temporary-files"
        temporary_files.mkdir()
        helper_text = "\n".join((
            "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK", "Source commit: " + "a" * 40,
            "Bundle SHA-256: " + "b" * 64, "Service hardening SHA-256: " + "c" * 64,
            "Private helper outcome receipt SHA-256: " + "d" * 64, "",
        ))
        helper = receipts / "gateway-repair-receipt.txt"
        helper.write_bytes(helper_text.encode())
        if case == "bad_helper_binding":
            helper.write_bytes(helper_text.replace("Source commit: " + "a" * 40, "Source commit: " + "e" * 40).encode())
        if case == "start_collision":
            (receipts / "public-verification-started.json").mkdir()
        if case in {"terminal_collision_failure", "terminal_collision_success"}:
            (receipts / "public-verification-outcome.json").mkdir()
        body = _gateway_external_postcheck_step()
        assert "ssh " not in body and "sudo " not in body and "systemctl " not in body
        body = body.replace("/tmp/gateway-repair", receipts.as_posix())
        body = body.replace("${{ steps.package.outputs.bundle_sha }}", "b" * 64)
        body = body.replace("${{ steps.package.outputs.hardening_sha }}", "c" * 64)
        if case == "early_success_exit":
            body = body.replace("start_stage health_request\n", "exit 0\nstart_stage health_request\n", 1)
        stubs = r'''
python3() { "$FIXTURE_PYTHON" "$@"; }
jq() {
  if [[ "$FIXTURE_CASE" == contract_failure && "$POSTCHECK_STAGE" == status_contract ]]; then return 1; fi
  return 0
}
curl() {
  local output='' headers='' format='' url='' argument
  while [[ "$#" -gt 0 ]]; do
    argument="$1"; shift
    case "$argument" in
      -o|--output) output="$1"; shift ;;
      --dump-header) headers="$1"; shift ;;
      -w|--write-out) format="$1"; shift ;;
      --header|--max-time) shift ;;
      https://*) url="$argument" ;;
    esac
  done
  printf '%s\n' "$POSTCHECK_STAGE" >> "$FIXTURE_CALLS"
  printf '%s' 'SANITIZED_BODY_MUST_NOT_APPEAR_IN_RECEIPTS' > "$output"
  if [[ -n "$headers" ]]; then
    printf 'www-authenticate: Bearer\ncache-control: no-store\npragma: no-cache\n' > "$headers"
  fi
  if [[ "$POSTCHECK_STAGE" == health_request ]]; then
    case "$FIXTURE_CASE" in
      first_failure|terminal_collision_failure) return 22 ;;
      interrupted) kill -TERM "$$"; return 143 ;;
      helper_changed) printf '%s\n' 'unexpected helper output' >> "$FIXTURE_HELPER" ;;
    esac
  fi
  case "$POSTCHECK_STAGE" in
    health_request|status_request) printf 200 ;;
    websocket) printf 403 ;;
    docs) if [[ "$FIXTURE_CASE" == later_failure ]]; then printf '200\tapplication/json'; else printf '401\tapplication/json'; fi ;;
    *) printf '401\tapplication/json' ;;
  esac
}
'''
        script = root / "actual-postcheck.sh"
        script.write_bytes((stubs + "\n" + body).encode())
        env = dict(os.environ, FIXTURE_CASE=case, FIXTURE_PYTHON=sys.executable,
                   FIXTURE_CALLS=(root / "calls").as_posix(), FIXTURE_HELPER=helper.as_posix(),
                   TMPDIR=temporary_files.as_posix(), RELEASE_COMMIT="a" * 40,
                   BUNDLE_SHA="b" * 64, HARDENING_SHA="c" * 64,
                   GITHUB_RUN_ID="12345", GITHUB_RUN_ATTEMPT="2")
        result = subprocess.run([_gateway_rollback_test_bash(), script.as_posix()], cwd=root,
                                env=env, text=True, capture_output=True, timeout=20)
        records = {}
        for kind, filename in (("started", "public-verification-started.json"),
                               ("terminal", "public-verification-outcome.json")):
            path = receipts / filename
            if path.is_file():
                raw = path.read_bytes()
                assert b"SANITIZED_BODY_MUST_NOT_APPEAR_IN_RECEIPTS" not in raw
                records[kind] = json.loads(raw)
                records[kind + "_sha256"] = hashlib.sha256(raw).hexdigest()
        calls = root / "calls"
        return dict(rc=result.returncode, stdout=result.stdout, stderr=result.stderr,
                    records=records, calls=calls.read_text().splitlines() if calls.exists() else [],
                    remaining_temporary_files=list(temporary_files.iterdir()),
                    legacy_receipt=(receipts / "public-verification-receipt.txt").is_file())


def test_gateway_external_postcheck_first_and_later_failures_preserve_stage_and_status() -> None:
    for case, code, stage, calls, completed in (
        ("first_failure", 22, "health_request", 1, []),
        ("contract_failure", 1, "status_contract", 2, ["health_request", "status_request", "health_contract"]),
        ("later_failure", 1, "docs", 5, ["health_request", "status_request", "health_contract", "status_contract", "metrics", "openapi_json"]),
    ):
        result = _run_gateway_external_postcheck(case)
        assert result["rc"] == code, result
        terminal = result["records"]["terminal"]
        assert terminal["original_exit_code"] == code and terminal["stage"] == stage
        assert terminal["stage_began"] and not terminal["stage_completed"]
        assert terminal["completed_stages"] == completed and len(result["calls"]) == calls
        assert terminal["status"] == "EXTERNAL_VERIFICATION_FAILED"
        assert not terminal["restoration_attempted"] and not terminal["restoration_verified"]
        assert not result["remaining_temporary_files"] and not result["legacy_receipt"]


def test_gateway_external_postcheck_success_binds_run_helper_and_complete_stages() -> None:
    result = _run_gateway_external_postcheck("success")
    assert result["rc"] == 0, result
    start, terminal = result["records"]["started"], result["records"]["terminal"]
    assert start["status"] == "EXTERNAL_VERIFICATION_STARTED_UNKNOWN"
    assert terminal["status"] == "EXTERNAL_CHECKS_PASSED"
    assert terminal["started_receipt_sha256"] == result["records"]["started_sha256"]
    assert terminal["binding"] == start["binding"]
    assert terminal["binding"]["RELEASE_COMMIT"] == "a" * 40
    assert terminal["binding"]["BUNDLE_SHA"] == "b" * 64
    assert terminal["binding"]["HARDENING_SHA"] == "c" * 64
    assert terminal["binding"]["GITHUB_RUN_ID"] == "12345"
    assert terminal["binding"]["GITHUB_RUN_ATTEMPT"] == "2"
    assert terminal["binding"]["helper_outcome_reported_sha256"] == "d" * 64
    assert len(terminal["completed_stages"]) == 10 and len(result["calls"]) == 7
    assert terminal["stage"] == "complete" and terminal["original_exit_code"] == 0
    assert not any(terminal[key] for key in ("interrupted", "restoration_attempted", "restoration_verified", "service_state_verified", "production_readiness_verified"))
    assert result["legacy_receipt"] and not result["remaining_temporary_files"]


def test_gateway_external_postcheck_persistence_failure_never_becomes_success() -> None:
    for case, code in (("terminal_collision_failure", 22), ("terminal_collision_success", 97), ("helper_changed", 97)):
        result = _run_gateway_external_postcheck(case)
        assert result["rc"] == code, result
        assert "started" in result["records"] and "terminal" not in result["records"]
        assert "outcome persistence failed" in result["stderr"]
        assert not result["remaining_temporary_files"]


def test_gateway_external_postcheck_invalid_start_refuses_all_probes() -> None:
    for case in ("bad_helper_binding", "start_collision"):
        result = _run_gateway_external_postcheck(case)
        assert result["rc"] == 96, result
        assert result["calls"] == [] and result["records"] == {}
        assert not result["legacy_receipt"]


def test_gateway_external_postcheck_interruption_and_incomplete_zero_exit_remain_unknown() -> None:
    for case, code, status in (("interrupted", 143, "UNKNOWN_INTERRUPTED_EXTERNAL_VERIFICATION"),
                               ("early_success_exit", 97, "UNKNOWN_INCOMPLETE_EXTERNAL_VERIFICATION")):
        result = _run_gateway_external_postcheck(case)
        assert result["rc"] == code, result
        terminal = result["records"]["terminal"]
        assert terminal["status"] == status and not terminal["restoration_attempted"]
        assert terminal["original_exit_code"] == (143 if case == "interrupted" else 0)
        assert terminal["interrupted"] == (case == "interrupted")
        assert not result["legacy_receipt"] and not result["remaining_temporary_files"]


def _gateway_post_mutation_guards(script: str) -> list[str]:
    segment = script.split('systemctl stop "$SERVICE"\nSERVICE_STOPPED=true', 1)[1]
    segment = segment.split("\nprobe_json() {", 1)[0]
    guards = re.findall(
        r'(?m)^\s*(?:\[\[ [^\n]+ \]\]|systemctl is-active --quiet "\$SERVICE")'
        r' \|\| \{\n[^\n]*\n[^\n]*\n[ \t]*\}',
        segment,
    )
    assert len(guards) == 12, "Exercise every post-mutation failure guard"
    return guards


def _write_lock_probe_runtime(root: Path) -> None:
    # Execute the production stdin body, replacing only os.kill. Never call
    # native Windows os.kill (even signal zero can have different semantics).
    (root / "lock-probe-runtime.py").write_text(r'''
import errno
import os
import sys
from pathlib import Path

source = sys.stdin.read()
mode = os.environ.get("LOCK_PROBE_CASE", "dead")
def fixture_probe(pid, number):
    assert number == 0
    with Path("lock-probe.calls").open("a") as stream:
        stream.write(f"{pid}:{number}\n")
    if mode == "live": return None
    if mode == "dead": raise ProcessLookupError(errno.ESRCH, "fixture")
    if mode == "permission": raise PermissionError(errno.EPERM, "fixture")
    if mode == "invalid": raise OSError(errno.EINVAL, "fixture")
    if mode == "unknown": raise OSError(errno.EIO, "fixture")
    if mode == "unclassified_lookup": raise ProcessLookupError("fixture without errno")
    if mode == "overflow": raise OverflowError("fixture")
    if mode == "value": raise ValueError("fixture")
    raise RuntimeError("unexpected fixture probe error")
os.kill = fixture_probe
if os.environ.get("LOCK_READ_CASE") == "permission":
    def denied_open(*args, **kwargs): raise PermissionError(errno.EACCES, "fixture")
    os.open = denied_open
if 'sys.stdout.write("ABSENT")' in source:
    calls = Path("lock-presence.calls")
    previous = calls.read_text() if calls.exists() else ""
    calls.write_text(previous + "observe\n")
    stage = "initial" if not previous else "after"
    requested = os.environ.get("LOCK_PRESENCE_CASE", "")
    if requested.startswith(stage + ":"):
        case = requested.split(":", 1)[1]
        if case in {"empty", "wrong", "trailing_lf", "print_then_failure", "interpreter_failure"}:
            sys.stdout.write({"empty": "", "wrong": "UNKNOWN", "trailing_lf": "ABSENT\n",
                              "print_then_failure": "ABSENT", "interpreter_failure": ""}[case])
            raise SystemExit(29 if case in {"print_then_failure", "interpreter_failure"} else 0)
        def fixture_lstat(*args, **kwargs):
            if case == "unclassified_lookup": raise FileNotFoundError("fixture without errno")
            raise OSError({"enoent": errno.ENOENT, "permission": errno.EACCES,
                           "eperm": errno.EPERM, "not_directory": errno.ENOTDIR,
                           "unknown": errno.EIO}[case], "fixture")
        os.lstat = fixture_lstat
sys.argv = sys.argv[1:]
exec(compile(source, "<actual-lock-owner-probe>", "exec"), {"__name__": "__main__"})
''', encoding="utf-8", newline="\n")
    (root / "lock-remove-result.py").write_text('''
import os
import sys
from pathlib import Path
p = Path(sys.argv[1])
case = os.environ.get("LOCK_REMOVE_CASE", "")
if case == "regular": p.write_bytes(b"intervening lock owner\\n")
elif case == "directory": p.mkdir()
elif case == "symlink": p.symlink_to(p.parent / "missing-lock-target")
elif case: raise AssertionError(case)
''', encoding="utf-8", newline="\n")


def _run_gateway_lock_file_case(raw: bytes, caller: str, *, main_pid: str = "12",
                                probe_case: str = "dead", read_case: str = "",
                                file_kind: str = "regular", extra_argument: bool = False,
                                presence_case: str = "", remove_case: str = "") -> dict:
    script = _repair_script()
    with tempfile.TemporaryDirectory(prefix="gateway-lock-bytes-test-") as directory:
        root = Path(directory)
        lock = root / "fixture.lock"
        if file_kind == "regular": lock.write_bytes(raw)
        elif file_kind == "directory": lock.mkdir()
        elif file_kind in {"symlink", "dangling"}:
            outside = root / "outside.lock"
            if file_kind == "symlink": outside.write_bytes(raw)
            lock.symlink_to(outside)
        elif file_kind != "missing": raise AssertionError(file_kind)
        _write_lock_probe_runtime(root)
        harness = r'''
set -Eeuo pipefail
LOCK_FILE="$PWD/fixture.lock"
SERVICE=fixture
PYTHON_BIN=fixture_lock_python
RECOVERY_TIMEOUT_BIN=fixture_timeout
fixture_timeout() {
  [[ "$1 $2 $3" == '--signal=TERM --kill-after=5s 60s' ]] || return 99
  shift 3
  "$@"
}
fixture_lock_python() {
  if [[ "$LOCK_READ_CASE" == launcher_failure ]]; then return 29; fi
  "$TEST_PYTHON" "$PWD/lock-probe-runtime.py" "$@"
}
systemctl() { printf '%s\n' "$MAIN_PID"; }
sleep() { printf 'sleep\n' >> "$PWD/sleep.calls"; }
rollback() { printf '%s\n' "$1" >> "$PWD/rollback.calls"; exit "$1"; }
rm() {
  printf 'remove\n' >> "$PWD/remove.calls"
  if [[ "$LOCK_REMOVE_CASE" == noop ]]; then return 0; fi
  command rm "$@" || return $?
  "$TEST_PYTHON" "$PWD/lock-remove-result.py" "$LOCK_FILE"
}
'''
        for name in ("read_gateway_lock_pid", "require_absent_lock_owner", "read_gateway_lock_presence", "bounded_recovery_mutation", "remove_verified_dead_lock"):
            harness += _bash_function(script, name) + "\n"
        if caller == "cleanup": harness += "remove_verified_dead_lock\n"
        elif caller == "reader": harness += "read_gateway_lock_pid" + (" ignored" if extra_argument else "") + "\n"
        elif caller == "presence": harness += "read_gateway_lock_presence" + (" ignored" if extra_argument else "") + "\n"
        elif caller == "identity":
            # Execute the actual post-start polling and failure guard, replacing
            # only systemd, sleep and rollback side effects with bounded stubs.
            identity = script.split("\nlock_ready=false\n", 1)[1]
            identity = identity.split('[[ "$(stat -c \'%U:%G:%a\' "$LOCK_FILE")"', 1)[0]
            harness += "lock_ready=false\n" + identity
        else: raise AssertionError(caller)
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        completed = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
            env=dict(os.environ, TEST_PYTHON=Path(sys.executable).as_posix(), MAIN_PID=main_pid,
                     LOCK_PROBE_CASE=probe_case, LOCK_READ_CASE=read_case,
                     LOCK_PRESENCE_CASE=presence_case, LOCK_REMOVE_CASE=remove_case),
            capture_output=True, text=True, timeout=10, check=False)
        result = {"completed": completed, "exists": lock.exists() or lock.is_symlink()}
        for name in ("lock-probe", "lock-presence", "sleep", "rollback", "remove"):
            path = root / (name + ".calls")
            result[name] = path.read_text() if path.exists() else ""
        return result


def test_gateway_lock_file_grammar_refuses_malformed_original_bytes_at_both_callers() -> None:
    malformed = (b"1 2", b"1\t2", b"1\n2", b"12\n\n", b"12\r", b"12\r\r\n",
                 b" 12", b"12 ", b"12\x00", b"1\x002", b"", b"\n", b"0", b"01",
                 b"-12", b"+12", b"2147483648", b"9" * 13, b"12" + b" " * 65536,
                 "１２".encode("utf-8"), "١٢".encode("utf-8"), b"\xef\xbb\xbf12")
    for raw in malformed:
        for caller, expected in (("cleanup", 14), ("identity", 18)):
            result = _run_gateway_lock_file_case(raw, caller)
            assert result["completed"].returncode == expected, (raw[:30], caller, result)
            assert result["exists"] and result["lock-probe"] == result["remove"] == result["sleep"] == ""
            assert result["rollback"] == ("18\n" if caller == "identity" else "")


def test_gateway_lock_file_valid_grammar_and_identity_mismatch_controls() -> None:
    for raw in (b"12", b"12\n", b"12\r\n", b"2147483647\r\n"):
        expected = raw.rstrip(b"\r\n").decode("ascii")
        cleanup = _run_gateway_lock_file_case(raw, "cleanup")
        assert cleanup["completed"].returncode == 0 and not cleanup["exists"], cleanup
        assert cleanup["lock-probe"] == expected + ":0\n" and cleanup["remove"] == "remove\n"
        identity = _run_gateway_lock_file_case(raw, "identity", main_pid=expected)
        assert identity["completed"].returncode == 0 and identity["exists"], identity
        assert identity["lock-probe"] == identity["remove"] == identity["sleep"] == ""
    mismatch = _run_gateway_lock_file_case(b"12\n", "identity", main_pid="13")
    assert mismatch["completed"].returncode == 18 and mismatch["exists"]
    assert mismatch["sleep"] == "sleep\n" * 12 and mismatch["remove"] == mismatch["lock-probe"] == ""
    live = _run_gateway_lock_file_case(b"12", "cleanup", probe_case="live")
    assert live["completed"].returncode == 14 and live["exists"] and live["remove"] == ""
    assert live["lock-probe"] == "12:0\n"


def test_gateway_lock_file_reader_errors_and_argument_refuse_without_probe() -> None:
    for read_case, expected in (("permission", 14), ("launcher_failure", 29)):
        for caller in ("cleanup", "identity"):
            result = _run_gateway_lock_file_case(b"12", caller, read_case=read_case)
            assert result["completed"].returncode == (18 if caller == "identity" else expected), result
            assert result["exists"] and result["remove"] == result["lock-probe"] == ""
    for kind in ("missing", "directory"):
        result = _run_gateway_lock_file_case(b"12", "reader", file_kind=kind)
        assert result["completed"].returncode == 14 and result["completed"].stdout == "", result
    result = _run_gateway_lock_file_case(b"12", "reader", extra_argument=True)
    assert result["completed"].returncode == 14 and result["completed"].stdout == ""


@unittest.skipIf(os.name != "posix", "Actual lock-reader symlink checks require Linux CI")
def test_gateway_lock_file_reader_rejects_links_without_probe() -> None:
    for kind in ("symlink", "dangling"):
        result = _run_gateway_lock_file_case(b"12", "reader", file_kind=kind)
        assert result["completed"].returncode == 14 and result["exists"]
        assert result["remove"] == result["lock-probe"] == result["completed"].stdout == ""


def _run_gateway_rollback_guard(
    guard: str, *, predicate_passes: bool, copy_fails: bool = False,
    signal_during_copy: bool = False,
    recovery_case: str | None = None, evidence: dict | None = None,
    service_failure: str = "", service_exit_code: int = 9,
    service_was_active: bool = True, real_timeout_mode: str = "",
    restore_fault: str = "", second_source: bool = False, prior_dropin: bool = False,
    directory_case: str = "", metadata_case: str = "", real_lock_case: str = "",
    lock_file_bytes: bytes | None = None,
    lock_presence_case: str = "", lock_remove_case: str = "",
    source_drift: str = "", drift_boundary: str = "stop", source_query_case: str = "",
    target_drift: str = "", target_boundary: str = "stop", forward_case: str = "",
    target_query_case: str = "", target_relative: str = "",
    result_fault: str = "", result_relative: str = "entry.py", result_query_case: str = "",
    dropin_fault: str = "", dropin_query_case: str = "",
    runtime_directory_fault: str = "", runtime_directory_query_case: str = "",
    dropin_directory_fault: str = "", dropin_directory_query_case: str = "",
    dropin_target_drift: str = "", dropin_target_boundary: str = "stop",
    dropin_forward_case: str = "", dropin_target_query_case: str = "",
    run_target_drift: str = "", run_target_boundary: str = "stop",
    run_forward_case: str = "", run_target_query_case: str = "",
    dropin_dir_drift: str = "", dropin_dir_boundary: str = "before_directory_restore",
    dropin_dir_forward_case: str = "", dropin_dir_query_case: str = "",
    copy_deadline_target: str = "", copy_deadline_exit_code: int = 124,
    copy_deadline_partial: bool = False,
    mutation_deadline_fault: str = "", mutation_deadline_exit_code: int = 124,
    mutation_deadline_after: bool = False,
    forward_lock_deadline_failure: bool = False,
    evidence_deadline_kind: str = "", evidence_deadline_exit_code: int = 124,
    evidence_deadline_after: bool = False,
    target_deadline_query: str = "", target_deadline_exit_code: int = 124,
    target_deadline_after: bool = True,
) -> tuple[subprocess.CompletedProcess[str], bytes | None, bool]:
    script = _repair_script()
    # Execute the actual guard and actual rollback body. Every filesystem target
    # is a disposable fixture; systemd, ownership and runtime probes are stubs.
    rollback_source = _bash_function(script, "rollback")
    error_trap = next(
        line for line in script.splitlines()
        if line.startswith("trap 'rc=$?;") and line.endswith(" ERR")
    )
    with tempfile.TemporaryDirectory(prefix="gateway-rollback-test-") as directory:
        root = Path(directory)
        for relative in ("target", "backup/existing", "dropins", "run"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "target/entry.py").write_bytes(b"candidate source\n")
        (root / "backup/existing/entry.py").write_bytes(b"previous source\n")
        (root / "dropins/hardening.conf").write_bytes(b"candidate hardening\n")
        run_info = (root / "run").stat()
        dropin_dir_info = (root / "dropins").stat()
        for name, value in {
            "service-drop-in.state": "missing\n",
            "service-drop-in-dir.state": "present\n",
            "service-drop-in-dir.metadata": f"{dropin_dir_info.st_uid} {dropin_dir_info.st_gid} {dropin_dir_info.st_mode & 0o7777:o}\n",
            "run-dir.state": "present\n",
            "run-dir.metadata": f"{run_info.st_uid} {run_info.st_gid} {run_info.st_mode & 0o7777:o}\n",
            "service.state": f"service_was_active={str(service_was_active).lower()}\n",
        }.items():
            (root / "backup" / name).write_text(value, encoding="utf-8", newline="\n")
        if second_source:
            (root / "target/second.py").write_bytes(b"second candidate\n")
            (root / "backup/existing/second.py").write_bytes(b"second previous\n")
        if prior_dropin:
            (root / "backup/service-drop-in.state").write_text("present\n")
            (root / "backup/service-drop-in.before").write_bytes(b"previous hardening\n")
        if directory_case:
            family = "service-drop-in-dir" if directory_case.endswith("dropin") else "run-dir"
            folder = root / ("dropins" if directory_case.endswith("dropin") else "run")
            (root / f"backup/{family}.state").write_text("missing\n", newline="\n")
            (root / f"backup/{family}.metadata").unlink()
            if directory_case.startswith("nonempty"):
                (folder / "unrelated-retained").write_bytes(b"preserve unrelated bytes\n")
            if directory_case.startswith("absent"):
                if (folder / "hardening.conf").exists():
                    (folder / "hardening.conf").unlink()
                folder.rmdir()
        if metadata_case and not metadata_case.startswith("missing:"):
            filename, invalid = metadata_case.split(":", 1)
            (root / "backup" / filename).write_text(invalid + "\n")
        if runtime_directory_fault in {"uid_mismatch", "gid_mismatch"}:
            # Ownership calls are stubs. Bind a different numeric expectation
            # to show a zero exit cannot substitute for matching actual metadata.
            (root / "backup/run-dir.metadata").write_text(
                f"{run_info.st_uid + (runtime_directory_fault == 'uid_mismatch')} "
                f"{run_info.st_gid + (runtime_directory_fault == 'gid_mismatch')} {run_info.st_mode & 0o7777:o}\n", newline="\n")
        if runtime_directory_fault:
            (root / "runtime-directory-fault.py").write_text('''from pathlib import Path
import os
p = Path("run")
kind = os.environ["RUNTIME_DIRECTORY_FAULT"]
if kind == "file": p.rmdir(); p.write_bytes(b"not a directory")
elif kind == "missing": p.rmdir()
elif kind == "mode": p.chmod(0o700 if p.stat().st_mode & 0o7777 != 0o700 else 0o755)
elif kind == "symlink": p.rename("outside-run"); p.symlink_to(Path("outside-run").resolve(), target_is_directory=True)
elif kind == "dangling_symlink": p.symlink_to(Path("missing-run-target").resolve(), target_is_directory=True)
elif kind == "parent_mode": p.parent.chmod(0o777)
elif kind == "state_changed": Path("backup/run-dir.state").write_bytes(b"missing\\n")
elif kind == "metadata_changed": Path("backup/run-dir.metadata").write_bytes(b"0 0 700\\n")
elif kind == "manifest_changed":
    q=Path("backup/prepared.json"); q.write_bytes(q.read_bytes()+b" ")
elif kind in {"uid_mismatch", "gid_mismatch", "remove_noop"}: pass
else: raise ValueError("unsupported_runtime_directory_fault")
Path("runtime-directory-fault-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if dropin_directory_fault in {"uid_mismatch", "gid_mismatch"}:
            # Ownership calls are stubs. Bind a different numeric expectation
            # to show a zero exit cannot substitute for matching actual metadata.
            (root / "backup/service-drop-in-dir.metadata").write_text(
                f"{dropin_dir_info.st_uid + (dropin_directory_fault == 'uid_mismatch')} "
                f"{dropin_dir_info.st_gid + (dropin_directory_fault == 'gid_mismatch')} {dropin_dir_info.st_mode & 0o7777:o}\n", newline="\n")
        if dropin_directory_fault:
            (root / "dropin-directory-fault.py").write_text('''from pathlib import Path
import os
p = Path("dropins")
kind = os.environ["DROPIN_DIRECTORY_FAULT"]
if kind == "file": p.rmdir(); p.write_bytes(b"not a directory")
elif kind == "missing": p.rmdir()
elif kind == "mode": p.chmod(0o700 if p.stat().st_mode & 0o7777 != 0o700 else 0o755)
elif kind == "symlink": p.rename("outside-dropin-dir"); p.symlink_to(Path("outside-dropin-dir").resolve(), target_is_directory=True)
elif kind == "dangling_symlink": p.symlink_to(Path("missing-dropin-dir-target").resolve(), target_is_directory=True)
elif kind == "parent_mode": p.parent.chmod(0o777)
elif kind == "state_changed": Path("backup/service-drop-in-dir.state").write_bytes(b"missing\\n")
elif kind == "metadata_changed": Path("backup/service-drop-in-dir.metadata").write_bytes(b"0 0 700\\n")
elif kind == "manifest_changed":
    q=Path("backup/prepared.json"); q.write_bytes(q.read_bytes()+b" ")
elif kind in {"uid_mismatch", "gid_mismatch", "remove_noop"}: pass
else: raise ValueError("unsupported_dropin_directory_fault")
Path("dropin-directory-fault-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if dropin_dir_drift:
            (root / "dropin-dir-drift.py").write_text('''from pathlib import Path
import os
p=Path("dropins"); kind=os.environ["DROPIN_DIR_DRIFT"]
if kind == "identity": p.rename("prior-dropin-dir"); p.mkdir(); p.chmod(0o755)
elif kind == "missing": p.rmdir()
elif kind == "file": p.rmdir(); p.write_bytes(b"intervening directory replacement")
elif kind == "mode": p.chmod(0o700)
elif kind == "symlink": p.rename("outside-dropin-dir"); p.symlink_to(Path("outside-dropin-dir").resolve(), target_is_directory=True)
elif kind == "children": (p/"new-child").mkdir(); (p/"new-child").rmdir()
elif kind == "parent_mode": p.parent.chmod(0o777)
else: raise ValueError("unsupported_dropin_directory_drift")
Path("dropin-dir-drift-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if run_target_drift:
            (root / "run-target-drift.py").write_text('''from pathlib import Path
import os
p=Path("run"); kind=os.environ["RUN_TARGET_DRIFT"]
if kind == "identity": p.rename("prior-run-identity"); p.mkdir()
elif kind == "missing": p.rmdir()
elif kind == "file": p.rmdir(); p.write_bytes(b"intervening file")
elif kind == "mode": p.chmod(0o700)
elif kind == "symlink": p.rename("outside-run"); p.symlink_to(Path("outside-run").resolve(), target_is_directory=True)
elif kind == "children": (p/"new-child").mkdir(); (p/"new-child").rmdir()
elif kind == "parent_mode": p.parent.chmod(0o777)
else: raise ValueError("unsupported_runtime_directory_drift")
Path("run-target-drift-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if source_drift:
            # Controlled interleavings in disposable paths only. The production
            # verifier and rollback body are extracted without modification.
            (root / "source-drift.py").write_text('''from pathlib import Path
import os
kind = os.environ["SOURCE_DRIFT"]
assert kind in {"missing", "changed", "directory", "mtime", "mode", "unexpected", "symlink", "hardlink", "xattr"}
relative = "absent.py" if kind == "unexpected" else "second.py" if os.environ["DRIFT_BOUNDARY"] == "after_first_copy" else "entry.py"
p = Path("backup/existing") / relative
if kind == "missing": p.unlink()
elif kind in {"changed", "unexpected"}: p.write_bytes(b"intervening backup bytes\\n")
elif kind == "directory": p.unlink(); p.mkdir()
elif kind == "mtime":
    current = p.stat(); os.utime(p, ns=(current.st_atime_ns, current.st_mtime_ns + 1000000000))
elif kind == "mode": p.chmod(0o400)
elif kind == "symlink": p.unlink(); p.symlink_to(Path("target").resolve() / relative)
elif kind == "hardlink": os.link(p, "outside-hardlink")
elif kind == "xattr": os.setxattr(p, "user.fixture", b"changed")
Path("source-drift-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if target_drift:
            (root / "target-drift.py").write_text('''from pathlib import Path
import os
kind = os.environ["TARGET_DRIFT"]
relative = os.environ["TARGET_RELATIVE"] or ("second.py" if os.environ["TARGET_BOUNDARY"] == "after_first_copy" else "entry.py")
assert relative in {"entry.py", "second.py", "absent.py"}
p = Path("target") / relative
if kind == "missing": p.unlink()
elif kind in {"changed", "reappeared"}: p.write_bytes(b"intervening target bytes\\n")
elif kind == "identity":
    q = p.with_name("replacement"); q.write_bytes(p.read_bytes()); q.replace(p)
elif kind == "directory": p.unlink(); p.mkdir()
elif kind == "mtime":
    current = p.stat(); os.utime(p, ns=(current.st_atime_ns, current.st_mtime_ns + 1000000000))
elif kind == "mode": p.chmod(0o400)
elif kind == "symlink":
    q = Path("outside-target"); q.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(q.resolve())
elif kind == "hardlink": os.link(p, "outside-target")
elif kind == "parent_link":
    q=Path("target"); q.rename("outside-target-directory"); q.symlink_to(Path("outside-target-directory").resolve(), target_is_directory=True)
elif kind == "xattr": os.setxattr(p, "user.fixture", b"changed")
else: raise ValueError("unsupported_fixture_drift")
Path("target-drift-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if result_fault:
            (root / "result-fault.py").write_text('''from pathlib import Path
import os
kind, relative = os.environ["RESULT_FAULT"], os.environ["RESULT_RELATIVE"]
assert relative in {"entry.py", "second.py", "absent.py"}
p = Path("target") / relative
if kind == "copy_bytes": p.write_bytes(b"wrong restoration bytes\\n")
elif kind == "copy_mtime":
    current=p.stat(); os.utime(p, ns=(current.st_atime_ns, current.st_mtime_ns + 1000000000))
elif kind == "copy_mode": p.chmod(0o400)
elif kind == "copy_xattr": os.setxattr(p, "user.fixture", b"incorrect-result")
elif kind == "copy_directory": p.unlink(); p.mkdir()
elif kind == "copy_symlink":
    q=Path("outside-result"); q.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(q.resolve())
elif kind == "copy_hardlink": os.link(p, "outside-result")
elif kind == "copy_parent_link":
    q=Path("target"); q.rename("outside-result-directory"); q.symlink_to(Path("outside-result-directory").resolve(), target_is_directory=True)
elif kind == "remove_symlink": p.symlink_to(Path("uncreated-result").resolve())
elif kind == "manifest_changed": Path("backup/prepared.json").write_bytes(b"changed preparation")
elif kind == "backup_changed": (Path("backup/existing") / relative).write_bytes(b"changed backup")
else: raise ValueError("unsupported_result_fault")
Path("result-fault-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if dropin_fault:
            (root / "dropin-fault.py").write_text('''from pathlib import Path
import os
kind = os.environ["DROPIN_FAULT"]
p = Path("dropins/hardening.conf")
if kind == "copy_bytes": p.write_bytes(b"wrong drop-in result\\n")
elif kind == "copy_mtime":
    current=p.stat(); os.utime(p, ns=(current.st_atime_ns, current.st_mtime_ns + 1000000000))
elif kind == "copy_mode": p.chmod(0o400)
elif kind == "copy_xattr": os.setxattr(p, "user.fixture", b"incorrect-dropin")
elif kind == "copy_directory": p.unlink(); p.mkdir()
elif kind == "copy_symlink":
    q=Path("outside-dropin"); q.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(q.resolve())
elif kind == "copy_hardlink": os.link(p, "outside-dropin")
elif kind in {"copy_parent_link", "remove_parent_link"}:
    q=Path("dropins"); q.rename("outside-dropin-directory"); q.symlink_to(Path("outside-dropin-directory").resolve(), target_is_directory=True)
elif kind == "copy_parent_mode": p.parent.chmod(0o777)
elif kind == "remove_symlink": p.symlink_to(Path("uncreated-dropin").resolve())
elif kind == "remove_parent_file": p.parent.rmdir(); p.parent.write_bytes(b"not a directory")
elif kind == "manifest_changed": Path("backup/prepared.json").write_bytes(b"changed preparation")
elif kind == "backup_changed": Path("backup/service-drop-in.before").write_bytes(b"changed backup")
elif kind == "state_changed": Path("backup/service-drop-in.state").write_bytes(b"missing\\n")
else: raise ValueError("unsupported_dropin_fault")
Path("dropin-fault-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        if dropin_target_drift:
            (root / "dropin-target-drift.py").write_text('''from pathlib import Path
import os
kind = os.environ["DROPIN_TARGET_DRIFT"]
p = Path("dropins/hardening.conf")
if kind in {"changed", "reappeared"}: p.write_bytes(b"intervening drop-in writer\\n")
elif kind == "missing": p.unlink()
elif kind == "identity":
    q=p.with_name("replacement"); q.write_bytes(p.read_bytes()); q.replace(p)
elif kind == "mtime":
    t=p.stat(); os.utime(p, ns=(t.st_atime_ns,t.st_mtime_ns+1000000000))
elif kind == "mode": p.chmod(0o400)
elif kind == "directory": p.unlink(); p.mkdir()
elif kind == "symlink":
    q=Path("outside-dropin-target"); q.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(q.resolve())
elif kind == "hardlink": os.link(p,"outside-dropin-target")
elif kind == "parent_link":
    q=Path("dropins"); q.rename("outside-dropin-parent"); q.symlink_to(Path("outside-dropin-parent").resolve(),target_is_directory=True)
elif kind == "xattr": os.setxattr(p,"user.fixture",b"intervening")
else: raise ValueError("unsupported_dropin_target_drift")
Path("dropin-target-drift-applied").write_text(kind)
''', encoding="utf-8", newline="\n")
        harness = r'''
set -Eeuo pipefail
TARGET_ROOT="$PWD/target"
SOURCE_ROOT="$PWD/source"
BACKUP_DIR="$PWD/backup"
SERVICE_DROP_IN_DIR="$PWD/dropins"
SERVICE_DROP_IN="$SERVICE_DROP_IN_DIR/hardening.conf"
RUN_DIR="$PWD/run"
LOCK_FILE="$RUN_DIR/fixture.lock"
SERVICE=fixture-gateway
SERVICE_USER=lumencore
SERVICE_GROUP=lumencore
BUNDLE_FILES=(entry.py)
rel=entry.py
HARDENING_SHA=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
SOURCE_COMMIT=0123456789abcdef0123456789abcdef01234567
BUNDLE_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
RECOVERY_MANIFEST_SHA=""
RECOVERY_SERVICE_RESULTS=""
RECOVERY_SERVICE_FAILURE=""
RECOVERY_RESTORE_ATTEMPTED=false
RECOVERY_RESTORE_FAILURE=""
RECOVERY_RESTORE_EXIT_CODE=0
RECOVERY_RESTORE_TARGET=""
RECOVERY_DROPIN_RESULT=NOT_CHECKED
RECOVERY_RUNTIME_DIRECTORY_RESULT=NOT_CHECKED
DROPIN_WRITE_STATE=UNTOUCHED
DROPIN_TARGET_VERSION=""
DROPIN_DIR_WRITE_STATE=UNTOUCHED
DROPIN_DIR_TARGET_VERSION=""
DROPIN_DIR_CANDIDATE_METADATA="0:0:755"
RUN_WRITE_STATE=UNTOUCHED
RUN_TARGET_VERSION=""
RUN_CANDIDATE_METADATA="$("$TEST_PYTHON" -c 'import os;print(str(os.getuid() if hasattr(os,"getuid") else 0)+":"+str(os.getgid() if hasattr(os,"getgid") else 0)+":750")')"
declare -A SOURCE_WRITE_STATES=() SOURCE_CANDIDATE_SHA=() SOURCE_TARGET_VERSION=() SOURCE_RESULT_STATES=()
python3() { "$TEST_PYTHON" "$@"; }
FIXTURE_FORWARD=false
FIXTURE_DROPIN_FORWARD=false
FIXTURE_DROPIN_DIR_FORWARD=false
FIXTURE_RUN_FORWARD=false
RECOVERY_TIMEOUT_BIN=fixture_timeout
fixture_timeout() {
  [[ "$1 $2 $3" == '--signal=TERM --kill-after=5s 60s' ]] || return 99
  shift 3
  if [[ "$1" == python3 && "$3" == "$TARGET_ROOT" ]]; then
    [[ "$2" == - && "$4" == "$SERVICE_DROP_IN" && "$5" == "$RUN_DIR" ]] || return 99
    local target_phase=rollback target_query
    if [[ "${RECOVERY_RESTORE_ATTEMPTED:-false}" != true && ( "$FIXTURE_FORWARD" == true || "$FIXTURE_DROPIN_FORWARD" == true || "$FIXTURE_DROPIN_DIR_FORWARD" == true || "$FIXTURE_RUN_FORWARD" == true ) ]]; then target_phase=forward; fi
    target_query="$6:$7:$8:$target_phase"
    printf '%s\n' "$target_query" >> "$PWD/target-timeout.calls"
    if [[ "$TARGET_DEADLINE_QUERY" == "$target_query" ]]; then
      if [[ "$TARGET_DEADLINE_AFTER" == true ]]; then "$@" || return $?; fi
      return "$TARGET_DEADLINE_EXIT_CODE"
    fi
  elif [[ "$1" == python3 && "$3" == "$BACKUP_DIR" ]]; then
    printf '%s\n' "$4" >> "$PWD/evidence-timeout.calls"
    if [[ "$EVIDENCE_DEADLINE_KIND" == "$4" ]]; then
      # Simulate failure after real fixture publication/output as well as before
      # it. A valid-looking response must not turn a nonzero launch into success.
      if [[ "$EVIDENCE_DEADLINE_AFTER" == true ]]; then "$@" || return $?; fi
      return "$EVIDENCE_DEADLINE_EXIT_CODE"
    fi
  fi
  if [[ "$1" == cp ]]; then
    [[ $# -eq 5 && "$2 $3" == '-a --' ]] || return 99
    local copy_target=unknown
    case "$5" in
      "$TARGET_ROOT/entry.py") copy_target=first_source ;;
      "$TARGET_ROOT/second.py") copy_target=second_source ;;
      "$SERVICE_DROP_IN") copy_target=dropin ;;
    esac
    printf '%s\n' "$copy_target" >> "$PWD/copy-timeout.calls"
    if [[ "$COPY_DEADLINE_TARGET" == "$copy_target" ]]; then
      if [[ "$COPY_DEADLINE_PARTIAL" == true ]]; then printf 'partial copy\n' > "$5"; fi
      return "$COPY_DEADLINE_EXIT_CODE"
    fi
  fi
  if [[ "$1" == rm || "$1" == install || "$1" == chown || "$1" == chmod || "$1" == rmdir ]]; then
    local mutation_target=unknown mutation_key
    case "${@: -1}" in
      "$TARGET_ROOT/entry.py") mutation_target=first_source ;;
      "$TARGET_ROOT/second.py") mutation_target=second_source ;;
      "$SERVICE_DROP_IN") mutation_target=dropin ;;
      "$SERVICE_DROP_IN_DIR") mutation_target=dropin_dir ;;
      "$RUN_DIR") mutation_target=run_dir ;;
      "$LOCK_FILE") mutation_target=lock ;;
    esac
    mutation_key="$1:$mutation_target"
    printf '%s\n' "$mutation_key" >> "$PWD/mutation-timeout.calls"
    if [[ "$MUTATION_DEADLINE_FAULT" == "$mutation_key" ]]; then
      if [[ "$MUTATION_DEADLINE_AFTER" == true ]]; then "$@" || return $?; fi
      return "$MUTATION_DEADLINE_EXIT_CODE"
    fi
  fi
  "$@"
}
STAGE_DIR=""
post_apply_source_sha=good
post_apply_target_sha=wrong
REPAIR_COMPLETE=false
SERVICE_WAS_ACTIVE=true
SERVICE_STOPPED=false
effective_user=wrong
effective_group=wrong
effective_restart=wrong
effective_umask=wrong
effective_no_new_privileges=wrong
effective_private_tmp=wrong
lock_ready=false
if [[ "$PREDICATE_PASSES" == true ]]; then
  post_apply_target_sha=good
  effective_user=lumencore
  effective_group=lumencore
  effective_restart=on-failure
  effective_umask=0027
  effective_no_new_privileges=yes
  effective_private_tmp=yes
  lock_ready=true
fi
systemctl() {
  if [[ "$1" == is-active ]]; then
    [[ "$PREDICATE_PASSES" == true ]]
  else
    printf 'SYSTEMCTL:%s\n' "$1" >> "$PWD/systemctl.calls"
    if [[ "$1" == stop ]]; then fixture_source_drift stop || return $?; fixture_target_drift stop || return $?; fi
    if [[ "$1" == stop ]]; then fixture_dropin_target_drift stop || return $?; fixture_run_target_drift stop || return $?; fi
    if [[ "$1" == stop && -n "$DROP_BACKUP_AFTER_VERIFY" ]]; then
      command rm -- "$BACKUP_DIR/$DROP_BACKUP_AFTER_VERIFY"
    fi
    if [[ "$1" == "$SERVICE_FAILURE" ]]; then return "$SERVICE_EXIT_CODE"; fi
  fi
}
sha256sum() {
  if [[ "$PREDICATE_PASSES" == true || "$1" == "$SOURCE_ROOT/"* ]]; then
    printf '%s  fixture\n' "$HARDENING_SHA"
  else
    printf 'wrong  fixture\n'
  fi
}
stat() {
  if [[ "$PREDICATE_PASSES" != true ]]; then
    printf 'wrong\n'
  elif [[ "${@: -1}" == "$SERVICE_DROP_IN" ]]; then
    printf 'root:root:644\n'
  elif [[ "${@: -1}" == "$RUN_DIR" ]]; then
    printf 'lumencore:lumencore:750\n'
  else
    printf 'lumencore:lumencore:640\n'
  fi
}
require_safe_recovery_directory() { :; }
remove_verified_dead_lock() { printf 'lock\n' >> "$PWD/restore.calls"; }
record_recovery_evidence() {
  if [[ "$1" == source_state ]]; then printf 'present\n'; fi
  if [[ "$1" == source_result ]]; then printf 'observed_present\n'; fi
  if [[ "$1" == dropin_result ]]; then
    if [[ -f "$BACKUP_DIR/service-drop-in.before" ]]; then printf 'dropin_present\n'; else printf 'dropin_absent\n'; fi
  elif [[ "$1" == dropin_directory_result ]]; then
    if [[ -f "$BACKUP_DIR/service-drop-in-dir.metadata" ]]; then printf 'dropin_directory_present\n'; else printf 'dropin_directory_absent\n'; fi
  elif [[ "$1" == runtime_directory_result ]]; then
    if [[ -f "$BACKUP_DIR/run-dir.metadata" ]]; then printf 'runtime_directory_present\n'; else printf 'runtime_directory_absent\n'; fi
  fi
}
fixture_source_drift() {
  if [[ -n "$SOURCE_DRIFT" && "$DRIFT_BOUNDARY" == "$1" && ! -e "$PWD/source-drift-applied" ]]; then
    "$TEST_PYTHON" "$PWD/source-drift.py" || return $?
  fi
}
fixture_target_drift() {
  if [[ -n "$TARGET_DRIFT" && "$TARGET_BOUNDARY" == "$1" && ! -e "$PWD/target-drift-applied" ]]; then
    "$TEST_PYTHON" "$PWD/target-drift.py" || return $?
  fi
}
fixture_result_fault() {
  if [[ -n "$RESULT_FAULT" ]]; then "$TEST_PYTHON" "$PWD/result-fault.py" || return $?; fi
}
fixture_dropin_fault() {
  if [[ -n "$DROPIN_FAULT" ]]; then "$TEST_PYTHON" "$PWD/dropin-fault.py" || return $?; fi
}
fixture_runtime_directory_fault() {
  if [[ -n "$RUNTIME_DIRECTORY_FAULT" ]]; then "$TEST_PYTHON" "$PWD/runtime-directory-fault.py" || return $?; fi
}
fixture_dropin_directory_fault() {
  if [[ -n "$DROPIN_DIRECTORY_FAULT" ]]; then "$TEST_PYTHON" "$PWD/dropin-directory-fault.py" || return $?; fi
}
fixture_dropin_target_drift() {
  if [[ -n "$DROPIN_TARGET_DRIFT" && "$DROPIN_TARGET_BOUNDARY" == "$1" && ! -e "$PWD/dropin-target-drift-applied" ]]; then
    "$TEST_PYTHON" "$PWD/dropin-target-drift.py" || return $?
  fi
}
fixture_run_target_drift() {
  if [[ -n "$RUN_TARGET_DRIFT" && "$RUN_TARGET_BOUNDARY" == "$1" && ! -e "$PWD/run-target-drift-applied" ]]; then
    "$TEST_PYTHON" "$PWD/run-target-drift.py" || return $?
  fi
}
fixture_dropin_dir_drift() {
  if [[ -n "$DROPIN_DIR_DRIFT" && "$DROPIN_DIR_BOUNDARY" == "$1" && ! -e "$PWD/dropin-dir-drift-applied" ]]; then
    "$TEST_PYTHON" "$PWD/dropin-dir-drift.py" || return $?
  fi
}
fixture_operation() {
  local command_name="$1" fixture_target=unknown
  case "$2" in
    "$TARGET_ROOT/entry.py") fixture_target=first_source ;;
    "$TARGET_ROOT/second.py") fixture_target=second_source ;;
    "$SERVICE_DROP_IN") fixture_target=dropin ;;
    "$SERVICE_DROP_IN_DIR") fixture_target=dropin_dir ;;
    "$RUN_DIR") fixture_target=run_dir ;;
    "$LOCK_FILE") fixture_target=lock ;;
  esac
  printf '%s:%s\n' "$command_name" "$fixture_target" >> "$PWD/operation.calls"
  if [[ "$RESTORE_FAULT" == "$command_name:$fixture_target" ]]; then return 23; fi
}
chown() { printf 'chown\n' >> "$PWD/restore.calls"; fixture_operation chown "${@: -1}"; }
chmod() {
  printf 'chmod\n' >> "$PWD/restore.calls"
  fixture_operation chmod "${@: -1}" || return $?
  if [[ "${@: -1}" == "$RUN_DIR" ]]; then
    "$TEST_PYTHON" -c 'import os,sys; os.chmod(sys.argv[2], int(sys.argv[1],8))' "$1" "$RUN_DIR" || return $?
    fixture_runtime_directory_fault || return $?
  elif [[ "${@: -1}" == "$SERVICE_DROP_IN_DIR" ]]; then
    "$TEST_PYTHON" -c 'import os,sys; os.chmod(sys.argv[2], int(sys.argv[1],8))' "$1" "$SERVICE_DROP_IN_DIR" || return $?
    fixture_dropin_directory_fault || return $?
    fixture_run_target_drift before_run_restore || return $?
  fi
}
rm() {
  printf 'rm\n' >> "$PWD/restore.calls"
  fixture_operation rm "${@: -1}" || return $?
  if [[ "${@: -1}" == "$LOCK_FILE" && "$LOCK_REMOVE_CASE" == noop ]]; then return 0; fi
  if [[ "$RESULT_FAULT" == remove_noop && "${@: -1}" == "$TARGET_ROOT/$RESULT_RELATIVE" ]]; then
    printf no_op > "$PWD/result-fault-applied"
    return 0
  fi
  if [[ "$DROPIN_FAULT" == remove_noop && "${@: -1}" == "$SERVICE_DROP_IN" ]]; then
    printf no_op > "$PWD/dropin-fault-applied"
    return 0
  fi
  command rm "$@" || return $?
  if [[ "${@: -1}" == "$LOCK_FILE" ]]; then "$TEST_PYTHON" "$PWD/lock-remove-result.py" "$LOCK_FILE" || return $?; fi
  if [[ "$DROPIN_FAULT" == remove_* && "${@: -1}" == "$SERVICE_DROP_IN" ]]; then fixture_dropin_fault || return $?; fi
  if [[ "$RESULT_FAULT" == remove_symlink && "${@: -1}" == "$TARGET_ROOT/$RESULT_RELATIVE" ]]; then fixture_result_fault || return $?; fi
  if [[ "${@: -1}" == "$TARGET_ROOT/entry.py" ]]; then fixture_source_drift after_first_remove || return $?; fixture_target_drift after_first_remove || return $?; fi
  if [[ "${@: -1}" == "$SERVICE_DROP_IN" ]]; then fixture_dropin_target_drift after_remove || return $?; fi
}
install() {
  if [[ "$FIXTURE_DROPIN_DIR_FORWARD" == true ]]; then
    printf '%s\n' "${@: -1}" >> "$PWD/dropin-dir-forward.calls"
    command mkdir -p -- "${@: -1}" || return $?
    if [[ "$DROPIN_DIR_FORWARD_CASE" == partial ]]; then return 31; fi
    if [[ "$DROPIN_DIR_FORWARD_CASE" == wrong_type ]]; then command mv -- "${@: -1}" "$PWD/partial-dropin-dir"; printf 'wrong type' > "${@: -1}"; return 0; fi
    command chmod 0755 -- "${@: -1}" || return $?
  elif [[ "$FIXTURE_RUN_FORWARD" == true ]]; then
    printf '%s\n' "${@: -1}" >> "$PWD/run-forward.calls"
    command mkdir -p -- "${@: -1}" || return $?
    if [[ "$RUN_FORWARD_CASE" == partial ]]; then return 31; fi
    if [[ "$RUN_FORWARD_CASE" == wrong_type ]]; then command rmdir -- "${@: -1}"; printf 'wrong type' > "${@: -1}"; return 0; fi
    command chmod 0750 -- "${@: -1}" || return $?
  elif [[ "$FIXTURE_DROPIN_FORWARD" == true ]]; then
    printf '%s\n' "${@: -1}" >> "$PWD/dropin-forward.calls"
    if [[ "$DROPIN_FORWARD_CASE" == partial ]]; then printf 'partial hardening\n' > "${@: -1}"; return 31; fi
    if [[ "$DROPIN_FORWARD_CASE" == wrong_bytes ]]; then printf 'wrong candidate\n' > "${@: -1}"; return 0; fi
    command cp -- "${@: -2:1}" "${@: -1}" || return $?
    command chmod 0644 -- "${@: -1}"
  elif [[ "$FIXTURE_FORWARD" == true ]]; then
    # Run the real forward transition/readback; only ownership/system install
    # effects are substituted so this fixture remains unprivileged and local.
    printf '%s\n' "${@: -1}" >> "$PWD/forward.calls"
    command mkdir -p -- "$(dirname -- "${@: -1}")" || return $?
    if [[ "$FORWARD_CASE" == partial_first && "${@: -1}" == "$TARGET_ROOT/entry.py"
       || "$FORWARD_CASE" == partial_second && "${@: -1}" == "$TARGET_ROOT/second.py" ]]; then
      printf 'partial candidate\n' > "${@: -1}"
      return 31
    fi
    if [[ "$FORWARD_CASE" == readback_mismatch ]]; then printf 'unexpected candidate\n' > "${@: -1}"; return 0; fi
    command cp -- "${@: -2:1}" "${@: -1}" || return $?
    command chmod 0644 -- "${@: -1}"
  else
    fixture_operation install "${@: -1}" || return $?
    command mkdir -p -- "${@: -1}"
  fi
}
rmdir() {
  fixture_operation rmdir "${@: -1}" || return $?
  if [[ "$RUNTIME_DIRECTORY_FAULT" == remove_noop && "${@: -1}" == "$RUN_DIR" ]]; then fixture_runtime_directory_fault; return $?; fi
  if [[ "$DROPIN_DIRECTORY_FAULT" == remove_noop && "${@: -1}" == "$SERVICE_DROP_IN_DIR" ]]; then fixture_dropin_directory_fault; return $?; fi
  command rmdir "$@" || return $?
  if [[ "$DROPIN_DIRECTORY_FAULT" == dangling_symlink && "${@: -1}" == "$SERVICE_DROP_IN_DIR" ]]; then fixture_dropin_directory_fault || return $?; fi
  if [[ "$RUNTIME_DIRECTORY_FAULT" == dangling_symlink && "${@: -1}" == "$RUN_DIR" ]]; then fixture_runtime_directory_fault || return $?; fi
}
cp() {
  printf 'cp\n' >> "$PWD/restore.calls"
  fixture_operation cp "${@: -1}" || return $?
  if [[ "$SIGNAL_DURING_COPY" == true ]]; then
    kill -TERM "$BASHPID"
    printf 'FIXTURE_TERM_SENT\n' >&2
  fi
  if [[ "$COPY_FAILS" == true ]]; then
    printf 'FIXTURE_COPY_FAILURE\n' >&2
    return 9
  fi
  if [[ "$RESULT_FAULT" == copy_noop && "${@: -1}" == "$TARGET_ROOT/$RESULT_RELATIVE" ]]; then
    printf no_op > "$PWD/result-fault-applied"
    return 0
  fi
  if [[ "$DROPIN_FAULT" == copy_noop && "${@: -1}" == "$SERVICE_DROP_IN" ]]; then
    printf no_op > "$PWD/dropin-fault-applied"
    return 0
  fi
  command cp "$@" || return $?
  if [[ -n "$DROPIN_FAULT" && "${@: -1}" == "$SERVICE_DROP_IN" ]]; then fixture_dropin_fault || return $?; fi
  if [[ ( "$RESULT_FAULT" == copy_* || "$RESULT_FAULT" == manifest_changed || "$RESULT_FAULT" == backup_changed ) && "${@: -1}" == "$TARGET_ROOT/$RESULT_RELATIVE" ]]; then fixture_result_fault || return $?; fi
  if [[ "${@: -1}" == "$TARGET_ROOT/entry.py" ]]; then fixture_source_drift after_first_copy || return $?; fixture_target_drift after_first_copy || return $?; fi
  if [[ "${@: -1}" == "$TARGET_ROOT/entry.py" ]]; then fixture_dropin_target_drift after_first_copy || return $?; fixture_run_target_drift after_first_copy || return $?; fi
}
cleanup() {
  if [[ -f "$PWD/systemctl.calls" ]]; then cat "$PWD/systemctl.calls"; fi
  printf 'CLEANUP\n'
}
trap cleanup EXIT
'''
        harness = harness.replace("HARDENING_SHA=" + "c" * 64,
                                  "HARDENING_SHA=" + hashlib.sha256(b"candidate hardening\n").hexdigest())
        bounded = _bash_function(script, "bounded_recovery_systemctl")
        if real_timeout_mode:
            # Only the extracted disposable fixture gets a shorter fixed policy;
            # production has no caller-controlled duration or environment escape.
            assert bounded.count("--kill-after=5s 60s") == 1
            bounded = bounded.replace("--kill-after=5s 60s", "--kill-after=0.2s 0.2s")
            # Only systemctl uses the real launcher. Copy/filesystem commands
            # must retain their shell fixture stubs and operation accounting.
            assert bounded.count('"$RECOVERY_TIMEOUT_BIN"') == 1
            bounded = bounded.replace('"$RECOVERY_TIMEOUT_BIN"', '"$FIXTURE_NATIVE_TIMEOUT_BIN"')
            (root / "bin").mkdir()
            fake = root / "bin/systemctl"
            fake.write_text('''#!/bin/bash
printf 'SYSTEMCTL:%s\\n' "$1" >> "$PWD/systemctl.calls"
if [[ "$1" == "$SERVICE_FAILURE" ]]; then
  record_fixture_process() {
    local identity
    IFS= read -r identity < "/proc/$BASHPID/stat"
    printf '%s\\n' "$identity" > "$PWD/fixture-process-$BASHPID.stat"
  }
  record_fixture_process
  if [[ "$REAL_TIMEOUT_MODE" == ignore_term* ]]; then trap '' TERM; fi
  if [[ "$REAL_TIMEOUT_MODE" == ignore_term_descendant ]]; then
    (trap '' TERM; record_fixture_process; while :; do :; done) &
  fi
  printf 'COMMAND_ENTERED\\n' >> "$PWD/command-entered"
  while :; do :; done
fi
''', encoding="utf-8", newline="\n")
            fake.chmod(0o755)
            harness += 'export PATH="/usr/bin:$PATH"\nFIXTURE_NATIVE_TIMEOUT_BIN="$(type -P timeout)"\n'
            harness += 'export PATH="$PWD/bin:$PATH"\n'
        harness += bounded + "\n" + _bash_function(script, "finish_rollback") + "\n"
        for name in ("bounded_recovery_copy", "bounded_recovery_mutation", "checked_restore_step", "read_recovery_state", "read_recovery_source_state", "read_recovery_source_result", "read_recovery_dropin_result", "read_recovery_runtime_directory_result", "read_recovery_dropin_directory_result", "read_recovery_metadata", "remove_recovery_directory",
                     "recorded_target_version", "source_target_version", "capture_source_target_version", "install_gateway_source", "read_recovery_target_state", "require_recovery_target_absent",
                     "dropin_target_version", "capture_dropin_target_version", "install_gateway_dropin", "read_recovery_dropin_target_state", "require_recovery_dropin_absent",
                     "dropin_directory_target_version", "capture_dropin_directory_target_version", "install_gateway_dropin_directory", "read_recovery_dropin_directory_target_state",
                     "runtime_directory_target_version", "capture_runtime_directory_target_version", "install_gateway_runtime_directory", "read_recovery_runtime_directory_target_state"):
            function = _bash_function(script, name)
            if name == "recorded_target_version":
                # Production requires numeric root:root. Disposable fixtures
                # do not change ownership; adapt only that capture expectation.
                needle = '    if (before.st_uid, before.st_gid, stat.S_IMODE(before.st_mode)) != (uid, gid, permissions):'
                assert function.count(needle) == 1
                function = function.replace(needle, '    if object_kind == "dropin_directory":\n        uid, gid = (os.getuid(), os.getgid()) if os.name == "posix" else (0, 0)\n' + needle)
            if os.name != "posix" and name == "recorded_target_version":
                # Windows cannot represent Unix directory mode0750. Substitute
                # only that fixture comparison; real mode/link coverage is POSIX.
                assert function.count("!= (uid, gid, permissions)") == 1
                function = function.replace("!= (uid, gid, permissions)", "!= (uid, gid, stat.S_IMODE(before.st_mode))")
            harness += function + "\n"
        harness += _bash_function(script, "read_recovery_state").replace(
            "read_recovery_state() {", "actual_read_recovery_state() {", 1) + "\n"
        harness += r'''
read_recovery_state() {
  actual_read_recovery_state "$@" || return $?
  if [[ "$1" == "$BACKUP_DIR/service-drop-in.state" ]]; then fixture_dropin_dir_drift before_parent_install || return $?; fi
  if [[ "$1" == "$BACKUP_DIR/service-drop-in-dir.state" ]]; then fixture_dropin_dir_drift before_directory_restore || return $?; fi
}
'''
        if run_target_boundary == "query":
            harness += _bash_function(script, "read_recovery_runtime_directory_target_state").replace(
                "read_recovery_runtime_directory_target_state() {", "actual_runtime_target_state() {", 1) + "\n"
            harness += 'read_recovery_runtime_directory_target_state() { fixture_run_target_drift query || return $?; actual_runtime_target_state "$@"; }\n'
        if real_lock_case:
            _write_lock_probe_runtime(root)
            harness += _bash_function(script, "read_gateway_lock_pid") + "\n"
            harness += _bash_function(script, "require_absent_lock_owner") + "\n"
            harness += _bash_function(script, "read_gateway_lock_presence") + "\n"
            harness += r'''
PYTHON_BIN=fixture_lock_python
fixture_lock_python() {
  if [[ "$LOCK_PROBE_CASE" == launcher_failure ]]; then return 29; fi
  "$TEST_PYTHON" "$PWD/lock-probe-runtime.py" "$@"
}
'''
            harness += _bash_function(script, "remove_verified_dead_lock") + "\n"
            if real_lock_case == "reader_failure":
                harness += 'read_gateway_lock_pid() { return 27; }\n'
            if lock_file_bytes is not None:
                (root / "run/fixture.lock").write_bytes(lock_file_bytes)
            elif real_lock_case == "live":
                harness += 'printf "%s\\n" "$BASHPID" > "$LOCK_FILE"\n'
            elif real_lock_case == "invalid":
                harness += 'printf "invalid\\n" > "$LOCK_FILE"\n'
            elif real_lock_case == "invalid_range":
                harness += 'printf "2147483648\\n" > "$LOCK_FILE"\n'
            elif real_lock_case == "symlink":
                (root / "run/fixture.lock").symlink_to(root / "not-present")
            elif real_lock_case != "absent":
                harness += 'printf "999999999\\n" > "$LOCK_FILE"\n'
        harness += rollback_source + "\n"
        if second_source:
            harness += 'BUNDLE_FILES+=(second.py)\n'
        if not service_was_active:
            harness += 'SERVICE_WAS_ACTIVE=false\n'
        if recovery_case:
            harness += _bash_function(script, "record_recovery_evidence") + "\n"
            harness += _bash_function(script, "cleanup") + "\n"
            harness += 'cleanup_manifest() { :; }\npython3() { "$TEST_PYTHON" "$@"; }\n'
            if recovery_case == "prepared_write_failure":
                harness += 'printf collision > "$BACKUP_DIR/prepared.json"\n'
            if recovery_case == "valid_missing":
                harness += 'BUNDLE_FILES+=(absent.py)\nprintf candidate > "$TARGET_ROOT/absent.py"\nprintf "absent.py\\n" > "$BACKUP_DIR/missing-before.txt"\n'
            # This exact production sequence precedes service mutation and ERR
            # rollback registration; preparation failure must leave runtime alone.
            harness += 'RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"\n'
            harness += '[[ "$RECOVERY_MANIFEST_SHA" =~ ^[0-9a-f]{64}$ ]]\n'
            if recovery_case == "rollback_write_failure":
                harness += 'printf collision > "$BACKUP_DIR/rollback.json"\n'
            if recovery_case == "helper_write_failure":
                harness += 'printf collision > "$BACKUP_DIR/helper.json"\n'
            if recovery_case == "manifest_changed":
                harness += 'printf changed >> "$BACKUP_DIR/prepared.json"\n'
            if recovery_case == "backup_changed":
                harness += 'printf changed >> "$BACKUP_DIR/existing/entry.py"\n'
            mutations = {
                "backup_missing": 'Path("backup/existing/entry.py").unlink()',
                "backup_metadata": 'p=Path("backup/existing/entry.py"); t=p.stat().st_mtime_ns; os.utime(p, ns=(t,t+1000000000))',
                "backup_symlink": 'p=Path("backup/existing/entry.py"); p.unlink(); p.symlink_to(Path("target/entry.py").resolve())',
                "backup_parent_symlink": 'p=Path("backup/existing"); p.rename("outside"); p.symlink_to(Path("outside").resolve(), target_is_directory=True)',
                "backup_hardlink": 'p=Path("backup/existing/entry.py"); os.link(p,"outside-hardlink")',
                "backup_extra": 'Path("backup/existing/unexpected.py").write_text("unexpected")',
                "backup_extra_directory": 'Path("backup/existing/unexpected").mkdir()',
                "manifest_missing": 'Path("backup/prepared.json").unlink()',
                "manifest_symlink": 'p=Path("backup/prepared.json"); p.rename("outside-manifest.json"); p.symlink_to(Path("outside-manifest.json").resolve())',
                "missing_contradiction": 'Path("backup/missing-before.txt").write_text("entry.py\\n")',
                "missing_duplicate": 'Path("backup/missing-before.txt").write_text("entry.py\\nentry.py\\n")',
                "missing_unexpected": 'Path("backup/missing-before.txt").write_text("outside.py\\n")',
                "backup_xattr": 'os.setxattr("backup/existing/entry.py", "user.fixture", b"changed")',
                "custody_parent_symlink": 'p=Path("backup"); p.rename("outside-backup"); p.symlink_to(Path("outside-backup").resolve(), target_is_directory=True)',
            }
            if recovery_case in mutations:
                mutation = "from pathlib import Path; import os; " + mutations[recovery_case]
                harness += "python3 -c '" + mutation.replace("'", "'\"'\"'") + "'\n"
            if recovery_case in {"source_binding", "bundle_binding"}:
                variable = {"source_binding": "SOURCE_COMMIT", "bundle_binding": "BUNDLE_SHA", "hardening_binding": "HARDENING_SHA"}[recovery_case]
                harness += variable + "=" + ("d" * (40 if variable == "SOURCE_COMMIT" else 64)) + "\n"
            if recovery_case == "refusal_write_failure":
                harness += 'printf collision > "$BACKUP_DIR/rollback_refused.json"\nprintf changed >> "$BACKUP_DIR/existing/entry.py"\n'
            malformed = {
                "inventory_omitted": 'd["files"].pop()',
                "inventory_extra": 'd["files"].append(dict(d["files"][0], path="unexpected.py"))',
                "manifest_schema": 'd["schema"]="unexpected_schema"',
                "manifest_kind": 'd["kind"]="helper"',
                "manifest_status": 'd["status"]="UNKNOWN"',
            }
            if recovery_case in malformed:
                # Bind deliberately malformed preparation to test schema/coverage,
                # separately from ordinary byte tampering with an unchanged hash.
                mutation = ('from pathlib import Path; import hashlib,json; p=Path("backup/prepared.json"); '
                            'd=json.loads(p.read_text()); ' + malformed[recovery_case] +
                            '; p.write_text(json.dumps(d)); print(hashlib.sha256(p.read_bytes()).hexdigest())')
                harness += "RECOVERY_MANIFEST_SHA=\"$(python3 -c '" + mutation.replace("'", "'\"'\"'") + "')\"\n"
        if source_query_case:
            harness += _bash_function(script, "record_recovery_evidence").replace(
                "record_recovery_evidence() {", "actual_record_recovery_evidence() {", 1) + "\n"
            harness += r'''
record_recovery_evidence() {
  if [[ "$1" != source_state ]]; then actual_record_recovery_evidence "$@"; return $?; fi
  case "$SOURCE_QUERY_CASE" in
    failed) printf 'present\n'; return 29 ;;
    extra_line) printf 'present\nmissing\n' ;;
    extra_newline) printf 'present\n\n' ;;
    carriage_return) printf 'present\r\n' ;;
    empty) : ;;
    no_newline) printf present ;;
    invalid) printf 'unknown\n' ;;
    outside) actual_record_recovery_evidence source_state 0 ../outside.py ;;
    unregistered) actual_record_recovery_evidence source_state 0 outside.py ;;
    empty_path) actual_record_recovery_evidence source_state 0 '' ;;
    extra_argument) actual_record_recovery_evidence source_state 0 entry.py outside.py ;;
    second_missing)
      if [[ -e "$PWD/query-called" ]]; then printf 'missing\n'; else
        printf first > "$PWD/query-called"
        actual_record_recovery_evidence "$@"
      fi ;;
    *) return 99 ;;
  esac
}
'''
        # Execute actual forward state transitions before the chosen failed guard.
        # A partial install enters the real ERR trap and leaves WRITE_PENDING.
        harness += error_trap + "\n" + r'''
STAGE_DIR="$PWD/stage"
command mkdir -p -- "$STAGE_DIR"
for fixture_rel in "${BUNDLE_FILES[@]}"; do
  command cp -- "$TARGET_ROOT/$fixture_rel" "$STAGE_DIR/$fixture_rel"
  SOURCE_WRITE_STATES[$fixture_rel]=UNTOUCHED
  SOURCE_CANDIDATE_SHA[$fixture_rel]="$("$TEST_PYTHON" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$STAGE_DIR/$fixture_rel")"
done
printf 'candidate hardening\n' > "$STAGE_DIR/20-lumencore-runtime-hardening.conf"
if [[ "$DROPIN_FORWARD_CASE" == stage_changed ]]; then printf 'changed staged hardening\n' > "$STAGE_DIR/20-lumencore-runtime-hardening.conf"; fi
if [[ "$DROPIN_FORWARD_CASE" == capture_failed ]]; then capture_dropin_target_version() { return 29; }; fi
if [[ "$DROPIN_DIR_FORWARD_CASE" == capture_failed ]]; then capture_dropin_directory_target_version() { return 29; }; fi
if [[ "$DROPIN_DIR_FORWARD_CASE" != untouched ]]; then
  FIXTURE_DROPIN_DIR_FORWARD=true
  install_gateway_dropin_directory
  FIXTURE_DROPIN_DIR_FORWARD=false
fi
if [[ "$DROPIN_FORWARD_CASE" != untouched && "$DROPIN_DIR_FORWARD_CASE" != untouched ]]; then
  FIXTURE_DROPIN_FORWARD=true
  install_gateway_dropin
  FIXTURE_DROPIN_FORWARD=false
fi
if [[ "$RUN_FORWARD_CASE" == capture_failed ]]; then capture_runtime_directory_target_version() { return 29; }; fi
if [[ "$RUN_FORWARD_CASE" == invalid_candidate ]]; then RUN_CANDIDATE_METADATA=invalid; fi
if [[ "$RUN_FORWARD_CASE" != untouched ]]; then
  FIXTURE_RUN_FORWARD=true
  install_gateway_runtime_directory
  FIXTURE_RUN_FORWARD=false
fi
if [[ "$FORWARD_CASE" == stage_changed ]]; then printf 'changed staged candidate\n' > "$STAGE_DIR/entry.py"; fi
FIXTURE_FORWARD=true
for fixture_rel in "${BUNDLE_FILES[@]}"; do
  if [[ "$FORWARD_CASE" == untouched || "$FORWARD_CASE" == untouched_missing && "$fixture_rel" == absent.py ]]; then continue; fi
  install_gateway_source "$fixture_rel"
done
FIXTURE_FORWARD=false
# Cleanup is tested separately; avoid treating a fixture stage as production /tmp.
STAGE_DIR=""
case "$FORWARD_CASE" in
  missing_state) unset 'SOURCE_WRITE_STATES[entry.py]' ;;
  unknown_state) SOURCE_WRITE_STATES[entry.py]=UNKNOWN ;;
  invalid_state) SOURCE_WRITE_STATES[entry.py]=invalid ;;
  missing_version) unset 'SOURCE_TARGET_VERSION[entry.py]' ;;
  invalid_version) SOURCE_TARGET_VERSION[entry.py]=invalid ;;
  missing_candidate) unset 'SOURCE_CANDIDATE_SHA[entry.py]' ;;
esac
case "$RUN_FORWARD_CASE" in
  unknown_state) RUN_WRITE_STATE=UNKNOWN ;;
  invalid_state) RUN_WRITE_STATE=invalid ;;
  missing_version) RUN_TARGET_VERSION="" ;;
  invalid_version) RUN_TARGET_VERSION=invalid ;;
  untouched_version) RUN_WRITE_STATE=UNTOUCHED ;;
esac
case "$DROPIN_DIR_FORWARD_CASE" in
  unknown_state) DROPIN_DIR_WRITE_STATE=UNKNOWN ;;
  invalid_state) DROPIN_DIR_WRITE_STATE=invalid ;;
  missing_version) DROPIN_DIR_TARGET_VERSION="" ;;
  invalid_version) DROPIN_DIR_TARGET_VERSION=invalid ;;
  untouched_version) DROPIN_DIR_WRITE_STATE=UNTOUCHED ;;
  untouched_child_installed) DROPIN_DIR_WRITE_STATE=UNTOUCHED; DROPIN_DIR_TARGET_VERSION="" ;;
esac
case "$DROPIN_FORWARD_CASE" in
  unknown_state) DROPIN_WRITE_STATE=UNKNOWN ;;
  invalid_state) DROPIN_WRITE_STATE=invalid ;;
  missing_version) DROPIN_TARGET_VERSION="" ;;
  invalid_version) DROPIN_TARGET_VERSION=invalid ;;
  untouched_version) DROPIN_WRITE_STATE=UNTOUCHED ;;
esac
'''
        if recovery_case == "hardening_binding":
            harness += "HARDENING_SHA=" + "d" * 64 + "\n"
        if dropin_dir_query_case:
            harness += _bash_function(script, "dropin_directory_target_version").replace(
                "dropin_directory_target_version() {", "actual_dropin_directory_target_version() {", 1) + "\n"
            harness += r'''
dropin_directory_target_version() {
  case "$DROPIN_DIR_QUERY_CASE" in
    failed) actual_dropin_directory_target_version; return 29 ;;
    extra_line) actual_dropin_directory_target_version; printf 'extra\n' ;;
    extra_newline) actual_dropin_directory_target_version; printf '\n' ;;
    no_newline) printf '%064d' 0 ;;
    extra_argument) actual_dropin_directory_target_version ignored ;;
    supplied_path) recorded_target_version dropin_directory capture ../outside "$DROPIN_DIR_CANDIDATE_METADATA" ;;
    invalid_mode) recorded_target_version dropin_directory absent '' '' ;;
    *) return 99 ;;
  esac
}
'''
        if run_target_query_case:
            harness += _bash_function(script, "runtime_directory_target_version").replace(
                "runtime_directory_target_version() {", "actual_runtime_directory_target_version() {", 1) + "\n"
            harness += r'''
runtime_directory_target_version() {
  case "$RUN_TARGET_QUERY_CASE" in
    failed) actual_runtime_directory_target_version; return 29 ;;
    extra_line) actual_runtime_directory_target_version; printf 'extra\n' ;;
    extra_newline) actual_runtime_directory_target_version; printf '\n' ;;
    carriage_return) printf '%064d\r\n' 0 ;;
    no_newline) printf '%064d' 0 ;;
    empty) : ;;
    extra_argument) actual_runtime_directory_target_version ignored ;;
    invalid_mode) recorded_target_version runtime absent '' '' ;;
    supplied_path) recorded_target_version runtime capture ../outside "$RUN_CANDIDATE_METADATA" ;;
    *) return 99 ;;
  esac
}
'''
        if dropin_target_query_case:
            harness += _bash_function(script, "dropin_target_version").replace(
                "dropin_target_version() {", "actual_dropin_target_version() {", 1) + "\n"
            harness += r'''
dropin_target_version() {
  case "$DROPIN_TARGET_QUERY_CASE" in
    failed) actual_dropin_target_version "$@"; return 29 ;;
    extra_line) actual_dropin_target_version "$@"; printf 'extra\n' ;;
    extra_newline) actual_dropin_target_version "$@"; printf '\n' ;;
    carriage_return) printf '%064d\r\n' 0 ;;
    no_newline) printf '%064d' 0 ;;
    empty) : ;;
    extra_argument) actual_dropin_target_version "$1" ignored ;;
    invalid_mode) actual_dropin_target_version invalid ;;
    unknown_object) recorded_target_version unknown capture '' "$HARDENING_SHA" ;;
    supplied_path) recorded_target_version dropin capture ../outside "$HARDENING_SHA" ;;
    absent_failed) if [[ "$1" == absent ]]; then printf 'absent\n'; return 29; fi; actual_dropin_target_version "$@" ;;
    absent_extra) if [[ "$1" == absent ]]; then printf 'absent\n\n'; else actual_dropin_target_version "$@"; fi ;;
    *) return 99 ;;
  esac
}
'''
        if target_query_case:
            harness += _bash_function(script, "source_target_version").replace(
                "source_target_version() {", "actual_source_target_version() {", 1) + "\n"
            harness += r'''
source_target_version() {
  case "$TARGET_QUERY_CASE" in
    failed) actual_source_target_version "$@"; return 29 ;;
    extra_line) actual_source_target_version "$@"; printf 'extra\n' ;;
    extra_newline) actual_source_target_version "$@"; printf '\n' ;;
    carriage_return) printf '%s\r\n' "${SOURCE_TARGET_VERSION[entry.py]}" ;;
    no_newline) printf '%s' "${SOURCE_TARGET_VERSION[entry.py]}" ;;
    empty) : ;;
    invalid) printf 'invalid\n' ;;
    outside) actual_source_target_version capture ../outside.py "$3" ;;
    unregistered) actual_source_target_version capture outside.py "$3" ;;
    *) return 99 ;;
  esac
}
'''
        if result_query_case:
            harness += _bash_function(script, "record_recovery_evidence").replace(
                "record_recovery_evidence() {", "actual_result_record_recovery_evidence() {", 1) + "\n"
            harness += r'''
record_recovery_evidence() {
  if [[ "$1" != source_result ]]; then actual_result_record_recovery_evidence "$@"; return $?; fi
  case "$RESULT_QUERY_CASE" in
    failed) printf 'observed_present\n'; return 29 ;;
    extra_line) printf 'observed_present\nextra\n' ;;
    extra_newline) printf 'observed_present\n\n' ;;
    carriage_return) printf 'observed_present\r\n' ;;
    no_newline) printf observed_present ;;
    empty) : ;;
    contradictory) printf 'observed_absent\n' ;;
    invalid) printf 'verified\n' ;;
    outside) actual_result_record_recovery_evidence source_result 0 ../outside.py ;;
    unregistered) actual_result_record_recovery_evidence source_result 0 outside.py ;;
    empty_path) actual_result_record_recovery_evidence source_result 0 '' ;;
    extra_argument) actual_result_record_recovery_evidence source_result 0 entry.py extra ;;
    *) return 99 ;;
  esac
}
'''
        if dropin_query_case:
            harness += _bash_function(script, "record_recovery_evidence").replace(
                "record_recovery_evidence() {", "actual_dropin_record_recovery_evidence() {", 1) + "\n"
            harness += r'''
record_recovery_evidence() {
  if [[ "$1" != dropin_result ]]; then actual_dropin_record_recovery_evidence "$@"; return $?; fi
  case "$DROPIN_QUERY_CASE" in
    failed) printf 'dropin_present\n'; return 29 ;;
    extra_line) printf 'dropin_present\nextra\n' ;;
    extra_newline) printf 'dropin_present\n\n' ;;
    carriage_return) printf 'dropin_present\r\n' ;;
    no_newline) printf dropin_present ;;
    empty) : ;;
    contradictory) printf 'dropin_absent\n' ;;
    invalid) printf 'verified\n' ;;
    source_argument) actual_dropin_record_recovery_evidence dropin_result 0 entry.py ;;
    empty_argument) actual_dropin_record_recovery_evidence dropin_result 0 '' ;;
    extra_arguments) actual_dropin_record_recovery_evidence dropin_result 0 service_drop_in extra ;;
    *) return 99 ;;
  esac
}
'''
        if runtime_directory_query_case:
            harness += _bash_function(script, "record_recovery_evidence").replace(
                "record_recovery_evidence() {", "actual_runtime_record_recovery_evidence() {", 1) + "\n"
            harness += r'''
record_recovery_evidence() {
  if [[ "$1" != runtime_directory_result ]]; then actual_runtime_record_recovery_evidence "$@"; return $?; fi
  case "$RUNTIME_DIRECTORY_QUERY_CASE" in
    failed) printf 'runtime_directory_present\n'; return 29 ;;
    extra_line) printf 'runtime_directory_present\nextra\n' ;;
    extra_newline) printf 'runtime_directory_present\n\n' ;;
    carriage_return) printf 'runtime_directory_present\r\n' ;;
    no_newline) printf runtime_directory_present ;;
    empty) : ;;
    contradictory) printf 'runtime_directory_absent\n' ;;
    invalid) printf 'verified\n' ;;
    source_argument) actual_runtime_record_recovery_evidence runtime_directory_result 0 entry.py ;;
    empty_argument) actual_runtime_record_recovery_evidence runtime_directory_result 0 '' ;;
    extra_arguments) actual_runtime_record_recovery_evidence runtime_directory_result 0 run_directory extra ;;
    *) return 99 ;;
  esac
}
'''
        if dropin_directory_query_case:
            harness += _bash_function(script, "record_recovery_evidence").replace(
                "record_recovery_evidence() {", "actual_dropin_directory_record_recovery_evidence() {", 1) + "\n"
            harness += r'''
record_recovery_evidence() {
  if [[ "$1" != dropin_directory_result ]]; then actual_dropin_directory_record_recovery_evidence "$@"; return $?; fi
  case "$DROPIN_DIRECTORY_QUERY_CASE" in
    failed) printf 'dropin_directory_present\n'; return 29 ;;
    extra_line) printf 'dropin_directory_present\nextra\n' ;;
    extra_newline) printf 'dropin_directory_present\n\n' ;;
    carriage_return) printf 'dropin_directory_present\r\n' ;;
    no_newline) printf dropin_directory_present ;;
    empty) : ;;
    contradictory) printf 'dropin_directory_absent\n' ;;
    invalid) printf 'verified\n' ;;
    source_argument) actual_dropin_directory_record_recovery_evidence dropin_directory_result 0 entry.py ;;
    empty_argument) actual_dropin_directory_record_recovery_evidence dropin_directory_result 0 '' ;;
    extra_arguments) actual_dropin_directory_record_recovery_evidence dropin_directory_result 0 service_drop_in_directory extra ;;
    *) return 99 ;;
  esac
}
'''
        if forward_lock_deadline_failure:
            harness += r'''
forward_lock_rc=0
remove_verified_dead_lock || forward_lock_rc=$?
[[ "$forward_lock_rc" == 124 && "$RECOVERY_MUTATION_FAILURE" == dead_lock ]] || exit 97
printf 'FORWARD_LOCK_FAILURE=%s\n' "$forward_lock_rc"
MUTATION_DEADLINE_FAULT=""
rollback "$forward_lock_rc"
'''
        harness += guard
        if recovery_case in {"later_gate_failure", "helper_write_failure", "manifest_changed", "backup_changed"}:
            outcome = script.split('if ! helper_receipt_sha="$(record_recovery_evidence helper 0)";', 1)[1]
            outcome = 'if ! helper_receipt_sha="$(record_recovery_evidence helper 0)";' + outcome
            outcome = outcome.split('\necho "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK"', 1)[0]
            harness += "\n" + outcome + "\nexit 41\n"
        else:
            harness += "\nprintf 'GUARD_PASSED\\n'\n"
        env = dict(os.environ)
        env.update(
            PREDICATE_PASSES=str(predicate_passes).lower(),
            COPY_FAILS=str(copy_fails).lower(),
            COPY_DEADLINE_TARGET=copy_deadline_target,
            COPY_DEADLINE_EXIT_CODE=str(copy_deadline_exit_code),
            COPY_DEADLINE_PARTIAL=str(copy_deadline_partial).lower(),
            MUTATION_DEADLINE_FAULT=mutation_deadline_fault,
            MUTATION_DEADLINE_EXIT_CODE=str(mutation_deadline_exit_code),
            MUTATION_DEADLINE_AFTER=str(mutation_deadline_after).lower(),
            EVIDENCE_DEADLINE_KIND=evidence_deadline_kind,
            EVIDENCE_DEADLINE_EXIT_CODE=str(evidence_deadline_exit_code),
            EVIDENCE_DEADLINE_AFTER=str(evidence_deadline_after).lower(),
            TARGET_DEADLINE_QUERY=target_deadline_query,
            TARGET_DEADLINE_EXIT_CODE=str(target_deadline_exit_code),
            TARGET_DEADLINE_AFTER=str(target_deadline_after).lower(),
            SIGNAL_DURING_COPY=str(signal_during_copy).lower(),
            TEST_PYTHON=Path(sys.executable).as_posix(),
            SERVICE_FAILURE=service_failure,
            SERVICE_EXIT_CODE=str(service_exit_code),
            REAL_TIMEOUT_MODE=real_timeout_mode,
            RESTORE_FAULT=restore_fault, REAL_LOCK_CASE=real_lock_case,
            LOCK_PRESENCE_CASE=lock_presence_case, LOCK_REMOVE_CASE=lock_remove_case,
            LOCK_PROBE_CASE=real_lock_case if real_lock_case in {
                "live", "permission", "unknown", "overflow", "value", "unclassified_lookup",
                "unexpected", "launcher_failure"} else "dead",
            SOURCE_DRIFT=source_drift, DRIFT_BOUNDARY=drift_boundary, SOURCE_QUERY_CASE=source_query_case,
            TARGET_DRIFT=target_drift, TARGET_BOUNDARY=target_boundary, FORWARD_CASE=forward_case,
            TARGET_QUERY_CASE=target_query_case,
            TARGET_RELATIVE=target_relative,
            RESULT_FAULT=result_fault, RESULT_RELATIVE=result_relative, RESULT_QUERY_CASE=result_query_case,
            DROPIN_FAULT=dropin_fault, DROPIN_QUERY_CASE=dropin_query_case,
            RUNTIME_DIRECTORY_FAULT=runtime_directory_fault, RUNTIME_DIRECTORY_QUERY_CASE=runtime_directory_query_case,
            DROPIN_DIRECTORY_FAULT=dropin_directory_fault, DROPIN_DIRECTORY_QUERY_CASE=dropin_directory_query_case,
            DROPIN_TARGET_DRIFT=dropin_target_drift, DROPIN_TARGET_BOUNDARY=dropin_target_boundary,
            DROPIN_FORWARD_CASE=dropin_forward_case, DROPIN_TARGET_QUERY_CASE=dropin_target_query_case,
            RUN_TARGET_DRIFT=run_target_drift, RUN_TARGET_BOUNDARY=run_target_boundary,
            RUN_FORWARD_CASE=run_forward_case, RUN_TARGET_QUERY_CASE=run_target_query_case,
            DROPIN_DIR_DRIFT=dropin_dir_drift, DROPIN_DIR_BOUNDARY=dropin_dir_boundary,
            DROPIN_DIR_FORWARD_CASE=dropin_dir_forward_case, DROPIN_DIR_QUERY_CASE=dropin_dir_query_case,
            DROP_BACKUP_AFTER_VERIFY=metadata_case.split(":", 1)[1] if metadata_case.startswith("missing:") else "",
        )
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [_gateway_rollback_test_bash(), "fixture.sh"],
                cwd=root, env=env, capture_output=True, text=True, timeout=20,
                check=False,
            )
        finally:
            # timeout owns a different process group from the harness. Even if
            # the regression breaks its termination, kill only recorded fixture
            # processes with the same kernel start identity, never a reused PID.
            live_fixture_pids = []
            identities = list(root.glob("fixture-process-*.stat")) if real_timeout_mode else []
            for identity_path in identities:
                original = identity_path.read_text()
                pid = int(original.split(" ", 1)[0])
                original_fields = original[original.rfind(")") + 2:].split()
                try:
                    current = Path(f"/proc/{pid}/stat").read_text()
                except FileNotFoundError:
                    continue
                fields = current[current.rfind(")") + 2:].split()
                if fields[19] == original_fields[19] and fields[0] != "Z":
                    live_fixture_pids.append(pid)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            if evidence is not None:
                evidence["live_fixture_processes_after_command"] = len(live_fixture_pids)
                evidence["recorded_fixture_processes"] = len(identities)
        target = root / "target/entry.py"
        if evidence is not None:
            evidence["elapsed_seconds"] = time.monotonic() - started
            evidence["copy_timeout_calls"] = (root / "copy-timeout.calls").read_text().splitlines() if (root / "copy-timeout.calls").exists() else []
            evidence["mutation_timeout_calls"] = (root / "mutation-timeout.calls").read_text().splitlines() if (root / "mutation-timeout.calls").exists() else []
            evidence["evidence_timeout_calls"] = (root / "evidence-timeout.calls").read_text().splitlines() if (root / "evidence-timeout.calls").exists() else []
            evidence["target_timeout_calls"] = (root / "target-timeout.calls").read_text().splitlines() if (root / "target-timeout.calls").exists() else []
            evidence["command_entered"] = (root / "command-entered").exists()
            backup_path = root / "backup/existing/entry.py"
            evidence["backup"] = backup_path.read_bytes() if backup_path.is_file() else None
            evidence["target_inode"] = target.stat().st_ino if target.is_file() else None
            evidence["backup_inode"] = backup_path.stat().st_ino if backup_path.is_file() else None
            evidence["backup_exists"] = (root / "backup").is_dir()
            evidence["second_target"] = (root / "target/second.py").read_bytes() if (root / "target/second.py").is_file() else None
            evidence["target_drift_applied"] = (root / "target-drift-applied").exists()
            evidence["target_is_directory"] = target.is_dir()
            evidence["target_is_symlink"] = target.is_symlink()
            evidence["result_fault_applied"] = (root / "result-fault-applied").exists()
            evidence["source_result_receipt_exists"] = (root / "backup/source_result.json").exists()
            evidence["forward_calls"] = (root / "forward.calls").read_text().splitlines() if (root / "forward.calls").exists() else []
            evidence["second_backup"] = (root / "backup/existing/second.py").read_bytes() if (root / "backup/existing/second.py").is_file() else None
            evidence["source_drift_applied"] = (root / "source-drift-applied").exists()
            evidence["source_state_receipt_exists"] = (root / "backup/source_state.json").exists()
            evidence["retained_unrelated_files"] = [p.read_bytes() for p in root.glob("*/unrelated-retained")]
            evidence["lock_exists"] = (root / "run/fixture.lock").exists() or (root / "run/fixture.lock").is_symlink()
            evidence["lock_probe_calls"] = (root / "lock-probe.calls").read_text() if (root / "lock-probe.calls").exists() else ""
            evidence["dropin_directory_exists"] = (root / "dropins").exists()
            evidence["dropin_dir_drift_applied"] = (root / "dropin-dir-drift-applied").exists()
            evidence["dropin_dir_forward_calls"] = (root / "dropin-dir-forward.calls").read_text().splitlines() if (root / "dropin-dir-forward.calls").exists() else []
            dropin_path = root / "dropins/hardening.conf"
            evidence["dropin_bytes"] = dropin_path.read_bytes() if dropin_path.is_file() else None
            evidence["dropin_is_symlink"] = dropin_path.is_symlink()
            evidence["dropin_is_directory"] = dropin_path.is_dir()
            evidence["dropin_inode"] = dropin_path.stat().st_ino if dropin_path.is_file() else None
            dropin_backup = root / "backup/service-drop-in.before"
            evidence["dropin_backup_inode"] = dropin_backup.stat().st_ino if dropin_backup.is_file() else None
            evidence["dropin_fault_applied"] = (root / "dropin-fault-applied").exists()
            evidence["dropin_target_drift_applied"] = (root / "dropin-target-drift-applied").exists()
            evidence["dropin_forward_calls"] = (root / "dropin-forward.calls").read_text().splitlines() if (root / "dropin-forward.calls").exists() else []
            evidence["dropin_result_receipt_exists"] = (root / "backup/dropin_result.json").exists()
            evidence["run_forward_calls"] = (root / "run-forward.calls").read_text().splitlines() if (root / "run-forward.calls").exists() else []
            evidence["run_target_drift_applied"] = (root / "run-target-drift-applied").exists()
            evidence["run_directory_exists"] = (root / "run").exists()
            evidence["runtime_directory_is_directory"] = (root / "run").is_dir()
            evidence["runtime_directory_is_symlink"] = (root / "run").is_symlink()
            evidence["runtime_directory_fault_applied"] = (root / "runtime-directory-fault-applied").exists()
            evidence["runtime_directory_result_receipt_exists"] = (root / "backup/runtime_directory_result.json").exists()
            if (root / "run").is_dir():
                restored_run = (root / "run").stat()
                evidence["runtime_directory_metadata"] = (restored_run.st_uid, restored_run.st_gid, restored_run.st_mode & 0o7777)
            evidence["original_runtime_directory_metadata"] = (run_info.st_uid, run_info.st_gid, run_info.st_mode & 0o7777)
            evidence["dropin_directory_is_directory"] = (root / "dropins").is_dir()
            evidence["dropin_directory_is_symlink"] = (root / "dropins").is_symlink()
            evidence["dropin_directory_fault_applied"] = (root / "dropin-directory-fault-applied").exists()
            evidence["dropin_directory_result_receipt_exists"] = (root / "backup/dropin_directory_result.json").exists()
            if (root / "dropins").exists():
                observed_dir = (root / "dropins").stat()
                evidence["dropin_directory_metadata"] = (observed_dir.st_uid, observed_dir.st_gid, observed_dir.st_mode & 0o7777)
            evidence["original_dropin_directory_metadata"] = (dropin_dir_info.st_uid, dropin_dir_info.st_gid, dropin_dir_info.st_mode & 0o7777)
            evidence["originally_missing_target_exists"] = (root / "target/absent.py").exists()
            evidence["originally_missing_target_is_symlink"] = (root / "target/absent.py").is_symlink()
            missing_target = root / "target/absent.py"
            evidence["originally_missing_target_bytes"] = missing_target.read_bytes() if missing_target.is_file() else None
            evidence["outside_refusal_written"] = (root / "outside-backup/rollback_refused.json").exists()
            calls = root / "systemctl.calls"
            evidence["service_calls"] = calls.read_text() if calls.exists() else ""
            calls = root / "restore.calls"
            evidence["restore_calls"] = calls.read_text() if calls.exists() else ""
            calls = root / "operation.calls"
            evidence["operation_calls"] = calls.read_text() if calls.exists() else ""
            for kind in ("prepared", "helper", "rollback", "rollback_refused"):
                path = root / "backup" / (kind + ".json")
                if path.exists():
                    evidence[kind + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    evidence[kind + "_mode"] = path.stat().st_mode & 0o777
                    try:
                        evidence[kind] = json.loads(path.read_text())
                    except json.JSONDecodeError:
                        evidence[kind] = None
        return (
            completed,
            target.read_bytes() if target.is_file() else None,
            (root / "dropins/hardening.conf").exists(),
        )


def test_gateway_post_mutation_failures_restore_source_before_cleanup() -> None:
    for guard in _gateway_post_mutation_guards(_repair_script()):
        failure_code = re.search(r"(?:rollback|exit) (17|18)\n", guard)
        assert failure_code is not None
        completed, restored, dropin_exists = _run_gateway_rollback_guard(
            guard, predicate_passes=False
        )
        assert completed.returncode == int(failure_code.group(1)), completed.stderr
        assert completed.stderr.count("Rolling back the complete gateway") == 1
        assert restored == b"previous source\n", guard
        assert not dropin_exists
        assert completed.stdout.count("SYSTEMCTL:stop\n") == 1
        assert completed.stdout.count("SYSTEMCTL:start\n") == 1
        assert completed.stdout.endswith("CLEANUP\n")
        assert "GUARD_PASSED" not in completed.stdout

        completed, candidate, dropin_exists = _run_gateway_rollback_guard(
            guard, predicate_passes=True
        )
        assert completed.returncode == 0, completed.stderr
        assert candidate == b"candidate source\n"
        assert dropin_exists
        assert "Rolling back" not in completed.stderr
        assert completed.stdout == "GUARD_PASSED\nCLEANUP\n"


def test_gateway_mutation_deadlines_cover_every_runtime_command_and_stop_sequence() -> None:
    cases = (
        ("rm:lock", "dead_lock", "gateway_lock", {"real_lock_case": "dead"}),
        ("rm:first_source", "source_remove", "entry.py", {}),
        ("rm:dropin", "dropin_remove", "service_drop_in", {}),
        ("install:dropin_dir", "dropin_parent_create", "service_drop_in_directory", {"prior_dropin": True}),
        ("chown:dropin_dir", "dropin_chown", "service_drop_in_directory", {}),
        ("chmod:dropin_dir", "dropin_chmod", "service_drop_in_directory", {}),
        ("rmdir:dropin_dir", "dropin_directory_remove", "service_drop_in_directory", {"directory_case": "empty_dropin"}),
        ("chown:run_dir", "run_chown", "run_directory", {}),
        ("chmod:run_dir", "run_chmod", "run_directory", {}),
        ("rmdir:run_dir", "run_directory_remove", "run_directory", {"directory_case": "empty_run"}),
    )
    # Deterministic launcher failures: no sleep, spin or native signal is used.
    for fault, operation, target, options in cases:
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="mutation_deadline", mutation_deadline_fault=fault, evidence=evidence, **options)
        assert completed.returncode == 17, (fault, completed.stderr)
        assert evidence["mutation_timeout_calls"][-1] == fault
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["backup"] == b"previous source\n" and evidence["backup_exists"]
        assert fault not in evidence["operation_calls"].splitlines()
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"] == dict(
            operation=operation, target=target, exit_code=124,
            outcome="DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124", timeout_seconds=60,
            kill_after_seconds=5, mutation_effect_verified=False)
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert receipt["further_restoration_stopped"] and receipt["service_restart_attempted"] is False
        assert receipt["restoration_verified"] is False
        if fault in {"rm:lock", "rm:first_source"}:
            assert current == b"candidate source\n" and evidence["copy_timeout_calls"] == []


def test_gateway_mutation_deadline_can_follow_a_completed_mutation_without_claiming_unchanged() -> None:
    for fault, options, code in (
        ("rm:first_source", {}, 124),
        ("rm:second_source", {"second_source": True}, 137),
        ("rm:dropin", {}, 124),
        ("rm:lock", {"real_lock_case": "dead"}, 137),
    ):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="mutation_partial", mutation_deadline_fault=fault,
            mutation_deadline_exit_code=code, mutation_deadline_after=True,
            evidence=evidence, **options)
        assert completed.returncode == 17 and evidence["service_calls"] == "SYSTEMCTL:stop\n", completed.stderr
        assert evidence["operation_calls"].splitlines()[-1] == fault
        assert evidence["mutation_timeout_calls"][-1] == fault and evidence["backup_exists"]
        failure = evidence["rollback"]["failed_restoration_operation"]
        assert failure["exit_code"] == code and failure["mutation_effect_verified"] is False
        assert failure["outcome"] == ("FORCED_TERMINATION_OR_SIGKILL" if code == 137
                                      else "DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124")
        if fault == "rm:first_source": assert current is None
        if fault == "rm:second_source": assert current == b"previous source\n" and evidence["second_target"] is None
        if fault == "rm:dropin": assert not dropin_exists
        if fault == "rm:lock": assert not evidence["lock_exists"] and "Removed verified dead-PID" not in completed.stdout


def test_gateway_mutation_deadline_launcher_and_receipt_failures_preserve_trigger() -> None:
    for collision, code in ((False, 125), (False, 127), (True, 124)):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="rollback_write_failure" if collision else "mutation_launcher",
            mutation_deadline_fault="rm:first_source", mutation_deadline_exit_code=code, evidence=evidence)
        assert completed.returncode == 17 and current == b"candidate source\n", completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        assert evidence["operation_calls"] == ""
        if collision:
            assert evidence["rollback"] is None and "receipt persistence failed" in completed.stderr
        else:
            assert evidence["rollback"]["failed_restoration_operation"]["outcome"] == "LAUNCHER_OR_COMMAND_FAILURE"


def test_gateway_mutation_wrapper_has_exact_allowlist_argv_and_fixed_policy() -> None:
    function = _bash_function(_repair_script(), "bounded_recovery_mutation")
    assert function.count('--signal=TERM --kill-after=5s 60s') == 1
    with tempfile.TemporaryDirectory(prefix="gateway-mutation-policy-") as directory:
        root = Path(directory)
        harness = r'''set -u
RECOVERY_TIMEOUT_BIN=fixture_timeout
TARGET_ROOT=/fixture/source
LOCK_FILE=/fixture/run/lock
SERVICE_DROP_IN=/fixture/dropins/hardening
SERVICE_DROP_IN_DIR=/fixture/dropins
RUN_DIR=/fixture/run
BUNDLE_FILES=(entry.py nested/module.py)
RECOVERY_UID=${FIXTURE_UID:-12}
RECOVERY_GID=${FIXTURE_GID:-34}
RECOVERY_MODE=${FIXTURE_MODE:-0750}
fixture_timeout() {
  [[ "$1 $2 $3" == '--signal=TERM --kill-after=5s 60s' ]] || return 99
  shift 3
  printf '%s\0' "$@" >> "$PWD/argv.calls"
  printf '\n' >> "$PWD/argv.calls"
  return "$COMMAND_EXIT"
}
''' + function + r'''
bounded_recovery_mutation "$OPERATION" "$TARGET_ID" ${EXTRA_ARGUMENT:+unexpected}
rc=$?
printf '%s|%s|%s\n' "${RECOVERY_MUTATION_FAILURE:-}" "${RECOVERY_MUTATION_TARGET:-}" "${RECOVERY_MUTATION_EXIT_CODE:-0}"
exit "$rc"
'''
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        cases = (
            ("dead_lock", "gateway_lock", ["rm", "-f", "--", "/fixture/run/lock"]),
            ("source_remove", "nested/module.py", ["rm", "-f", "--", "/fixture/source/nested/module.py"]),
            ("dropin_remove", "service_drop_in", ["rm", "-f", "--", "/fixture/dropins/hardening"]),
            ("dropin_parent_create", "service_drop_in_directory", ["install", "-d", "-o", "root", "-g", "root", "-m", "0755", "--", "/fixture/dropins"]),
            ("dropin_chown", "service_drop_in_directory", ["chown", "--no-dereference", "12:34", "/fixture/dropins"]),
            ("run_chown", "run_directory", ["chown", "--no-dereference", "12:34", "/fixture/run"]),
            ("dropin_chmod", "service_drop_in_directory", ["chmod", "0750", "/fixture/dropins"]),
            ("run_chmod", "run_directory", ["chmod", "0750", "/fixture/run"]),
            ("dropin_directory_remove", "service_drop_in_directory", ["rmdir", "--", "/fixture/dropins"]),
            ("run_directory_remove", "run_directory", ["rmdir", "--", "/fixture/run"]),
        )
        for operation, target, expected in cases:
            for code in (0, 9, 124, 137):
                calls = root / "argv.calls"
                calls.unlink(missing_ok=True)
                result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                    env=dict(os.environ, OPERATION=operation, TARGET_ID=target, COMMAND_EXIT=str(code), EXTRA_ARGUMENT=""),
                    capture_output=True, text=True, timeout=10, check=False)
                assert result.returncode == code, result.stderr
                assert calls.read_bytes() == b"\x00".join(item.encode() for item in expected) + b"\x00\n"
                assert result.stdout == (f"{operation}|{target}|{code}\n" if code else "||0\n")
        for operation, target, extra in (("unknown", "gateway_lock", ""), ("dead_lock", "wrong", ""),
                ("source_remove", "../entry.py", ""), ("source_remove", "/entry.py", ""),
                ("source_remove", "unregistered.py", ""), ("run_chown", "service_drop_in_directory", ""),
                ("dead_lock", "gateway_lock", "yes")):
            calls = root / "argv.calls"
            calls.unlink(missing_ok=True)
            result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                env=dict(os.environ, OPERATION=operation, TARGET_ID=target, COMMAND_EXIT="0", EXTRA_ARGUMENT=extra),
                capture_output=True, text=True, timeout=10, check=False)
            assert result.returncode == 125 and not calls.exists(), result.stderr
        for operation, variable, invalid in (("run_chown", "FIXTURE_UID", "--reference=evil"),
                ("run_chown", "FIXTURE_GID", "1:2"), ("run_chmod", "FIXTURE_MODE", "888")):
            calls = root / "argv.calls"
            calls.unlink(missing_ok=True)
            result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                env=dict(os.environ, OPERATION=operation, TARGET_ID="run_directory", COMMAND_EXIT="0",
                         EXTRA_ARGUMENT="", **{variable: invalid}),
                capture_output=True, text=True, timeout=10, check=False)
            assert result.returncode == 125 and not calls.exists(), result.stderr


def test_gateway_forward_lock_mutation_failure_does_not_poison_rollback_evidence() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="forward_lock_deadline", real_lock_case="dead",
        mutation_deadline_fault="rm:lock", forward_lock_deadline_failure=True, evidence=evidence)
    assert completed.returncode == 124 and current == b"previous source\n", completed.stderr
    assert "FORWARD_LOCK_FAILURE=124" in completed.stdout
    assert evidence["mutation_timeout_calls"][:2] == ["rm:lock", "rm:lock"]
    assert evidence["service_calls"].splitlines() == [
        "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]
    assert evidence["rollback"]["trigger_exit_code"] == 124
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert "failed_restoration_operation" not in evidence["rollback"]
    assert evidence["backup_exists"] and not evidence["lock_exists"]


def test_gateway_mutation_success_keeps_result_checks_and_missing_directory_policy() -> None:
    for directory_case, prior_dropin in (("", True), ("empty_run", False), ("empty_dropin", False)):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="mutation_success", second_source=True, prior_dropin=prior_dropin,
            real_lock_case="dead", directory_case=directory_case, evidence=evidence)
        assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
        assert evidence["second_target"] == b"second previous\n" and not evidence["lock_exists"]
        assert evidence["service_calls"].splitlines() == [
            "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]
        assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
        assert evidence["rollback"]["restoration_verified"] is False
        assert "failed_restoration_operation" not in evidence["rollback"]
        assert evidence["mutation_timeout_calls"][:3] == ["rm:lock", "rm:first_source", "rm:second_source"]
        if directory_case: assert "rmdir:" + ("run_dir" if directory_case == "empty_run" else "dropin_dir") in evidence["mutation_timeout_calls"]


def test_gateway_copy_deadline_preserves_partial_state_and_stops_sequence() -> None:
    # A bounded launcher stub returns immediately: these are outcome/control-flow
    # fixtures, not elapsed-time or native-copy failure evidence.
    for target, code, options, calls in (
        ("first_source", 124, {}, ["first_source"]),
        ("second_source", 137, {"second_source": True}, ["first_source", "second_source"]),
        ("dropin", 124, {"prior_dropin": True}, ["first_source", "dropin"]),
    ):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="copy_deadline", copy_deadline_target=target,
            copy_deadline_exit_code=code, copy_deadline_partial=True, evidence=evidence, **options,
        )
        assert completed.returncode == 17, completed.stderr
        assert completed.stderr.count("Rolling back the complete gateway") == 1
        assert evidence["copy_timeout_calls"] == calls
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["backup"] == b"previous source\n" and evidence["backup_exists"]
        receipt = evidence["rollback"]
        assert receipt["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert receipt["trigger_exit_code"] == 17 and receipt["restoration_verified"] is False
        assert receipt["partial_state_possible"] and receipt["further_restoration_stopped"]
        assert receipt["service_restart_attempted"] is False
        assert receipt["failed_restoration_operation"] == dict(
            operation="dropin_copy" if target == "dropin" else "source_copy",
            target={"first_source": "entry.py", "second_source": "second.py", "dropin": "service_drop_in"}[target],
            exit_code=code,
            outcome="DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124" if code == 124 else "FORCED_TERMINATION_OR_SIGKILL",
            timeout_seconds=60, kill_after_seconds=5, partial_destination_possible=True,
        )
        assert current == (b"partial copy\n" if target == "first_source" else b"previous source\n")
        if target == "second_source":
            assert evidence["second_target"] == b"partial copy\n"
            assert evidence["second_backup"] == b"second previous\n"
        if target == "dropin":
            assert evidence["dropin_bytes"] == b"partial copy\n"


def test_gateway_copy_deadline_launcher_and_receipt_failure_keep_original_status() -> None:
    for collision, code in ((False, 125), (True, 124)):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="rollback_write_failure" if collision else "copy_launcher_failure",
            copy_deadline_target="first_source", copy_deadline_exit_code=code,
            evidence=evidence,
        )
        assert completed.returncode == 17 and current is None and dropin_exists
        assert evidence["copy_timeout_calls"] == ["first_source"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["backup"] == b"previous source\n" and evidence["backup_exists"]
        if collision:
            assert evidence["rollback"] is None
            assert "receipt persistence failed" in completed.stderr
        else:
            assert evidence["rollback"]["failed_restoration_operation"]["outcome"] == "LAUNCHER_OR_COMMAND_FAILURE"


def test_gateway_bounded_copy_success_keeps_existing_result_checks() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="bounded_copy_success", second_source=True, prior_dropin=True,
        evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert current == b"previous source\n" and evidence["second_target"] == b"second previous\n"
    assert dropin_exists and evidence["dropin_bytes"] == b"previous hardening\n"
    assert evidence["copy_timeout_calls"] == ["first_source", "second_source", "dropin"]
    assert evidence["service_calls"].splitlines() == [
        "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert evidence["rollback"]["restoration_verified"] is False
    assert "failed_restoration_operation" not in evidence["rollback"]


def test_gateway_copy_deadline_wrapper_has_fixed_policy_and_preserves_command_codes() -> None:
    script = _repair_script()
    function = _bash_function(script, "bounded_recovery_copy")
    assert function.count('--signal=TERM --kill-after=5s 60s') == 1
    assert _bash_function(script, "rollback").count(" bounded_recovery_copy ") == 2
    with tempfile.TemporaryDirectory(prefix="gateway-copy-policy-") as directory:
        root = Path(directory)
        harness = '''set -u
RECOVERY_TIMEOUT_BIN=fixture_timeout
fixture_timeout() {
  [[ "$1 $2 $3 $4 $5 $6 $7 $8" == '--signal=TERM --kill-after=5s 60s cp -a -- -source -destination' ]] || return 99
  printf 'FIXED_COPY_POLICY\n'
  shift 3
  "$@"
}
cp() { return "$COMMAND_EXIT"; }
''' + function + '''
if [[ "$BAD_ARITY" == true ]]; then bounded_recovery_copy -source; else bounded_recovery_copy -source -destination; fi
'''
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        for code, invalid in ((0, False), (9, False), (124, False), (137, False), (0, True)):
            completed = subprocess.run(
                [_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                env=dict(os.environ, COMMAND_EXIT=str(code), BAD_ARITY=str(invalid).lower()),
                capture_output=True, text=True, timeout=10, check=False,
            )
            assert completed.returncode == (125 if invalid else code), completed.stderr
            assert completed.stdout == ("" if invalid else "FIXED_COPY_POLICY\n")
    # In particular an underlying copy exit124 is preserved, not identified as
    # proof that a deadline expired. No child sleeps or spins in these fixtures.


def test_gateway_recovery_service_failure_stops_sequence_and_keeps_original_code() -> None:
    verbs = ["stop", "daemon-reload", "reset-failed", "start"]
    for verb in verbs:
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="service_failure", service_failure=verb, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        assert completed.stderr.count("Rolling back the complete gateway") == 1
        expected = verbs[:verbs.index(verb) + 1]
        assert evidence["service_calls"].splitlines() == ["SYSTEMCTL:" + item for item in expected]
        receipt = evidence["rollback"]
        assert receipt["trigger_exit_code"] == 17 and receipt["restoration_verified"] is False
        assert receipt["service_state_verified"] is False
        assert receipt["systemd_job_cancellation_verified"] is False
        assert receipt["service_commands"][-1] == dict(
            verb=verb, exit_code=9, outcome="COMMAND_FAILED", timeout_seconds=60, kill_after_seconds=5)
        assert evidence["backup"] == b"previous source\n"
        if verb == "stop":
            assert current == b"candidate source\n" and dropin_exists
            assert evidence["restore_calls"] == ""
            assert receipt["status"] == "ROLLBACK_ABORTED_SERVICE_STOP_UNCONFIRMED"
            assert receipt["restore_attempted"] is False
        else:
            assert current == b"previous source\n" and not dropin_exists
            assert receipt["status"] == "ROLLBACK_INCOMPLETE_SERVICE_COMMAND_FAILED"
            assert receipt["restore_attempted"] is True


def test_gateway_recovery_stop_failure_receipt_failure_preserves_trigger_and_backup() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure", service_failure="stop", evidence=evidence,
    )
    assert completed.returncode == 17 and "receipt persistence failed" in completed.stderr
    assert current == b"candidate source\n" and dropin_exists
    assert evidence["restore_calls"] == "" and evidence["backup"] == b"previous source\n"
    assert evidence["rollback"] is None


def test_gateway_recovery_reserved_exit_codes_remain_ambiguous_in_receipt() -> None:
    for code, outcome in ((124, "DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124"),
                          (137, "FORCED_TERMINATION_OR_SIGKILL"),
                          (125, "LAUNCHER_OR_COMMAND_FAILURE")):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="reserved_exit", service_failure="stop", service_exit_code=code, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"candidate source\n"
        assert evidence["restore_calls"] == ""
        assert evidence["rollback"]["service_commands"][-1]["outcome"] == outcome


def test_gateway_recovery_keeps_originally_inactive_service_stopped() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="inactive_service", service_was_active=False, evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n"
    assert evidence["service_calls"].splitlines() == [
        "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed"]
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert all(item["outcome"] == "COMPLETED" for item in evidence["rollback"]["service_commands"])


def test_gateway_recovery_timeout_preflight_is_required_before_mutation() -> None:
    script = _repair_script()
    function = _bash_function(script, "require_recovery_timeout")
    with tempfile.TemporaryDirectory(prefix="gateway-timeout-preflight-") as directory:
        root = Path(directory)
        (root / "bin").mkdir()
        harness = 'set -Eeuo pipefail\n' + function + '\nPATH="$PWD/bin"\nrequire_recovery_timeout\nprintf MUTATED\n'
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        for fixture in (None, "unrelated timeout implementation", "timeout (GNU coreutils) fixture"):
            if fixture:
                executable = root / "bin/timeout"
                executable.write_text("#!/bin/bash\nprintf '%s\\n' '" + fixture + "'\n", newline="\n")
                executable.chmod(0o755)
            completed = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                                       capture_output=True, text=True, timeout=10, check=False)
            assert completed.returncode == (0 if fixture and fixture.startswith("timeout (GNU") else 10), completed.stderr
            assert completed.stdout == ("MUTATED" if completed.returncode == 0 else "")
    assert script.index('require_recovery_timeout || {') < script.index('systemctl stop "$SERVICE"\nSERVICE_STOPPED=true')
    assert script.index('require_recovery_timeout || {') < script.index('RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"')
    assert script.index('record_recovery_evidence verify "$rc"') < script.index('if ! bounded_recovery_systemctl stop;')


def test_gateway_evidence_deadline_dispatch_is_fixed_and_rejects_unknown_kinds() -> None:
    function = _bash_function(_repair_script(), "record_recovery_evidence")
    # This launcher never runs the Python body. It checks the real wrapper's
    # fixed argv and proves stdout cannot hide a nonzero subprocess exit.
    harness = r'''
set -uo pipefail
BACKUP_DIR=fixture-backup SOURCE_COMMIT=fixture-source BUNDLE_SHA=fixture-bundle
HARDENING_SHA=fixture-hardening RECOVERY_MANIFEST_SHA=fixture-manifest
TARGET_ROOT=fixture-target SERVICE_DROP_IN=fixture-dropin RUN_DIR=fixture-run
SERVICE_DROP_IN_DIR=fixture-dropin-dir RECOVERY_TIMEOUT_BIN=fixture_timeout
BUNDLE_FILES=(entry.py)
declare -A SOURCE_WRITE_STATES=() SOURCE_CANDIDATE_SHA=() SOURCE_TARGET_VERSION=() SOURCE_RESULT_STATES=()
fixture_timeout() {
  [[ "$1 $2 $3 $4 $5" == '--signal=TERM --kill-after=5s 60s python3 -' ]] || return 99
  [[ "$6" == fixture-backup && "$7" == "$expected_kind" ]] || return 98
  printf '%s\n' "$7" >> calls
  printf 'valid-looking-output\n'
  return "$fixture_rc"
}
'''
    harness += function + r'''
for expected_kind in prepared helper rollback verify rollback_refused source_state source_result dropin_result runtime_directory_result dropin_directory_result; do
  for fixture_rc in 0 29 124 125 126 127 137; do
    output="$(record_recovery_evidence "$expected_kind" 0)"; actual_rc=$?
    [[ "$actual_rc" == "$fixture_rc" && "$output" == valid-looking-output ]] || exit 97
  done
done
for invalid in unknown 'prepared;printf unsafe' ''; do
  record_recovery_evidence "$invalid"; [[ $? == 14 ]] || exit 96
done
record_recovery_evidence; [[ $? == 14 ]] || exit 95
record_recovery_evidence prepared 0 extra excess; [[ $? == 14 ]] || exit 94
for invalid in dropin_result runtime_directory_result dropin_directory_result; do
  record_recovery_evidence "$invalid" 0 extra; [[ $? == 14 ]] || exit 93
done
'''
    with tempfile.TemporaryDirectory(prefix="gateway-evidence-dispatch-") as directory:
        root = Path(directory)
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                                capture_output=True, text=True, timeout=10, check=False)
        assert result.returncode == 0, result.stderr
        assert len((root / "calls").read_text().splitlines()) == 70
    assert result.stdout == ""
    for outcome in ("DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124", "FORCED_TERMINATION_OR_SIGKILL",
                    "LAUNCHER_OR_COMMAND_FAILURE", "COMMAND_FAILED"):
        assert outcome in result.stderr
    assert result.stderr.count("completion=UNKNOWN possibly_published=true retained=true retry=false") == 60


def test_gateway_evidence_deadline_preparation_and_verification_fail_before_runtime() -> None:
    for kind in ("prepared", "verify"):
        for code in (124, 137, 125):
            evidence: dict = {}
            completed, current, _ = _run_gateway_rollback_guard(
                _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
                recovery_case="evidence_deadline", evidence=evidence,
                evidence_deadline_kind=kind, evidence_deadline_exit_code=code,
                evidence_deadline_after=True)
            assert completed.returncode == (code if kind == "prepared" else 17), completed.stderr
            assert current == b"candidate source\n" and evidence["backup"] == b"previous source\n"
            assert evidence["service_calls"] == evidence["restore_calls"] == ""
            # Preparation precedes the fixture's forward copy. Verification is
            # a rollback entry guard after that copy, but before recovery work.
            assert len(evidence["forward_calls"]) == (0 if kind == "prepared" else 1)
            # Even a preparation receipt already published before timeout is
            # retained, but its stdout is not accepted as a verified result.
            assert evidence["prepared"]["kind"] == "prepared"
            assert evidence["evidence_timeout_calls"].count(kind) == 1
            assert f"kind={kind} exit={code}" in completed.stderr
            assert "completion=UNKNOWN" in completed.stderr
            if kind == "verify":
                assert evidence["rollback_refused"]["trigger_exit_code"] == 17


def test_gateway_evidence_deadline_queries_reject_valid_stdout_and_stop_recovery() -> None:
    for kind in ("source_state", "source_result", "dropin_result",
                 "runtime_directory_result", "dropin_directory_result"):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="evidence_deadline", evidence=evidence,
            evidence_deadline_kind=kind, evidence_deadline_exit_code=137,
            evidence_deadline_after=True)
        assert completed.returncode == 17, (kind, completed.stderr)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["backup"] == b"previous source\n" and evidence["backup_exists"]
        assert evidence["evidence_timeout_calls"].count(kind) == 1
        assert f"kind={kind} exit=137" in completed.stderr
        assert "completion=UNKNOWN" in completed.stderr
        assert evidence["rollback"]["trigger_exit_code"] == 17
        assert evidence["rollback"]["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert evidence["rollback"]["failed_restoration_operation"]["exit_code"] == 137
        assert not evidence[kind + "_receipt_exists"]
        if kind == "source_state":
            # The established sequence checks/removes the dead lock first;
            # source-query failure must prevent source restoration after it.
            assert evidence["restore_calls"] == "lock\n"


def test_gateway_evidence_deadline_terminal_failures_retain_receipts_and_original_trigger() -> None:
    for kind in ("helper", "rollback", "rollback_refused"):
        for after in (False, True):
            evidence: dict = {}
            completed, _, _ = _run_gateway_rollback_guard(
                _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=kind == "helper",
                recovery_case="later_gate_failure" if kind == "helper" else "backup_changed" if kind == "rollback_refused" else "evidence_deadline",
                evidence=evidence, evidence_deadline_kind=kind,
                evidence_deadline_exit_code=124, evidence_deadline_after=after)
            assert completed.returncode == (23 if kind == "helper" else 17), (kind, completed.stderr)
            assert evidence["backup_exists"]
            assert evidence["evidence_timeout_calls"].count(kind) == 1
            assert (kind in evidence) is after
            assert f"kind={kind} exit=124" in completed.stderr
            assert "completion=UNKNOWN possibly_published=true retained=true retry=false" in completed.stderr
            assert "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK" not in completed.stdout
            if after and kind != "helper":
                assert evidence[kind]["trigger_exit_code"] == 17
            if kind == "rollback_refused":
                assert evidence["service_calls"] == evidence["restore_calls"] == ""


def test_gateway_evidence_deadline_normal_receipts_and_queries_keep_existing_contract() -> None:
    evidence: dict = {}
    completed, current, dropin = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="evidence_success", second_source=True, prior_dropin=True, evidence=evidence)
    assert completed.returncode == 17, completed.stderr
    assert current == b"previous source\n" and evidence["second_target"] == b"second previous\n"
    assert dropin and evidence["dropin_bytes"] == b"previous hardening\n"
    assert set(evidence["evidence_timeout_calls"]) == {
        "prepared", "verify", "source_state", "source_result", "dropin_result",
        "runtime_directory_result", "dropin_directory_result", "rollback"}
    assert evidence["rollback"]["manifest_sha256"] == evidence["prepared_sha256"]
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert evidence["rollback"]["restoration_verified"] is False
    assert "Recovery evidence failed:" not in completed.stderr


def test_gateway_target_reader_deadline_dispatch_preserves_argv_and_status() -> None:
    function = _bash_function(_repair_script(), "recorded_target_version")
    harness = r'''
set -uo pipefail
TARGET_ROOT=fixture-target SERVICE_DROP_IN=fixture-dropin RUN_DIR=fixture-run
BUNDLE_FILES=(entry.py second.py)
RECOVERY_TIMEOUT_BIN=fixture_timeout
fixture_timeout() {
  [[ "$1 $2 $3 $4 $5" == '--signal=TERM --kill-after=5s 60s python3 -' ]] || return 99
  shift 5
  [[ $# == 9 && "$1" == fixture-target && "$2" == fixture-dropin && "$3" == fixture-run ]] || return 98
  [[ "$4" == "$kind" && "$5" == "$mode" && "$6" == "$relative" && "$7" == "$candidate" && "$8 $9" == 'entry.py second.py' ]] || return 97
  printf 'call\n' >> calls
  printf 'valid-looking-output\n'
  return "$fixture_rc"
}
'''
    harness += function + r'''
for query in source:capture source:absent dropin:capture dropin:absent runtime:capture dropin_directory:capture; do
  kind="${query%:*}"; mode="${query#*:}"
  relative=''; candidate=''
  [[ "$kind" != source ]] || relative=entry.py
  if [[ "$mode" == capture ]]; then candidate=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; fi
  [[ "$kind" != runtime ]] || candidate=1:2:750
  [[ "$kind" != dropin_directory ]] || candidate=0:0:755
  for fixture_rc in 0 29 124 125 126 127 137; do
    output="$(recorded_target_version "$kind" "$mode" "$relative" "$candidate")"; actual_rc=$?
    [[ "$actual_rc" == "$fixture_rc" && "$output" == valid-looking-output ]] || exit 96
  done
done
recorded_target_version; [[ $? == 14 ]] || exit 95
recorded_target_version a b c d e; [[ $? == 14 ]] || exit 94
'''
    with tempfile.TemporaryDirectory(prefix="gateway-target-dispatch-") as directory:
        root = Path(directory)
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
                                capture_output=True, text=True, timeout=10, check=False)
        assert result.returncode == 0, result.stderr
        assert len((root / "calls").read_text().splitlines()) == 42
    assert result.stdout == ""
    for outcome in ("DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124", "FORCED_TERMINATION_OR_SIGKILL",
                    "LAUNCHER_OR_COMMAND_FAILURE", "COMMAND_FAILED"):
        assert outcome in result.stderr
    assert result.stderr.count("observation=UNKNOWN retry=false") == 36


def test_gateway_target_reader_deadline_recovery_capture_stops_at_first_failure() -> None:
    cases = (
        ("source:capture:entry.py:rollback", "target_state", "entry.py", 124),
        ("source:capture:second.py:rollback", "target_state", "second.py", 137),
        ("dropin_directory:capture::rollback", "dropin_directory_target_state", "service_drop_in_directory", 125),
        ("dropin:capture::rollback", "dropin_target_state", "service_drop_in", 126),
        ("runtime:capture::rollback", "run_target_state", "run_directory", 127),
    )
    for query, operation, target, code in cases:
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="target_reader_deadline", second_source=True, prior_dropin=True,
            target_deadline_query=query, target_deadline_exit_code=code, evidence=evidence)
        assert completed.returncode == 17, (query, completed.stderr)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        assert evidence["target_timeout_calls"].count(query) == 1
        assert evidence["rollback"]["failed_restoration_operation"] == dict(
            operation=operation, target=target, exit_code=code)
        assert evidence["rollback"]["trigger_exit_code"] == 17
        assert evidence["rollback"]["partial_state_possible"]
        assert evidence["rollback"]["restoration_verified"] is False
        assert f"Target version reader failed: exit={code}" in completed.stderr
        if target == "entry.py":
            assert current == b"candidate source\n" and "rm:first_source" not in evidence["operation_calls"]
        elif target == "second.py":
            assert current == b"previous source\n" and evidence["second_target"] == b"second candidate\n"
            assert "rm:second_source" not in evidence["operation_calls"]
        elif target.startswith("service_drop_in"):
            assert evidence["dropin_bytes"] == b"candidate hardening\n"
            assert "rm:dropin" not in evidence["operation_calls"]
        else:
            assert "chown:run_dir" not in evidence["operation_calls"]


def test_gateway_target_reader_deadline_absence_rejects_valid_stdout_before_copy() -> None:
    for query, operation, target in (
        ("source:absent:entry.py:rollback", "target_absent", "entry.py"),
        ("dropin:absent::rollback", "dropin_target_absent", "service_drop_in"),
    ):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="target_reader_deadline", prior_dropin=True,
            target_deadline_query=query, target_deadline_exit_code=137, evidence=evidence)
        assert completed.returncode == 17 and evidence["service_calls"] == "SYSTEMCTL:stop\n", completed.stderr
        assert evidence["target_timeout_calls"].count(query) == 1
        assert evidence["rollback"]["failed_restoration_operation"] == dict(operation=operation, target=target, exit_code=137)
        assert evidence["rollback"]["partial_state_possible"] and evidence["backup_exists"]
        if target == "entry.py":
            assert current is None and "cp:first_source" not in evidence["operation_calls"]
        else:
            assert evidence["dropin_bytes"] is None and "cp:dropin" not in evidence["operation_calls"]


def test_gateway_target_reader_deadline_forward_readback_keeps_write_pending() -> None:
    for query, field in (
        ("source:capture:entry.py:forward", "source_write_states"),
        ("dropin:capture::forward", "dropin_write_state"),
        ("dropin_directory:capture::forward", "dropin_directory_write_state"),
        ("runtime:capture::forward", "runtime_directory_write_state"),
    ):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="target_reader_deadline", prior_dropin=True,
            target_deadline_query=query, target_deadline_exit_code=124, evidence=evidence)
        assert completed.returncode == 124 and evidence["service_calls"] == "SYSTEMCTL:stop\n", (query, completed.stderr)
        assert evidence["target_timeout_calls"].count(query) == 1
        receipt = evidence["rollback"]
        state = next(item for item in receipt[field] if item["path"] == "entry.py") if field == "source_write_states" else receipt[field]
        assert state["state"] == "WRITE_PENDING" and state["installed_version_sha256"] is None
        assert receipt["trigger_exit_code"] == 124 and receipt["partial_state_possible"]
        assert receipt["failed_restoration_operation"]["exit_code"] == 14
        assert current == b"candidate source\n" and evidence["backup_exists"]


def test_gateway_target_reader_deadline_receipt_failure_retains_original_trigger() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="target_reader_deadline", target_deadline_query="source:capture:entry.py:rollback",
        target_deadline_exit_code=124, evidence_deadline_kind="rollback",
        evidence_deadline_exit_code=137, evidence_deadline_after=False, evidence=evidence)
    assert completed.returncode == 17 and current == b"candidate source\n", completed.stderr
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
    assert "rollback" not in evidence and "receipt persistence failed" in completed.stderr
    assert "Target version reader failed: exit=124" in completed.stderr
    assert "kind=rollback exit=137" in completed.stderr


def _run_native_gateway_target_reader_deadline(mode: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    # Only this extracted reader launch uses native GNU timeout. The fake reader
    # cannot invoke service or target mutations; its PID identity enables cleanup.
    function = _bash_function(_repair_script(), "recorded_target_version")
    policy = '"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s'
    assert function.count(policy) == 1
    function = function.replace(policy, '"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=0.2s 0.2s')
    with tempfile.TemporaryDirectory(prefix="gateway-target-native-") as directory:
        root = Path(directory)
        (root / "bin").mkdir()
        reader = root / "bin/python3"
        reader.write_text(r'''#!/bin/bash
set -eu
[[ "$1" == - && "$2" == "$PWD/target" && "$5 $6 $7" == 'source capture entry.py' ]] || exit 91
printf 'capture\n' >> "$PWD/reader.calls"
/bin/cat "/proc/$BASHPID/stat" > "$PWD/reader.stat"
printf '%064d\n' 0
if [[ "$FIXTURE_MODE" == success ]]; then exit 0; fi
if [[ "$FIXTURE_MODE" == ignore_term ]]; then trap '' TERM; fi
while :; do :; done
''', encoding="utf-8", newline="\n")
        reader.chmod(0o700)
        harness = 'set -Eeuo pipefail\n' + _bash_function(_repair_script(), "require_recovery_timeout") + r'''
require_recovery_timeout
TARGET_ROOT="$PWD/target" SERVICE_DROP_IN="$PWD/dropin" RUN_DIR="$PWD/run"
BUNDLE_FILES=(entry.py)
CAPTURED_TARGET_VERSION=not-adopted
PATH="$PWD/bin:$PATH"
'''
        harness += function + "\n" + _bash_function(_repair_script(), "source_target_version") + "\n"
        harness += _bash_function(_repair_script(), "capture_source_target_version") + r'''
reader_status=0
capture_source_target_version entry.py aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa || reader_status=$?
printf 'STATUS=%s\nCAPTURE=%s\n' "$reader_status" "$CAPTURED_TARGET_VERSION"
exit "$reader_status"
'''
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        env = dict(os.environ, FIXTURE_MODE=mode)
        started = time.monotonic()
        live = []
        try:
            result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=5, check=False)
        finally:
            identity = root / "reader.stat"
            if identity.exists():
                original = identity.read_text()
                pid = int(original.split(" ", 1)[0])
                original_fields = original[original.rfind(")") + 2:].split()
                try:
                    current = Path(f"/proc/{pid}/stat").read_text()
                except FileNotFoundError:
                    current = ""
                if current:
                    fields = current[current.rfind(")") + 2:].split()
                    if fields[19] == original_fields[19] and fields[0] != "Z":
                        live.append(pid)
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
        return result, {"elapsed_seconds": time.monotonic() - started,
                        "live_after_command": len(live),
                        "calls": (root / "reader.calls").read_text().splitlines()}


@unittest.skipIf(sys.platform != "linux", "Native target reader isolation requires Linux CI")
def test_gateway_native_target_reader_deadline_success_control() -> None:
    completed, facts = _run_native_gateway_target_reader_deadline("success")
    assert completed.returncode == 0 and completed.stderr == "", completed.stderr
    assert completed.stdout == "STATUS=0\nCAPTURE=" + "0" * 64 + "\n"
    assert facts["calls"] == ["capture"] and facts["live_after_command"] == 0


@unittest.skipIf(sys.platform != "linux", "Native target reader deadline and ignored TERM require Linux CI")
def test_gateway_hung_target_reader_and_ignored_term_are_bounded_without_adoption() -> None:
    for mode, code, outcome in (("hang", 124, "DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124"),
                                ("ignore_term", 137, "FORCED_TERMINATION_OR_SIGKILL")):
        completed, facts = _run_native_gateway_target_reader_deadline(mode)
        assert completed.returncode == code, completed.stderr
        assert completed.stdout == f"STATUS={code}\nCAPTURE=not-adopted\n"
        assert facts["elapsed_seconds"] < 4 and facts["live_after_command"] == 0
        assert facts["calls"] == ["capture"]
        assert outcome in completed.stderr and "observation=UNKNOWN retry=false" in completed.stderr


def _run_native_gateway_evidence_deadline(mode: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    # Execute the real wrapper with native GNU timeout and a fake Python writer.
    # Only the extracted test copy's two durations are shortened. The fake writer
    # creates one private fixture artifact, never source/runtime/service state.
    function = _bash_function(_repair_script(), "record_recovery_evidence")
    assert function.count('"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s') == 1
    function = function.replace('"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s',
                                '"$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=0.2s 0.2s')
    with tempfile.TemporaryDirectory(prefix="gateway-evidence-native-") as directory:
        root = Path(directory)
        (root / "bin").mkdir()
        writer = root / "bin/python3"
        writer.write_text(r'''#!/bin/bash
set -eu
[[ "$1" == - && "$2" == "$PWD/backup" && "$3" == rollback ]] || exit 91
printf '%s\n' "$3" >> "$PWD/writer.calls"
/bin/cat "/proc/$BASHPID/stat" > "$PWD/writer.stat"
set -C
printf 'possibly published receipt\n' > "$2/rollback.json"
printf 'valid-looking-hash\n'
if [[ "$FIXTURE_MODE" == success ]]; then exit 0; fi
if [[ "$FIXTURE_MODE" == ignore_term ]]; then trap '' TERM; fi
while :; do :; done
''', encoding="utf-8", newline="\n")
        writer.chmod(0o700)
        (root / "backup").mkdir()
        harness = 'set -Eeuo pipefail\n' + _bash_function(_repair_script(), "require_recovery_timeout") + r'''
require_recovery_timeout
BACKUP_DIR="$PWD/backup" SOURCE_COMMIT=fixture-source BUNDLE_SHA=fixture-bundle
HARDENING_SHA=fixture-hardening RECOVERY_MANIFEST_SHA=fixture-manifest
TARGET_ROOT="$PWD/target" SERVICE_DROP_IN="$PWD/dropin" RUN_DIR="$PWD/run"
SERVICE_DROP_IN_DIR="$PWD/dropins"
BUNDLE_FILES=()
declare -A SOURCE_WRITE_STATES=() SOURCE_CANDIDATE_SHA=() SOURCE_TARGET_VERSION=() SOURCE_RESULT_STATES=()
PATH="$PWD/bin:$PATH"
'''
        harness += function + "\n" + _bash_function(_repair_script(), "finish_rollback") + '\nfinish_rollback 17\n'
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        env = dict(os.environ, FIXTURE_MODE=mode)
        started = time.monotonic()
        live = []
        try:
            result = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh"], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=5, check=False)
        finally:
            # Guard cleanup by the recorded process start identity. A regression
            # must not leave the deliberately hung writer alive or kill a reused PID.
            identity = root / "writer.stat"
            if identity.exists():
                original = identity.read_text()
                pid = int(original.split(" ", 1)[0])
                original_fields = original[original.rfind(")") + 2:].split()
                try:
                    current = Path(f"/proc/{pid}/stat").read_text()
                except FileNotFoundError:
                    current = ""
                if current:
                    fields = current[current.rfind(")") + 2:].split()
                    if fields[19] == original_fields[19] and fields[0] != "Z":
                        live.append(pid)
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
        facts = {"elapsed_seconds": time.monotonic() - started, "live_after_command": len(live),
                 "calls": (root / "writer.calls").read_text().splitlines(),
                 "receipt": (root / "backup/rollback.json").read_bytes(),
                 "backup_files": sorted(p.name for p in (root / "backup").iterdir())}
        return result, facts


@unittest.skipIf(sys.platform != "linux", "Native evidence launcher isolation requires Linux CI")
def test_gateway_native_evidence_launcher_isolated_success_control() -> None:
    completed, facts = _run_native_gateway_evidence_deadline("success")
    assert completed.returncode == 17, completed.stderr
    assert completed.stdout == "valid-looking-hash\n" and completed.stderr == ""
    assert facts["calls"] == ["rollback"] and facts["live_after_command"] == 0
    assert facts["backup_files"] == ["rollback.json"]
    assert facts["receipt"] == b"possibly published receipt\n"


@unittest.skipIf(sys.platform != "linux", "Native evidence deadline and ignored TERM require Linux CI")
def test_gateway_hung_evidence_writer_and_ignored_term_are_bounded_without_retry() -> None:
    for mode, outcome in (("hang", "DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124"),
                          ("ignore_term", "FORCED_TERMINATION_OR_SIGKILL")):
        completed, facts = _run_native_gateway_evidence_deadline(mode)
        assert completed.returncode == 17, completed.stderr
        assert facts["elapsed_seconds"] < 4 and facts["live_after_command"] == 0
        assert facts["calls"] == ["rollback"] and facts["backup_files"] == ["rollback.json"]
        assert facts["receipt"] == b"possibly published receipt\n"
        assert outcome in completed.stderr and "completion=UNKNOWN" in completed.stderr
        assert "receipt persistence failed" in completed.stderr
        assert completed.stdout == "valid-looking-hash\n"


@unittest.skipIf(sys.platform != "linux", "Native service launcher isolation requires Linux CI")
def test_gateway_native_service_launcher_keeps_filesystem_commands_inert() -> None:
    # No command hangs in this control. Native timeout dispatch applies only to
    # the fake systemctl executable, never root ownership or other FS commands.
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="native_service_isolation", real_timeout_mode="success",
        second_source=True, prior_dropin=True, real_lock_case="dead", evidence=evidence)
    assert completed.returncode == 17, completed.stderr
    assert current == b"previous source\n" and evidence["second_target"] == b"second previous\n"
    assert dropin_exists and evidence["dropin_bytes"] == b"previous hardening\n"
    assert evidence["copy_timeout_calls"] == ["first_source", "second_source", "dropin"]
    assert evidence["mutation_timeout_calls"] == [
        "rm:lock", "rm:first_source", "rm:second_source", "rm:dropin", "install:dropin_dir",
        "chown:dropin_dir", "chmod:dropin_dir", "chown:run_dir", "chmod:run_dir"]
    assert evidence["service_calls"].splitlines() == [
        "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]
    assert not evidence["command_entered"] and evidence["recorded_fixture_processes"] == 0
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert evidence["rollback"]["restoration_verified"] is False


@unittest.skipIf(sys.platform != "linux", "Real GNU timeout process-group signals require Linux CI")
def test_gateway_hung_service_commands_and_ignored_term_are_bounded() -> None:
    for verb, mode in (("stop", "hang"), ("stop", "ignore_term"),
                       ("stop", "ignore_term_descendant"),
                       ("daemon-reload", "ignore_term"), ("reset-failed", "hang"), ("start", "ignore_term")):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="timed_service", service_failure=verb, real_timeout_mode=mode, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        assert evidence["command_entered"] and evidence["elapsed_seconds"] < 5
        assert evidence["live_fixture_processes_after_command"] == 0
        assert evidence["recorded_fixture_processes"] == (2 if mode == "ignore_term_descendant" else 1)
        assert completed.stderr.count("Rolling back the complete gateway") == 1
        commands = evidence["rollback"]["service_commands"]
        assert commands[-1]["verb"] == verb and commands[-1]["exit_code"] in {124, 137}
        assert commands[-1]["outcome"] in {"DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124", "FORCED_TERMINATION_OR_SIGKILL"}
        assert evidence["rollback"]["trigger_exit_code"] == 17
        assert evidence["backup"] == b"previous source\n"
        if verb == "stop":
            assert current == b"candidate source\n" and evidence["restore_calls"] == ""
        else:
            assert current == b"previous source\n"


def test_gateway_rollback_failure_keeps_original_code_without_reentry() -> None:
    guard = _gateway_post_mutation_guards(_repair_script())[0]
    completed, restored, dropin_exists = _run_gateway_rollback_guard(
        guard, predicate_passes=False, copy_fails=True
    )
    assert completed.returncode == 17, completed.stderr
    assert completed.stderr.count("Rolling back the complete gateway") == 1
    assert completed.stderr.count("FIXTURE_COPY_FAILURE") == 1
    assert completed.stdout.count("SYSTEMCTL:stop\n") == 1
    assert completed.stdout.count("SYSTEMCTL:start\n") == 0
    assert completed.stdout.endswith("CLEANUP\n")
    # A failed restore remains a real failure, never a claim of recovery success.
    assert restored is None
    assert dropin_exists


def test_gateway_term_during_rollback_preserves_recovery_and_original_code() -> None:
    guard = _gateway_post_mutation_guards(_repair_script())[0]
    completed, restored, dropin_exists = _run_gateway_rollback_guard(
        guard, predicate_passes=False, signal_during_copy=True
    )
    assert completed.returncode == 17, completed.stderr
    assert completed.stderr.count("Rolling back the complete gateway") == 1
    assert completed.stderr.count("FIXTURE_TERM_SENT") == 1
    assert completed.stdout.count("SYSTEMCTL:stop\n") == 1
    assert completed.stdout.count("SYSTEMCTL:start\n") == 1
    assert completed.stdout.endswith("CLEANUP\n")
    assert restored == b"previous source\n"
    assert not dropin_exists


def test_gateway_failed_restore_retains_private_backup_and_unverified_receipt() -> None:
    evidence: dict = {}
    completed, restored, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        copy_fails=True, recovery_case="failed_restore", evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert restored is None and evidence["backup_exists"]
    assert evidence["backup"] == b"previous source\n"
    assert evidence["rollback"]["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
    assert evidence["rollback"]["trigger_exit_code"] == 17
    assert evidence["rollback"]["restoration_verified"] is False
    assert evidence["rollback"]["manifest_sha256"] == evidence["prepared_sha256"]
    stored = next(item for item in evidence["prepared"]["files"] if item["path"] == "existing/entry.py")
    assert stored["sha256"] == hashlib.sha256(evidence["backup"]).hexdigest()
    assert "previous source" not in json.dumps(evidence["prepared"])
    assert "evidence retained" in completed.stdout
    if os.name == "posix":
        assert evidence["prepared_mode"] == evidence["rollback_mode"] == 0o600


def test_gateway_restoration_faults_stop_before_all_later_operations() -> None:
    cases = [
        ("rm:first_source", "source_remove", {}),
        ("cp:first_source", "source_copy", {}),
        ("rm:second_source", "source_remove", {"second_source": True}),
        ("cp:second_source", "source_copy", {"second_source": True}),
        ("rm:dropin", "dropin_remove", {}),
        ("install:dropin_dir", "dropin_parent_create", {"prior_dropin": True}),
        ("cp:dropin", "dropin_copy", {"prior_dropin": True}),
        ("chown:dropin_dir", "dropin_chown", {}),
        ("chmod:dropin_dir", "dropin_chmod", {}),
        ("chown:run_dir", "run_chown", {}),
        ("chmod:run_dir", "run_chmod", {}),
        ("rmdir:dropin_dir", "dropin_directory_remove", {"directory_case": "empty_dropin"}),
        ("rmdir:run_dir", "run_directory_remove", {"directory_case": "empty_run"}),
    ]
    for fault, operation, options in cases:
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="restoration_fault", restore_fault=fault, evidence=evidence, **options,
        )
        assert completed.returncode == 17, (fault, completed.stderr)
        assert completed.stderr.count("Rolling back the complete gateway") == 1
        assert evidence["operation_calls"].splitlines()[-1] == fault, (fault, evidence)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n", (fault, evidence)
        receipt = evidence["rollback"]
        assert receipt["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert receipt["failed_restoration_operation"]["operation"] == operation
        assert receipt["failed_restoration_operation"]["exit_code"] == 23
        assert receipt["trigger_exit_code"] == 17 and receipt["restoration_verified"] is False
        assert receipt["partial_state_possible"] is True and receipt["further_restoration_stopped"] is True
        assert receipt["service_restart_attempted"] is False
        assert evidence["backup"] == b"previous source\n"
        if fault == "rm:first_source":
            assert current == b"candidate source\n" and dropin_exists
        if fault == "cp:first_source":
            assert current is None and dropin_exists
        if "second_source" in fault:
            assert current == b"previous source\n" and dropin_exists
            assert evidence["second_backup"] == b"second previous\n"
            assert evidence["second_target"] == (b"second candidate\n" if fault.startswith("rm:") else None)


def test_gateway_lock_owner_probe_requires_explicit_esrch_and_bounded_pid() -> None:
    function = _bash_function(_repair_script(), "require_absent_lock_owner")
    with tempfile.TemporaryDirectory(prefix="gateway-lock-probe-test-") as directory:
        root = Path(directory)
        _write_lock_probe_runtime(root)
        harness = r'''
set -Eeuo pipefail
PYTHON_BIN=fixture_lock_python
fixture_lock_python() {
  if [[ "$LOCK_PROBE_CASE" == launcher_failure ]]; then return 29; fi
  "$TEST_PYTHON" "$PWD/lock-probe-runtime.py" "$@"
}
''' + function + '\nrequire_absent_lock_owner "$@"\n'
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        cases = [(mode, ["123"], rc, True) for mode, rc in (
            ("dead", 0), ("live", 14), ("permission", 14), ("invalid", 14),
            ("unknown", 14), ("unclassified_lookup", 14), ("overflow", 14),
            ("value", 14), ("unexpected", 1),
        )]
        cases += [("dead", [value], 14, False) for value in (
            "0", "-1", "+1", "01", "2147483648", "99999999999", "1 2", "", "١",
        )]
        cases += [("dead", [], 14, False), ("dead", ["123", "extra"], 14, False),
                  ("dead", ["2147483647"], 0, True), ("launcher_failure", ["123"], 29, False)]
        for mode, arguments, expected, probed in cases:
            calls = root / "lock-probe.calls"
            if calls.exists(): calls.unlink()
            completed = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh", *arguments],
                cwd=root, env=dict(os.environ, TEST_PYTHON=Path(sys.executable).as_posix(), LOCK_PROBE_CASE=mode),
                capture_output=True, text=True, timeout=10, check=False)
            assert completed.returncode == expected, (mode, arguments, completed.stderr)
            assert calls.exists() == probed, (mode, arguments)
            if probed: assert calls.read_text() == f"{arguments[0]}:0\n"
        # Native Windows/MSYS argv transport strips the trailing newline in
        # this otherwise-invalid direct input. Exercise the actual Python body
        # without that shell transport; original file grammar is tested separately.
        if calls.exists(): calls.unlink()
        body = function.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        completed = subprocess.run([sys.executable, "lock-probe-runtime.py", "-", "1\n"],
            input=body, cwd=root, env=dict(os.environ, LOCK_PROBE_CASE="dead"),
            capture_output=True, text=True, timeout=10, check=False)
        assert completed.returncode == 14 and not calls.exists(), completed.stderr


def test_gateway_lock_probe_refusal_stops_actual_rollback_before_restoration() -> None:
    for mode, expected in (("permission", 14), ("unknown", 14), ("invalid_range", 14),
                           ("unclassified_lookup", 14), ("launcher_failure", 29)):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="lock_probe_refusal", real_lock_case=mode, evidence=evidence)
        assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["operation_calls"] == ""
        assert evidence["lock_exists"] and evidence["backup"] == b"previous source\n"
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"] == dict(operation="dead_lock", target="gateway_lock", exit_code=expected)
        assert receipt["trigger_exit_code"] == 17 and receipt["service_restart_attempted"] is False
        assert receipt["restoration_verified"] is False and receipt["further_restoration_stopped"] is True
        assert "Removed verified dead-PID" not in completed.stdout


def test_gateway_lock_file_malformed_bytes_stop_actual_rollback_and_preserve_trigger() -> None:
    for raw, case in ((b"1 2", "lock_grammar"), (b"12\x00", "lock_grammar"),
                      (b"12\n\n", "rollback_write_failure")):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case=case, real_lock_case="dead", lock_file_bytes=raw, evidence=evidence)
        assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["operation_calls"] == ""
        assert evidence["lock_exists"] and evidence["lock_probe_calls"] == ""
        assert evidence["backup"] == b"previous source\n" and "Removed verified dead-PID" not in completed.stdout
        if case == "rollback_write_failure":
            assert "private rollback receipt persistence failed" in completed.stderr
        else:
            receipt = evidence["rollback"]
            assert receipt["failed_restoration_operation"] == dict(operation="dead_lock", target="gateway_lock", exit_code=14)
            assert receipt["trigger_exit_code"] == 17 and receipt["service_restart_attempted"] is False
            assert receipt["restoration_verified"] is False and receipt["further_restoration_stopped"] is True


def test_gateway_lock_probe_refusal_preserves_trigger_when_receipt_write_fails() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure", real_lock_case="permission", evidence=evidence)
    assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["operation_calls"] == ""
    assert evidence["lock_exists"] and evidence["backup"] == b"previous source\n"
    assert "private rollback receipt persistence failed" in completed.stderr
    assert "Removed verified dead-PID" not in completed.stdout


def test_gateway_inner_lock_errors_cannot_be_hidden_by_successful_echo() -> None:
    for lock_case, fault, expected_code in (
        ("dead", "rm:lock", 23), ("reader_failure", "", 27), ("invalid", "", 14), ("live", "", 14),
    ):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="inner_lock_failure", real_lock_case=lock_case, restore_fault=fault, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["operation_calls"] == ("rm:lock\n" if fault else "")
        assert "Removed verified dead-PID" not in completed.stdout
        assert evidence["lock_exists"]
        expected_failure = dict(operation="dead_lock", target="gateway_lock", exit_code=expected_code)
        if fault:
            expected_failure.update(outcome="COMMAND_FAILED", timeout_seconds=60,
                                    kill_after_seconds=5, mutation_effect_verified=False)
        assert evidence["rollback"]["failed_restoration_operation"] == expected_failure


def test_gateway_valid_or_absent_lock_and_prior_dropin_restore_normally() -> None:
    for lock_case in ("dead", "absent"):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="valid_lock", real_lock_case=lock_case, prior_dropin=True, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n" and dropin_exists
        assert evidence["dropin_bytes"] == b"previous hardening\n"
        assert not evidence["lock_exists"]
        assert evidence["service_calls"].splitlines() == [
            "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]
        assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
        assert "failed_restoration_operation" not in evidence["rollback"]


def test_gateway_lock_presence_only_explicit_enoent_means_absent() -> None:
    for kind, expected in (("missing", "ABSENT"), ("regular", "PRESENT"), ("directory", "PRESENT")):
        result = _run_gateway_lock_file_case(b"12", "presence", file_kind=kind)
        assert result["completed"].returncode == 0 and result["completed"].stdout == expected, result
        assert result["lock-probe"] == result["remove"] == ""
    explicit = _run_gateway_lock_file_case(b"", "presence", file_kind="missing", presence_case="initial:enoent")
    assert explicit["completed"].returncode == 0 and explicit["completed"].stdout == "ABSENT"
    extra = _run_gateway_lock_file_case(b"12", "presence", extra_argument=True)
    assert extra["completed"].returncode == 14 and extra["lock-presence"] == ""


def test_gateway_lock_presence_errors_and_malformed_output_refuse_at_both_observations() -> None:
    for stage in ("initial", "after"):
        for case in ("permission", "eperm", "not_directory", "unknown", "unclassified_lookup",
                     "empty", "wrong", "trailing_lf", "print_then_failure", "interpreter_failure"):
            # An actually missing path must not hide an initial observation error.
            result = _run_gateway_lock_file_case(b"12", "cleanup",
                file_kind="missing" if stage == "initial" else "regular",
                presence_case=stage + ":" + case)
            expected = 29 if case in {"print_then_failure", "interpreter_failure"} else 14
            assert result["completed"].returncode == expected, (stage, case, result)
            assert "Removed verified dead-PID" not in result["completed"].stdout
            assert result["remove"] == ("remove\n" if stage == "after" else "")
            assert result["lock-probe"] == ("12:0\n" if stage == "after" else "")


def _assert_gateway_lock_presence_rollback_refuses(*, remove_case: str = "", presence_case: str = "",
                                                  absent_before: bool = False, receipt_failure: bool = False) -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "lock_presence_result",
        real_lock_case="absent" if absent_before else "dead", lock_remove_case=remove_case,
        lock_presence_case=presence_case, evidence=evidence)
    assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists, completed.stderr
    assert evidence["backup"] == b"previous source\n" and evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert evidence["operation_calls"] == ("" if presence_case.startswith("initial:") else "rm:lock\n")
    assert "Removed verified dead-PID" not in completed.stdout
    if remove_case:
        assert evidence["lock_exists"], evidence
    if receipt_failure:
        assert "private rollback receipt persistence failed" in completed.stderr
    else:
        receipt = evidence["rollback"]
        operation_rc = 29 if presence_case.endswith((":print_then_failure", ":interpreter_failure")) else 14
        assert receipt["failed_restoration_operation"] == dict(operation="dead_lock", target="gateway_lock", exit_code=operation_rc)
        assert receipt["trigger_exit_code"] == 17 and receipt["further_restoration_stopped"] is True
        assert receipt["restoration_verified"] is False and receipt["service_restart_attempted"] is False


def test_gateway_lock_presence_noop_or_reappearance_stops_all_later_restoration() -> None:
    for case in ("noop", "regular", "directory"):
        _assert_gateway_lock_presence_rollback_refuses(remove_case=case)


def test_gateway_lock_presence_observation_and_receipt_failures_keep_original_trigger() -> None:
    _assert_gateway_lock_presence_rollback_refuses(presence_case="initial:permission", absent_before=True)
    _assert_gateway_lock_presence_rollback_refuses(presence_case="after:unknown")
    _assert_gateway_lock_presence_rollback_refuses(presence_case="after:print_then_failure")
    _assert_gateway_lock_presence_rollback_refuses(remove_case="noop", receipt_failure=True)


@unittest.skipIf(os.name != "posix", "Actual lock presence symlinks require Linux CI")
def test_gateway_lock_presence_symlink_is_present_and_reappearance_refuses() -> None:
    for kind in ("symlink", "dangling"):
        result = _run_gateway_lock_file_case(b"12", "presence", file_kind=kind)
        assert result["completed"].returncode == 0 and result["completed"].stdout == "PRESENT", result
        assert result["lock-probe"] == result["remove"] == ""
    _assert_gateway_lock_presence_rollback_refuses(remove_case="symlink")


@unittest.skipIf(os.name != "posix", "Real dangling lock symlink refusal requires Linux CI")
def test_gateway_dangling_lock_link_cannot_be_mistaken_for_absence() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="linked_lock", real_lock_case="symlink", evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"candidate source\n"
    assert evidence["operation_calls"] == "" and evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert evidence["rollback"]["failed_restoration_operation"]["exit_code"] == 14


def test_gateway_missing_before_directories_preserve_nonempty_and_allow_absence() -> None:
    for family in ("dropin", "run"):
        for case in ("nonempty", "empty", "absent"):
            evidence: dict = {}
            completed, current, _ = _run_gateway_rollback_guard(
                _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
                recovery_case="directory_restore", directory_case=case + "_" + family, evidence=evidence,
            )
            assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
            if case == "nonempty":
                assert evidence["retained_unrelated_files"] == [b"preserve unrelated bytes\n"]
                assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
                assert evidence["operation_calls"].splitlines()[-1] == "rmdir:" + ("dropin_dir" if family == "dropin" else "run_dir")
                assert evidence["rollback"]["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
            else:
                assert not evidence["dropin_directory_exists" if family == "dropin" else "run_directory_exists"]
                assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
                assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"


def test_gateway_malformed_metadata_stops_restoration_without_starting_service() -> None:
    for filename, operation in (("service-drop-in-dir.metadata", "dropin_metadata_read"),
                                ("run-dir.metadata", "run_metadata_read")):
        for malformed in ("1000 bad 755", "1000 1000 999", "1000 1000 755 extra", "1000 1000 755\n0 0 700"):
            evidence: dict = {}
            completed, current, _ = _run_gateway_rollback_guard(
                _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
                recovery_case="bad_metadata", metadata_case=filename + ":" + malformed, evidence=evidence,
            )
            assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
            assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
            assert evidence["rollback"]["failed_restoration_operation"]["operation"] == operation
            assert evidence["rollback"]["failed_restoration_operation"]["exit_code"] == 14
            expected = ["rm:first_source", "cp:first_source", "rm:dropin"]
            if operation == "run_metadata_read":
                expected += ["chown:dropin_dir", "chmod:dropin_dir"]
            assert evidence["operation_calls"].splitlines() == expected


def test_gateway_missing_required_reads_stop_and_do_not_weaken_receipt_validation() -> None:
    for filename in (
        "service-drop-in.state", "service-drop-in-dir.state", "run-dir.state",
        "service-drop-in-dir.metadata", "run-dir.metadata",
    ):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="missing_after_verification", metadata_case="missing:" + filename, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        # Repeated full inventory validation now detects this even earlier,
        # before the first source target is removed.
        assert "restoration operation source_state failed" in completed.stderr
        assert "receipt persistence failed" in completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert "rollback" not in evidence and evidence["backup"] == b"previous source\n"
        assert evidence["operation_calls"] == ""


def _assert_source_drift_stops_before_next_mutation(kind: str, boundary: str) -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing" if kind == "unexpected" else "source_drift",
        source_drift=kind, drift_boundary=boundary,
        second_source=boundary == "after_first_copy" and kind != "unexpected", evidence=evidence,
    )
    assert completed.returncode == 17, (kind, boundary, completed.stderr)
    assert evidence["source_drift_applied"] and evidence["backup_exists"]
    assert "RECOVERY_EVIDENCE_VERIFIED_BEFORE_RESTORATION" in completed.stdout
    expected_operation = "source_result" if boundary == "after_first_copy" else "source_state"
    assert f"restoration operation {expected_operation} failed" in completed.stderr
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and dropin_exists
    assert not evidence["source_state_receipt_exists"]
    # Corrupt evidence still prevents an ordinary receipt: do not weaken its
    # inventory/hash checks to report an apparent recovery success.
    assert "receipt persistence failed" in completed.stderr and "rollback" not in evidence
    expected = [] if boundary == "stop" else ["rm:first_source"]
    if boundary == "after_first_copy":
        expected.append("cp:first_source")
    assert evidence["operation_calls"].splitlines() == expected
    assert current == (b"candidate source\n" if boundary == "stop" else
                       b"previous source\n" if boundary == "after_first_copy" else None)
    if boundary == "after_first_copy" and kind != "unexpected":
        assert evidence["second_target"] == b"second candidate\n"
    if kind == "unexpected":
        assert evidence["prepared"]["missing_source_files"] == ["absent.py"]
        assert evidence["originally_missing_target_bytes"] == b"candidate"


def test_gateway_source_drift_after_stop_cannot_change_restoration_intent() -> None:
    for kind in ("missing", "changed", "directory", "mtime", "unexpected"):
        _assert_source_drift_stops_before_next_mutation(kind, "stop")


def test_gateway_source_drift_after_earlier_restore_stops_remaining_sources() -> None:
    for kind in ("missing", "changed", "directory", "mtime", "unexpected"):
        _assert_source_drift_stops_before_next_mutation(kind, "after_first_copy")


def test_gateway_source_drift_after_remove_stops_copy_with_partial_state() -> None:
    for kind in ("missing", "changed", "directory", "mtime"):
        _assert_source_drift_stops_before_next_mutation(kind, "after_first_remove")


@unittest.skipIf(os.name != "posix", "Real source links and extended metadata require Linux CI")
def test_gateway_source_link_and_metadata_drift_cannot_reach_next_mutation() -> None:
    for boundary in ("stop", "after_first_copy"):
        for kind in ("symlink", "hardlink", "mode", "xattr"):
            _assert_source_drift_stops_before_next_mutation(kind, boundary)


def test_gateway_source_query_failure_or_malformed_output_stops_restore() -> None:
    for case, expected_code in (("failed", 29), ("extra_line", 14), ("extra_newline", 14),
                                ("carriage_return", 14), ("empty", 14), ("no_newline", 14), ("invalid", 14),
                                ("outside", 1), ("unregistered", 1), ("empty_path", 1), ("extra_argument", 14)):
        evidence: dict = {}
        completed, current, dropin_exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="source_query", source_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"candidate source\n" and dropin_exists, case
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["operation_calls"] == ""
        assert evidence["backup"] == b"previous source\n" and not evidence["source_state_receipt_exists"]
        receipt = evidence["rollback"]
        assert receipt["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert receipt["trigger_exit_code"] == 17 and receipt["service_restart_attempted"] is False
        assert receipt["failed_restoration_operation"] == dict(
            operation="source_state", target="entry.py", exit_code=expected_code)


def test_gateway_source_query_cannot_change_present_intent_before_copy() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="source_query", source_query_case="second_missing", evidence=evidence,
    )
    assert completed.returncode == 17 and current is None and dropin_exists
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert evidence["operation_calls"] == "rm:first_source\n"
    assert evidence["backup"] == b"previous source\n"
    assert evidence["rollback"]["failed_restoration_operation"] == dict(
        operation="source_state", target="entry.py", exit_code=14)
    assert evidence["rollback"]["partial_state_possible"] is True


def test_gateway_source_state_query_valid_states_are_read_only() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n" and not dropin_exists
    assert not evidence["originally_missing_target_exists"] and not evidence["source_state_receipt_exists"]
    assert evidence["rollback"]["manifest_sha256"] == evidence["prepared_sha256"]
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert evidence["service_calls"].splitlines() == [
        "SYSTEMCTL:stop", "SYSTEMCTL:daemon-reload", "SYSTEMCTL:reset-failed", "SYSTEMCTL:start"]


def _assert_target_drift_preserved(kind: str, boundary: str = "stop", *, receipt_failure: bool = False) -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "target_guard",
        target_drift=kind, target_boundary=boundary, second_source=True, evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert evidence["target_drift_applied"] and evidence["backup"] == b"previous source\n"
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    if boundary == "after_first_copy":
        assert current == b"previous source\n"
        assert "rm:first_source" in evidence["operation_calls"] and "cp:first_source" in evidence["operation_calls"]
        assert "rm:second_source" not in evidence["operation_calls"]
        if kind == "changed": assert evidence["second_target"] == b"intervening target bytes\n"
        failed_target = "second.py"
    else:
        assert "cp:first_source" not in evidence["operation_calls"]
        if boundary == "stop": assert "rm:first_source" not in evidence["operation_calls"]
        if kind in {"changed", "reappeared"}: assert current == b"intervening target bytes\n"
        if kind == "missing": assert current is None
        if kind == "directory": assert evidence["target_is_directory"]
        if kind == "symlink": assert evidence["target_is_symlink"]
        failed_target = "entry.py"
    if receipt_failure:
        assert evidence["rollback"] is None and "receipt persistence failed" in completed.stderr
    else:
        receipt = evidence["rollback"]
        failure = receipt["failed_restoration_operation"]
        assert failure["operation"] == ("target_absent" if boundary == "after_first_remove" else "target_state")
        assert failure["target"] == failed_target and failure["exit_code"] != 0
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"] is True
        assert receipt["service_restart_attempted"] is False and receipt["restoration_verified"] is False
        assert all(item["state"] == "INSTALLED" for item in receipt["source_write_states"])


def test_gateway_target_byte_identity_and_metadata_drift_stops_before_remove() -> None:
    for kind in ("changed", "missing", "identity", "directory", "mtime"):
        _assert_target_drift_preserved(kind)


def test_gateway_target_change_after_prior_restore_or_removal_is_preserved() -> None:
    _assert_target_drift_preserved("changed", "after_first_copy")
    _assert_target_drift_preserved("reappeared", "after_first_remove")


@unittest.skipIf(os.name != "posix", "Target link, mode and xattr identity requires POSIX")
def test_gateway_target_links_parent_substitution_and_xattrs_are_refused() -> None:
    for kind in ("symlink", "hardlink", "parent_link", "mode", "xattr"):
        _assert_target_drift_preserved(kind)


def test_gateway_actual_forward_install_captures_versions_and_valid_missing_intent() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
    assert len(evidence["forward_calls"]) == 2 and not evidence["originally_missing_target_exists"]
    receipt = evidence["rollback"]
    assert receipt["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    for item in receipt["source_write_states"]:
        assert item["state"] == "INSTALLED"
        assert re.fullmatch(r"[a-f0-9]{64}", item["candidate_sha256"])
        assert re.fullmatch(r"[a-f0-9]{64}", item["installed_version_sha256"])


def test_gateway_valid_sibling_installs_and_restoration_do_not_invalidate_parent_identity() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="target_guard", second_source=True, evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
    assert evidence["second_target"] == b"second previous\n" and len(evidence["forward_calls"]) == 2
    assert evidence["service_calls"].splitlines() == ["SYSTEMCTL:" + item for item in ("stop", "daemon-reload", "reset-failed", "start")]
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"


def test_gateway_changed_originally_missing_target_is_not_deleted() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", target_drift="changed", target_relative="absent.py", evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
    assert evidence["originally_missing_target_bytes"] == b"intervening target bytes\n"
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert evidence["rollback"]["failed_restoration_operation"]["target"] == "absent.py"


def test_gateway_candidate_hash_is_pinned_from_approved_manifest_before_runtime_mutation() -> None:
    script = _repair_script()
    pin = 'SOURCE_CANDIDATE_SHA[$rel]="$(awk -v relative="$rel" \'$2 == relative { print $1 }\' "$MANIFEST_FILE")"'
    compare = '[[ "$(sha256sum "$staged" | awk \'{print $1}\')" == "${SOURCE_CANDIDATE_SHA[$rel]}" ]]'
    assert script.index(pin) < script.index(compare) < script.index('systemctl stop "$SERVICE"\nSERVICE_STOPPED=true')
    assert script.index(compare) < script.index('RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"')
    install = _bash_function(script, "install_gateway_source")
    assert install.index('SOURCE_WRITE_STATES[$relative]=WRITE_PENDING') < install.index('install -D')
    assert install.index('capture_source_target_version') < install.index('SOURCE_WRITE_STATES[$relative]=INSTALLED')


def test_gateway_untouched_source_targets_are_not_restored_or_deleted() -> None:
    for case in ("untouched", "untouched_missing"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="valid_missing", forward_case=case, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        assert current == (b"candidate source\n" if case == "untouched" else b"previous source\n")
        assert evidence["originally_missing_target_bytes"] == b"candidate"
        states = {item["path"]: item for item in evidence["rollback"]["source_write_states"]}
        assert states["absent.py"]["state"] == "UNTOUCHED" and states["absent.py"]["installed_version_sha256"] is None
        assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
        if case == "untouched":
            assert evidence["forward_calls"] == [] and "rm:first_source" not in evidence["operation_calls"]


def test_gateway_partial_forward_install_or_readback_cannot_authorize_restoration() -> None:
    for case in ("partial_first", "partial_second", "readback_mismatch", "stage_changed"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            "printf 'UNREACHED_FORWARD_FAILURE\\n'", predicate_passes=False,
            recovery_case="target_guard", forward_case=case, second_source=True, evidence=evidence,
        )
        expected_code = 1 if case in {"readback_mismatch", "stage_changed"} else 31
        assert completed.returncode == expected_code, completed.stderr
        assert "UNREACHED_FORWARD_FAILURE" not in completed.stdout
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        failure = evidence["rollback"]["failed_restoration_operation"]
        assert failure["operation"] == "target_state" and failure["exit_code"] == 14
        states = {item["path"]: item["state"] for item in evidence["rollback"]["source_write_states"]}
        if case == "partial_second":
            assert current == b"previous source\n" and evidence["second_target"] == b"partial candidate\n"
            assert states == {"entry.py": "INSTALLED", "second.py": "WRITE_PENDING"}
            assert "rm:second_source" not in evidence["operation_calls"]
        else:
            expected = {"readback_mismatch": b"unexpected candidate\n", "stage_changed": b"changed staged candidate\n"}
            assert current == expected.get(case, b"partial candidate\n")
            assert states == {"entry.py": "WRITE_PENDING", "second.py": "UNTOUCHED"}
            assert "rm:first_source" not in evidence["operation_calls"]


def test_gateway_unknown_state_or_malformed_version_query_stops_recovery() -> None:
    for case in ("missing_state", "unknown_state", "invalid_state", "missing_version", "invalid_version", "missing_candidate"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="target_guard", forward_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"candidate source\n", completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and "rm:first_source" not in evidence["operation_calls"]
        assert "restoration operation target_state failed" in completed.stderr
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty", "invalid", "outside", "unregistered"):
        evidence = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="target_guard", target_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"candidate source\n", completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and "rm:first_source" not in evidence["operation_calls"]
        failure = evidence["rollback"]["failed_restoration_operation"]
        assert failure["operation"] == "target_state" and failure["exit_code"] != 0


def test_gateway_target_conflict_receipt_failure_preserves_trigger_and_files() -> None:
    _assert_target_drift_preserved("changed", receipt_failure=True)


def _assert_source_result_fault_stops(fault: str, *, relative: str = "entry.py", receipt_failure: bool = False) -> dict:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "valid_missing" if relative == "absent.py" else "source_result",
        result_fault=fault, result_relative=relative, second_source=relative != "absent.py", evidence=evidence,
    )
    assert completed.returncode == 17, (fault, completed.stderr)
    assert evidence["result_fault_applied"] and evidence["backup_exists"]
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert "restoration operation source_result failed" in completed.stderr
    assert not evidence["source_result_receipt_exists"]
    if relative == "entry.py":
        assert "rm:second_source" not in evidence["operation_calls"]
        if fault == "copy_noop": assert current is None
        if fault == "copy_bytes": assert current == b"wrong restoration bytes\n"
        if fault == "copy_directory": assert evidence["target_is_directory"]
    elif relative == "second.py":
        assert current == b"previous source\n"
        assert evidence["second_target"] is None if fault == "copy_noop" else evidence["second_target"] == b"wrong restoration bytes\n"
    elif fault == "remove_noop":
        assert evidence["originally_missing_target_bytes"] == b"candidate"
    elif fault == "remove_symlink":
        assert evidence["originally_missing_target_is_symlink"]
    if receipt_failure:
        assert evidence["rollback"] is None and "receipt persistence failed" in completed.stderr
    else:
        receipt = evidence["rollback"]
        failure = receipt["failed_restoration_operation"]
        assert failure["operation"] == "source_result" and failure["target"] == relative and failure["exit_code"] != 0
        assert receipt["trigger_exit_code"] == 17 and receipt["restoration_verified"] is False
        assert receipt["partial_state_possible"] and not receipt["service_restart_attempted"]
        rows = {item["path"]: item["restoration_result_observation"] for item in receipt["source_write_states"]}
        assert rows[relative] == "FAILED"
        if relative != "entry.py": assert rows["entry.py"] == "MATCHED_PREPARED_PRESENT"
        else: assert rows["second.py"] == "NOT_CHECKED"
    return evidence


def test_gateway_copy_success_requires_source_result_bytes_type_and_metadata() -> None:
    for fault in ("copy_noop", "copy_bytes", "copy_mtime", "copy_directory"):
        _assert_source_result_fault_stops(fault)


def test_gateway_later_source_result_failure_preserves_prior_partial_observation() -> None:
    _assert_source_result_fault_stops("copy_noop", relative="second.py")
    _assert_source_result_fault_stops("copy_bytes", relative="second.py")


def test_gateway_missing_source_result_requires_actual_absence_after_remove_success() -> None:
    _assert_source_result_fault_stops("remove_noop", relative="absent.py")


@unittest.skipIf(os.name != "posix", "Restored source links, mode and xattrs require POSIX")
def test_gateway_source_result_links_metadata_and_parent_substitution_are_refused() -> None:
    for fault in ("copy_symlink", "copy_hardlink", "copy_parent_link", "copy_mode", "copy_xattr"):
        _assert_source_result_fault_stops(fault)
    _assert_source_result_fault_stops("remove_symlink", relative="absent.py")


def test_gateway_source_result_query_failure_or_malformed_output_stops_restart() -> None:
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty", "contradictory", "invalid",
                 "outside", "unregistered", "empty_path", "extra_argument"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="source_result", result_query_case=case, second_source=True, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n", (case, completed.stderr)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["operation_calls"] == "rm:first_source\ncp:first_source\n"
        assert evidence["second_target"] == b"second candidate\n" and not evidence["source_result_receipt_exists"]
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"]["operation"] == "source_result"
        assert receipt["failed_restoration_operation"]["exit_code"] == (29 if case == "failed" else 1 if case in {"outside", "unregistered", "empty_path"} else 14)
        assert receipt["source_write_states"][0]["restoration_result_observation"] == "FAILED"
        assert receipt["partial_state_possible"] and receipt["restoration_verified"] is False


def test_gateway_valid_source_results_compare_preserved_metadata_not_copied_identity() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", second_source=True, evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
    assert evidence["target_inode"] != evidence["backup_inode"]
    assert evidence["second_target"] == b"second previous\n" and not evidence["originally_missing_target_exists"]
    assert evidence["service_calls"].endswith("SYSTEMCTL:start\n") and not evidence["source_result_receipt_exists"]
    receipt = evidence["rollback"]
    assert {item["path"]: item["restoration_result_observation"] for item in receipt["source_write_states"]} == {
        "entry.py": "MATCHED_PREPARED_PRESENT", "second.py": "MATCHED_PREPARED_PRESENT", "absent.py": "MATCHED_PREPARED_ABSENCE"}
    assert receipt["restoration_verified"] is False and receipt["service_state_verified"] is False
    assert receipt["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"


def test_gateway_untouched_sources_do_not_claim_observed_restoration_results() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", forward_case="untouched", result_query_case="failed", evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"candidate source\n", completed.stderr
    assert evidence["originally_missing_target_bytes"] == b"candidate"
    assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
    assert all(item["restoration_result_observation"] == "UNCHECKED_UNTOUCHED" for item in evidence["rollback"]["source_write_states"])
    assert evidence["rollback"]["restoration_verified"] is False


def test_gateway_source_result_checks_preserve_receipt_and_prepared_evidence_failures() -> None:
    _assert_source_result_fault_stops("copy_noop", receipt_failure=True)
    for fault in ("manifest_changed", "backup_changed"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="source_result", result_fault=fault, second_source=True, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert "source_result failed" in completed.stderr and "receipt persistence failed" in completed.stderr
        assert "rollback" not in evidence and evidence["backup_exists"]
        assert "rm:second_source" not in evidence["operation_calls"]


def _assert_dropin_result_fault_stops(fault: str, *, present: bool = True, receipt_failure: bool = False) -> dict:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "dropin_result",
        prior_dropin=present, dropin_fault=fault, evidence=evidence,
    )
    assert completed.returncode == 17 and current == b"previous source\n", (fault, completed.stderr)
    assert evidence["dropin_fault_applied"] and evidence["backup_exists"]
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert "restoration operation dropin_result failed" in completed.stderr
    assert not evidence["dropin_result_receipt_exists"]
    expected = ["rm:first_source", "cp:first_source", "rm:dropin"]
    if present: expected += ["install:dropin_dir", "cp:dropin"]
    assert evidence["operation_calls"].splitlines() == expected
    if fault == "copy_noop": assert evidence["dropin_bytes"] is None
    if fault == "copy_bytes": assert evidence["dropin_bytes"] == b"wrong drop-in result\n"
    if fault == "remove_noop": assert evidence["dropin_bytes"] == b"candidate hardening\n"
    if fault == "remove_symlink": assert evidence["dropin_is_symlink"]
    if receipt_failure:
        assert evidence["rollback"] is None and "receipt persistence failed" in completed.stderr
    else:
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"]["operation"] == "dropin_result"
        assert receipt["failed_restoration_operation"]["target"] == "service_drop_in"
        assert receipt["failed_restoration_operation"]["exit_code"] != 0
        assert receipt["dropin_result_observation"] == "FAILED"
        assert receipt["source_write_states"][0]["restoration_result_observation"] == "MATCHED_PREPARED_PRESENT"
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert receipt["restoration_verified"] is False and receipt["service_state_verified"] is False
        assert not receipt["service_restart_attempted"]
    return evidence


def test_gateway_dropin_result_detects_copy_success_with_incorrect_file() -> None:
    for fault in ("copy_noop", "copy_bytes", "copy_mtime", "copy_directory"):
        _assert_dropin_result_fault_stops(fault)


def test_gateway_dropin_result_requires_actual_missing_before_absence() -> None:
    for fault in ("remove_noop", "remove_parent_file"):
        _assert_dropin_result_fault_stops(fault, present=False)


@unittest.skipIf(os.name != "posix", "Drop-in result links, mode, parent permissions and xattrs require POSIX")
def test_gateway_dropin_result_rejects_links_metadata_and_unsafe_parents() -> None:
    for fault in ("copy_symlink", "copy_hardlink", "copy_mode", "copy_xattr", "copy_parent_link", "copy_parent_mode"):
        _assert_dropin_result_fault_stops(fault)
    for fault in ("remove_symlink", "remove_parent_link"):
        _assert_dropin_result_fault_stops(fault, present=False)


def test_gateway_dropin_result_query_failures_and_malformed_output_stop_recovery() -> None:
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty",
                 "contradictory", "invalid", "source_argument", "empty_argument", "extra_arguments"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_result", prior_dropin=True, dropin_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n", (case, completed.stderr)
        assert evidence["dropin_bytes"] == b"previous hardening\n"
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and not evidence["dropin_result_receipt_exists"]
        assert evidence["operation_calls"].splitlines() == ["rm:first_source", "cp:first_source", "rm:dropin", "install:dropin_dir", "cp:dropin"]
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"] == dict(operation="dropin_result", target="service_drop_in", exit_code=29 if case == "failed" else 14)
        assert receipt["dropin_result_observation"] == "FAILED" and receipt["partial_state_possible"]
        assert receipt["restoration_verified"] is False and not receipt["service_restart_attempted"]


def test_gateway_dropin_result_accepts_valid_copy_and_absence_with_or_without_parent() -> None:
    for present, directory_case in ((True, ""), (False, ""), (False, "empty_dropin"), (False, "absent_dropin")):
        evidence: dict = {}
        completed, current, exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_result", prior_dropin=present, directory_case=directory_case, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
        assert exists is present and evidence["dropin_bytes"] == (b"previous hardening\n" if present else None)
        if present: assert evidence["dropin_inode"] != evidence["dropin_backup_inode"]
        receipt = evidence["rollback"]
        assert receipt["dropin_result_observation"] == ("MATCHED_PREPARED_PRESENT" if present else "MATCHED_PREPARED_ABSENCE")
        assert receipt["restoration_verified"] is False and receipt["service_state_verified"] is False
        assert receipt["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
        assert evidence["service_calls"].endswith("SYSTEMCTL:start\n") and not evidence["dropin_result_receipt_exists"]


def test_gateway_dropin_result_keeps_custody_and_receipt_failure_visible() -> None:
    _assert_dropin_result_fault_stops("copy_noop", receipt_failure=True)
    for fault in ("manifest_changed", "backup_changed", "state_changed"):
        evidence: dict = {}
        completed, current, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_result", prior_dropin=True, dropin_fault=fault, evidence=evidence,
        )
        assert completed.returncode == 17 and current == b"previous source\n", completed.stderr
        assert evidence["dropin_bytes"] == b"previous hardening\n" and evidence["backup_exists"]
        assert "dropin_result failed" in completed.stderr and "receipt persistence failed" in completed.stderr
        assert "rollback" not in evidence and evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["operation_calls"].splitlines()[-1] == "cp:dropin"


def test_gateway_state_parser_rejects_missing_or_noncanonical_values() -> None:
    function = _bash_function(_repair_script(), "read_recovery_state")
    with tempfile.TemporaryDirectory(prefix="gateway-state-read-") as directory:
        root = Path(directory)
        (root / "fixture.sh").write_text('set -Eeuo pipefail\n' + function + '\nread_recovery_state "$1"\nprintf READ_OK\n', newline="\n")
        for value, expected in (("present\n", 0), ("missing\n", 0), ("unexpected\n", 14),
                                ("present\nmissing\n", 14), ("\n", 14), (None, 1)):
            state = root / "state"
            if value is None:
                state.unlink()
            else:
                state.write_text(value, newline="\n")
            completed = subprocess.run([_gateway_rollback_test_bash(), "fixture.sh", "state"], cwd=root,
                                       capture_output=True, text=True, timeout=10, check=False)
            assert completed.returncode == expected, completed.stderr
            assert completed.stdout == ("READ_OK" if expected == 0 else "")


def test_gateway_restoration_receipt_failure_and_second_signal_keep_trigger_code() -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure", copy_fails=True, signal_during_copy=True, evidence=evidence,
    )
    assert completed.returncode == 17 and current is None and dropin_exists
    assert completed.stderr.count("Rolling back the complete gateway") == 1
    assert "FIXTURE_TERM_SENT" in completed.stderr and "receipt persistence failed" in completed.stderr
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup"] == b"previous source\n"
    assert evidence["rollback"] is None


def test_gateway_later_gate_failure_cannot_remove_recovery_evidence() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=True,
        recovery_case="later_gate_failure", evidence=evidence,
    )
    assert completed.returncode == 41, completed.stderr
    assert current == b"candidate source\n" and evidence["backup_exists"]
    assert evidence["backup"] == b"previous source\n"
    assert evidence["helper"]["status"] == "HELPER_CHECKS_PASSED_EXTERNAL_VERIFICATION_PENDING"
    assert evidence["helper"]["external_verification"] == "NOT_RECORDED_BY_HELPER"
    assert evidence["helper"]["restoration_verified"] is False
    assert evidence["helper"]["manifest_sha256"] == evidence["prepared_sha256"]
    assert evidence["service_calls"] == ""
    workflow = (ROOT / ".github/workflows/repair-gateway-dependency-closure.yml").read_text()
    assert "/var/backups/lumencore-gateway-repair" not in workflow


def test_gateway_manifest_write_failure_prevents_runtime_changes() -> None:
    evidence: dict = {}
    completed, current, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=True,
        recovery_case="prepared_write_failure", evidence=evidence,
    )
    assert completed.returncode != 0
    assert "FileExistsError" in completed.stderr
    assert evidence["prepared"] is None
    assert current == b"candidate source\n"
    assert evidence["backup"] == b"previous source\n" and evidence["backup_exists"]
    assert evidence["service_calls"] == "" and "helper" not in evidence
    script = _repair_script()
    assert script.index('RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"') < script.index(
        'systemctl stop "$SERVICE"\nSERVICE_STOPPED=true'
    )


def test_gateway_after_change_receipt_failures_preserve_non_success_and_backups() -> None:
    for kind, expected_code in (("helper_write_failure", 23), ("rollback_write_failure", 17)):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0],
            predicate_passes=kind == "helper_write_failure", recovery_case=kind,
            evidence=evidence,
        )
        assert completed.returncode == expected_code, completed.stderr
        assert evidence["backup_exists"] and evidence["backup"] == b"previous source\n"
        assert "receipt persistence failed" in completed.stderr
        assert completed.stderr.count("Rolling back the complete gateway") == 1


def test_gateway_changed_recovery_evidence_cannot_publish_helper_success() -> None:
    for kind, error in (("manifest_changed", "recovery_manifest_hash_mismatch"),
                        ("backup_changed", "recovery_backup_changed")):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=True,
            recovery_case=kind, evidence=evidence,
        )
        assert completed.returncode == 23, completed.stderr
        assert error in completed.stderr
        assert "helper" not in evidence and "rollback" not in evidence
        assert evidence["backup_exists"]
        assert "Rolling back the complete gateway" not in completed.stderr
        assert evidence["service_calls"] == evidence["restore_calls"] == ""
        assert evidence["rollback_refused"]["status"] == "ROLLBACK_REFUSED_INVALID_RECOVERY_EVIDENCE"
        assert evidence["rollback_refused"]["restore_attempted"] is False


def _assert_gateway_recovery_refused(kind: str, *, receipt_expected: bool = True) -> None:
    evidence: dict = {}
    completed, current, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case=kind, evidence=evidence,
    )
    assert completed.returncode == 17, (kind, completed.stderr)
    assert current == b"candidate source\n" and dropin_exists, kind
    assert evidence["service_calls"] == evidence["restore_calls"] == "", kind
    assert evidence["backup_exists"] and "rollback" not in evidence, kind
    assert "ROLLBACK_REFUSED_INVALID_RECOVERY_EVIDENCE" in completed.stderr, kind
    assert "Rolling back the complete gateway" not in completed.stderr, kind
    if receipt_expected:
        refusal = evidence["rollback_refused"]
        assert refusal["status"] == "ROLLBACK_REFUSED_INVALID_RECOVERY_EVIDENCE"
        assert refusal["restore_attempted"] is False
        assert refusal["recovery_evidence_verified"] is False
        assert refusal["restoration_verified"] is False
        assert refusal["trigger_exit_code"] == 17
        assert "manifest_sha256" not in refusal
    else:
        assert "private rollback refusal receipt unavailable" in completed.stderr
        assert not evidence["outside_refusal_written"]


def test_gateway_invalid_recovery_is_refused_before_any_restore_command() -> None:
    for kind in ("backup_changed", "backup_missing", "backup_metadata", "backup_hardlink",
                 "backup_extra", "backup_extra_directory", "manifest_changed", "manifest_missing",
                 "missing_contradiction", "missing_duplicate", "missing_unexpected",
                 "source_binding", "bundle_binding", "hardening_binding",
                 "inventory_omitted", "inventory_extra", "manifest_schema", "manifest_kind", "manifest_status"):
        _assert_gateway_recovery_refused(kind)


def test_gateway_refusal_receipt_failure_keeps_original_code_and_does_not_restore() -> None:
    _assert_gateway_recovery_refused("refusal_write_failure", receipt_expected=False)


def test_gateway_valid_recovery_restores_present_and_removes_originally_missing_file() -> None:
    evidence: dict = {}
    completed, restored, dropin_exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="valid_missing", evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert restored == b"previous source\n" and not dropin_exists
    assert not evidence["originally_missing_target_exists"]
    assert evidence["prepared"]["missing_source_files"] == ["absent.py"]
    assert evidence["service_calls"].count("SYSTEMCTL:stop") == 1
    assert evidence["restore_calls"].count("cp\n") == 1
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert "RECOVERY_EVIDENCE_VERIFIED_BEFORE_RESTORATION" in completed.stdout


@unittest.skipIf(os.name != "posix", "Real symlink and xattr refusal requires Linux CI")
def test_gateway_linked_recovery_paths_and_extended_metadata_cannot_restore() -> None:
    for kind in ("backup_symlink", "backup_parent_symlink", "manifest_symlink", "backup_xattr"):
        _assert_gateway_recovery_refused(kind)
    _assert_gateway_recovery_refused("custody_parent_symlink", receipt_expected=False)


def _assert_runtime_directory_result_failure(fault: str, *, missing: bool = False, receipt_failure: bool = False) -> dict:
    evidence = {}
    completed, source, dropin = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "runtime_directory_result",
        directory_case="empty_run" if missing else "", runtime_directory_fault=fault, evidence=evidence,
    )
    assert completed.returncode == 17 and source == b"previous source\n" and not dropin
    assert evidence["runtime_directory_fault_applied"] and evidence["backup_exists"]
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert "restoration operation runtime_directory_result failed" in completed.stderr
    assert evidence["operation_calls"].splitlines()[-1] == ("rmdir:run_dir" if missing else "chmod:run_dir")
    assert not evidence["runtime_directory_result_receipt_exists"]
    if receipt_failure:
        assert "receipt persistence failed" in completed.stderr and evidence["rollback"] is None
    else:
        receipt = evidence["rollback"]
        assert receipt["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert receipt["failed_restoration_operation"]["operation"] == "runtime_directory_result"
        assert receipt["failed_restoration_operation"]["target"] == "run_directory"
        assert receipt["runtime_directory_result_observation"] == "FAILED"
        assert receipt["source_write_states"][0]["restoration_result_observation"] == "MATCHED_PREPARED_PRESENT"
        assert receipt["dropin_result_observation"] == "MATCHED_PREPARED_ABSENCE"
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
        assert not receipt["service_restart_attempted"]
    return evidence


def test_gateway_runtime_directory_result_requires_actual_removal() -> None:
    evidence = _assert_runtime_directory_result_failure("remove_noop", missing=True)
    assert evidence["runtime_directory_is_directory"]


def test_gateway_runtime_directory_result_requires_matching_type_and_numeric_metadata() -> None:
    for fault in ("uid_mismatch", "gid_mismatch", "file", "missing"):
        evidence = _assert_runtime_directory_result_failure(fault)
        if fault == "file": assert evidence["run_directory_exists"] and not evidence["runtime_directory_is_directory"]
        if fault == "missing": assert not evidence["run_directory_exists"]


@unittest.skipIf(os.name != "posix", "Real directory permissions and links require Linux CI")
def test_gateway_runtime_directory_result_rejects_mode_links_and_unsafe_parents() -> None:
    for fault in ("mode", "symlink", "parent_mode"):
        _assert_runtime_directory_result_failure(fault)
    evidence = _assert_runtime_directory_result_failure("dangling_symlink", missing=True)
    assert evidence["runtime_directory_is_symlink"] and not evidence["run_directory_exists"]


def test_gateway_runtime_directory_result_rejects_failed_or_malformed_query() -> None:
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty",
                 "contradictory", "invalid", "source_argument", "empty_argument", "extra_arguments"):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_result", runtime_directory_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and not dropin, case
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"] == dict(
            operation="runtime_directory_result", target="run_directory", exit_code=29 if case == "failed" else 14)
        assert receipt["runtime_directory_result_observation"] == "FAILED" and receipt["partial_state_possible"]
        assert not evidence["runtime_directory_result_receipt_exists"]


def test_gateway_runtime_directory_result_accepts_metadata_and_true_absence_preserving_nonempty() -> None:
    for directory_case in ("", "empty_run", "absent_run", "nonempty_run"):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_result", directory_case=directory_case, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and not dropin
        receipt = evidence["rollback"]
        if directory_case == "nonempty_run":
            assert receipt["failed_restoration_operation"]["operation"] == "run_directory_remove"
            assert receipt["runtime_directory_result_observation"] == "NOT_CHECKED"
            assert evidence["retained_unrelated_files"] == [b"preserve unrelated bytes\n"]
            assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
            continue
        expected = "MATCHED_PREPARED_PRESENT" if not directory_case else "MATCHED_PREPARED_ABSENCE"
        assert receipt["runtime_directory_result_observation"] == expected
        if not directory_case:
            assert evidence["runtime_directory_metadata"] == evidence["original_runtime_directory_metadata"]
        else:
            assert not evidence["run_directory_exists"] and not evidence["runtime_directory_is_symlink"]
        assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
        assert not evidence["runtime_directory_result_receipt_exists"]


def test_gateway_runtime_directory_result_retains_custody_and_receipt_failure() -> None:
    _assert_runtime_directory_result_failure("remove_noop", missing=True, receipt_failure=True)
    for fault in ("state_changed", "metadata_changed", "manifest_changed"):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_result", runtime_directory_fault=fault, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and not dropin
        assert evidence["runtime_directory_fault_applied"] and evidence["backup_exists"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert "runtime_directory_result failed" in completed.stderr and "receipt persistence failed" in completed.stderr
        assert "rollback" not in evidence and not evidence["runtime_directory_result_receipt_exists"]


def _assert_dropin_directory_result_failure(fault: str, *, missing: bool = False, receipt_failure: bool = False) -> dict:
    evidence = {}
    completed, source, dropin = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "dropin_directory_result",
        directory_case="empty_dropin" if missing else "", dropin_directory_fault=fault, evidence=evidence,
    )
    assert completed.returncode == 17 and source == b"previous source\n" and not dropin
    assert evidence["dropin_directory_fault_applied"] and evidence["backup_exists"]
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert ":run_dir" not in evidence["operation_calls"]
    assert "restoration operation dropin_directory_result failed" in completed.stderr
    assert evidence["operation_calls"].splitlines()[-1] == ("rmdir:dropin_dir" if missing else "chmod:dropin_dir")
    assert not evidence["dropin_directory_result_receipt_exists"]
    if receipt_failure:
        assert "receipt persistence failed" in completed.stderr and evidence["rollback"] is None
    else:
        receipt = evidence["rollback"]
        assert receipt["status"] == "ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED"
        assert receipt["failed_restoration_operation"]["operation"] == "dropin_directory_result"
        assert receipt["failed_restoration_operation"]["target"] == "service_drop_in_directory"
        assert receipt["dropin_directory_result_observation"] == "FAILED"
        assert receipt["source_write_states"][0]["restoration_result_observation"] == "MATCHED_PREPARED_PRESENT"
        assert receipt["dropin_result_observation"] == "MATCHED_PREPARED_ABSENCE"
        assert receipt["runtime_directory_result_observation"] == "NOT_CHECKED"
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
        assert not receipt["service_restart_attempted"]
    return evidence


def test_gateway_dropin_directory_result_requires_actual_removal() -> None:
    evidence = _assert_dropin_directory_result_failure("remove_noop", missing=True)
    assert evidence["dropin_directory_is_directory"]


def test_gateway_dropin_directory_result_requires_matching_type_and_numeric_metadata() -> None:
    for fault in ("uid_mismatch", "gid_mismatch", "file", "missing"):
        evidence = _assert_dropin_directory_result_failure(fault)
        if fault == "file": assert evidence["dropin_directory_exists"] and not evidence["dropin_directory_is_directory"]
        if fault == "missing": assert not evidence["dropin_directory_exists"]


@unittest.skipIf(os.name != "posix", "Real directory permissions and links require Linux CI")
def test_gateway_dropin_directory_result_rejects_mode_links_and_unsafe_parents() -> None:
    for fault in ("mode", "symlink", "parent_mode"):
        _assert_dropin_directory_result_failure(fault)
    evidence = _assert_dropin_directory_result_failure("dangling_symlink", missing=True)
    assert evidence["dropin_directory_is_symlink"] and not evidence["dropin_directory_exists"]


def test_gateway_dropin_directory_result_rejects_failed_or_malformed_query() -> None:
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty",
                 "contradictory", "invalid", "source_argument", "empty_argument", "extra_arguments"):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_result", dropin_directory_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and not dropin, case
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert ":run_dir" not in evidence["operation_calls"] and evidence["backup_exists"]
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"] == dict(
            operation="dropin_directory_result", target="service_drop_in_directory", exit_code=29 if case == "failed" else 14)
        assert receipt["dropin_directory_result_observation"] == "FAILED" and receipt["partial_state_possible"]
        assert not evidence["dropin_directory_result_receipt_exists"]


def test_gateway_dropin_directory_result_accepts_metadata_and_true_absence_preserving_nonempty() -> None:
    for directory_case, prior_dropin in (("", False), ("", True), ("empty_dropin", False),
                                       ("absent_dropin", False), ("nonempty_dropin", False)):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_result", directory_case=directory_case,
            prior_dropin=prior_dropin, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and dropin == prior_dropin
        if prior_dropin:
            assert evidence["dropin_bytes"] == b"previous hardening\n"
        receipt = evidence["rollback"]
        if directory_case == "nonempty_dropin":
            assert receipt["failed_restoration_operation"]["operation"] == "dropin_directory_remove"
            assert receipt["dropin_directory_result_observation"] == "NOT_CHECKED"
            assert evidence["retained_unrelated_files"] == [b"preserve unrelated bytes\n"]
            assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
            assert ":run_dir" not in evidence["operation_calls"]
            continue
        expected = "MATCHED_PREPARED_PRESENT" if not directory_case else "MATCHED_PREPARED_ABSENCE"
        assert receipt["dropin_directory_result_observation"] == expected
        if not directory_case:
            assert evidence["dropin_directory_metadata"] == evidence["original_dropin_directory_metadata"]
        else:
            assert not evidence["dropin_directory_exists"] and not evidence["dropin_directory_is_symlink"]
        assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
        assert not evidence["dropin_directory_result_receipt_exists"]


def test_gateway_dropin_directory_result_retains_custody_and_receipt_failure() -> None:
    _assert_dropin_directory_result_failure("remove_noop", missing=True, receipt_failure=True)
    for fault in ("state_changed", "metadata_changed", "manifest_changed"):
        evidence = {}
        completed, source, dropin = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_result", dropin_directory_fault=fault, evidence=evidence,
        )
        assert completed.returncode == 17 and source == b"previous source\n" and not dropin
        assert evidence["dropin_directory_fault_applied"] and evidence["backup_exists"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert ":run_dir" not in evidence["operation_calls"]
        assert "dropin_directory_result failed" in completed.stderr and "receipt persistence failed" in completed.stderr
        assert "rollback" not in evidence and not evidence["dropin_directory_result_receipt_exists"]


def _assert_dropin_target_conflict(kind: str, boundary: str = "stop", *, receipt_failure: bool = False, prior_dropin: bool = True) -> dict:
    evidence: dict = {}
    completed, source, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "dropin_target_guard",
        prior_dropin=prior_dropin, dropin_target_drift=kind, dropin_target_boundary=boundary, evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert evidence["dropin_target_drift_applied"] and evidence["backup_exists"]
    assert source == b"previous source\n"  # Earlier restoration is explicitly partial.
    assert len(evidence["dropin_forward_calls"]) == 1
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    absent_guard = boundary == "after_remove"
    operation = "dropin_directory_target_state" if kind == "parent_link" else "dropin_target_absent" if absent_guard else "dropin_target_state"
    assert f"restoration operation {operation} failed" in completed.stderr
    expected_calls = ["rm:first_source", "cp:first_source"]
    if absent_guard:
        expected_calls += ["rm:dropin", "install:dropin_dir"]
    assert evidence["operation_calls"].splitlines() == expected_calls
    if kind in {"changed", "reappeared"}:
        assert evidence["dropin_bytes"] == b"intervening drop-in writer\n"
    if receipt_failure:
        assert "receipt persistence failed" in completed.stderr and evidence.get("rollback") is None
    else:
        receipt = evidence["rollback"]
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert receipt["failed_restoration_operation"]["operation"] == operation
        assert receipt["dropin_write_state"]["state"] == "INSTALLED"
        assert receipt["dropin_result_observation"] == "NOT_CHECKED"
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
    return evidence


def test_gateway_dropin_target_guard_preserves_intervening_bytes_identity_and_metadata() -> None:
    for kind in ("changed", "missing", "identity", "mtime", "directory"):
        _assert_dropin_target_conflict(kind)
    _assert_dropin_target_conflict("changed", "after_first_copy")
    _assert_dropin_target_conflict("changed", prior_dropin=False)


@unittest.skipIf(os.name != "posix", "POSIX target links, modes and extended attributes")
def test_gateway_dropin_target_guard_rejects_links_parent_and_extended_metadata() -> None:
    for kind in ("mode", "symlink", "hardlink", "parent_link", "xattr"):
        _assert_dropin_target_conflict(kind)


def test_gateway_dropin_target_guard_preserves_reappearance_before_copy_and_receipt_failure() -> None:
    _assert_dropin_target_conflict("reappeared", "after_remove")
    _assert_dropin_target_conflict("changed", receipt_failure=True)


def test_gateway_dropin_target_guard_uses_actual_forward_states_and_valid_controls() -> None:
    for prior in (False, True):
        evidence: dict = {}
        completed, _, exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_target_guard", prior_dropin=prior, evidence=evidence,
        )
        assert completed.returncode == 17 and exists is prior, completed.stderr
        assert evidence["dropin_bytes"] == (b"previous hardening\n" if prior else None)
        receipt = evidence["rollback"]
        state = receipt["dropin_write_state"]
        assert state["state"] == "INSTALLED" and len(state["installed_version_sha256"]) == 64
        assert state["candidate_sha256"] == hashlib.sha256(b"candidate hardening\n").hexdigest()
        assert len(evidence["dropin_forward_calls"]) == 1
        assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
        assert not receipt["restoration_verified"]
    evidence = {}
    completed, _, exists = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="dropin_target_guard", prior_dropin=True, dropin_forward_case="untouched", evidence=evidence,
    )
    assert completed.returncode == 17 and exists
    assert evidence["dropin_bytes"] == b"candidate hardening\n" and not evidence["dropin_forward_calls"]
    assert "rm:dropin" not in evidence["operation_calls"] and "cp:dropin" not in evidence["operation_calls"]
    receipt = evidence["rollback"]
    assert receipt["dropin_result_observation"] == "UNCHECKED_UNTOUCHED"
    assert receipt["dropin_write_state"]["state"] == "UNTOUCHED"
    assert receipt["dropin_write_state"]["installed_version_sha256"] is None


def test_gateway_dropin_target_guard_partial_install_and_failed_readback_cannot_restore() -> None:
    for case, trigger in (("partial", 31), ("wrong_bytes", 1), ("stage_changed", 1), ("capture_failed", 29)):
        evidence: dict = {}
        completed, source, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_target_guard", prior_dropin=True, dropin_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == trigger, (case, completed.stderr)
        assert source == b"candidate source\n" and evidence["operation_calls"] == ""
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        receipt = evidence["rollback"]
        assert receipt["dropin_write_state"]["state"] == "WRITE_PENDING"
        assert receipt["dropin_write_state"]["installed_version_sha256"] is None
        assert receipt["failed_restoration_operation"] == dict(operation="dropin_target_state", target="service_drop_in", exit_code=14)
        assert receipt["trigger_exit_code"] == trigger and receipt["partial_state_possible"]
        assert receipt["dropin_result_observation"] == "NOT_CHECKED"


def test_gateway_dropin_target_guard_strict_query_failures_stop_before_later_work() -> None:
    for case in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline", "empty",
                 "extra_argument", "invalid_mode", "unknown_object", "supplied_path", "absent_failed", "absent_extra"):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_target_guard", prior_dropin=True, dropin_target_query_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and evidence["service_calls"] == "SYSTEMCTL:stop\n", (case, completed.stderr)
        absent = case.startswith("absent_")
        expected = ["rm:first_source", "cp:first_source"] + (["rm:dropin", "install:dropin_dir"] if absent else [])
        assert evidence["operation_calls"].splitlines() == expected, case
        failure = evidence["rollback"]["failed_restoration_operation"]
        assert failure["operation"] == ("dropin_target_absent" if absent else "dropin_target_state")
        assert failure["exit_code"] == (29 if case in {"failed", "absent_failed"} else 1 if case in {"unknown_object", "supplied_path"} else 14)
        assert evidence["dropin_bytes"] == (None if absent else b"candidate hardening\n")


def test_gateway_dropin_target_guard_unknown_or_inconsistent_state_refuses_mutation() -> None:
    for case in ("unknown_state", "invalid_state", "missing_version", "invalid_version", "untouched_version"):
        evidence: dict = {}
        completed, _, exists = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_target_guard", prior_dropin=True, dropin_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and exists, (case, completed.stderr)
        assert evidence["dropin_bytes"] == b"candidate hardening\n"
        assert evidence["operation_calls"].splitlines() == ["rm:first_source", "cp:first_source"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        assert "dropin_target_state failed" in completed.stderr
        if case in {"invalid_state", "invalid_version"}:
            assert "receipt persistence failed" in completed.stderr and "rollback" not in evidence
        else:
            assert evidence["rollback"]["failed_restoration_operation"] == dict(
                operation="dropin_target_state", target="service_drop_in", exit_code=14)


def test_gateway_dropin_target_guard_keeps_approved_pin_before_forward_mutation() -> None:
    script = _repair_script()
    compare = '[[ "$(sha256sum "$STAGE_DIR/20-lumencore-runtime-hardening.conf" | awk \'{print $1}\')" == "$HARDENING_SHA" ]]'
    assert script.index(compare) < script.index('RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"')
    assert script.index(compare) < script.index('systemctl stop "$SERVICE"\nSERVICE_STOPPED=true')
    install = _bash_function(script, "install_gateway_dropin")
    assert install.index("DROPIN_WRITE_STATE=WRITE_PENDING") < install.index("install -o")
    assert install.index("capture_dropin_target_version") < install.index("DROPIN_WRITE_STATE=INSTALLED")
    rollback = _bash_function(script, "rollback")
    assert rollback.index("read_recovery_dropin_target_state") < rollback.index("dropin_remove")
    assert rollback.index("require_recovery_dropin_absent") < rollback.index("dropin_copy")


def test_gateway_recovery_directory_requires_root_and_private_permissions() -> None:
    function = _bash_function(_repair_script(), "require_safe_recovery_directory")
    # The actual guard checks real fixture file types. Controlled stat responses
    # make root ownership and mode refusals testable without elevated privileges.
    cases = [
        ("0", "755", "0", False, 0), ("1000", "755", "0", False, 13),
        ("0", "777", "0", False, 13), ("0", "775", "0", False, 13),
        ("0", "757", "0", False, 13), ("0", "invalid", "0", False, 13),
        ("0", "700", "0", True, 0), ("0", "755", "0", True, 13),
        ("0", "700", "1000", True, 13),
    ]
    with tempfile.TemporaryDirectory(prefix="gateway-recovery-directory-") as directory:
        root = Path(directory)
        (root / "fixture").mkdir()
        (root / "file").write_text("fixture")
        harness = r'''set -Eeuo pipefail
stat() {
  case "$2" in
    '%u') printf '%s\n' "$FIXTURE_UID" ;;
    '%a') printf '%s\n' "$FIXTURE_MODE" ;;
    '%u:%g:%a') printf '%s:%s:%s\n' "$FIXTURE_UID" "$FIXTURE_GID" "$FIXTURE_MODE" ;;
    *) return 99 ;;
  esac
}
'''
        harness += function + '\nrequire_safe_recovery_directory "$1" "$2"\n'
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        for owner, mode, group, private, expected in cases:
            env = dict(os.environ, FIXTURE_UID=owner, FIXTURE_MODE=mode, FIXTURE_GID=group)
            completed = subprocess.run(
                [_gateway_rollback_test_bash(), "fixture.sh", "fixture", str(private).lower()],
                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False,
            )
            assert completed.returncode == expected, (owner, mode, group, private, completed.stderr)
        for name in ("file", "missing"):
            completed = subprocess.run(
                [_gateway_rollback_test_bash(), "fixture.sh", name, "false"],
                cwd=root, capture_output=True, text=True, timeout=10, check=False,
            )
            assert completed.returncode == 13, completed.stderr
        if os.name == "posix":
            (root / "linked").symlink_to(root / "fixture", target_is_directory=True)
            completed = subprocess.run(
                [_gateway_rollback_test_bash(), "fixture.sh", "linked", "false"],
                cwd=root, capture_output=True, text=True, timeout=10, check=False,
            )
            assert completed.returncode == 13, completed.stderr


def _run_gateway_unsafe_recovery_root(owner: str, mode: str, group: str, *, symlink: bool = False) -> None:
    script = _repair_script()
    function = _bash_function(script, "prepare_recovery_directory")
    directory_guard = _bash_function(script, "require_safe_recovery_directory").replace(
        "require_safe_recovery_directory()", "fixture_directory_guard()", 1
    )
    with tempfile.TemporaryDirectory(prefix="gateway-recovery-unsafe-root-") as directory:
        root = Path(directory)
        (root / "unsafe-root").mkdir()
        (root / "unsafe-root/retained").write_bytes(b"do not modify")
        if symlink:
            (root / "linked-root").symlink_to(root / "unsafe-root", target_is_directory=True)
        harness = r'''set -Eeuo pipefail
RECOVERY_ROOT="$PWD/$FIXTURE_ROOT"
stat() {
  case "$2" in
    '%u') printf '%s\n' "$FIXTURE_UID" ;;
    '%a') printf '%s\n' "$FIXTURE_MODE" ;;
    '%u:%g:%a') printf '%s:%s:%s\n' "$FIXTURE_UID" "$FIXTURE_GID" "$FIXTURE_MODE" ;;
    *) return 99 ;;
  esac
}
require_safe_recovery_directory() {
  case "$1" in
    /|/var|/var/backups) return 0 ;;
    *) fixture_directory_guard "$@" ;;
  esac
}
install() { printf 'UNEXPECTED_INSTALL\n'; return 99; }
mktemp() { printf 'UNEXPECTED_MKTEMP\n'; return 99; }
'''
        harness += directory_guard + "\n" + function + '\nprepare_recovery_directory\n'
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        env = dict(os.environ, FIXTURE_UID=owner, FIXTURE_MODE=mode, FIXTURE_GID=group,
                   FIXTURE_ROOT="linked-root" if symlink else "unsafe-root")
        completed = subprocess.run(
            [_gateway_rollback_test_bash(), "fixture.sh"], cwd=root,
            env=env, capture_output=True, text=True, timeout=10, check=False,
        )
        assert completed.returncode == 13, completed.stderr
        assert completed.stdout == ""
        assert (root / "unsafe-root/retained").read_bytes() == b"do not modify"
        assert sorted(path.name for path in (root / "unsafe-root").iterdir()) == ["retained"]


def test_gateway_existing_unsafe_recovery_root_is_never_repaired() -> None:
    # Execute both real functions. Only the fixed production ancestors are
    # substituted; filesystem writes remain confined to the disposable fixture.
    for owner, mode, group in (("1000", "700", "0"), ("0", "777", "0"),
                               ("0", "755", "0"), ("0", "700", "1000")):
        _run_gateway_unsafe_recovery_root(owner, mode, group)


@unittest.skipIf(os.name != "posix", "Real POSIX symlink refusal requires Linux CI")
def test_gateway_symbolic_recovery_root_is_never_repaired() -> None:
    _run_gateway_unsafe_recovery_root("0", "700", "0", symlink=True)


def test_gateway_repair_http_boundary_probe_fails_closed() -> None:
    if not Path("/bin/bash").is_file():
        return

    function_source = _bash_function(
        _repair_script(), "probe_operator_http_boundary"
    )
    harness = (
        """
set -u
SOURCE_COMMIT=0123456789abcdef0123456789abcdef01234567
seq() { printf '1\\n'; }
sleep() { :; }
curl() {
  local body_file=""
  local header_file=""
  while (( $# )); do
    case "$1" in
      --output) body_file=$2; shift 2 ;;
      --dump-header) header_file=$2; shift 2 ;;
      --write-out) shift 2 ;;
      *) shift ;;
    esac
  done
  [[ -n "$body_file" && -n "$header_file" ]]
  printf '{"detail":"%s"}' "$FAKE_DETAIL" > "$body_file"
  {
    printf 'HTTP/1.1 %s Fixture\\r\\n' "$FAKE_STATUS"
    printf 'Content-Type: application/json\\r\\n'
    printf 'Cache-Control: no-store\\r\\n'
    printf 'Pragma: no-cache\\r\\n'
    if [[ "$FAKE_STATUS" == 401 ]]; then
      printf 'WWW-Authenticate: Bearer\\r\\n'
    fi
    printf '\\r\\n'
  } > "$header_file"
  printf '%s\\tapplication/json' "$FAKE_STATUS"
}
body_file=$(mktemp)
header_file=$(mktemp)
trap 'rm -f -- "$body_file" "$header_file"' EXIT
"""
        + function_source
        + '\nprobe_operator_http_boundary "https://example.invalid/metrics" "$body_file" "$header_file"\n'
    )

    cases = (
        ("401", "operator API authentication required", True),
        ("503", "operator API access unavailable", True),
        ("200", "unexpected public body", False),
        ("401", "wrong denial detail", False),
    )
    for status, detail, should_pass in cases:
        completed = subprocess.run(
            ["/bin/bash", "-c", harness],
            check=False,
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "FAKE_STATUS": status,
                "FAKE_DETAIL": detail,
            },
        )
        assert (completed.returncode == 0) is should_pass
        assert completed.stdout.strip() == status


def test_gateway_repair_websocket_probe_distinguishes_origin_and_edge() -> None:
    if not Path("/bin/bash").is_file():
        return

    function_source = _bash_function(
        _repair_script(), "probe_operator_websocket_boundary"
    )
    harness = (
        """
set -u
SOURCE_COMMIT=0123456789abcdef0123456789abcdef01234567
seq() { printf '1\\n'; }
sleep() { :; }
curl() {
  local output=""
  while (( $# )); do
    case "$1" in
      --output) output=$2; shift 2 ;;
      --write-out) shift 2 ;;
      *) shift ;;
    esac
  done
  [[ -n "$output" ]]
  : > "$output"
  printf '%s' "$FAKE_STATUS"
}
output=$(mktemp)
trap 'rm -f -- "$output"' EXIT
"""
        + function_source
        + '\nprobe_operator_websocket_boundary "https://example.invalid/ws" "$output" "$ALLOW_NOT_FOUND"\n'
    )

    cases = (
        ("403", "false", True),
        ("404", "false", False),
        ("404", "true", True),
        ("101", "true", False),
    )
    for status, allow_not_found, should_pass in cases:
        completed = subprocess.run(
            ["/bin/bash", "-c", harness],
            check=False,
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "FAKE_STATUS": status,
                "ALLOW_NOT_FOUND": allow_not_found,
            },
        )
        assert (completed.returncode == 0) is should_pass
        assert completed.stdout.strip() == status


def test_declared_gateway_closure_covers_recursive_local_imports() -> None:
    declared = _declared_gateway_closure(_repair_script())
    local_modules: dict[str, str] = {}
    for path in CODE.rglob("*.py"):
        relative = path.relative_to(CODE).as_posix()
        if path.name == "__init__.py":
            module = ".".join(path.relative_to(CODE).parent.parts)
        else:
            module = ".".join(path.relative_to(CODE).with_suffix("").parts)
        local_modules[module] = relative

    pending = ["luma_experience_gateway.py"]
    visited: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        tree = ast.parse((CODE / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [node.module]
            for module in imported:
                candidate = local_modules.get(module)
                if candidate and candidate not in visited:
                    pending.append(candidate)

    assert visited <= declared


def test_gateway_service_restart_policy_is_bounded() -> None:
    deploy = (ROOT / "code" / "deploy" / "deploy_vps.sh").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"cat > \"\$GATEWAY_SERVICE\" <<EOF\n(?P<body>.*?)\nEOF",
        deploy,
        flags=re.DOTALL,
    )
    assert match is not None
    service = match.group("body")
    assert "Restart=on-failure" in service
    assert "Restart=always" not in service
    assert "StartLimitIntervalSec=300" in service
    assert "StartLimitBurst=10" in service


def test_gateway_and_refresh_services_run_as_bounded_non_root_account() -> None:
    deploy = (ROOT / "code" / "deploy" / "deploy_vps.sh").read_text(
        encoding="utf-8"
    )
    assert (
        'install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 '
        '"$STACK_ROOT/run"'
    ) in deploy
    assert "required non-root service account does not exist" in deploy
    assert "refusing to run LumenCore application services as root" in deploy
    assert 'SERVICE_USER="root"' not in deploy

    gateway_match = re.search(
        r'cat > "\$GATEWAY_SERVICE" <<EOF\n(?P<body>.*?)\nEOF',
        deploy,
        flags=re.DOTALL,
    )
    refresh_match = re.search(
        r'cat > "\$DASH_REFRESH_SERVICE" <<EOF\n(?P<body>.*?)\nEOF',
        deploy,
        flags=re.DOTALL,
    )
    assert gateway_match is not None
    assert refresh_match is not None
    for service in (gateway_match.group("body"), refresh_match.group("body")):
        assert "User=$SERVICE_USER" in service
        assert "Group=$SERVICE_GROUP" in service
        assert "UMask=0027" in service
        assert "NoNewPrivileges=true" in service
        assert "PrivateTmp=true" in service


def test_health_probe_classifies_static_and_dynamic_surfaces() -> None:
    import runpy

    health = runpy.run_path(str(ROOT / "code/ops/probe_public_health.py"))
    endpoints = health["ENDPOINTS"]
    assert len(endpoints) == 16
    assert sum(contract in health["MARKERS"] for _, _, contract in endpoints) == 14
    by_name = {name: (url, contract) for name, url, contract in endpoints}
    assert by_name["www_portal"] == ("https://www.lumen-core.ai/", "home")
    assert by_name["gateway_public_status"] == (
        "https://lumen-core.ai/api/public/status", "public_status"
    )
    assert by_name["gateway_health"] == (
        "https://lumen-core.ai/health", "gateway_health"
    )
    assert all(url != "https://lumen-core.ai/api/snapshot" for _, url, _ in endpoints)
    for retired_path in (
        "mission_control.html", "quant_lab.html", "kraken_execution_dashboard.html",
        "grants.html", "forecast.html", "anomalies.html", "explain.html", "lab.html",
    ):
        assert (f"https://lumen-core.ai/{retired_path}", "legacy_hold") in {
            (url, contract) for _, url, contract in endpoints
        }


def test_health_probe_is_read_only_artifact_only_and_outage_fails_job() -> None:
    health = (ROOT / ".github/workflows/health-probe.yml").read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in health
    assert "persist-credentials: false" in health
    assert "runner.temp }}/lumencore-health-probe" in health
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in health
    assert "retention-days: 14" in health
    assert "Production health verdict:" in health
    assert "A completed probe is not evidence of a healthy deployment" in health
    assert "no repository commit or deployment occurred" in health
    assert "site_health_samples.jsonl" in health
    assert "--rounds 4 --interval-seconds 60" in health
    assert ".observation_window.all_samples_complete == true" in health
    assert ".observation_window.failed_observations == 0" in health
    assert "if: always()" in health
    assert "exit 1" in health
    for forbidden in ("contents: write", "git config user.", "git add ", "git commit ", "git pull ", "git push "):
        assert forbidden not in health


def test_live_metrics_sync_is_read_only_artifact_only_and_fail_closed() -> None:
    metrics = (ROOT / ".github" / "workflows" / "live-metrics-sync.yml").read_text(
        encoding="utf-8"
    )

    assert "permissions:\n  contents: read" in metrics
    assert "persist-credentials: false" in metrics
    assert "runner.temp }}/lumencore-live-metrics" in metrics
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in metrics
    assert "retention-days: 14" in metrics
    assert "available_objects" in metrics
    assert "Live metrics verdict:" in metrics
    assert "A completed metrics capture is not evidence of a healthy deployment" in metrics
    assert "Fail closed on non-operational verdict" in metrics
    for forbidden in (
        "contents: write",
        "git config user.",
        "git add ",
        "git commit ",
        "git pull ",
        "git push ",
    ):
        assert forbidden not in metrics


def test_health_probe_static_contract_fails_closed() -> None:
    import runpy

    classify = runpy.run_path(str(ROOT / "code/ops/probe_public_health.py"))["classify"]
    for body, content_type, expected in (
        (b"<meta content='proof-to-pilot-home-v1'>", "text/html; charset=utf-8", True),
        (b"<html>wrong release</html>", "text/html; charset=utf-8", False),
        (b"proof-to-pilot-home-v1", "text/plain", False),
    ):
        row = classify("home", 200, content_type, body, transport_ok=True, same_origin_ok=True)
        assert row["http_ok"] is True
        assert row["reachable"] is True
        assert row["contract_ok"] is expected
        assert row["ok"] is expected


def test_gateway_recovery_workflow_requires_exact_main_commit_and_gate() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "repair-gateway-dependency-closure.yml"
    ).read_text(encoding="utf-8")
    assert "REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE" in workflow
    assert '[[ "$APPROVAL" == "REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE" ]]' in workflow
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in workflow
    assert '[[ "$(git rev-parse origin/main)" == "$RELEASE_COMMIT" ]]' in workflow
    assert "VPS_KNOWN_HOSTS" in workflow
    assert "StrictHostKeyChecking=yes" in workflow
    assert "secrets.LUMA_HUMAN_UNLOCK_TOKEN" in workflow
    assert "Repository secret LUMA_HUMAN_UNLOCK_TOKEN is missing" in workflow
    assert "no VPS change was attempted" in workflow
    assert "LUMENCORE_HUMAN_UNLOCK_FILE='$REMOTE_STAGE/human-unlock'" in workflow
    assert 'LUMA_HUMAN_UNLOCK_TOKEN="$(cat' not in workflow
    assert "LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256" in workflow
    assert "LUMENCORE_EXPECTED_GATEWAY_HARDENING_SHA256" in workflow
    assert "--hardening-sha" in workflow
    assert "service_hardening_sha256" in workflow
    assert 'test "$(id -u lumencore)" -ne 0' in workflow
    assert 'test "$(id -gn lumencore)" = lumencore' in workflow
    assert "sudo -n -u lumencore test -x /opt/lumencore/.venv/bin/python" in workflow
    assert "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh" in workflow
    assert "--apply" in workflow
    for path in ("/metrics", "/openapi.json", "/docs", "/redoc"):
        assert f"probe_anonymous_operator_http {path} " in workflow
    for marker in (
        "probe_anonymous_operator_http()",
        "anonymous_%s_http=%s",
        "anonymous_ws_upgrade_http=%s",
        '[[ "$code" == 401 || "$code" == 503 ]]',
        '[[ "$websocket_code" == 403 || "$websocket_code" == 404 ]]',
        "operator API authentication required",
        "operator API access unavailable",
        "keys == [\"detail\"]",
        "public-verification-receipt.txt",
        "awk grep seq sleep tr",
    ):
        assert marker in workflow
    assert "Authorization: Bearer" not in workflow
    assert "x-luma-operator-token" not in workflow.lower()
    assert "Remove remote repair staging" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in workflow
    assert "shimataro/ssh-key-action@87a8f067114a8ce263df83e9ed5c849953548bc3 # v2.8.1" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in workflow

    workflow = (
        ROOT / ".github" / "workflows" / "gateway-public-contract-ci.yml"
    ).read_text(
        encoding="utf-8"
    )
    assert "Gateway Public Contract Gate" in workflow
    assert "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh" in workflow
    assert "WRONG_HASH_FAIL_CLOSED_OK" in workflow
    assert "WRONG_HARDENING_HASH_FAIL_CLOSED_OK" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0" in workflow


def _assert_runtime_directory_target_conflict(kind: str, *, boundary: str = "stop",
                                               missing_before: bool = False, receipt_failure: bool = False) -> dict:
    evidence: dict = {}
    completed, source, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "runtime_directory_target_guard",
        directory_case="missing_run" if missing_before else "", run_target_drift=kind,
        run_target_boundary=boundary, evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert evidence["run_target_drift_applied"] and len(evidence["run_forward_calls"]) == 1
    assert evidence["backup_exists"] and source == b"previous source\n"
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert ":run_dir" not in evidence["operation_calls"]
    assert "run_target_state failed" in completed.stderr
    if kind == "identity": assert evidence["runtime_directory_is_directory"]
    if kind == "file": assert evidence["run_directory_exists"] and not evidence["runtime_directory_is_directory"]
    if receipt_failure:
        assert "receipt persistence failed" in completed.stderr and evidence.get("rollback") is None
    else:
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"]["operation"] == "run_target_state"
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert receipt["runtime_directory_write_state"]["state"] == "INSTALLED"
        assert receipt["runtime_directory_result_observation"] == "NOT_CHECKED"
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
    return evidence


def test_gateway_runtime_directory_target_guard_preserves_replaced_missing_or_wrong_type() -> None:
    for kind in ("identity", "missing", "file"):
        _assert_runtime_directory_target_conflict(kind)
    _assert_runtime_directory_target_conflict("identity", missing_before=True)
    _assert_runtime_directory_target_conflict("identity", boundary="after_first_copy")
    _assert_runtime_directory_target_conflict("identity", boundary="before_run_restore")
    _assert_runtime_directory_target_conflict("identity", boundary="query")
    _assert_runtime_directory_target_conflict("identity", receipt_failure=True)


@unittest.skipIf(os.name != "posix", "POSIX runtime-directory mode and symbolic-link guard")
def test_gateway_runtime_directory_target_guard_rejects_modes_links_and_unsafe_parent() -> None:
    for kind in ("mode", "symlink", "parent_mode"):
        evidence = _assert_runtime_directory_target_conflict(kind, boundary="query" if kind == "parent_mode" else "stop")
        if kind == "mode": assert evidence["runtime_directory_metadata"][2] == 0o700
        if kind == "symlink": assert evidence["runtime_directory_is_symlink"]


def test_gateway_runtime_directory_target_guard_actual_forward_valid_and_untouched() -> None:
    for case in ("", "missing_run", "absent_run", "nonempty_run"):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_target_guard", directory_case=case, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        assert len(evidence["run_forward_calls"]) == 1
        receipt = evidence["rollback"]
        state = receipt["runtime_directory_write_state"]
        assert state["state"] == "INSTALLED" and len(state["installed_version_sha256"]) == 64
        assert state["candidate_metadata"].endswith(":750")
        if case == "nonempty_run":
            assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
            assert evidence["retained_unrelated_files"] == [b"preserve unrelated bytes\n"]
        else:
            assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
            assert receipt["runtime_directory_result_observation"] == (
                "MATCHED_PREPARED_PRESENT" if not case else "MATCHED_PREPARED_ABSENCE")
    for case in ("", "missing_run"):
        evidence = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_target_guard", directory_case=case,
            run_forward_case="untouched", evidence=evidence,
        )
        assert completed.returncode == 17 and not evidence["run_forward_calls"]
        assert ":run_dir" not in evidence["operation_calls"] and evidence["run_directory_exists"]
        assert evidence["rollback"]["runtime_directory_result_observation"] == "UNCHECKED_UNTOUCHED"
        assert evidence["rollback"]["runtime_directory_write_state"]["state"] == "UNTOUCHED"


def test_gateway_runtime_directory_target_guard_partial_install_and_readback_failure() -> None:
    for case, trigger in (("partial", 31), ("wrong_type", 1), ("capture_failed", 29)):
        evidence: dict = {}
        completed, source, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_target_guard", run_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == trigger, (case, completed.stderr)
        assert source == b"candidate source\n" and evidence["backup_exists"]
        assert ":run_dir" not in evidence["operation_calls"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        receipt = evidence["rollback"]
        assert receipt["runtime_directory_write_state"]["state"] == "WRITE_PENDING"
        assert receipt["runtime_directory_write_state"]["installed_version_sha256"] is None
        assert receipt["failed_restoration_operation"] == dict(operation="run_target_state", target="run_directory", exit_code=14)


def test_gateway_runtime_directory_target_guard_query_and_state_failures() -> None:
    for query in ("failed", "extra_line", "extra_newline", "carriage_return", "no_newline",
                  "empty", "extra_argument", "invalid_mode", "supplied_path"):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_target_guard", run_target_query_case=query, evidence=evidence,
        )
        assert completed.returncode == 17 and ":run_dir" not in evidence["operation_calls"], (query, completed.stderr)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        failure = evidence["rollback"]["failed_restoration_operation"]
        assert failure["operation"] == "run_target_state"
        assert failure["exit_code"] == (29 if query == "failed" else 1 if query in {"invalid_mode", "supplied_path"} else 14)
    for case in ("unknown_state", "invalid_state", "missing_version", "invalid_version", "untouched_version"):
        evidence = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="runtime_directory_target_guard", run_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and ":run_dir" not in evidence["operation_calls"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        assert "run_target_state failed" in completed.stderr
        if case in {"invalid_state", "invalid_version"}:
            assert "receipt persistence failed" in completed.stderr and "rollback" not in evidence


def test_gateway_runtime_directory_target_guard_allows_own_child_changes_and_pins_before_mutation() -> None:
    evidence: dict = {}
    completed, _, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="runtime_directory_target_guard", second_source=True,
        run_target_drift="children", evidence=evidence,
    )
    assert completed.returncode == 17 and evidence["run_target_drift_applied"], completed.stderr
    assert evidence["second_target"] == b"second previous\n"
    assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
    script = _repair_script()
    assert script.index('RUN_CANDIDATE_METADATA="${service_uid}:$(id -g "$SERVICE_USER"):750"') < script.index(
        'RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"')
    install = _bash_function(script, "install_gateway_runtime_directory")
    assert install.index("RUN_WRITE_STATE=WRITE_PENDING") < install.index("install -d")
    assert install.index("capture_runtime_directory_target_version") < install.index("RUN_WRITE_STATE=INSTALLED")
    rollback = _bash_function(script, "rollback")
    assert rollback.index("run_target_state") < rollback.index("run_directory_state_read")


def _assert_dropin_directory_target_conflict(kind: str, *, boundary: str = "before_directory_restore",
                                            receipt_failure: bool = False) -> dict:
    evidence: dict = {}
    completed, source, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="rollback_write_failure" if receipt_failure else "dropin_directory_target_guard",
        prior_dropin=boundary == "before_parent_install",
        directory_case="" if boundary == "before_parent_install" else "missing_dropin",
        dropin_dir_drift=kind, dropin_dir_boundary=boundary, evidence=evidence,
    )
    assert completed.returncode == 17, completed.stderr
    assert evidence["dropin_dir_drift_applied"] and len(evidence["dropin_dir_forward_calls"]) == 1
    assert source == b"previous source\n" and evidence["backup_exists"]
    assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
    assert ":dropin_dir" not in evidence["operation_calls"] and ":run_dir" not in evidence["operation_calls"]
    assert "cp:dropin" not in evidence["operation_calls"]
    assert "dropin_directory_target_state failed" in completed.stderr
    if kind == "identity": assert evidence["dropin_directory_is_directory"]
    if kind == "file": assert evidence["dropin_directory_exists"] and not evidence["dropin_directory_is_directory"]
    if receipt_failure:
        assert "receipt persistence failed" in completed.stderr and evidence.get("rollback") is None
    else:
        receipt = evidence["rollback"]
        assert receipt["failed_restoration_operation"]["operation"] == "dropin_directory_target_state"
        assert receipt["trigger_exit_code"] == 17 and receipt["partial_state_possible"]
        assert receipt["dropin_directory_write_state"]["state"] == "INSTALLED"
        assert receipt["dropin_directory_result_observation"] == "NOT_CHECKED"
        assert not receipt["restoration_verified"] and not receipt["service_state_verified"]
    return evidence


def test_gateway_dropin_directory_target_guard_protects_both_restoration_sites() -> None:
    # This is the preserved baseline interleaving, plus the earlier parent-install
    # mutation site. Neither may adopt or remove a newly substituted directory.
    for boundary in ("before_directory_restore", "before_parent_install"):
        _assert_dropin_directory_target_conflict("identity", boundary=boundary)
    for kind in ("missing", "file"):
        _assert_dropin_directory_target_conflict(kind)
    _assert_dropin_directory_target_conflict("identity", receipt_failure=True)


@unittest.skipIf(os.name != "posix", "POSIX fixed-directory metadata, links and safe parents")
def test_gateway_dropin_directory_target_guard_rejects_metadata_links_and_parent_drift() -> None:
    for kind in ("mode", "symlink", "parent_mode"):
        evidence = _assert_dropin_directory_target_conflict(kind)
        if kind == "mode": assert evidence["dropin_directory_metadata"][2] == 0o700
        if kind == "symlink": assert evidence["dropin_directory_is_symlink"]


def test_gateway_dropin_directory_target_guard_actual_forward_valid_and_untouched() -> None:
    for case, prior_file in (("", True), ("missing_dropin", False), ("nonempty_dropin", False)):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_target_guard", directory_case=case,
            prior_dropin=prior_file, second_source=True, evidence=evidence,
        )
        assert completed.returncode == 17, completed.stderr
        assert len(evidence["dropin_dir_forward_calls"]) == 1
        receipt = evidence["rollback"]
        version = receipt["dropin_directory_write_state"]
        assert version["state"] == "INSTALLED" and len(version["installed_version_sha256"]) == 64
        assert version["candidate_metadata"] == "0:0:755"
        if case == "nonempty_dropin":
            assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
            assert evidence["retained_unrelated_files"] == [b"preserve unrelated bytes\n"]
        else:
            assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
            assert receipt["dropin_directory_result_observation"] == (
                "MATCHED_PREPARED_PRESENT" if not case else "MATCHED_PREPARED_ABSENCE")
            assert evidence["second_target"] == b"second previous\n"
            if prior_file: assert evidence["dropin_bytes"] == b"previous hardening\n"
    evidence = {}
    completed, _, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="dropin_directory_target_guard", dropin_dir_forward_case="untouched", evidence=evidence,
    )
    assert completed.returncode == 17 and not evidence["dropin_dir_forward_calls"]
    assert not evidence["dropin_forward_calls"] and evidence["dropin_bytes"] == b"candidate hardening\n"
    assert ":dropin_dir" not in evidence["operation_calls"] and "rm:dropin\n" not in evidence["operation_calls"]
    assert evidence["rollback"]["dropin_directory_result_observation"] == "UNCHECKED_UNTOUCHED"
    assert evidence["rollback"]["dropin_result_observation"] == "UNCHECKED_UNTOUCHED"


def test_gateway_dropin_directory_target_guard_partial_write_or_readback_refuses_child_work() -> None:
    for case, trigger in (("partial", 31), ("wrong_type", 1), ("capture_failed", 29)):
        evidence: dict = {}
        completed, source, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_target_guard", dropin_dir_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == trigger, (case, completed.stderr)
        assert source == b"candidate source\n" and evidence["backup_exists"]
        assert not evidence["dropin_forward_calls"] and not evidence["run_forward_calls"]
        assert ":dropin_dir" not in evidence["operation_calls"] and "rm:dropin\n" not in evidence["operation_calls"]
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        receipt = evidence["rollback"]
        assert receipt["dropin_directory_write_state"]["state"] == "WRITE_PENDING"
        assert receipt["dropin_directory_write_state"]["installed_version_sha256"] is None
        assert receipt["failed_restoration_operation"] == dict(operation="dropin_directory_target_state", target="service_drop_in_directory", exit_code=14)


def test_gateway_dropin_directory_target_guard_strict_queries_and_inconsistent_state() -> None:
    for query in ("failed", "extra_line", "extra_newline", "no_newline", "extra_argument", "supplied_path", "invalid_mode"):
        evidence: dict = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_target_guard", dropin_dir_query_case=query, evidence=evidence,
        )
        assert completed.returncode == 17 and "rm:dropin\n" not in evidence["operation_calls"], (query, completed.stderr)
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n"
        assert evidence["rollback"]["failed_restoration_operation"]["operation"] == "dropin_directory_target_state"
    for case in ("unknown_state", "invalid_state", "missing_version", "invalid_version", "untouched_version", "untouched_child_installed"):
        evidence = {}
        completed, _, _ = _run_gateway_rollback_guard(
            _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
            recovery_case="dropin_directory_target_guard", dropin_dir_forward_case=case, evidence=evidence,
        )
        assert completed.returncode == 17 and "rm:dropin\n" not in evidence["operation_calls"], completed.stderr
        assert evidence["service_calls"] == "SYSTEMCTL:stop\n" and evidence["backup_exists"]
        assert "dropin_directory_target_state failed" in completed.stderr
        if case in {"invalid_state", "invalid_version"}:
            assert "receipt persistence failed" in completed.stderr and "rollback" not in evidence


def test_gateway_dropin_directory_target_guard_allows_child_changes_and_pins_before_write() -> None:
    evidence: dict = {}
    completed, _, _ = _run_gateway_rollback_guard(
        _gateway_post_mutation_guards(_repair_script())[0], predicate_passes=False,
        recovery_case="dropin_directory_target_guard", prior_dropin=True,
        dropin_dir_drift="children", evidence=evidence,
    )
    assert completed.returncode == 17 and evidence["dropin_dir_drift_applied"], completed.stderr
    assert evidence["service_calls"].endswith("SYSTEMCTL:start\n")
    script = _repair_script()
    assert script.index('DROPIN_DIR_CANDIDATE_METADATA="0:0:755"') < script.index('RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"')
    install = _bash_function(script, "install_gateway_dropin_directory")
    assert install.index("DROPIN_DIR_WRITE_STATE=WRITE_PENDING") < install.index("install -d -o 0 -g 0 -m 0755")
    assert install.index("capture_dropin_directory_target_version") < install.index("DROPIN_DIR_WRITE_STATE=INSTALLED")
    rollback = _bash_function(script, "rollback")
    assert rollback.index("dropin_directory_target_state") < rollback.index("dropin_target_state service_drop_in")
    assert 'install_gateway_dropin_directory\ninstall_gateway_dropin\n' in script
