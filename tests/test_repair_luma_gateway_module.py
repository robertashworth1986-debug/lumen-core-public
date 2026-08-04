from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "REPAIR_LUMA_GATEWAY_MODULE.ps1"
MODULE = ROOT / "code" / "booth_public_contract.py"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def _fake_native_bin(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "fake-native"
    fake_bin.mkdir(parents=True)
    marker = tmp_path / "native-command-called.txt"

    for command in ("ssh", "scp"):
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


def _run_repair(
    tmp_path: Path,
    arguments: list[str],
    *,
    token: str | None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    assert POWERSHELL
    fake_bin, marker = _fake_native_bin(tmp_path)
    environment = os.environ.copy()
    environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")
    environment["FAKE_NATIVE_MARKER"] = str(marker)
    environment["USERPROFILE"] = str(tmp_path / "empty-profile")
    environment.pop("LUMA_VPS_SSH_KEY", None)
    environment.pop("LUMA_SSH_KNOWN_HOSTS", None)
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
            str(SCRIPT),
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


def test_gateway_repair_script_is_bounded_and_human_gated() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "booth_public_contract.py" in text
    assert "This bounded repair accepts only booth_public_contract.py." in text
    assert "LUMA_HUMAN_UNLOCK_TOKEN" in text
    assert "ApprovedModuleSha256" in text
    assert "must exactly match the current module SHA-256" in text
    assert "sudo -n systemctl restart luma-gateway" in text
    assert "systemctl restart nginx" not in text
    assert "systemctl restart caddy" not in text
    assert "rm -rf" not in text
    assert "sudo -n true" in text
    assert "sudo -n install" in text
    assert "sudo -n systemctl restart luma-gateway" in text
    assert "DRY RUN: no network call, upload, restart, or remote mutation was performed." in text


def test_gateway_repair_source_contract_is_present_and_hashable() -> None:
    assert MODULE.is_file()
    digest = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    assert len(digest) == 64
    assert "public_booth_projection" in MODULE.read_text(encoding="utf-8")


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
@pytest.mark.parametrize("arguments", [[], ["-DryRun"]])
def test_gateway_repair_dry_run_never_calls_native_commands(
    tmp_path: Path,
    arguments: list[str],
) -> None:
    sentinel = "do-not-print-this-human-unlock-value-1234567890"
    result, marker = _run_repair(tmp_path, arguments, token=sentinel)

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "DRY RUN" in output
    assert "no network call" in output
    assert sentinel not in output
    assert not marker.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
def test_gateway_repair_apply_rejects_wrong_hash_before_native_commands(
    tmp_path: Path,
) -> None:
    sentinel = "do-not-print-this-human-unlock-value-1234567890"
    result, marker = _run_repair(
        tmp_path,
        ["-Apply", "-ApprovedModuleSha256", "0" * 64],
        token=sentinel,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "must exactly match the current module SHA-256" in output
    assert sentinel not in output
    assert not marker.exists()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")
@pytest.mark.parametrize("token", [None, "too-short"])
def test_gateway_repair_apply_rejects_missing_or_short_unlock_before_native_commands(
    tmp_path: Path,
    token: str | None,
) -> None:
    digest = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    result, marker = _run_repair(
        tmp_path,
        ["-Apply", "-ApprovedModuleSha256", digest],
        token=token,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "at least 32 characters" in output
    assert "too-short" not in output
    assert not marker.exists()
