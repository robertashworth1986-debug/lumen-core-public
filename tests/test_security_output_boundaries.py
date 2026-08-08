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


def test_public_dashboard_activity_requires_rows_and_measured_evidence(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        stack = Path(tmp)
        monkeypatch.setenv("LUMA_STACK_ROOT", str(stack))
        monkeypatch.setenv("LUMA_DASHBOARD_DIR", str(stack / "dashboard"))
        monkeypatch.setenv("LUMA_TWIN_SEED_PATH", str(stack / "missing_twin_seed.json"))
        module = load_path(
            "unified_dashboard_boundary_test",
            ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py",
        )

    assert module.source_is_active(
        {
            "enabled": True,
            "rows": 10,
            "status": "LIVE_KEY_PRESENT",
            "basis": "ESTIMATED",
        }
    ) is False
    assert module.source_is_active(
        {"enabled": True, "rows": 10, "status": "OK", "basis": "OBSERVED"}
    ) is True
    assert module.source_is_active(
        {"enabled": True, "rows": 0, "status": "LIVE_MEASURED", "basis": "MEASURED"}
    ) is False


def test_public_dashboard_withholds_private_execution_identifiers(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        stack = Path(tmp)
        execution = stack / "out" / "execution"
        execution.mkdir(parents=True)
        raw_identifier = "PRIVATE-TXID-DO-NOT-PUBLISH"
        (execution / "binanceus_paper_ledger.jsonl").write_text(
            json.dumps(
                {
                    "event_type": "binanceus_paper_fill",
                    "txid": raw_identifier,
                    "trade_id": "PRIVATE-TRADE-ID",
                    "ledger_hash": "PRIVATE-LEDGER-HASH",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("LUMA_STACK_ROOT", str(stack))
        monkeypatch.setenv("LUMA_DASHBOARD_DIR", str(stack / "dashboard"))
        monkeypatch.setenv("LUMA_TWIN_SEED_PATH", str(stack / "missing_twin_seed.json"))
        module = load_path(
            "unified_dashboard_identifier_test",
            ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py",
        )
        data = module.collect_data()
        rendered = module.render_html(data)

    assert data["proof_event_count"] == 1
    assert raw_identifier not in rendered
    assert "PRIVATE-TRADE-ID" not in rendered
    assert "PRIVATE-LEDGER-HASH" not in rendered
    assert "identifiers withheld from public output" in rendered


def test_public_dashboard_serialization_and_links_fail_closed(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        stack = Path(tmp)
        monkeypatch.setenv("LUMA_STACK_ROOT", str(stack))
        monkeypatch.setenv("LUMA_DASHBOARD_DIR", str(stack / "dashboard"))
        monkeypatch.setenv("LUMA_TWIN_SEED_PATH", str(stack / "missing_twin_seed.json"))
        unified = load_path(
            "unified_dashboard_serialization_test",
            ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py",
        )
        combined = load_path(
            "combined_dashboard_link_test",
            ROOT / "code" / "execution" / "build_combined_dashboard.py",
        )

    serialized = unified.json_for_script({"value": "</script><script>alert(1)</script>"})
    assert "</script>" not in serialized
    assert "\\u003c" in serialized
    assert combined.safe_dashboard_href("reviewer_evidence.html") == "reviewer_evidence.html"
    assert combined.safe_dashboard_href("javascript:alert.html") == "#"
    assert combined.safe_dashboard_href("https://evil.example/report.html") == "#"
    fallback_html = combined.build_dashboard(
        {
            "trade_log": [{"txid": "PRIVATE-FALLBACK-TXID"}],
            "dashboard_links": ["javascript:alert.html"],
            "watchdog": ["RAW WATCHDOG DETAIL"],
            "level2_summary": ["RAW LEVEL 2 DETAIL"],
        }
    )
    assert "PRIVATE-FALLBACK-TXID" not in fallback_html
    assert "RAW WATCHDOG DETAIL" not in fallback_html
    assert "RAW LEVEL 2 DETAIL" not in fallback_html
    assert "href='#'" in fallback_html


def test_public_dashboard_builders_do_not_publish_credential_state_or_raw_ids() -> None:
    kraken_source = (ROOT / "build_kraken_execution_dashboard.py").read_text(
        encoding="utf-8"
    )
    live_source = (ROOT / "build_live_sources_dashboard.py").read_text(
        encoding="utf-8"
    )
    combined_source = (
        ROOT / "code" / "execution" / "build_combined_dashboard.py"
    ).read_text(encoding="utf-8")
    unified_source = (ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py").read_text(
        encoding="utf-8"
    )

    assert 'os.environ.get("KRAKEN_API_KEY"' not in kraken_source
    assert "api_key_present" not in live_source
    assert '"api_keys":' not in combined_source
    assert "load_trade_txids" not in combined_source
    assert "proof_txid_tail" not in unified_source
    assert 'row.get("ledger_hash") or row.get("trade_id")' not in unified_source
    assert "drilldownChipsEl.innerHTML" not in unified_source
