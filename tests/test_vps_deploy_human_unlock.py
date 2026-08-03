from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PUSH_STACK = ROOT / "deploy" / "PUSH_TO_VPS.ps1"
PUSH_PROOF_FEEDS = ROOT / "deploy" / "PUSH_PROOF_FEEDS_TO_VPS.ps1"
REMOTE_DEPLOY = ROOT / "code" / "deploy" / "deploy_vps.sh"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def _usable_bash() -> str | None:
    candidates = [
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except OSError:
            continue
        if probe.returncode == 0:
            return candidate
    return None


def _make_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "proof_bundle"
    (bundle / "data").mkdir(parents=True)
    (bundle / "dashboard" / "data").mkdir(parents=True)
    manifest = {
        "summary": {
            "feed_only_deploy_ready": True,
            "publishes_config_or_secrets": False,
            "service_restart_required": False,
            "required_ready_count": 1,
            "required_feed_count": 1,
        }
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def _make_fake_native_bin(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "fake-native"
    fake_bin.mkdir(parents=True)
    marker = tmp_path / "native-command-called.txt"

    for command in ("ssh", "scp", "tar"):
        if os.name == "nt":
            path = fake_bin / f"{command}.cmd"
            path.write_text(
                '@echo %~n0>>"%FAKE_NATIVE_MARKER%"\r\nexit /b 97\r\n',
                encoding="ascii",
            )
        else:
            path = fake_bin / command
            path.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$0" >>"$FAKE_NATIVE_MARKER"\nexit 97\n',
                encoding="ascii",
            )
            path.chmod(0o755)

    return fake_bin, marker


def _run_powershell(
    script: Path,
    arguments: list[str],
    tmp_path: Path,
    *,
    token: str | None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    assert POWERSHELL
    fake_bin, marker = _make_fake_native_bin(tmp_path)
    environment = os.environ.copy()
    environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")
    environment["FAKE_NATIVE_MARKER"] = str(marker)
    environment["USERPROFILE"] = str(tmp_path / "empty-profile")
    environment.pop("LUMA_VPS_SSH_KEY", None)
    if token is None:
        environment.pop("LUMA_HUMAN_UNLOCK_TOKEN", None)
    else:
        environment["LUMA_HUMAN_UNLOCK_TOKEN"] = token

    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    return result, marker


def test_static_guards_precede_every_deployment_mutation_surface() -> None:
    stack_text = PUSH_STACK.read_text(encoding="utf-8")
    proof_text = PUSH_PROOF_FEEDS.read_text(encoding="utf-8")
    remote_text = REMOTE_DEPLOY.read_text(encoding="utf-8")

    for text in (stack_text, proof_text):
        assert "[switch]$Apply" in text
        assert "LUMA_HUMAN_UNLOCK_TOKEN" in text
        assert ".Length -lt 32" in text
        assert "Remove-Item Env:LUMA_HUMAN_UNLOCK_TOKEN" in text
        assert "if (-not $Apply)" in text

    assert stack_text.index("if (-not $Apply)") < stack_text.index(
        '$stamp = (Get-Date)'
    )
    assert stack_text.index("if (-not $Apply)") < stack_text.index(
        'Invoke-Ssh -StepLabel "1/5 VPS preflight"'
    )
    assert "LUMA_VPS_DEPLOY_APPLY=1" in stack_text
    assert "$HumanUnlockToken | & ssh" in stack_text

    assert proof_text.index("if (-not $Apply)") < proof_text.index(
        "$archive = New-BundleArchive"
    )
    assert proof_text.index("if (-not $Apply)") < proof_text.index(
        "Invoke-CheckedNative -FilePath scp"
    )
    assert "LUMA_VPS_DEPLOY_APPLY=1" in proof_text
    assert "$SecretInput | & $FilePath" in proof_text

    guard = 'if [[ "${LUMA_VPS_DEPLOY_APPLY:-0}" != "1" ]]'
    first_mutation = 'chmod +x "$SCRIPT_DIR/verify_dashboard_endpoints.sh"'
    assert remote_text.index(guard) < remote_text.index(first_mutation)
    assert remote_text.index(guard) < remote_text.index("apt-get update -qq")
    assert remote_text.index(guard) < remote_text.index("rsync -av --delete")
    assert "${#human_unlock_token} -lt 32" in remote_text
    assert "unset human_unlock_token LUMA_HUMAN_UNLOCK_TOKEN" in remote_text
    assert "rsync -av --delete" in remote_text


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
def test_stack_default_is_local_preflight_without_native_commands(
    tmp_path: Path,
) -> None:
    sentinel = "do-not-print-this-human-unlock-value-1234567890"
    result, marker = _run_powershell(
        PUSH_STACK,
        ["-Root", str(ROOT)],
        tmp_path,
        token=sentinel,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "PRECHECK ONLY" in output
    assert "No network calls" in output
    assert sentinel not in output
    assert not marker.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
@pytest.mark.parametrize("dry_run_argument", [[], ["-DryRun"]])
def test_proof_feed_default_and_dry_run_never_call_native_commands(
    tmp_path: Path,
    dry_run_argument: list[str],
) -> None:
    bundle = _make_bundle(tmp_path)
    result, marker = _run_powershell(
        PUSH_PROOF_FEEDS,
        ["-BundleRoot", str(bundle), *dry_run_argument],
        tmp_path,
        token="do-not-print-this-human-unlock-value-1234567890",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "DRY RUN" in output
    assert "no archive was created" in output
    assert "do-not-print-this-human-unlock-value" not in output
    assert not marker.exists()
    assert list(tmp_path.glob("luma_proof_feeds_*.tar.gz")) == []


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
@pytest.mark.parametrize("token", [None, "too-short"])
def test_apply_rejects_missing_or_short_unlock_before_native_commands(
    tmp_path: Path,
    token: str | None,
) -> None:
    bundle = _make_bundle(tmp_path)

    stack_result, stack_marker = _run_powershell(
        PUSH_STACK,
        ["-Root", str(ROOT), "-Apply"],
        tmp_path / "stack",
        token=token,
    )
    proof_result, proof_marker = _run_powershell(
        PUSH_PROOF_FEEDS,
        ["-BundleRoot", str(bundle), "-Apply"],
        tmp_path / "proof",
        token=token,
    )

    for result, marker in (
        (stack_result, stack_marker),
        (proof_result, proof_marker),
    ):
        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "at least 32 characters" in output
        assert "too-short" not in output
        assert not marker.exists()


def test_remote_script_parses_without_execution_when_bash_is_available() -> None:
    bash = _usable_bash()
    if bash is None:
        pytest.skip("bash is unavailable")

    result = subprocess.run(
        [bash, "-n", str(REMOTE_DEPLOY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
