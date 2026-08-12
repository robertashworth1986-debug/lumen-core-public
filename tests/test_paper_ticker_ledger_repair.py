from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "REPAIR_PAPER_TICKER_LEDGER_ON_VPS.sh"
REPAIR_WORKFLOW = ROOT / ".github" / "workflows" / "repair-paper-ticker-ledger.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "paper-ticker-recovery-ci.yml"
DIAGNOSTIC_WORKFLOW = ROOT / ".github" / "workflows" / "vps-storage-diagnostic.yml"
DEPLOY = ROOT / "code" / "deploy" / "deploy_vps.sh"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_repair_script_is_exact_path_and_inspect_only_by_default() -> None:
    text = _read(SCRIPT)

    assert 'LEDGER="${EXECUTION_OUTPUT}/multi_exchange_paper_ticker_ledger.jsonl"' in text
    assert 'APPLY=false' in text
    assert 'if [[ "$APPLY" != true ]]' in text
    assert '[[ "$LEDGER_RESOLVED" == "$LEDGER" ]]' in text
    assert '[[ -f "$LEDGER" ]]' in text
    assert '[[ "$(stat -c \'%h\' "$LEDGER")" == "1" ]]' in text
    assert "LUMENCORE_PAPER_LEDGER_PATH" not in text
    assert "LUMENCORE_PAPER_SERVICE" not in text


def test_apply_requires_exact_commit_script_hash_incident_and_human_unlock() -> None:
    text = _read(SCRIPT)

    required = (
        '[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]',
        '[[ "$EXPECTED_SCRIPT_SHA" =~ ^[0-9a-f]{64}$ && "$EXPECTED_SCRIPT_SHA" == "$SCRIPT_SHA" ]]',
        '[[ "$EXPECTED_LEDGER_SHA" =~ ^[0-9a-f]{64}$ ]]',
        '[[ "$EXPECTED_LEDGER_OWNER" == "opc"',
        '[[ "$HUMAN_UNLOCK_FILE" =~ ^/tmp/lumencore-paper-ticker-repair-',
        '[[ "$(stat -c \'%U:%a\' "$HUMAN_UNLOCK_FILE")" == "opc:600" ]]',
        '[[ ${#human_unlock_token} -ge 32 ]]',
        '[[ "${EUID}" -eq 0 ]]',
        '[[ "$initial_sha" == "$EXPECTED_LEDGER_SHA" ]]',
        '[[ "$initial_owner" == "$EXPECTED_LEDGER_OWNER"',
    )
    for marker in required:
        assert marker in text, marker


def test_repair_preserves_bytes_and_changes_only_exact_metadata_and_dropin() -> None:
    text = _read(SCRIPT)

    assert 'systemctl stop "$SERVICE"' in text
    assert 'chown --no-dereference "$SERVICE_USER:$SERVICE_GROUP" "$LEDGER"' in text
    assert 'chmod 0640 "$LEDGER"' in text
    assert '[[ "$(sha256sum "$LEDGER" | awk' in text
    assert 'DROPIN_FILE="${DROPIN_DIR}/10-restart-bounds.conf"' in text
    assert "StartLimitIntervalSec=300" in text
    assert "StartLimitBurst=5" in text
    assert "Restart=on-failure" in text
    assert "UMask=0027" in text
    assert 'systemctl start "$SERVICE"' in text
    assert 'restart_count_before=' in text
    assert '[[ "$restart_count_before" == "$restart_count_after" ]]' in text
    assert "chown -R" not in text
    assert "chmod -R" not in text
    assert "systemctl restart" not in text

    metadata_marker = text.index("METADATA_CHANGED=true", text.index('systemctl stop "$SERVICE"'))
    chown_marker = text.index(
        'chown --no-dereference "$SERVICE_USER:$SERVICE_GROUP" "$LEDGER"',
        metadata_marker,
    )
    chmod_marker = text.index('chmod 0640 "$LEDGER"', chown_marker)
    assert metadata_marker < chown_marker < chmod_marker

    dropin_marker = text.index("DROPIN_CHANGED=true", chmod_marker)
    install_marker = text.index(
        'install -o root -g root -m 0644 -- "$dropin_stage" "$DROPIN_FILE"',
        dropin_marker,
    )
    assert dropin_marker < install_marker


def test_repair_rolls_back_exact_metadata_and_restart_policy() -> None:
    text = _read(SCRIPT)

    assert "rollback()" in text
    assert 'chown --no-dereference "$initial_uid:$initial_gid" "$LEDGER"' in text
    assert 'chmod "$initial_mode" "$LEDGER"' in text
    assert 'install -D -o root -g root -m 0644 -- "$BACKUP_DIR/restart-bounds.conf" "$DROPIN_FILE"' in text
    assert 'rm -f -- "$DROPIN_FILE"' in text
    assert 'rmdir -- "$DROPIN_DIR"' in text
    assert '[[ "$BACKUP_DIR" =~ ^/tmp/lumencore-paper-ticker-rollback\\.[A-Za-z0-9]+$ ]]' in text
    assert 'rm -rf -- "$BACKUP_DIR"' in text
    assert "rm -rf /opt" not in text
    assert "rm -rf $STACK_ROOT" not in text


