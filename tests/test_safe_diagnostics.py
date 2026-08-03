from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "safe_diagnostics.py"
SANITIZER = ROOT / "code" / "ops" / "SANITIZE_LIVE_SOURCE_DIAGNOSTICS.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_diagnostic_text_redacts_common_secret_forms():
    module = load_module(SCRIPT, "safe_diagnostics")
    fake_key = "FAKE-SECRET-123456"
    fake_email = "reviewer@example.test"
    text = (
        "url=https://example.test/probe?"
        f"email=reviewer%40example.test&key={fake_key} "
        f'json={{"api_key":"{fake_key}"}} '
        f"Authorization: Bearer {fake_key} "
        f"contact={fake_email} status=400"
    )

    sanitized = module.sanitize_diagnostic_text(
        text,
        [fake_key, fake_email],
    )

    assert fake_key not in sanitized
    assert fake_email not in sanitized
    assert "reviewer%40example.test" not in sanitized
    assert "status=400" in sanitized
    assert sanitized.count("[REDACTED]") >= 3


def test_only_diagnostic_fields_are_rewritten():
    module = load_module(SCRIPT, "safe_diagnostics_fields")
    payload = {
        "probe_note": "key=FAKE-SECRET-123456",
        "nested": {
            "url": "https://example.test/?token=FAKE-SECRET-123456",
            "label": "key=FAKE-SECRET-123456",
        },
    }

    sanitized = module.sanitize_diagnostic_fields(payload)

    assert sanitized["probe_note"] == "key=[REDACTED]"
    assert sanitized["nested"]["url"].endswith("token=[REDACTED]")
    assert sanitized["nested"]["label"] == "key=FAKE-SECRET-123456"


def test_artifact_sanitizer_is_idempotent(tmp_path):
    module = load_module(SANITIZER, "sanitize_live_source_diagnostics")
    path = tmp_path / "live_sources.json"
    path.write_text(
        '{"providers":{"X":{"probe_note":"email=a%40b.test&key=FAKE12345"}}}',
        encoding="utf-8",
    )

    assert module.sanitize_path(path) is True
    assert module.sanitize_path(path) is False
    assert "FAKE12345" not in path.read_text(encoding="utf-8")
