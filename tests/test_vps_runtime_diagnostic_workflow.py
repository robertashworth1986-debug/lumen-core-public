from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "vps-storage-diagnostic.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_runtime_diagnostic_is_read_only_and_host_key_strict() -> None:
    text = _workflow_text()

    assert "StrictHostKeyChecking=yes" in text
    assert "StrictHostKeyChecking=no" not in text
    assert "systemctl restart" not in text
    assert "systemctl start" not in text
    assert "systemctl stop" not in text
    assert "systemctl enable" not in text
    assert "systemctl disable" not in text
    assert "rm -" not in text
    assert "truncate" not in text
    assert "journalctl --vacuum" not in text


def test_runtime_diagnostic_covers_gateway_failure_chain() -> None:
    text = _workflow_text()

    required = (
        "public_nginx_health",
        "public_gateway_health",
        "public_gateway_snapshot",
        "loopback_gateway_via_nginx",
        "loopback_gateway_direct",
        "http://127.0.0.1:8787/health",
        "show_unit \"$unit\"",
        "luma-gateway",
        "ExecMainStatus",
        "NRestarts",
        "RestartUSec",
        "StartLimitBurst",
        "ss -ltnH",
        "nginx -t",
        "nginx -T",
    )
    for marker in required:
        assert marker in text, marker


def test_runtime_diagnostic_does_not_publish_bodies_or_unfiltered_logs() -> None:
    text = _workflow_text()

    assert "--output /dev/null" in text
    assert "journalctl -u luma-gateway -n" not in text
    assert "journalctl -u luma-gateway -f" not in text
    assert 'printf "%s\\n" "$journal_window" \\' in text
    assert '| grep -E "ModuleNotFoundError|ImportError|' in text
    assert "cat /var/log" not in text
    assert "EnvironmentFile" not in text
    assert "cat /etc/nginx" not in text
    assert "allowlisted directives only" in text


def test_gateway_lock_diagnostic_checks_identity_without_exposing_cmdline() -> None:
    text = _workflow_text()

    assert "gateway singleton-lock identity" in text
    assert "gateway_main_pid=$(systemctl show luma-gateway" in text
    assert "gateway_lock=/opt/lumencore/run/luma_experience_gateway.lock" in text
    assert "lock_pid_matches_systemd_main" in text
    assert 'show_process_identity gateway_lock_owner "$gateway_lock_pid"' in text
    assert 'expected_marker="luma_experience_gateway:app"' not in text
    assert "echo \"$cmdline\"" not in text
    assert "cat \"$gateway_lock\"" not in text


def test_runtime_failure_signatures_are_allowlisted_and_redacted() -> None:
    text = _workflow_text()

    assert "gateway executable and source preflight" in text
    assert "/opt/lumencore/.venv/bin/python --version" in text
    assert 'importlib.util.find_spec(\\"uvicorn\\")' in text
    assert "runtime allowlisted failure signatures (redacted)" in text
    assert 'show_allowlisted_failure_signatures luma-gateway "2 minutes ago" 80' in text
    assert 'show_allowlisted_failure_signatures luma-paper-ticker "5 minutes ago" 80' in text
    assert 'show_allowlisted_failure_signatures luma-symbol-awareness "5 minutes ago" 80' in text
    assert 'journalctl -u "$unit" --since "$since"' in text
    assert "luma-gateway|luma-paper-ticker|luma-symbol-awareness" in text
    assert "refused_unapproved_journal_unit" in text
    assert 'grep -E "ModuleNotFoundError|ImportError|' in text
    assert "[REDACTED]" in text
    assert "cut -c1-400" in text
    assert 'tail -n "$max_lines"' in text
    assert "journalctl -u luma-gateway -n" not in text
    assert "journalctl -u luma-paper-ticker -n" not in text
    assert "journalctl -u luma-symbol-awareness -n" not in text


def test_runtime_diagnostic_preserves_capacity_evidence() -> None:
    text = _workflow_text()

    assert "df -hP / /opt /var /home /tmp" in text
    assert "df -iP / /opt /var /home /tmp" in text
    assert "journalctl --disk-usage" in text
    assert "du -x -k -d2 /var /opt /home/opc /tmp" in text
