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


def test_pull_request_validation_cannot_enter_the_production_diagnostic_job() -> None:
    text = _workflow_text()

    assert "pull_request:" in text
    assert "- 'tests/test_vps_runtime_diagnostic_workflow.py'" in text
    assert "if: github.event_name != 'pull_request'" in text
    assert "needs: validate" in text
    assert "permissions:\n      contents: read\n      statuses: write" in text
    assert "persist-credentials: false" in text
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in text
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in text


def test_runtime_diagnostic_covers_gateway_failure_chain() -> None:
    text = _workflow_text()

    required = (
        "public_nginx_health",
        "public_gateway_health",
        "public_gateway_snapshot",
        "loopback_gateway_via_nginx",
        "loopback_gateway_direct",
        "http://127.0.0.1:8787/health",
        "probe_loopback_tls loopback_nginx_health /nginx-health",
        "probe_loopback_tls loopback_gateway_via_nginx /health",
        '--resolve "lumen-core.ai:443:127.0.0.1"',
        "--noproxy lumen-core.ai",
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

    assert "http://127.0.0.1/nginx-health" not in text
    assert "http://127.0.0.1/health" not in text
    assert "--insecure" not in text
    assert "--no-check-certificate" not in text


def test_loopback_nginx_probe_preserves_hostname_and_tls_identity() -> None:
    text = _workflow_text()
    function = text.split("probe_loopback_tls() {", 1)[1].split("show_unit() {", 1)[0]

    assert '--resolve "lumen-core.ai:443:127.0.0.1"' in function
    assert '"https://lumen-core.ai$path"' in function
    assert "--noproxy lumen-core.ai" in function
    assert "--output /dev/null" in function
    assert "--max-redirs 0" in function
    assert "--location" not in function
    assert "--insecure" not in function


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


def test_paper_ticker_path_access_is_metadata_only_and_allowlisted() -> None:
    text = _workflow_text()

    assert "paper ticker output-path access (metadata only)" in text
    assert "show_allowlisted_path_access stack_root /opt/lumencore" in text
    assert "show_allowlisted_path_access output_root /opt/lumencore/out" in text
    assert "show_allowlisted_path_access execution_output /opt/lumencore/out/execution" in text
    assert (
        "show_allowlisted_path_access paper_ticker_ledger "
        "/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl"
    ) in text
    assert "refused_unapproved_access_path" in text
    assert 'stat --printf="exists=true type=%F mode=%a owner=%U group=%G bytes=%s modified=%y\\n"' in text
    assert 'sudo -n -u lumencore test "-$permission" "$path"' in text
    assert "cat /opt/lumencore/out/execution" not in text
    assert "find /opt/lumencore/out/execution" not in text
    assert "chmod" not in text
    assert "chown" not in text


def test_runtime_diagnostic_preserves_capacity_evidence() -> None:
    text = _workflow_text()

    assert "df -hP / /opt /var /home /tmp" in text
    assert "df -iP / /opt /var /home /tmp" in text
    assert "journalctl --disk-usage" in text
    assert "du -x -k -d2 /var /opt /home/opc /tmp" in text


def test_gateway_closure_comparison_is_exact_commit_and_read_only() -> None:
    text = _workflow_text()

    assert "Compare the approved gateway closure with the VPS" in text
    assert "ref: ${{ github.sha }}" in text
    assert "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh" in text
    assert '--print-files' in text
    assert '--bundle-sha' in text
    assert '[[ "${#files[@]}" -eq 20 ]]' in text
    assert "approved_gateway_bundle_sha256" in text
    assert "expected_file_count" in text
    assert "closure_file status=match" in text
    assert "closure_file status=mismatch" in text
    assert "closure_file status=missing" in text
    assert "closure_file status=symbolic" in text
    assert "closure_file status=unreadable" in text
    assert "closure_match_count" in text
    assert "closure_mismatch_count" in text
    assert "closure_missing_count" in text
    assert "closure_symbolic_count" in text
    assert "closure_unreadable_count" in text
    assert 'target_root=/opt/lumencore/code' in text
    assert 'resolved=$(realpath -m -- "$target")' in text
    assert '[[ "$resolved" == "$target_root/"* ]]' in text
    assert "scp " not in text
