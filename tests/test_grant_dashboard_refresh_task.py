from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK_SCRIPT = ROOT / "code" / "ops" / "REGISTER_GRANT_DASHBOARD_REFRESH_TASK.ps1"
REFRESH_SCRIPT = ROOT / "code" / "ops" / "RUN_GRANT_DASHBOARD_AUTO_REFRESH.ps1"


def run_task_stager(*args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [
            "pwsh.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(TASK_SCRIPT),
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_grant_refresh_task_stager_is_dry_run_and_resilient_by_default() -> None:
    result = run_task_stager()

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["schema"] == "lumencore.grant_dashboard_refresh_task_stage.v2"
    assert plan["status"] == "dry_run"
    assert plan["task_name"] == "Luma Elite Grant Dashboard Auto Refresh"
    assert plan["interval_hours"] == 2
    assert plan["refresh_opportunities"] is True
    assert plan["hidden"] is True
    assert plan["noninteractive"] is True
    assert plan["start_when_available"] is True
    assert plan["multiple_instances"] == "Queue"
    assert plan["execution_time_limit_minutes"] == 30
    assert plan["restart_count"] == 3
    assert plan["restart_interval_minutes"] == 5
    assert plan["allow_start_on_batteries"] is True
    assert plan["stop_on_battery_transition"] is False
    assert plan["wake_to_run"] is True
    assert plan["requires_interactive_logon"] is True
    assert plan["mutation_performed"] is False
    assert plan["apply_requires_human_unlock"] is True
    assert plan["apply_requires_administrator"] is True


def test_grant_refresh_task_apply_is_human_unlock_gated() -> None:
    env = dict(os.environ)
    env.pop("LUMA_HUMAN_UNLOCK_TOKEN", None)
    result = run_task_stager("-Apply", env=env)

    assert result.returncode != 0
    assert "LUMA_HUMAN_UNLOCK_TOKEN" in result.stderr


def test_grant_refresh_task_definition_contains_post_apply_verification() -> None:
    source = TASK_SCRIPT.read_text(encoding="utf-8").lower()

    assert "new-scheduledtasksettingsset" in source
    assert "register-scheduledtask" in source
    assert "-multipleinstances queue" in source
    assert "-startwhenavailable" in source
    assert "-restartcount 3" in source
    assert "-allowstartifonbatteries" in source
    assert "-dontstopifgoingonbatteries" in source
    assert "-waketorun" in source
    assert "registered grant dashboard refresh task failed" in source


def test_grant_refresh_rebuilds_external_engagement_before_deadline_board() -> None:
    source = REFRESH_SCRIPT.read_text(encoding="utf-8").lower()

    register_step = "build_external_engagement_response_register"
    board_step = "build_near_deadline_submission_command_board"
    assert "build_external_engagement_response_register.py" in source
    assert register_step in source
    assert source.index(register_step) < source.index(board_step)


def test_grant_refresh_reconciles_receipt_dependent_controls_before_sealing() -> None:
    source = REFRESH_SCRIPT.read_text(encoding="utf-8").lower()

    provisional_pointer = (
        "write-atomicjson -path $latestpath -value $pointer -depth 6"
    )
    human_docket = "reconcile_human_action_docket_after_refresh_receipt"
    agency_gate = "reconcile_agency_submission_assembly_gate_after_refresh_receipt"
    authority_matrix = "reconcile_submission_authority_matrix_after_refresh_receipt"
    last_known_good = (
        "write-atomicjson -path $lastknowngoodpath -value $pointer -depth 6"
    )

    for marker in (
        provisional_pointer,
        human_docket,
        agency_gate,
        authority_matrix,
        last_known_good,
    ):
        assert marker in source

    assert source.index(provisional_pointer) < source.index(human_docket)
    assert source.index(human_docket) < source.index(agency_gate)
    assert source.index(agency_gate) < source.index(authority_matrix)
    assert source.index(authority_matrix) < source.index(last_known_good)
