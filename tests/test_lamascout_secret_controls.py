from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "LamaScout" / "src" / "credential_config.py"
SPEC = importlib.util.spec_from_file_location("credential_config", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

AUTH_ASSIGNMENT = re.compile(
    r"^\s+(api_key|client_id|client_secret|access_token|bearer_token):\s*(\S+)\s*$"
)
SAFE_REFERENCE = re.compile(r"^\$\{LUMASCOUT_[A-Z0-9_]+\}$")


def _synthetic_registry(value: str = "${LUMASCOUT_YOUTUBE_API_KEY}") -> dict:
    return {
        "sources": [
            {
                "name": "youtube",
                "auth": {"api_key": value},
            }
        ]
    }


def test_tracked_registry_contains_only_environment_references() -> None:
    registry_path = ROOT / "LamaScout" / "config" / "api_registry.yaml"
    assignments = []
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        match = AUTH_ASSIGNMENT.match(line)
        if match:
            assignments.append((match.group(1), match.group(2)))

    assert len(assignments) == 13
    assert all(SAFE_REFERENCE.fullmatch(value) for _, value in assignments)


def test_missing_environment_values_fail_closed() -> None:
    resolved = MODULE.resolve_registry_environment(_synthetic_registry(), {})
    assert resolved["sources"][0]["auth"]["api_key"] == ""


def test_synthetic_environment_value_resolves_without_mutating_template() -> None:
    template = _synthetic_registry()
    resolved = MODULE.resolve_registry_environment(
        template,
        {"LUMASCOUT_YOUTUBE_API_KEY": "synthetic-runtime-value"},
    )
    assert resolved["sources"][0]["auth"]["api_key"] == "synthetic-runtime-value"
    assert (
        template["sources"][0]["auth"]["api_key"]
        == "${LUMASCOUT_YOUTUBE_API_KEY}"
    )


def test_literal_and_wrong_environment_references_are_rejected() -> None:
    for value in (
        "synthetic-literal-secret",
        "${UNRELATED_SECRET}",
        "${LUMASCOUT_SPOTIFY_CLIENT_SECRET}",
    ):
        try:
            MODULE.validate_registry_auth_references(_synthetic_registry(value))
        except MODULE.RegistryCredentialError:
            continue
        raise AssertionError("unsafe registry auth value was accepted")


def test_local_env_file_is_ignored_and_example_contains_names_only() -> None:
    ignore_text = (ROOT / "LamaScout" / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in {line.strip() for line in ignore_text.splitlines()}
    root_ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    root_rules = {line.strip() for line in root_ignore.splitlines()}
    assert "!LamaScout/.env.example" in root_rules
    assert "!tests/test_lamascout_secret_controls.py" in root_rules

    example_lines = (
        ROOT / "LamaScout" / ".env.example"
    ).read_text(encoding="utf-8").splitlines()
    expected_names = set(MODULE.AUTH_ENV_BY_SOURCE.values())
    assert {line.split("=", 1)[0] for line in example_lines} == expected_names
    assert all(line.endswith("=") for line in example_lines)
