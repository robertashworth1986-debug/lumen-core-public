from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "code" / "ops" / "VERIFY_TRACKED_CREDENTIAL_LITERALS.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_tracked_secret_literals",
        VERIFIER,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_query_literal_is_rejected_without_returning_its_value():
    module = load_verifier()
    synthetic_secret = "SYNTHETIC_NOT_REAL_9f7a1c4e2d8b"
    findings = module.scan_text(
        f'https://example.invalid/data?api_key={synthetic_secret}&format=json',
        "synthetic.json",
    )

    assert findings == [
        {
            "path": "synthetic.json",
            "line": 1,
            "parameter": "api_key",
            "finding": "NON_PLACEHOLDER_QUERY_CREDENTIAL_LITERAL",
        }
    ]
    assert synthetic_secret not in json.dumps(findings)


def test_placeholders_and_runtime_references_are_allowed():
    module = load_verifier()
    text = "\n".join(
        (
            "https://example.invalid/a?api_key=REDACTED_ROTATION_REQUIRED",
            "https://example.invalid/b?token=${RUNTIME_TOKEN}",
            "https://example.invalid/c?client_secret={client_secret}",
            "https://example.invalid/d?authorization=<runtime-reference>",
            "https://example.invalid/e?api_key={quote(api_key)}",
            "https://example.invalid/f?apikey=$runtimeKey",
        )
    )

    assert module.scan_text(text, "synthetic.txt") == []


def test_current_tracked_text_scope_passes_and_output_is_value_free():
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--compact"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] == "PASS"
    assert payload["scope"] == "CURRENT_GIT_TRACKED_UTF8_TEXT_FILES"
    assert payload["scanned_file_count"] > 100
    assert payload["finding_count"] == 0
    assert payload["scan_failure_count"] == 0
    assert payload["values_emitted"] is False
    assert payload["external_action_performed"] is False
