from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CODECHECK_REVIEWER_RUNTIME.py"
CONFIG = ROOT / "config" / "codecheck_reviewer_runtime_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("codecheck_reviewer_runtime", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_os_release(path: Path, *, os_id: str, version_id: str) -> None:
    path.write_text(
        f'NAME="Fixture Linux"\nID={os_id}\nVERSION_ID="{version_id}"\n',
        encoding="utf-8",
    )


def set_expected_runtime(monkeypatch, module) -> None:
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.11.9")
    monkeypatch.setattr(module.platform, "libc_ver", lambda: ("glibc", "2.39"))
    for key, value in json.loads(CONFIG.read_text(encoding="utf-8"))[
        "expected"
    ]["environment"].items():
        monkeypatch.setenv(key, value)


def test_os_release_parser_handles_quotes_comments_and_escapes(tmp_path):
    module = load_module()
    path = tmp_path / "os-release"
    path.write_text(
        '# comment\nID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04 LTS"\n',
        encoding="utf-8",
    )

    values = module.read_os_release(path)

    assert values["ID"] == "ubuntu"
    assert values["VERSION_ID"] == "24.04"
    assert values["PRETTY_NAME"] == "Ubuntu 24.04 LTS"


def test_exact_runtime_passes_and_keeps_external_gates_false(tmp_path, monkeypatch):
    module = load_module()
    set_expected_runtime(monkeypatch, module)
    path = tmp_path / "os-release"
    write_os_release(path, os_id="ubuntu", version_id="24.04")
    monkeypatch.setattr(
        module,
        "source_identity",
        lambda _config, **_kwargs: {
            "git_metadata_available": True,
            "repository_commit_observed": "fixture",
            "repository_commit_declared_by_operator": None,
            "relevant_source_clean_observed": True,
            "relevant_change_line_count": 0,
            "files": [],
            "source_chain_sha256": module.canonical_sha256([]),
        },
    )

    receipt = module.build_receipt(
        config_path=CONFIG,
        os_release_path=path,
        generated_utc="2026-07-21T00:00:00+00:00",
    )

    assert receipt["status"] == "AUTHORITATIVE_RUNTIME_PASS"
    assert receipt["passed"] is True
    assert all(receipt["checks"].values())
    assert receipt["operator_controlled"] is True
    assert receipt["independent_execution_complete"] is False
    assert receipt["external_validation_complete"] is False


def test_runtime_fails_closed_on_distro_libc_or_environment_drift(
    tmp_path, monkeypatch
):
    module = load_module()
    set_expected_runtime(monkeypatch, module)
    path = tmp_path / "os-release"
    write_os_release(path, os_id="debian", version_id="12")
    monkeypatch.setattr(module.platform, "libc_ver", lambda: ("glibc", "2.36"))
    monkeypatch.setenv("OMP_NUM_THREADS", "8")
    monkeypatch.setattr(
        module,
        "source_identity",
        lambda _config, **_kwargs: {
            "git_metadata_available": True,
            "repository_commit_observed": "fixture",
            "repository_commit_declared_by_operator": None,
            "relevant_source_clean_observed": True,
            "relevant_change_line_count": 0,
            "files": [],
            "source_chain_sha256": module.canonical_sha256([]),
        },
    )

    receipt = module.build_receipt(config_path=CONFIG, os_release_path=path)

    assert receipt["status"] == "RUNTIME_MISMATCH"
    assert receipt["passed"] is False
    assert receipt["checks"]["os_release_id"] is False
    assert receipt["checks"]["os_release_version_id"] is False
    assert receipt["checks"]["libc_version"] is False
    assert receipt["checks"]["deterministic_environment"] is False


def test_missing_os_release_fails_closed(tmp_path, monkeypatch):
    module = load_module()
    set_expected_runtime(monkeypatch, module)
    monkeypatch.setattr(
        module,
        "source_identity",
        lambda _config, **_kwargs: {
            "git_metadata_available": True,
            "repository_commit_observed": "fixture",
            "repository_commit_declared_by_operator": None,
            "relevant_source_clean_observed": True,
            "relevant_change_line_count": 0,
            "files": [],
            "source_chain_sha256": module.canonical_sha256([]),
        },
    )

    receipt = module.build_receipt(
        config_path=CONFIG,
        os_release_path=tmp_path / "missing",
    )

    assert receipt["passed"] is False
    assert receipt["checks"]["os_release_id"] is False
    assert receipt["checks"]["os_release_version_id"] is False


def test_receipt_payload_hash_covers_every_field_except_itself(
    tmp_path, monkeypatch
):
    module = load_module()
    set_expected_runtime(monkeypatch, module)
    path = tmp_path / "os-release"
    write_os_release(path, os_id="ubuntu", version_id="24.04")
    monkeypatch.setattr(
        module,
        "source_identity",
        lambda _config, **_kwargs: {
            "git_metadata_available": True,
            "repository_commit_observed": "fixture",
            "repository_commit_declared_by_operator": None,
            "relevant_source_clean_observed": True,
            "relevant_change_line_count": 0,
            "files": [],
            "source_chain_sha256": module.canonical_sha256([]),
        },
    )
    receipt = module.build_receipt(config_path=CONFIG, os_release_path=path)
    without_hash = {
        key: value
        for key, value in receipt.items()
        if key != "receipt_payload_sha256"
    }

    assert receipt["receipt_payload_sha256"] == module.canonical_sha256(
        without_hash
    )
