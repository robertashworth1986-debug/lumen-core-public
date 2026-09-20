"""Regressions for legacy status files that must not confer operating authority."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import subprocess
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = spec_from_file_location("legacy_status_" + name, ROOT / "dashboard" / (name + ".py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def compliance(monkeypatch, tmp_path):
    subject = load("update_compliance_progress")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subject, "ROOT", tmp_path, raising=False)
    monkeypatch.setattr(subject, "PROGRESS_PATH", tmp_path / "dashboard/compliance_mvp_progress.json")
    monkeypatch.setattr(sys, "argv", ["update_compliance_progress.py"])
    (tmp_path / "dashboard").mkdir()
    return subject


def test_a_related_status_file_cannot_establish_functional_completion(compliance, tmp_path):
    (tmp_path / "dashboard/api_key_status.txt").write_text("Example inventory only", encoding="utf-8")
    assert compliance.check_complete("API key management UI") is False


def test_a_directory_named_like_a_component_cannot_establish_completion(compliance, tmp_path):
    (tmp_path / "dashboard/kyc_module.py").mkdir()
    assert compliance.check_complete("KYC/AML integration") is False


def test_generated_inventory_does_not_publish_compliance_completion(compliance, tmp_path):
    (tmp_path / "dashboard/legal.html").write_text("<h1>Draft</h1>", encoding="utf-8")
    compliance.main()
    items = json.loads(compliance.PROGRESS_PATH.read_text(encoding="utf-8"))
    assert len(items) == 9
    assert all(row["status"] != "complete" for row in items)


def test_modification_time_is_timezone_aware(tmp_path):
    subject = load("orchestrator_watchdog")
    path = tmp_path / "stdout.log"
    path.write_text("activity", encoding="utf-8")
    value = subject.get_last_mod_time(path)
    assert value.tzinfo is not None
    assert value.utcoffset().total_seconds() == 0


def test_quiet_error_logs_are_not_declared_stalled(monkeypatch, tmp_path):
    subject = load("orchestrator_watchdog")
    paths = [tmp_path / name for name in ("orchestrator_run_stdout.log", "orchestrator_run_stderr.log", "orchestrator_exceptions.log")]
    now = datetime.now(timezone.utc).timestamp()
    for index, path in enumerate(paths):
        path.write_text("activity" if index == 0 else "", encoding="utf-8")
        stamp = now if index == 0 else now - 86400
        os.utime(path, (stamp, stamp))
    output = tmp_path / "watchdog.txt"
    monkeypatch.setattr(subject, "LOG_PATHS", paths)
    monkeypatch.setattr(subject, "WATCHDOG_STATUS", output)
    monkeypatch.setattr(sys, "argv", ["orchestrator_watchdog.py"])
    subject.main()
    text = output.read_text(encoding="utf-8")
    assert "Stall detected in orchestrator_run_stderr.log" not in text
    assert "Stall detected in orchestrator_exceptions.log" not in text


def test_legacy_restart_cannot_launch_full_stack_or_log_unverified_success(monkeypatch, tmp_path):
    subject = load("self_heal_orchestrator")
    calls = []
    monkeypatch.setattr(os, "system", lambda command: calls.append(command) or 1)
    monkeypatch.setattr(subject, "RESTART_LOG", tmp_path / "restart.txt", raising=False)
    with pytest.raises(RuntimeError):
        subject.restart_orchestrator()
    assert calls == []
    assert not (tmp_path / "restart.txt").exists()


def test_alert_reader_cannot_treat_legacy_complete_as_verified(monkeypatch, tmp_path):
    subject = load("send_stack_alerts")
    path = tmp_path / "compliance.json"
    path.write_text(json.dumps([{"item": "Legal/terms of service", "status": "complete"}]), encoding="utf-8")
    monkeypatch.setattr(subject, "COMPLIANCE_STATUS", path)
    assert subject.check_compliance() is not None


def test_inventory_observes_metadata_without_reading_artifact_contents(compliance, monkeypatch, tmp_path):
    path = tmp_path / "dashboard/api_key_status.txt"
    path.write_text("Do not read artifact contents", encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("Inventory crossed into artifact contents")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    rows = compliance.build_progress()
    row = next(row for row in rows if row["item"] == "API key management UI")
    assert row["status"] == "artifact_present_unverified"
    assert row["completion_verified"] is False
    assert row["compliance_verified"] is False
    assert row["artifacts"][0]["bytes"] == path.stat().st_size


def test_inventory_paths_do_not_depend_on_the_current_directory(compliance, monkeypatch, tmp_path):
    (tmp_path / "dashboard/legal.html").write_text("draft", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    row = next(row for row in compliance.build_progress() if row["item"] == "Legal/terms of service")
    assert row["status"] == "artifact_present_unverified"


def test_empty_and_nonregular_artifacts_remain_unusable(compliance, tmp_path):
    (tmp_path / "dashboard/kyc_module.py").mkdir()
    (tmp_path / "dashboard/kyc_status.json").touch()
    row = next(row for row in compliance.build_progress() if row["item"] == "KYC/AML integration")
    assert row["status"] == "no_usable_artifact_observed"
    assert {x["state"] for x in row["artifacts"]} == {"empty_file_observed", "not_a_regular_file"}


def test_inventory_write_failure_keeps_the_previous_status(compliance, monkeypatch, tmp_path):
    compliance.PROGRESS_PATH.write_text("retained", encoding="utf-8")

    def fail_replace(*args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(compliance.os, "replace", fail_replace)
    with pytest.raises(OSError):
        compliance.main()
    assert compliance.PROGRESS_PATH.read_text(encoding="utf-8") == "retained"
    assert len(list((tmp_path / "dashboard").iterdir())) == 1


def test_log_age_uses_utc_and_quiet_error_absence_is_not_stall(tmp_path):
    subject = load("orchestrator_watchdog")
    now = datetime(2026, 9, 14, 1, tzinfo=timezone.utc)
    path = tmp_path / subject.LOG_NAMES[0]
    path.write_text("activity", encoding="utf-8")
    os.utime(path, (now.timestamp() - 60, now.timestamp() - 60))
    report = subject.assess_logs([path, tmp_path / subject.LOG_NAMES[1]], now=now)
    assert report["logs"][0]["age_seconds"] == pytest.approx(60)
    assert report["issues"] == []
    assert report["runtime_health_verified"] is False
    assert report["restart_authorized"] is False


@pytest.mark.parametrize("age", [600, -60])
def test_stale_or_future_activity_cannot_be_green_runtime_health(tmp_path, age):
    subject = load("orchestrator_watchdog")
    now = datetime(2026, 9, 14, 1, tzinfo=timezone.utc)
    path = tmp_path / subject.LOG_NAMES[0]
    path.write_text("activity", encoding="utf-8")
    os.utime(path, (now.timestamp() - age, now.timestamp() - age))
    report = subject.assess_logs([path], now=now)
    assert report["issues"]
    assert report["restart_authorized"] is False
    assert "ISSUES DETECTED:" in subject.render_status(report)


def test_error_tail_is_bounded_and_old_indicators_are_not_an_error_rate(tmp_path):
    subject = load("orchestrator_watchdog")
    now = datetime(2026, 9, 14, 1, tzinfo=timezone.utc)
    path = tmp_path / subject.LOG_NAMES[1]
    path.write_bytes(b"error\n" * 100000 + b"quiet\n" * 101)
    os.utime(path, (now.timestamp(), now.timestamp()))
    report = subject.assess_logs([path], now=now)
    assert report["logs"][0]["tail_lines_observed"] == 100
    assert report["logs"][0]["tail_indicator_count"] == 0
    path.write_bytes(b"error\n" * 4)
    os.utime(path, (now.timestamp() - 86400, now.timestamp() - 86400))
    report = subject.assess_logs([path], now=now)
    assert report["logs"][0]["tail_indicator_count"] == 4
    assert report["issues"] == []
    os.utime(path, (now.timestamp(), now.timestamp()))
    report = subject.assess_logs([path], now=now)
    assert len(report["issues"]) == 1
    assert "event rate is unverified" in report["issues"][0]


@pytest.mark.parametrize("content", ["[]", "{}", "invalid JSON", '[{"item":"private text","status":"complete"}]'])
def test_compliance_alerts_remain_unverified_without_echoing_arbitrary_contents(monkeypatch, tmp_path, content):
    subject = load("send_stack_alerts")
    path = tmp_path / "compliance.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(subject, "COMPLIANCE_STATUS", path)
    message = subject.check_compliance()
    assert "unverified" in message
    assert "private text" not in message


@pytest.mark.parametrize("offset", [-3600, 3600])
def test_stale_or_future_watchdog_status_cannot_silence_alerts(monkeypatch, tmp_path, offset):
    subject = load("send_stack_alerts")
    watchdog = load("orchestrator_watchdog")
    checked = datetime.now(timezone.utc) + timedelta(seconds=offset)
    report = watchdog.assess_logs([], now=checked)
    path = tmp_path / "status.txt"
    path.write_text(watchdog.render_status(report), encoding="utf-8")
    monkeypatch.setattr(subject, "WATCHDOG_STATUS", path)
    assert "stale or future-dated" in subject.check_watchdog()


def test_only_fresh_bounded_log_observations_can_clear_log_alerts(monkeypatch, tmp_path):
    subject = load("send_stack_alerts")
    watchdog = load("orchestrator_watchdog")
    log = tmp_path / watchdog.LOG_NAMES[0]
    log.write_text("activity", encoding="utf-8")
    report = watchdog.assess_logs([log])
    path = tmp_path / "status.txt"
    path.write_text(watchdog.render_status(report), encoding="utf-8")
    monkeypatch.setattr(subject, "WATCHDOG_STATUS", path)
    assert subject.check_watchdog() is None
    path.write_text("No issues detected.\n", encoding="utf-8")
    assert "legacy or malformed" in subject.check_watchdog()


def test_legacy_proof_entry_cannot_stamp_an_empty_example_as_validation(monkeypatch, tmp_path):
    subject = load("generate_validation_proof")
    data = tmp_path / "out/execution"
    data.mkdir(parents=True)
    (data / "trade_log.json").write_text('[{"close":100}]', encoding="utf-8")
    generated = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["generate_validation_proof.py"])
    monkeypatch.setattr(subject, "generate_proof_pack", lambda obj, _: generated.append(obj) or ("proof.json", "hash.txt"), raising=False)
    try:
        result = subject.main()
    except SystemExit as exc:
        result = exc.code
    assert result == 2
    assert generated == []


def test_proof_compatibility_entry_routes_to_the_existing_bounded_evaluator(tmp_path):
    subject = load("generate_validation_proof")
    output = tmp_path / "explicit-run"
    code = subject.main([
        "--input", str(ROOT / "examples/ensemble_research/synthetic_price_fixture.csv"),
        "--input-kind", "synthetic", "--timestamp-column", "timestamp",
        "--window", "65", "--step", "7", "--fee-bps", "10", "--slippage-bps", "5",
        "--output-dir", str(output),
    ])
    assert code == 0
    receipt = json.loads((output / "ensemble_run_receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema"] == "lumencore.ensemble_past_only_research.v2"
    assert receipt["evaluated_transitions"] == 31
    assert receipt["scientific_performance_claim_supported"] is False
    assert receipt["execution_authorized"] is False


@pytest.mark.parametrize("first_exit,watchdog_exit,expected", [(0, 2, 2), (7, 0, 1), (0, 0, 0)])
def test_observation_driver_uses_its_own_paths_and_preserves_exit_meanings(tmp_path, first_exit, watchdog_exit, expected):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell integration check requires pwsh")
    dashboard = tmp_path / "stack/dashboard"
    dashboard.mkdir(parents=True)
    driver = dashboard / "automate_luma_stack.ps1"
    driver.write_bytes((ROOT / "dashboard/automate_luma_stack.ps1").read_bytes())
    names = ["update_api_key_status.py", "orchestrator_watchdog.py", "update_compliance_progress.py"]
    for name, code in zip(names, [first_exit, watchdog_exit, 0]):
        (dashboard / name).write_text(
            "from pathlib import Path\n"
            "with Path(__file__).with_name('observed.txt').open('a') as stream:\n"
            "    stream.write(Path(__file__).name + '\\n')\n"
            f"raise SystemExit({code})\n", encoding="utf-8")
    result = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", str(driver), "-Python", sys.executable],
                            cwd=tmp_path, text=True, capture_output=True, timeout=30, check=False)
    assert result.returncode == expected, result.stderr
    assert (dashboard / "observed.txt").read_text().splitlines() == names
    assert "do not establish runtime health" in result.stdout
    assert "All LumaTrader stack health/compliance checks complete" not in result.stdout
