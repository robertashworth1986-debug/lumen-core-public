from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_google_drive_file_urls_require_the_exact_https_origin() -> None:
    module = load_path(
        "linkedin_launchpack_url_test",
        ROOT / "code" / "ops" / "BUILD_LINKEDIN_APP_LAUNCHPACK.py",
    )
    accepted = {
        "https://drive.google.com/file/d/abc_DEF-123/view": "abc_DEF-123",
        "https://drive.google.com/open?id=abc_DEF-123": "abc_DEF-123",
    }
    for url, expected in accepted.items():
        assert module._google_drive_file_id(url) == expected

    rejected = (
        "http://drive.google.com/file/d/abc_DEF-123/view",
        "https://drive.google.com.evil.example/file/d/abc_DEF-123/view",
        "https://evil.example/?next=https://drive.google.com/file/d/abc_DEF-123/view",
        "https://user@drive.google.com/file/d/abc_DEF-123/view",
        "https://drive.google.com:443/file/d/abc_DEF-123/view",
        "https://drive.google.com/open?id=bad/value",
    )
    for url in rejected:
        assert module._google_drive_file_id(url) == ""


def test_runtime_hydration_proof_never_persists_process_output_or_secret_values() -> None:
    script = ROOT / "code" / "HYDRATE_RUNTIME_ENV_AND_RERUN_KRAKEN.py"
    with tempfile.TemporaryDirectory() as tmp:
        stack = Path(tmp)
        (stack / "config").mkdir()
        (stack / "code").mkdir()
        (stack / "config" / "luma_live_keys.env").write_text(
            "KRAKEN_API_KEY=DO_NOT_PERSIST_KEY\n"
            "KRAKEN_API_SECRET=DO_NOT_PERSIST_SECRET\n",
            encoding="utf-8",
        )
        (stack / "code" / "kraken_smoke_test_stage2.py").write_text(
            'print("ENV CHECK OK")\n'
            'print("PRIVATE CHECKS SKIPPED: explicit_operator_opt_in_required")\n'
            'print("DO_NOT_PERSIST_SMOKE_OUTPUT")\n',
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["LUMA_STACK_ROOT"] = str(stack)
        env.pop("LUMA_ALLOW_PRIVATE_EXCHANGE_SMOKE", None)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=False,
        )
        proof_text = (stack / "out" / "runtime_env_hydration_proof.json").read_text(
            encoding="utf-8"
        )
        proof = json.loads(proof_text)

    assert result.returncode == 0
    assert proof["smoke_status"] == "pass"
    assert proof["smoke_markers"]["env_check_ok"] is True
    assert proof["smoke_markers"]["private_checks_skipped"] is True
    assert proof["private_exchange_contact_authorized"] is False
    assert proof["raw_process_output_persisted"] is False
    assert "stdout" not in proof_text.lower()
    assert "stderr" not in proof_text.lower()
    assert "DO_NOT_PERSIST" not in proof_text


def test_smoke_scripts_require_explicit_private_exchange_opt_in() -> None:
    for relative in ("kraken_smoke_test.py", "kraken_smoke_test_stage2.py"):
        source = (ROOT / "code" / relative).read_text(encoding="utf-8")
        assert "LUMA_ALLOW_PRIVATE_EXCHANGE_SMOKE" in source
        assert "PRIVATE CHECKS SKIPPED" in source
        assert "type(exc).__name__" in source
        assert "print(balance)" not in source
        assert "print(result)" not in source
        assert "print(env_status)" not in source


def test_paper_facade_does_not_leak_legacy_production_import_path() -> None:
    code = ROOT / "code"
    command = (
        "import sys; "
        "import execution.alpaca_paper_executor; "
        "assert not any(p.lower() == "
        "r'c:\\lumatrader\\institutional_stack_v2\\code'.lower() for p in sys.path)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(code)
    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
