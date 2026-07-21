from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_REVIEWER_DEPENDENCY_LOCK.py"
LOCK = ROOT / "requirements-reviewer-ubuntu-py311.lock"
PROTOCOL = ROOT / "config" / "reviewer_reproducibility_protocol_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "reviewer-reproducibility.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_dependency_lock", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_authoritative_linux_lock_is_complete_and_hash_verified():
    module = load_module()
    receipt = module.verify_lock()

    assert receipt["status"] == "AUTHORITATIVE_RUNNER_LOCK_VALID"
    assert receipt["passed"] is True
    assert receipt["direct_requirement_count"] == 8
    assert receipt["locked_package_count"] == 18
    assert receipt["locked_hash_count"] >= 18
    assert all(receipt["checks"].values())
    assert receipt["required_transitive_matches"] == {"nvidia-nccl-cu12": True}
    assert receipt["target"]["source_builds_allowed"] is False
    assert receipt["target"]["target_platform"] == "x86_64-unknown-linux-gnu"
    assert receipt["checks"]["resolver_header_matches_protocol"] is True
    assert receipt["checks"]["workflow_requires_hashes"] is True
    assert receipt["checks"]["workflow_requires_binary_artifacts"] is True
    assert receipt["checks"]["workflow_installs_declared_lock"] is True
    assert receipt["checks"]["workflow_runs_dependency_consistency_check"] is True
    assert receipt["checks"]["workflow_uses_authoritative_runner"] is True
    assert receipt["checks"]["workflow_verifies_lock_before_install"] is True
    assert len(receipt["locked_packages"]) == 18


def test_lock_verification_fails_closed_after_hash_tampering(tmp_path):
    module = load_module()
    tampered = tmp_path / LOCK.name
    text = LOCK.read_text(encoding="utf-8")
    tampered.write_text(text.replace("iniconfig==2.3.0", "iniconfig==2.2.0", 1), encoding="utf-8")

    receipt = module.verify_lock(lock_path=tampered)

    assert receipt["passed"] is False
    assert receipt["status"] == "DEPENDENCY_LOCK_FAIL_CLOSED"
    assert receipt["checks"]["lock_sha256_matched"] is False


def test_lock_verification_fails_closed_when_ci_skips_verifier(tmp_path):
    module = load_module()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "requirements-reviewer.txt").write_bytes(
        (ROOT / "requirements-reviewer.txt").read_bytes()
    )
    (tmp_path / LOCK.name).write_bytes(LOCK.read_bytes())
    workflow = WORKFLOW.read_text(encoding="utf-8").replace(
        "          python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py\n", ""
    )
    (tmp_path / ".github" / "workflows" / WORKFLOW.name).write_text(
        workflow, encoding="utf-8"
    )

    receipt = module.verify_lock(root=tmp_path, protocol_path=PROTOCOL)

    assert receipt["passed"] is False
    assert receipt["checks"]["workflow_verifies_lock_before_install"] is False


def test_lock_parser_rejects_unhashed_or_remote_requirements(tmp_path):
    module = load_module()
    unsafe = tmp_path / "unsafe.lock"
    unsafe.write_text(
        "example==1.0 \\\n    --hash=sha256:" + "a" * 64 + "\nhttps://example.invalid/pkg.whl\n",
        encoding="utf-8",
    )

    entries, errors = module.parse_lock(unsafe)

    assert "example" in entries
    assert entries["example"]["hashes"] == ["a" * 64]
    assert errors == ["unsupported lock syntax at line 3"]
    assert "https://" in unsafe.read_text(encoding="utf-8")
