from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "code" / "RUN_ALPACA_PAPER_247.ps1"
POWERSHELL = shutil.which("powershell")


pytestmark = pytest.mark.skipif(
    POWERSHELL is None,
    reason="Windows PowerShell is required for the paper-loop runner tests",
)


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _make_stack(
    tmp_path: Path,
    *,
    builder_source: str,
    runtime_text: str = '{"loop_seconds": 30}',
) -> Path:
    stack = tmp_path / "stack"
    code = stack / "code"
    config = stack / "config"
    code.mkdir(parents=True)
    config.mkdir(parents=True)

    shutil.copy2(RUNNER, code / RUNNER.name)
    (code / "alpaca_paper_loop_builder.py").write_text(
        textwrap.dedent(builder_source).lstrip(),
        encoding="utf-8",
    )
    (config / "paper_trader_runtime.json").write_text(runtime_text, encoding="utf-8")
    return stack


def _run(stack: Path, *runner_args: str) -> subprocess.CompletedProcess[str]:
    script = stack / "code" / RUNNER.name
    args = " ".join(runner_args)
    command = (
        "function Start-Sleep { param([int]$Seconds) }; "
        f"& {_ps_quote(script)} -PythonExe {_ps_quote(sys.executable)} {args}"
    )
    return subprocess.run(
        [
            str(POWERSHELL),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=stack,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_two_cycles_preserve_config_directory_path(tmp_path: Path) -> None:
    stack = _make_stack(
        tmp_path,
        builder_source="""
            from pathlib import Path

            state = Path(__file__).resolve().parents[1] / "out" / "cycles.txt"
            state.parent.mkdir(parents=True, exist_ok=True)
            count = int(state.read_text(encoding="utf-8")) if state.exists() else 0
            state.write_text(str(count + 1), encoding="utf-8")
        """,
        runtime_text=json.dumps(
            {
                "generated_utc": "2026-05-29T02:00:00Z",
                "loop_seconds": 30,
            }
        ),
    )

    result = _run(stack, "-MaxCycles", "2")
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert (stack / "out" / "cycles.txt").read_text(encoding="utf-8") == "2"
    assert "Cannot find drive" not in output
    assert "Path because it is null" not in output


def test_once_returns_failure_when_builder_fails(tmp_path: Path) -> None:
    stack = _make_stack(
        tmp_path,
        builder_source="""
            raise SystemExit(7)
        """,
    )

    result = _run(stack, "-Once")
    output = result.stdout + result.stderr

    assert result.returncode == 1
    assert "exited with code 7" in output


def test_once_tolerates_malformed_runtime_config_after_success(
    tmp_path: Path,
) -> None:
    stack = _make_stack(
        tmp_path,
        builder_source="""
            print("builder complete")
        """,
        runtime_text="{not-json",
    )

    result = _run(stack, "-Once")
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert "Using the default sleep interval" in output
