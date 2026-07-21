from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "RUN_CODECHECK_REVIEWER_CONTAINER.py"
CONFIG = ROOT / "config" / "codecheck_reviewer_container_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "codecheck_reviewer_container", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_container_protocol_is_digest_pinned_and_claim_bounded():
    config = load_config()
    recipe = config["recipe"]

    assert config["schema"] == "codecheck_reviewer_container_protocol.v1"
    assert recipe["base_image"]["platform"] == "linux/amd64"
    assert recipe["base_image"]["index_digest"].startswith("sha256:")
    assert recipe["base_image"]["platform_manifest_digest"].startswith("sha256:")
    assert recipe["uv"]["version"] == "0.11.28"
    assert len(recipe["uv"]["archive_sha256"]) == 64
    assert recipe["python"] == "3.11.9"
    assert config["execution"]["network"] == "none"
    assert config["execution"]["read_only"] is True
    assert config["execution"]["cap_drop"] == ["ALL"]
    assert config["execution"]["security_opt"] == ["no-new-privileges"]
    assert "not independent execution" in config["claim_boundary"]
    assert "fresh action-time HumanUnlock" in config["human_unlock_policy"]


def test_public_container_recipe_passes_static_inspection():
    module = load_module()
    result = module.inspect_recipe(load_config())

    assert result["passed"] is True
    assert all(result["checks"].values())
    assert all(
        isinstance(result[key], str) and len(result[key]) == 64
        for key in (
            "dockerfile_sha256",
            "runner_sha256",
            "orchestrator_sha256",
            "runtime_config_sha256",
        )
    )


def test_docker_commands_pin_build_and_fail_closed_runtime_controls(tmp_path):
    module = load_module()
    config = load_config()
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    image = "lumencore-codecheck-reviewer:abc123"
    commit = "a" * 40

    build = module.docker_build_command(source, config, image)
    run = module.docker_run_command(source, output, config, image, commit)

    assert build[:4] == ["docker", "build", "--pull", "--no-cache"]
    assert "--progress=plain" in build
    assert ["--platform", "linux/amd64"] == build[
        build.index("--platform") : build.index("--platform") + 2
    ]
    assert build[-3:] == ["--tag", image, str(source)]
    assert run[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == run[
        run.index("--network") : run.index("--network") + 2
    ]
    assert "--read-only" in run
    assert ["--cap-drop", "ALL"] == run[
        run.index("--cap-drop") : run.index("--cap-drop") + 2
    ]
    assert ["--security-opt", "no-new-privileges"] == run[
        run.index("--security-opt") : run.index("--security-opt") + 2
    ]
    assert ["--pids-limit", "512"] == run[
        run.index("--pids-limit") : run.index("--pids-limit") + 2
    ]
    assert ["--memory", "4g"] == run[
        run.index("--memory") : run.index("--memory") + 2
    ]
    assert ["--cpus", "4"] == run[run.index("--cpus") : run.index("--cpus") + 2]
    assert run.count("--tmpfs") == 2
    assert f"CODECHECK_SOURCE_COMMIT={commit}" in run
    mounts = [run[index + 1] for index, value in enumerate(run) if value == "--mount"]
    assert len(mounts) == 2
    assert mounts[0].endswith("target=/input,readonly")
    assert mounts[1].endswith("target=/output")
    assert run[-1] == image


def write_synthetic_bundle(path: Path, *, unsafe_name: str | None = None) -> None:
    content = b"bounded\n"
    row = {
        "path": "data.txt",
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "hash_mode": "utf8_lf",
    }
    manifest = {
        "schema": "codecheck_eia_release_manifest.v1",
        "source_commit": "b" * 40,
        "source_commit_utc": "2026-07-21T00:00:00Z",
        "bundle_inputs": [row],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("capsule/data.txt", content)
        archive.writestr(
            "capsule/RELEASE_MANIFEST.json",
            json.dumps(manifest, sort_keys=True),
        )
        archive.writestr("capsule/RELEASE_NOTES.md", "bounded\n")
        if unsafe_name:
            archive.writestr(unsafe_name, "unsafe")


def test_release_bundle_validation_reconciles_exact_manifest(tmp_path):
    module = load_module()
    bundle = tmp_path / "bundle.zip"
    write_synthetic_bundle(bundle)

    result = module.validate_bundle_archive(bundle)

    assert result["verified"] is True
    assert result["source_commit"] == "b" * 40
    assert result["bundle_input_count"] == 1
    assert result["entry_count"] == 3
    assert result["row_checks"] == [
        {"path": "data.txt", "bytes_matched": True, "sha256_matched": True}
    ]


def test_release_bundle_validation_rejects_path_escape(tmp_path):
    module = load_module()
    bundle = tmp_path / "unsafe.zip"
    write_synthetic_bundle(bundle, unsafe_name="../escape.txt")

    with pytest.raises(ValueError, match="unsafe bundle entry"):
        module.validate_bundle_archive(bundle)


def test_machine_receipt_preserves_external_gates_and_redacts_host_paths(tmp_path):
    module = load_module()
    config = load_config()
    output = tmp_path / "output"
    output.mkdir()
    runtime = {
        "status": "AUTHORITATIVE_RUNTIME_PASS",
        "passed": True,
        "observed": {"python": "3.11.9"},
        "checks": {"python": True},
        "independent_execution_complete": False,
        "external_validation_complete": False,
    }
    capsule = {
        "status": "BOUNDED_REPRODUCIBILITY_PASS",
        "summary": {
            "suite_count": 3,
            "suite_pass_count": 3,
            "assertion_count": 31,
            "assertion_pass_count": 31,
            "external_validation_complete": False,
        },
    }
    (output / "runtime_receipt.json").write_text(json.dumps(runtime), encoding="utf-8")
    (output / "reviewer_reproducibility_receipt.json").write_text(
        json.dumps(capsule), encoding="utf-8"
    )
    (output / "reviewer_suite_sbom.cdx.json").write_text("{}", encoding="utf-8")
    for name in ("eia_wave.log", "eia_residual.log", "mda_open_set.log", "fixture_tests.log"):
        path = output / "logs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n", encoding="utf-8")
    completed = subprocess.CompletedProcess([], 0, "", "")
    receipt = module.build_receipt(
        config=config,
        recipe=module.inspect_recipe(config),
        bundle={
            "verified": True,
            "source_commit": "c" * 40,
            "source_commit_utc": "2026-07-21T00:00:00Z",
            "bundle_input_count": 1,
            "entry_count": 3,
            "release_manifest_sha256": "d" * 64,
        },
        bundle_sha256="e" * 64,
        image_tag="lumencore-codecheck-reviewer:test",
        image_id="sha256:" + "f" * 64,
        build_result=completed,
        run_result=completed,
        output_dir=output,
    )

    assert receipt["status"] == "OPERATOR_CONTAINER_REBUILD_PASS"
    assert receipt["passed"] is True
    assert all(receipt["checks"].values())
    assert receipt["operator_controlled"] is True
    assert receipt["independent_execution_complete"] is False
    assert receipt["external_validation_complete"] is False
    rendered = json.dumps(receipt, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "<SOURCE_DIR>" in rendered
    assert "<OUTPUT_DIR>" in rendered
