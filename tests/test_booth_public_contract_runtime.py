from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
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
    assert "singleton lock owner is still alive; refusing removal" in script
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
        'install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 -- "$RUN_DIR"',
        'systemctl daemon-reload',
        'effective gateway service identity is not lumencore:lumencore',
        'gateway singleton lock did not bind to the systemd main PID',
        'gateway singleton lock identity is not bounded',
        'cp -a -- "$BACKUP_DIR/service-drop-in.before" "$SERVICE_DROP_IN"',
        'chown --no-dereference "$prior_drop_in_uid:$prior_drop_in_gid" "$SERVICE_DROP_IN_DIR"',
        'chown --no-dereference "$prior_run_uid:$prior_run_gid" "$RUN_DIR"',
        'if [[ "$SERVICE_WAS_ACTIVE" == true ]]',
        "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK",
    ):
        assert marker in script
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


def _run_gateway_rollback_guard(
    guard: str, *, predicate_passes: bool, copy_fails: bool = False,
    signal_during_copy: bool = False,
    recovery_case: str | None = None, evidence: dict | None = None,
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
        for name, value in {
            "service-drop-in.state": "missing\n",
            "service-drop-in-dir.state": "present\n",
            "service-drop-in-dir.metadata": "1000 1000 755\n",
            "run-dir.state": "present\n",
            "run-dir.metadata": "1000 1000 750\n",
            "service.state": "service_was_active=true\n",
        }.items():
            (root / "backup" / name).write_text(value, encoding="utf-8")
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
record_recovery_evidence() { :; }
chown() { printf 'chown\n' >> "$PWD/restore.calls"; }
chmod() { printf 'chmod\n' >> "$PWD/restore.calls"; }
rm() { printf 'rm\n' >> "$PWD/restore.calls"; command rm "$@"; }
cp() {
  printf 'cp\n' >> "$PWD/restore.calls"
  if [[ "$SIGNAL_DURING_COPY" == true ]]; then
    kill -TERM "$BASHPID"
    printf 'FIXTURE_TERM_SENT\n' >&2
  fi
  if [[ "$COPY_FAILS" == true ]]; then
    printf 'FIXTURE_COPY_FAILURE\n' >&2
    return 9
  fi
  command cp "$@"
}
cleanup() {
  if [[ -f "$PWD/systemctl.calls" ]]; then cat "$PWD/systemctl.calls"; fi
  printf 'CLEANUP\n'
}
trap cleanup EXIT
'''
        harness += rollback_source + "\n"
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
            if recovery_case in {"source_binding", "bundle_binding", "hardening_binding"}:
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
        harness += error_trap + "\n" + guard
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
            SIGNAL_DURING_COPY=str(signal_during_copy).lower(),
            TEST_PYTHON=Path(sys.executable).as_posix(),
        )
        (root / "fixture.sh").write_text(harness, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [_gateway_rollback_test_bash(), "fixture.sh"],
            cwd=root, env=env, capture_output=True, text=True, timeout=20,
            check=False,
        )
        target = root / "target/entry.py"
        if evidence is not None:
            backup_path = root / "backup/existing/entry.py"
            evidence["backup"] = backup_path.read_bytes() if backup_path.is_file() else None
            evidence["backup_exists"] = (root / "backup").is_dir()
            evidence["originally_missing_target_exists"] = (root / "target/absent.py").exists()
            evidence["outside_refusal_written"] = (root / "outside-backup/rollback_refused.json").exists()
            calls = root / "systemctl.calls"
            evidence["service_calls"] = calls.read_text() if calls.exists() else ""
            calls = root / "restore.calls"
            evidence["restore_calls"] = calls.read_text() if calls.exists() else ""
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
            target.read_bytes() if target.exists() else None,
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


def test_gateway_rollback_failure_keeps_original_code_without_reentry() -> None:
    guard = _gateway_post_mutation_guards(_repair_script())[0]
    completed, restored, dropin_exists = _run_gateway_rollback_guard(
        guard, predicate_passes=False, copy_fails=True
    )
    assert completed.returncode == 17, completed.stderr
    assert completed.stderr.count("Rolling back the complete gateway") == 1
    assert completed.stderr.count("FIXTURE_COPY_FAILURE") == 1
    assert completed.stdout.count("SYSTEMCTL:stop\n") == 1
    assert completed.stdout.count("SYSTEMCTL:start\n") == 1
    assert completed.stdout.endswith("CLEANUP\n")
    # A failed restore remains a real failure, never a claim of recovery success.
    assert restored is None
    assert not dropin_exists


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
    assert evidence["rollback"]["status"] == "ROLLBACK_ATTEMPTED_UNVERIFIED"
    assert evidence["rollback"]["trigger_exit_code"] == 17
    assert evidence["rollback"]["restoration_verified"] is False
    assert evidence["rollback"]["manifest_sha256"] == evidence["prepared_sha256"]
    stored = next(item for item in evidence["prepared"]["files"] if item["path"] == "existing/entry.py")
    assert stored["sha256"] == hashlib.sha256(evidence["backup"]).hexdigest()
    assert "previous source" not in json.dumps(evidence["prepared"])
    assert "evidence retained" in completed.stdout
    if os.name == "posix":
        assert evidence["prepared_mode"] == evidence["rollback_mode"] == 0o600


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
