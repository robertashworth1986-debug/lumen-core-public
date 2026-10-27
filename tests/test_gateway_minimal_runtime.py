from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gateway_minimal_runtime", ROOT / "code" / "ops" / "VERIFY_GATEWAY_MINIMAL_RUNTIME.py")
runtime = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runtime)


def test_minimal_serving_lock_has_independent_uvicorn_backbone():
    versions = runtime.lock_versions(runtime.LOCK.read_text())
    assert versions["uvicorn"] == "0.54.0"
    assert "pytest" not in versions and "numpy" not in versions and "requests" not in versions
    result = runtime.verify(check_lock_only=True)
    assert result["scope"] == "minimal-reviewer-http-serving"
    assert result["runtime_versions_checked"] is False
    assert result["optional_operator_components"] == "HOLD"


@pytest.mark.parametrize("damage", ["missing_hash", "duplicate", "unapproved_index", "missing_uvicorn"])
def test_minimal_lock_refuses_supply_chain_gaps(damage):
    text = runtime.LOCK.read_text()
    if damage == "missing_hash":
        text = "fastapi==0.138.2\n" + text[text.index("uvicorn=="):]
    elif damage == "duplicate":
        text += text[text.index("uvicorn=="):]
    elif damage == "unapproved_index":
        text += "--extra-index-url https://untrusted.invalid/simple\n"
    else:
        text = text[:text.index("uvicorn==")]
    with pytest.raises(ValueError):
        runtime.lock_versions(text)


def test_installed_runtime_must_match_every_minimal_lock_pin(monkeypatch):
    expected = runtime.lock_versions(runtime.LOCK.read_text())
    monkeypatch.setattr(runtime.sys, "version_info", (3, 11, 9))
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    monkeypatch.setattr(runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(runtime.importlib.metadata, "version", lambda name: "0.0.0" if name == "uvicorn" else expected[name])
    with pytest.raises(ValueError, match="installed version mismatch: uvicorn"):
        runtime.verify()


def test_runtime_identity_is_not_promoted_from_different_python(monkeypatch):
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 14))
    with pytest.raises(ValueError, match="CPython 3.11.9"):
        runtime.verify()
