from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "Run-EiaProspectiveHourlyRouterCycle.ps1"


def wrapper_text() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_quiet_run_uses_atomic_success_output_and_separate_stderr() -> None:
    text = wrapper_text()

    assert 'scheduler_cycle_latest.json.tmp' in text
    assert 'scheduler_stderr_latest.log.tmp' in text
    assert '-RedirectStandardOutput $SchedulerOutputTemp' in text
    assert '-RedirectStandardError $SchedulerStderrTemp' in text
    assert (
        'Move-Item -LiteralPath $SchedulerOutputTemp '
        '-Destination $SchedulerOutput -Force'
    ) in text
    assert text.index('if ($ExitCode -eq 0)') < text.index(
        'Move-Item -LiteralPath $SchedulerOutputTemp'
    )


def test_failure_preserves_last_good_cycle_and_logs_captured_stderr() -> None:
    text = wrapper_text()

    failure_block = text[text.index('if ($ExitCode -ne 0)') :]
    assert 'Get-Content -LiteralPath $SchedulerStderrTemp -Raw' in failure_block
    assert 'failed with exit code $ExitCode. $Stderr' in failure_block
    assert 'Move-Item -LiteralPath $SchedulerOutputTemp' not in failure_block.split(
        'catch {'
    )[0]


def test_python_path_is_validated_before_execution() -> None:
    text = wrapper_text()

    validation = 'Test-Path -LiteralPath $PythonExe -PathType Leaf'
    execution = '& $PythonExe @Arguments'
    assert validation in text
    assert text.index(validation) < text.index(execution)


def test_quiet_run_owns_and_terminates_timed_out_child_process() -> None:
    text = wrapper_text()

    assert '[int]$CycleTimeoutSeconds = 420' in text
    assert 'Start-Process `' in text
    assert '-WindowStyle Hidden `' in text
    assert '$Process.WaitForExit($CycleTimeoutSeconds * 1000)' in text
    assert 'Stop-Process -Id $Process.Id -Force' in text
    assert 'the last good scheduler receipt was preserved' in text
