#!/usr/bin/env python3
"""Rebuild and run the bounded reviewer capsule in a pinned Docker image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "codecheck_reviewer_container_v1.json"
RECEIPT_NAME = "container_rebuild_receipt.json"
CHECKSUM_NAME = "SHA256SUMS"


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def portable_bytes(raw: bytes, hash_mode: str) -> bytes:
    if hash_mode == "binary":
        return raw
    if hash_mode != "utf8_lf":
        raise ValueError(f"unsupported bundle hash mode: {hash_mode}")
    text = raw.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def inspect_recipe(config: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    recipe = config["recipe"]
    dockerfile = root / recipe["dockerfile_path"]
    runner = root / recipe["runner_path"]
    orchestrator = root / recipe["orchestrator_path"]
    runtime_config = root / recipe["runtime_config_path"]
    docker_text = dockerfile.read_text(encoding="utf-8") if dockerfile.is_file() else ""
    runner_text = runner.read_text(encoding="utf-8") if runner.is_file() else ""
    base = recipe["base_image"]
    uv = recipe["uv"]
    expected_from = (
        f"FROM {base['repository']}:{base['tag']}"
        f"@{base['platform_manifest_digest']}"
    )
    checks = {
        "schema_matched": config.get("schema")
        == "codecheck_reviewer_container_protocol.v1",
        "dockerfile_present": dockerfile.is_file(),
        "runner_present": runner.is_file(),
        "orchestrator_present": orchestrator.is_file(),
        "runtime_config_present": runtime_config.is_file(),
        "base_platform_exact": base.get("platform") == "linux/amd64",
        "base_index_digest_pinned": str(base.get("index_digest", "")).startswith(
            "sha256:"
        ),
        "base_manifest_digest_pinned": str(
            base.get("platform_manifest_digest", "")
        ).startswith("sha256:"),
        "dockerfile_base_exact": expected_from in docker_text,
        "uv_version_pinned": f"ARG UV_VERSION={uv['version']}" in docker_text,
        "uv_archive_hash_pinned": f"ARG UV_SHA256={uv['archive_sha256']}"
        in docker_text,
        "python_version_pinned": f"uv python install {recipe['python']}"
        in docker_text,
        "locked_install_enforced": "--require-hashes" in docker_text
        and "--only-binary=:all:" in docker_text,
        "runner_requires_release_manifest": "/input/RELEASE_MANIFEST.json"
        in runner_text,
        "runner_requires_empty_output": "The output mount must be empty"
        in runner_text,
        "runner_verifies_exact_runtime": "VERIFY_CODECHECK_REVIEWER_RUNTIME.py"
        in runner_text,
        "runner_executes_bounded_capsule": "RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py"
        in runner_text,
        "runner_uses_source_relative_output": "--run-dir out/codecheck_eia"
        in runner_text
        or '--run-dir "${CODECHECK_RUN_DIR}"' in runner_text,
        "runner_exports_completed_outputs": 'cp -a "${CODECHECK_RUN_DIR}/." /output/'
        in runner_text,
        "runner_preserves_failed_outputs": "trap copy_capsule_outputs EXIT"
        in runner_text,
        "claim_boundary_present": bool(config.get("claim_boundary")),
        "human_unlock_policy_present": bool(config.get("human_unlock_policy")),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "dockerfile_sha256": file_sha256(dockerfile) if dockerfile.is_file() else None,
        "runner_sha256": file_sha256(runner) if runner.is_file() else None,
        "orchestrator_sha256": (
            file_sha256(orchestrator) if orchestrator.is_file() else None
        ),
        "runtime_config_sha256": (
            file_sha256(runtime_config) if runtime_config.is_file() else None
        ),
    }


def validate_bundle_archive(bundle_path: Path) -> dict[str, Any]:
    if not bundle_path.is_file():
        raise FileNotFoundError(bundle_path)
    with zipfile.ZipFile(bundle_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos if not info.is_dir()]
        if not names or len(names) != len(set(names)):
            raise ValueError("bundle entries are empty or duplicated")
        top_levels: set[str] = set()
        for info in infos:
            name = info.filename
            if "\\" in name:
                raise ValueError(f"bundle entry uses backslashes: {name}")
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise ValueError(f"unsafe bundle entry: {name}")
            if (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                raise ValueError(f"symlink bundle entry is not allowed: {name}")
            top_levels.add(pure.parts[0])
        if len(top_levels) != 1:
            raise ValueError("bundle must contain exactly one top-level directory")
        top = next(iter(top_levels))
        manifest_name = f"{top}/RELEASE_MANIFEST.json"
        notes_name = f"{top}/RELEASE_NOTES.md"
        if manifest_name not in names or notes_name not in names:
            raise ValueError("bundle release manifest or notes are missing")
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
        if manifest.get("schema") != "codecheck_eia_release_manifest.v1":
            raise ValueError("unexpected release-manifest schema")
        rows = manifest.get("bundle_inputs", [])
        expected_names = {
            f"{top}/{row['path']}" for row in rows
        } | {manifest_name, notes_name}
        if set(names) != expected_names:
            raise ValueError("bundle entries do not match the release manifest")
        row_checks = []
        for row in rows:
            name = f"{top}/{row['path']}"
            content = portable_bytes(archive.read(name), row["hash_mode"])
            row_checks.append(
                {
                    "path": row["path"],
                    "bytes_matched": len(content) == row["bytes"],
                    "sha256_matched": hashlib.sha256(content).hexdigest()
                    == row["sha256"],
                }
            )
        if not row_checks or not all(
            row["bytes_matched"] and row["sha256_matched"] for row in row_checks
        ):
            raise ValueError("one or more bundle inputs failed hash reconciliation")
        return {
            "verified": True,
            "source_commit": manifest["source_commit"],
            "source_commit_utc": manifest["source_commit_utc"],
            "bundle_input_count": len(rows),
            "entry_count": len(names),
            "top_level_directory": top,
            "release_manifest_sha256": hashlib.sha256(
                archive.read(manifest_name)
            ).hexdigest(),
            "row_checks": row_checks,
        }


def extract_bundle(bundle_path: Path, destination: Path) -> tuple[Path, dict[str, Any]]:
    verification = validate_bundle_archive(bundle_path)
    top = verification["top_level_directory"]
    with zipfile.ZipFile(bundle_path) as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            target = destination.joinpath(*pure.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info.filename))
    return destination / top, verification


def docker_host_path(path: Path) -> str:
    value = path.resolve().as_posix() if os.name == "nt" else str(path.resolve())
    if "," in value:
        raise ValueError("Docker bind paths containing commas are not supported")
    return value


def docker_build_command(
    source_dir: Path, config: dict[str, Any], image_tag: str
) -> list[str]:
    recipe = config["recipe"]
    return [
        "docker",
        "build",
        "--pull",
        "--no-cache",
        "--progress=plain",
        "--platform",
        recipe["base_image"]["platform"],
        "--file",
        str(source_dir / recipe["dockerfile_path"]),
        "--tag",
        image_tag,
        str(source_dir),
    ]


def docker_run_command(
    source_dir: Path,
    output_dir: Path,
    config: dict[str, Any],
    image_tag: str,
    source_commit: str,
) -> list[str]:
    execution = config["execution"]
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        config["recipe"]["base_image"]["platform"],
        "--network",
        execution["network"],
        "--read-only",
    ]
    for capability in execution["cap_drop"]:
        command.extend(["--cap-drop", capability])
    for option in execution["security_opt"]:
        command.extend(["--security-opt", option])
    command.extend(["--pids-limit", str(execution["pids_limit"])])
    command.extend(["--memory", execution["memory"]])
    command.extend(["--cpus", execution["cpus"]])
    for mount in execution["tmpfs"]:
        command.extend(["--tmpfs", mount])
    command.extend(["--env", f"CODECHECK_SOURCE_COMMIT={source_commit}"])
    command.extend(
        [
            "--mount",
            (
                f"type=bind,source={docker_host_path(source_dir)},"
                f"target={execution['input_mount']},readonly"
            ),
            "--mount",
            (
                f"type=bind,source={docker_host_path(output_dir)},"
                f"target={execution['output_mount']}"
            ),
            image_tag,
        ]
    )
    return command


def command_templates(config: dict[str, Any], image_tag: str) -> dict[str, list[str]]:
    execution = config["execution"]
    recipe = config["recipe"]
    build = [
        "docker",
        "build",
        "--pull",
        "--no-cache",
        "--progress=plain",
        "--platform",
        recipe["base_image"]["platform"],
        "--file",
        f"<SOURCE_DIR>/{recipe['dockerfile_path']}",
        "--tag",
        image_tag,
        "<SOURCE_DIR>",
    ]
    run = [
        "docker",
        "run",
        "--rm",
        "--platform",
        recipe["base_image"]["platform"],
        "--network",
        execution["network"],
        "--read-only",
    ]
    for capability in execution["cap_drop"]:
        run.extend(["--cap-drop", capability])
    for option in execution["security_opt"]:
        run.extend(["--security-opt", option])
    run.extend(["--pids-limit", str(execution["pids_limit"])])
    run.extend(["--memory", execution["memory"]])
    run.extend(["--cpus", execution["cpus"]])
    for mount in execution["tmpfs"]:
        run.extend(["--tmpfs", mount])
    run.extend(
        [
            "--env",
            "CODECHECK_SOURCE_COMMIT=<SOURCE_COMMIT>",
            "--mount",
            f"type=bind,source=<SOURCE_DIR>,target={execution['input_mount']},readonly",
            "--mount",
            f"type=bind,source=<OUTPUT_DIR>,target={execution['output_mount']}",
            image_tag,
        ]
    )
    return {"build": build, "run": run}


def run_process(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def artifact_rows(output_dir: Path) -> list[dict[str, Any]]:
    excluded = {RECEIPT_NAME, CHECKSUM_NAME}
    return [
        {
            "path": path.relative_to(output_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name not in excluded
    ]


def build_receipt(
    *,
    config: dict[str, Any],
    recipe: dict[str, Any],
    bundle: dict[str, Any],
    bundle_sha256: str,
    image_tag: str,
    image_id: str | None,
    build_result: subprocess.CompletedProcess[str],
    run_result: subprocess.CompletedProcess[str] | None,
    output_dir: Path,
) -> dict[str, Any]:
    runtime_path = output_dir / "runtime_receipt.json"
    capsule_path = output_dir / "reviewer_reproducibility_receipt.json"
    runtime = read_json(runtime_path) if runtime_path.is_file() else {}
    capsule = read_json(capsule_path) if capsule_path.is_file() else {}
    expected_outputs = config["expected_outputs"]
    outputs_present = {
        relative_path: (output_dir / relative_path).is_file()
        for relative_path in expected_outputs
    }
    checks = {
        "recipe_static_checks_passed": recipe["passed"],
        "bundle_verified": bundle["verified"],
        "docker_build_passed": build_result.returncode == 0,
        "docker_run_passed": run_result is not None and run_result.returncode == 0,
        "image_id_observed": bool(image_id),
        "expected_outputs_present": all(outputs_present.values()),
        "runtime_passed": runtime.get("passed") is True,
        "runtime_independent_execution_false": runtime.get(
            "independent_execution_complete"
        )
        is False,
        "runtime_external_validation_false": runtime.get(
            "external_validation_complete"
        )
        is False,
        "capsule_passed": capsule.get("status")
        == "BOUNDED_REPRODUCIBILITY_PASS",
        "capsule_suites_3_of_3": capsule.get("summary", {}).get(
            "suite_pass_count"
        )
        == capsule.get("summary", {}).get("suite_count")
        == 3,
        "capsule_assertions_31_of_31": capsule.get("summary", {}).get(
            "assertion_pass_count"
        )
        == capsule.get("summary", {}).get("assertion_count")
        == 31,
        "capsule_external_validation_false": capsule.get("summary", {}).get(
            "external_validation_complete"
        )
        is False,
    }
    passed = all(checks.values())
    payload: dict[str, Any] = {
        "schema": "codecheck_reviewer_container_run_receipt.v1",
        "protocol_id": config["protocol_id"],
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "status": "OPERATOR_CONTAINER_REBUILD_PASS" if passed else "CONTAINER_REBUILD_BLOCKED",
        "passed": passed,
        "checks": checks,
        "source_bundle": {
            "sha256": bundle_sha256,
            "source_commit": bundle["source_commit"],
            "source_commit_utc": bundle["source_commit_utc"],
            "bundle_input_count": bundle["bundle_input_count"],
            "entry_count": bundle["entry_count"],
            "release_manifest_sha256": bundle["release_manifest_sha256"],
        },
        "recipe": {
            "base_image": config["recipe"]["base_image"],
            "uv": config["recipe"]["uv"],
            "python": config["recipe"]["python"],
            "dockerfile_sha256": recipe["dockerfile_sha256"],
            "runner_sha256": recipe["runner_sha256"],
            "orchestrator_sha256": recipe["orchestrator_sha256"],
            "runtime_config_sha256": recipe["runtime_config_sha256"],
        },
        "execution_controls": config["execution"],
        "command_templates": command_templates(config, image_tag),
        "image": {"tag": image_tag, "id": image_id},
        "build_returncode": build_result.returncode,
        "run_returncode": run_result.returncode if run_result is not None else None,
        "expected_outputs": outputs_present,
        "artifacts": artifact_rows(output_dir),
        "runtime_summary": {
            "status": runtime.get("status"),
            "observed": runtime.get("observed"),
            "checks": runtime.get("checks"),
        },
        "capsule_summary": capsule.get("summary"),
        "operator_controlled": True,
        "independent_execution_complete": False,
        "external_validation_complete": False,
        "claim_boundary": config["claim_boundary"],
        "human_unlock_policy": config["human_unlock_policy"],
    }
    payload["receipt_payload_sha256"] = canonical_sha256(payload)
    return payload


def write_checksums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != CHECKSUM_NAME:
            rows.append(
                f"{file_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n"
            )
    (output_dir / CHECKSUM_NAME).write_text(
        "".join(rows), encoding="utf-8", newline="\n"
    )


def execute(
    *, bundle_path: Path, output_dir: Path, config: dict[str, Any], image_tag: str | None
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lumencore-codecheck-bundle-") as temp:
        source_dir, bundle = extract_bundle(bundle_path, Path(temp))
        recipe = inspect_recipe(config, root=source_dir)
        if not recipe["passed"]:
            raise ValueError("the extracted container recipe failed static checks")
        resolved_tag = image_tag or (
            f"{config['recipe']['image_tag_prefix']}:{bundle['source_commit'][:12]}"
        )
        build_result = run_process(
            docker_build_command(source_dir, config, resolved_tag)
        )
        run_result: subprocess.CompletedProcess[str] | None = None
        image_id: str | None = None
        if build_result.returncode == 0:
            inspect_result = run_process(
                ["docker", "image", "inspect", resolved_tag, "--format", "{{.Id}}"]
            )
            if inspect_result.returncode == 0:
                image_id = inspect_result.stdout.strip() or None
            run_result = run_process(
                docker_run_command(
                    source_dir,
                    output_dir,
                    config,
                    resolved_tag,
                    bundle["source_commit"],
                )
            )
        (output_dir / "docker_build_stdout.txt").write_text(
            build_result.stdout, encoding="utf-8", newline="\n"
        )
        (output_dir / "docker_build_stderr.txt").write_text(
            build_result.stderr, encoding="utf-8", newline="\n"
        )
        if run_result is not None:
            (output_dir / "docker_run_stdout.txt").write_text(
                run_result.stdout, encoding="utf-8", newline="\n"
            )
            (output_dir / "docker_run_stderr.txt").write_text(
                run_result.stderr, encoding="utf-8", newline="\n"
            )
        receipt = build_receipt(
            config=config,
            recipe=recipe,
            bundle=bundle,
            bundle_sha256=file_sha256(bundle_path),
            image_tag=resolved_tag,
            image_id=image_id,
            build_result=build_result,
            run_result=run_result,
            output_dir=output_dir,
        )
        write_json(output_dir / RECEIPT_NAME, receipt)
        write_checksums(output_dir)
        return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--bundle-zip", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--image-tag")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = read_json(args.config.resolve())
        if not args.execute:
            result = inspect_recipe(config)
            print(
                json.dumps(
                    {
                        "status": "CONTAINER_RECIPE_READY" if result["passed"] else "CONTAINER_RECIPE_BLOCKED",
                        "checks": result["checks"],
                        "independent_execution_complete": False,
                        "external_validation_complete": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if result["passed"] else 1
        if args.bundle_zip is None or args.output_dir is None:
            raise ValueError("--bundle-zip and --output-dir are required with --execute")
        receipt = execute(
            bundle_path=args.bundle_zip.resolve(),
            output_dir=args.output_dir.resolve(),
            config=config,
            image_tag=args.image_tag,
        )
        print(
            json.dumps(
                {
                    "status": receipt["status"],
                    "passed": receipt["passed"],
                    "receipt_payload_sha256": receipt["receipt_payload_sha256"],
                    "independent_execution_complete": False,
                    "external_validation_complete": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if receipt["passed"] else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "CONTAINER_REBUILD_BLOCKED",
                    "reason": str(exc),
                    "independent_execution_complete": False,
                    "external_validation_complete": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