def test_service_identity_and_paper_only_preflight_are_required() -> None:
    text = _read(SCRIPT)

    assert 'SERVICE="luma-paper-ticker"' in text
    assert '[[ "$service_user" == "$SERVICE_USER" ]]' in text
    assert '[[ "$service_group" == "$SERVICE_GROUP" ]]' in text
    assert '[[ "$working_directory" == "/opt/lumencore/code" ]]' in text
    assert '/opt/lumencore/code/multi_exchange_paper_ticker.py' in text
    assert '--profile apex' in text
    assert '--seed-capital 250000' in text
    assert '/opt/lumencore/code/ops/assert_runtime_safety.py' in text


def test_repair_workflow_is_manual_current_main_and_secret_gated() -> None:
    text = _read(REPAIR_WORKFLOW)

    assert "workflow_dispatch:" in text
    assert "REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP" in text
    assert '[[ "$APPROVAL" == "REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP" ]]' in text
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in text
    assert '[[ "$(git rev-parse origin/main)" == "$RELEASE_COMMIT" ]]' in text
    assert "secrets.LUMA_HUMAN_UNLOCK_TOKEN" in text
    assert "Repository secret LUMA_HUMAN_UNLOCK_TOKEN is missing" in text
    assert "no VPS change was attempted" in text
    assert "LUMENCORE_HUMAN_UNLOCK_FILE='$REMOTE_STAGE/human-unlock'" in text
    assert 'LUMA_HUMAN_UNLOCK_TOKEN="$(cat' not in text
    assert "StrictHostKeyChecking=yes" in text
    assert "persist-credentials: false" in text
    assert "environment:\n      name: production" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text
    assert "\n  push:" not in text
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in text
    assert "shimataro/ssh-key-action@87a8f067114a8ce263df83e9ed5c849953548bc3 # v2.8.1" in text


def test_repair_workflow_binds_observed_incident_and_exact_script() -> None:
    text = _read(REPAIR_WORKFLOW)

    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in text
    assert "EXPECTED_LEDGER_OWNER: opc" in text
    assert "EXPECTED_LEDGER_GROUP: opc" in text
    assert "EXPECTED_LEDGER_MODE: '644'" in text
    assert "repair_script_sha256" in text
    assert "LUMENCORE_EXPECTED_PAPER_REPAIR_SCRIPT_SHA256='$SCRIPT_SHA'" in text
    assert "LUMENCORE_EXPECTED_PAPER_LEDGER_SHA256='$EXPECTED_LEDGER_SHA'" in text
    assert "lumencore:lumencore:640:1" in text
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in text


def test_future_deploy_prevents_recurrence_and_bounds_restart_storms() -> None:
    text = _read(DEPLOY)

    assert 'PAPER_TICKER_LEDGER="$STACK_ROOT/out/execution/multi_exchange_paper_ticker_ledger.jsonl"' in text
    assert 'chown --no-dereference "$SERVICE_USER:$SERVICE_GROUP" "$PAPER_TICKER_LEDGER"' in text
    assert 'chmod 0640 "$PAPER_TICKER_LEDGER"' in text
    assert 'install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 /dev/null "$PAPER_TICKER_LEDGER"' in text

    paper_block = text.split("Description=Luma Multi-Exchange Paper Ticker", 1)[1].split("EOF", 1)[0]
    awareness_block = text.split("Description=Luma Full-Universe Symbol Awareness (Shadow Only)", 1)[1].split("EOF", 1)[0]
    for block in (paper_block, awareness_block):
        assert "StartLimitIntervalSec=300" in block
        assert "StartLimitBurst=5" in block
        assert "Restart=on-failure" in block
        assert "Restart=always" not in block
        assert "UMask=0027" in block


def test_workflows_parse_and_recovery_gate_covers_all_owned_paths() -> None:
    for path in (REPAIR_WORKFLOW, CI_WORKFLOW, DIAGNOSTIC_WORKFLOW):
        payload = yaml.safe_load(_read(path))
        assert isinstance(payload, dict)
        assert "jobs" in payload

    ci_text = _read(CI_WORKFLOW)
    for relative in (
        ".github/workflows/repair-paper-ticker-ledger.yml",
        "code/deploy/deploy_vps.sh",
        "code/ops/REPAIR_PAPER_TICKER_LEDGER_ON_VPS.sh",
        "tests/test_paper_ticker_ledger_repair.py",
        "tests/test_vps_runtime_diagnostic_workflow.py",
    ):
        assert relative in ci_text
    assert "bash -n code/ops/REPAIR_PAPER_TICKER_LEDGER_ON_VPS.sh" in ci_text
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in ci_text
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0" in ci_text


def test_diagnostic_uses_current_artifact_runtime() -> None:
    text = _read(DIAGNOSTIC_WORKFLOW)
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in text
    assert "actions/upload-artifact@v4" not in text
    assert "shimataro/ssh-key-action@87a8f067114a8ce263df83e9ed5c849953548bc3 # v2.8.1" in text
