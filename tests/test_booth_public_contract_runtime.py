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
        'chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$SERVICE_DROP_IN_DIR"',
        'chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$RUN_DIR"',
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
    service_failure: str = "", service_exit_code: int = 9,
    service_was_active: bool = True, real_timeout_mode: str = "",
    restore_fault: str = "", second_source: bool = False, prior_dropin: bool = False,
    directory_case: str = "", metadata_case: str = "", real_lock_case: str = "",
    source_drift: str = "", drift_boundary: str = "stop", source_query_case: str = "",
    target_drift: str = "", target_boundary: str = "stop", forward_case: str = "",
    target_query_case: str = "", target_relative: str = "",
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
            "service.state": f"service_was_active={str(service_was_active).lower()}\n",
        }.items():
            (root / "backup" / name).write_text(value, encoding="utf-8")
        if second_source:
            (root / "target/second.py").write_bytes(b"second candidate\n")
            (root / "backup/existing/second.py").write_bytes(b"second previous\n")
        if prior_dropin:
            (root / "backup/service-drop-in.state").write_text("present\n")
            (root / "backup/service-drop-in.before").write_bytes(b"previous hardening\n")
        if directory_case:
            family = "service-drop-in-dir" if directory_case.endswith("dropin") else "run-dir"
            folder = root / ("dropins" if directory_case.endswith("dropin") else "run")
            (root / f"backup/{family}.state").write_text("missing\n")
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
declare -A SOURCE_WRITE_STATES=() SOURCE_CANDIDATE_SHA=() SOURCE_TARGET_VERSION=()
python3() { "$TEST_PYTHON" "$@"; }
FIXTURE_FORWARD=false
RECOVERY_TIMEOUT_BIN=fixture_timeout
fixture_timeout() {
  [[ "$1 $2 $3" == '--signal=TERM --kill-after=5s 60s' ]] || return 99
  shift 3
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
record_recovery_evidence() { if [[ "$1" == source_state ]]; then printf 'present\n'; fi; }
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
chmod() { printf 'chmod\n' >> "$PWD/restore.calls"; fixture_operation chmod "${@: -1}"; }
rm() {
  printf 'rm\n' >> "$PWD/restore.calls"
  fixture_operation rm "${@: -1}" || return $?
  command rm "$@" || return $?
  if [[ "${@: -1}" == "$TARGET_ROOT/entry.py" ]]; then fixture_source_drift after_first_remove || return $?; fixture_target_drift after_first_remove || return $?; fi
}
install() {
  if [[ "$FIXTURE_FORWARD" == true ]]; then
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
rmdir() { fixture_operation rmdir "${@: -1}" || return $?; command rmdir "$@"; }
tr() { if [[ "$REAL_LOCK_CASE" == tr_failure ]]; then return 27; fi; command tr "$@"; }
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
  command cp "$@" || return $?
  if [[ "${@: -1}" == "$TARGET_ROOT/entry.py" ]]; then fixture_source_drift after_first_copy || return $?; fixture_target_drift after_first_copy || return $?; fi
}
cleanup() {
  if [[ -f "$PWD/systemctl.calls" ]]; then cat "$PWD/systemctl.calls"; fi
  printf 'CLEANUP\n'
}
trap cleanup EXIT
'''
        bounded = _bash_function(script, "bounded_recovery_systemctl")
        if real_timeout_mode:
            # Only the extracted disposable fixture gets a shorter fixed policy;
            # production has no caller-controlled duration or environment escape.
            assert bounded.count("--kill-after=5s 60s") == 1
            bounded = bounded.replace("--kill-after=5s 60s", "--kill-after=0.2s 0.2s")
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
            harness += 'export PATH="/usr/bin:$PATH"\nRECOVERY_TIMEOUT_BIN="$(type -P timeout)"\n'
            harness += 'export PATH="$PWD/bin:$PATH"\n'
        harness += bounded + "\n" + _bash_function(script, "finish_rollback") + "\n"
        for name in ("checked_restore_step", "read_recovery_state", "read_recovery_source_state", "read_recovery_metadata", "remove_recovery_directory",
                     "source_target_version", "capture_source_target_version", "install_gateway_source", "read_recovery_target_state", "require_recovery_target_absent"):
            harness += _bash_function(script, name) + "\n"
        if real_lock_case:
            harness += _bash_function(script, "remove_verified_dead_lock") + "\n"
            if real_lock_case == "live":
                harness += 'printf "%s\\n" "$BASHPID" > "$LOCK_FILE"\n'
            elif real_lock_case == "invalid":
                harness += 'printf "invalid\\n" > "$LOCK_FILE"\n'
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
            SIGNAL_DURING_COPY=str(signal_during_copy).lower(),
            TEST_PYTHON=Path(sys.executable).as_posix(),
            SERVICE_FAILURE=service_failure,
            SERVICE_EXIT_CODE=str(service_exit_code),
            REAL_TIMEOUT_MODE=real_timeout_mode,
            RESTORE_FAULT=restore_fault, REAL_LOCK_CASE=real_lock_case,
            SOURCE_DRIFT=source_drift, DRIFT_BOUNDARY=drift_boundary, SOURCE_QUERY_CASE=source_query_case,
            TARGET_DRIFT=target_drift, TARGET_BOUNDARY=target_boundary, FORWARD_CASE=forward_case,
            TARGET_QUERY_CASE=target_query_case,
            TARGET_RELATIVE=target_relative,
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
            evidence["command_entered"] = (root / "command-entered").exists()
            backup_path = root / "backup/existing/entry.py"
            evidence["backup"] = backup_path.read_bytes() if backup_path.is_file() else None
            evidence["backup_exists"] = (root / "backup").is_dir()
            evidence["second_target"] = (root / "target/second.py").read_bytes() if (root / "target/second.py").is_file() else None
            evidence["target_drift_applied"] = (root / "target-drift-applied").exists()
            evidence["target_is_directory"] = target.is_dir()
            evidence["target_is_symlink"] = target.is_symlink()
            evidence["forward_calls"] = (root / "forward.calls").read_text().splitlines() if (root / "forward.calls").exists() else []
            evidence["second_backup"] = (root / "backup/existing/second.py").read_bytes() if (root / "backup/existing/second.py").is_file() else None
            evidence["source_drift_applied"] = (root / "source-drift-applied").exists()
            evidence["source_state_receipt_exists"] = (root / "backup/source_state.json").exists()
            evidence["retained_unrelated_files"] = [p.read_bytes() for p in root.glob("*/unrelated-retained")]
            evidence["lock_exists"] = (root / "run/fixture.lock").exists()
            evidence["dropin_directory_exists"] = (root / "dropins").exists()
            dropin_path = root / "dropins/hardening.conf"
            evidence["dropin_bytes"] = dropin_path.read_bytes() if dropin_path.is_file() else None
            evidence["run_directory_exists"] = (root / "run").exists()
            evidence["originally_missing_target_exists"] = (root / "target/absent.py").exists()
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
    assert script.index('record_recovery_evidence verify "$rc"') < script.index('if ! bounded_recovery_systemctl stop;')


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


def test_gateway_inner_lock_errors_cannot_be_hidden_by_successful_echo() -> None:
    for lock_case, fault, expected_code in (
        ("dead", "rm:lock", 23), ("tr_failure", "", 27), ("invalid", "", 14), ("live", "", 14),
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
        assert evidence["rollback"]["failed_restoration_operation"] == dict(
            operation="dead_lock", target="gateway_lock", exit_code=expected_code)


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
    assert "restoration operation source_state failed" in completed.stderr
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
