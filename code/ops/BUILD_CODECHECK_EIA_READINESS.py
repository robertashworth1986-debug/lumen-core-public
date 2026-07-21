from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "codecheck_eia_readiness_v1.json"
SCRIPT_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests" / "test_codecheck_eia_readiness.py"
OUT_JSON = (
    ROOT
    / "evidence"
    / "external_validation"
    / "codecheck_eia_author_readiness_20260720.json"
)
OUT_MD = ROOT / "docs" / "CODECHECK_EIA_AUTHOR_READINESS_2026-07-20.md"

PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.I),
    re.compile(r"private_estate", re.I),
    re.compile(r"cp575notice", re.I),
    re.compile(
        r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}",
        re.I,
    ),
)
ROOT_KEY_PATTERN = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?:\s|$)")
MANIFEST_FILE_PATTERN = re.compile(r"^\s+-\s+file:\s+(?P<value>.+?)\s*$")
PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page\b")

PREPRINT_REQUIRED_TOKENS = (
    "## Abstract",
    "## 1. Research Question And Claim Boundary",
    "## 3. Methods",
    "## 4. Frozen Results To Reproduce",
    "## 5. Preserved Failure And Protocol Amendment",
    "## 7. Limitations",
    "## 8. Data, Code, And Reproduction Availability",
    "## 9. Ethics, Funding, And Competing Interests",
    "## 10. Author Contribution",
)
PREPRINT_BOUNDARY_TOKENS = (
    "Not peer reviewed. No external validation or CODECHECK certificate has been issued.",
    "This result establishes first-party executable reproducibility only.",
    "No CODECHECK issue, codechecker assignment, certificate, journal review, or DOI exists",
    "A stable preprint identifier, immutable source release identifier, CODECHECK register issue, independent execution receipt, and certificate remain open gates.",
)
REQUEST_HOLD_TOKENS = (
    "HOLD_IDENTIFIER_COLLISION_DUPLICATE_RECHECK_AND_HUMANUNLOCK",
    "[IDENTIFIER_ASSIGNED_AT_ACTION_TIME]",
    "Leave unassigned.",
    "identifier collision",
    "fresh action-time HumanUnlock",
    "has not been posted, emailed, submitted, assigned, or accepted",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        text.rstrip("\r\n") + "\n",
        encoding="utf-8",
        newline="\n",
    )


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def display_path(path: Path) -> str:
    try:
        return repo_path(path)
    except ValueError:
        return path.resolve().as_posix()


def portable_file_bytes(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    if path.suffix.lower() in {".gz", ".zip", ".png", ".pdf"}:
        return raw, "raw"
    normalized = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8"), "utf8_lf"


def artifact_row(path: Path) -> dict[str, Any]:
    content, hash_mode = portable_file_bytes(path)
    return {
        "path": repo_path(path),
        "bytes": len(content),
        "hash_mode": hash_mode,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def _safe_manifest_path(value: str) -> bool:
    if not value or value.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    path = PurePosixPath(value.replace("\\", "/"))
    return ".." not in path.parts and "." not in path.parts


def parse_codecheck_config(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    root_keys: list[str] = []
    manifest: list[str] = []
    current_root: str | None = None

    for line in lines:
        root_match = ROOT_KEY_PATTERN.match(line)
        if root_match:
            current_root = root_match.group("key")
            root_keys.append(current_root)
            continue
        if current_root == "manifest":
            manifest_match = MANIFEST_FILE_PATTERN.match(line)
            if manifest_match:
                manifest.append(_yaml_scalar(manifest_match.group("value")))

    reference_match = re.search(
        r"^\s+reference:\s+(?P<value>.+?)\s*$", text, flags=re.MULTILINE
    )

    return {
        "utf8_decoded": True,
        "explicit_document_start": any(line.strip() == "---" for line in lines),
        "yaml_directive": next(
            (line.strip() for line in lines if line.strip().startswith("%YAML")),
            None,
        ),
        "version": next(
            (
                _yaml_scalar(line.split(":", 1)[1])
                for line in lines
                if line.startswith("version:")
            ),
            None,
        ),
        "root_keys": root_keys,
        "manifest": manifest,
        "manifest_paths_safe": all(_safe_manifest_path(value) for value in manifest),
        "manifest_paths_unique": len(manifest) == len(set(manifest)),
        "paper_title_present": bool(
            re.search(r"^\s+title:\s+.+$", text, flags=re.MULTILINE)
        ),
        "paper_reference": (
            _yaml_scalar(reference_match.group("value"))
            if reference_match
            else None
        ),
        "corresponding_author_present": bool(
            re.search(r"^\s+-\s+name:\s+.+$", text, flags=re.MULTILINE)
        ),
        "codechecker_metadata_present": "codechecker" in root_keys,
        "report_metadata_present": "report" in root_keys,
    }


def load_authority_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        "external_validation_authority_docket_for_codecheck", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_release_candidate_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        "codecheck_eia_release_candidate_for_readiness", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_private(value: Any) -> list[str]:
    rendered = json.dumps(value, sort_keys=True, default=str)
    return [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(rendered)]


def reconcile_archived_sources(
    receipt: dict[str, Any], noncomputational_paths: set[str]
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for archived in receipt["source_artifacts"]:
        path = ROOT / archived["path"]
        if path.is_file():
            content, _ = portable_file_bytes(path)
            actual_sha256 = hashlib.sha256(content).hexdigest()
            actual_bytes = len(content)
        else:
            actual_sha256 = None
            actual_bytes = None
        current_match = (
            actual_sha256 == archived["sha256"]
            and actual_bytes == archived["bytes"]
        )
        rows.append(
            {
                "path": archived["path"],
                "role": (
                    "documentation_or_packaging"
                    if archived["path"] in noncomputational_paths
                    else "computational_identity"
                ),
                "archived_sha256": archived["sha256"],
                "current_sha256": actual_sha256,
                "current_match": current_match,
            }
        )

    computational_rows = [
        row for row in rows if row["role"] == "computational_identity"
    ]
    mismatch_paths = [row["path"] for row in rows if not row["current_match"]]
    return {
        "archived_source_count": len(rows),
        "current_match_count": sum(row["current_match"] for row in rows),
        "full_source_exact_match": all(row["current_match"] for row in rows),
        "computational_identity_path_count": len(computational_rows),
        "computational_identity_exact_match": all(
            row["current_match"] for row in computational_rows
        ),
        "mismatch_count": len(mismatch_paths),
        "mismatch_paths": mismatch_paths,
        "rows": rows,
    }


def verify_operator_clean_runner(
    control: dict[str, Any], *, receipt_path: Path | None = None
) -> dict[str, Any]:
    path = receipt_path or (ROOT / control["receipt_path"])
    receipt = read_json(path)
    summary = receipt.get("summary", {})
    source_reconciliation = reconcile_archived_sources(
        receipt,
        set(control.get("noncomputational_documentation_or_packaging_paths", [])),
    )
    private_hits = scan_private(receipt)
    checks = {
        "receipt_sha256_matched": file_sha256(path)
        == control["receipt_sha256"],
        "schema_matched": receipt.get("schema") == control["expected_schema"],
        "status_matched": receipt.get("status") == control["expected_status"],
        "source_commit_matched": receipt.get("git", {}).get("commit")
        == control["source_commit"],
        "relevant_source_clean": summary.get("relevant_source_clean") is True,
        "clean_runner_replay": summary.get("clean_runner_replay") is True,
        "authoritative_runtime_matched": summary.get(
            "authoritative_runtime_match"
        )
        is True,
        "dependency_lock_passed": receipt.get("dependency_lock", {}).get(
            "passed"
        )
        is True,
        "dependency_closure_exact_match": summary.get(
            "dependency_closure_exact_match"
        )
        is True,
        "dependency_versions_exact_match": summary.get(
            "dependency_versions_exact_match"
        )
        is True,
        "fixture_tests_passed": summary.get("fixture_tests_passed") is True,
        "suites_matched": summary.get("suite_count")
        == summary.get("suite_pass_count")
        == control["expected_suite_count"],
        "assertions_matched": summary.get("assertion_count")
        == summary.get("assertion_pass_count")
        == control["expected_assertion_count"],
        "privacy_scan_passed": receipt.get("privacy_scan", {}).get("passed")
        is True
        and not private_hits,
        "external_validation_remains_false": summary.get(
            "external_validation_complete"
        )
        is False,
        "declared_computational_identity_still_matches": source_reconciliation[
            "computational_identity_exact_match"
        ],
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "receipt_path": control["receipt_path"],
        "receipt_sha256": file_sha256(path),
        "schema": receipt.get("schema"),
        "status": receipt.get("status"),
        "generated_utc": receipt.get("generated_utc"),
        "source_commit": receipt.get("git", {}).get("commit"),
        "source_chain_sha256": receipt.get("source_chain_sha256"),
        "capsule_sha256": receipt.get("capsule_sha256"),
        "suite_count": summary.get("suite_count"),
        "suite_pass_count": summary.get("suite_pass_count"),
        "assertion_count": summary.get("assertion_count"),
        "assertion_pass_count": summary.get("assertion_pass_count"),
        "relevant_source_clean": summary.get("relevant_source_clean"),
        "clean_runner_replay": summary.get("clean_runner_replay"),
        "authoritative_runtime_match": summary.get("authoritative_runtime_match"),
        "dependency_closure_exact_match": summary.get(
            "dependency_closure_exact_match"
        ),
        "fixture_tests_passed": summary.get("fixture_tests_passed"),
        "external_validation_complete": summary.get(
            "external_validation_complete"
        ),
        "source_reconciliation": source_reconciliation,
        "configured_private_pattern_hit_count": len(private_hits),
        "execution_control": control["execution_control"],
        "policy": control["policy"],
    }


def verify_reviewer_runtime(
    control: dict[str, Any], *, receipt_path: Path | None = None
) -> dict[str, Any]:
    path = receipt_path or (ROOT / control["receipt_path"])
    receipt = read_json(path)
    runtime_config = read_json(ROOT / control["config_path"])
    receipt_checks = receipt.get("checks", {})
    source_rows = receipt.get("source", {}).get("files", [])
    source_reconciliation = []
    for row in source_rows:
        relative_path = row.get("path", "")
        current_path = ROOT / relative_path
        current_sha256 = file_sha256(current_path) if current_path.is_file() else None
        source_reconciliation.append(
            {
                "path": relative_path,
                "receipt_sha256": row.get("sha256"),
                "current_sha256": current_sha256,
                "current_match": current_sha256 == row.get("sha256"),
            }
        )
    receipt_without_hash = {
        key: value
        for key, value in receipt.items()
        if key != "receipt_payload_sha256"
    }
    private_hits = scan_private(receipt)
    checks = {
        "receipt_sha256_matched": file_sha256(path) == control["receipt_sha256"],
        "receipt_payload_sha256_matched": receipt.get("receipt_payload_sha256")
        == canonical_sha256(receipt_without_hash),
        "schema_matched": receipt.get("schema") == control["expected_schema"],
        "protocol_id_matched": receipt.get("protocol_id")
        == control["expected_protocol_id"],
        "status_matched": receipt.get("status") == control["expected_status"],
        "passed": receipt.get("passed") is True,
        "expected_runtime_matches_config": receipt.get("expected")
        == runtime_config.get("expected"),
        "runtime_check_set_exact": sorted(receipt_checks)
        == sorted(control["expected_checks"]),
        "all_runtime_checks_passed": bool(receipt_checks)
        and all(value is True for value in receipt_checks.values()),
        "source_commit_declared": receipt.get("source", {}).get(
            "repository_commit_declared_by_operator"
        )
        == control["source_commit"],
        "source_files_present": bool(source_rows)
        and all(row["current_sha256"] for row in source_reconciliation),
        "source_files_current": bool(source_reconciliation)
        and all(row["current_match"] for row in source_reconciliation),
        "source_chain_sha256_matched": receipt.get("source", {}).get(
            "source_chain_sha256"
        )
        == canonical_sha256(source_rows),
        "operator_controlled": receipt.get("operator_controlled") is True,
        "independent_execution_remains_false": receipt.get(
            "independent_execution_complete"
        )
        is False,
        "external_validation_remains_false": receipt.get(
            "external_validation_complete"
        )
        is False,
        "privacy_scan_passed": not private_hits,
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "receipt_path": control["receipt_path"],
        "receipt_sha256": file_sha256(path),
        "receipt_payload_sha256": receipt.get("receipt_payload_sha256"),
        "schema": receipt.get("schema"),
        "protocol_id": receipt.get("protocol_id"),
        "status": receipt.get("status"),
        "generated_utc": receipt.get("generated_utc"),
        "source_commit": receipt.get("source", {}).get(
            "repository_commit_declared_by_operator"
        ),
        "runtime_check_count": len(receipt_checks),
        "runtime_check_pass_count": sum(value is True for value in receipt_checks.values()),
        "expected": receipt.get("expected"),
        "observed": receipt.get("observed"),
        "source_reconciliation": source_reconciliation,
        "operator_controlled": receipt.get("operator_controlled"),
        "independent_execution_complete": receipt.get(
            "independent_execution_complete"
        ),
        "external_validation_complete": receipt.get(
            "external_validation_complete"
        ),
        "configured_private_pattern_hit_count": len(private_hits),
        "policy": control["policy"],
    }


def verify_sha256_manifest(path: Path) -> dict[str, Any]:
    rows = []
    artifact_root = path.parent.resolve()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            rows.append(
                {
                    "path": line,
                    "expected_sha256": None,
                    "actual_sha256": None,
                    "path_safe": False,
                    "matched": False,
                }
            )
            continue
        expected_sha256, relative_path = match.groups()
        path_object = PurePosixPath(relative_path)
        artifact_path = path.parent.joinpath(*path_object.parts)
        lexical_path_safe = (
            bool(relative_path)
            and not path_object.is_absolute()
            and ".." not in path_object.parts
            and ":" not in relative_path
            and "\\" not in relative_path
        )
        try:
            resolved_path_safe = artifact_path.resolve().is_relative_to(artifact_root)
        except OSError:
            resolved_path_safe = False
        path_safe = lexical_path_safe and resolved_path_safe
        actual_sha256 = (
            file_sha256(artifact_path)
            if path_safe and artifact_path.is_file()
            else None
        )
        rows.append(
            {
                "path": relative_path,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "path_safe": path_safe,
                "matched": path_safe and actual_sha256 == expected_sha256,
            }
        )
    paths = [row["path"] for row in rows]
    checks = {
        "entries_present": bool(rows),
        "entry_paths_unique": len(paths) == len(set(paths)),
        "entry_paths_safe": all(row["path_safe"] for row in rows),
        "entry_hashes_matched": all(row["matched"] for row in rows),
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "entry_count": len(rows),
        "matched_entry_count": sum(row["matched"] for row in rows),
        "mismatch_paths": [row["path"] for row in rows if not row["matched"]],
        "rows": rows,
    }


def verify_operator_container_rebuild(
    control: dict[str, Any],
    *,
    container_config: dict[str, Any],
    capsule_receipt_path: Path,
    runtime_receipt_path: Path,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    path = receipt_path or (ROOT / control["receipt_path"])
    receipt = read_json(path)
    receipt_without_hash = {
        key: value
        for key, value in receipt.items()
        if key != "receipt_payload_sha256"
    }
    artifacts = {
        row.get("path"): row for row in receipt.get("artifacts", [])
    }
    outer_checks = receipt.get("checks", {})
    expected_outputs = receipt.get("expected_outputs", {})
    runtime_summary = receipt.get("runtime_summary", {})
    runtime_checks = runtime_summary.get("checks", {})
    capsule_summary = receipt.get("capsule_summary", {})
    recipe = receipt.get("recipe", {})
    recipe_control = container_config["recipe"]
    current_recipe_hashes = {
        "dockerfile_sha256": file_sha256(
            ROOT / recipe_control["dockerfile_path"]
        ),
        "runner_sha256": file_sha256(ROOT / recipe_control["runner_path"]),
        "orchestrator_sha256": file_sha256(
            ROOT / recipe_control["orchestrator_path"]
        ),
        "runtime_config_sha256": file_sha256(
            ROOT / recipe_control["runtime_config_path"]
        ),
    }
    capsule_file_sha256 = file_sha256(capsule_receipt_path)
    runtime_file_sha256 = file_sha256(runtime_receipt_path)
    output_manifest_path = ROOT / control["output_manifest_path"]
    output_manifest = verify_sha256_manifest(output_manifest_path)
    output_text = {}
    for row in output_manifest["rows"]:
        artifact_path = output_manifest_path.parent.joinpath(
            *PurePosixPath(row["path"]).parts
        )
        if row["path_safe"] and artifact_path.is_file():
            try:
                output_text[row["path"]] = artifact_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
    private_hits = scan_private({"receipt": receipt, "outputs": output_text})
    checks = {
        "receipt_sha256_matched": file_sha256(path)
        == control["receipt_sha256"],
        "receipt_payload_sha256_matched": receipt.get(
            "receipt_payload_sha256"
        )
        == canonical_sha256(receipt_without_hash),
        "output_manifest_sha256_matched": file_sha256(output_manifest_path)
        == control["output_manifest_sha256"],
        "output_manifest_entry_count_matched": output_manifest["entry_count"]
        == control["expected_output_manifest_entry_count"],
        "output_manifest_verified": output_manifest["verified"],
        "schema_matched": receipt.get("schema") == control["expected_schema"],
        "protocol_id_matched": receipt.get("protocol_id")
        == control["expected_protocol_id"],
        "status_matched": receipt.get("status") == control["expected_status"],
        "passed": receipt.get("passed") is True,
        "source_commit_matched": receipt.get("source_bundle", {}).get(
            "source_commit"
        )
        == control["source_commit"],
        "source_bundle_sha256_matched": receipt.get("source_bundle", {}).get(
            "sha256"
        )
        == control["source_bundle_sha256"],
        "release_manifest_sha256_matched": receipt.get(
            "source_bundle", {}
        ).get("release_manifest_sha256")
        == control["release_manifest_sha256"],
        "docker_build_and_run_passed": receipt.get("build_returncode") == 0
        and receipt.get("run_returncode") == 0,
        "outer_checks_all_passed": bool(outer_checks)
        and all(value is True for value in outer_checks.values()),
        "expected_outputs_all_present": bool(expected_outputs)
        and all(value is True for value in expected_outputs.values()),
        "runtime_status_passed": runtime_summary.get("status")
        == "AUTHORITATIVE_RUNTIME_PASS",
        "runtime_check_count_matched": len(runtime_checks)
        == control["expected_runtime_check_count"],
        "runtime_checks_all_passed": bool(runtime_checks)
        and all(value is True for value in runtime_checks.values()),
        "capsule_suites_matched": capsule_summary.get("suite_count")
        == capsule_summary.get("suite_pass_count")
        == control["expected_suite_count"],
        "capsule_assertions_matched": capsule_summary.get("assertion_count")
        == capsule_summary.get("assertion_pass_count")
        == control["expected_assertion_count"],
        "capsule_fixture_tests_passed": capsule_summary.get(
            "fixture_tests_passed"
        )
        is True,
        "capsule_source_state_verified": capsule_summary.get(
            "source_state_verified"
        )
        is True
        and capsule_summary.get("source_state_mode") == "release_manifest",
        "capsule_clean_runner_replay": capsule_summary.get(
            "clean_runner_replay"
        )
        is True,
        "capsule_receipt_hash_matched": artifacts.get(
            "reviewer_reproducibility_receipt.json", {}
        ).get("sha256")
        == control["capsule_receipt_sha256"]
        == capsule_file_sha256,
        "runtime_receipt_hash_matched": artifacts.get(
            "runtime_receipt.json", {}
        ).get("sha256")
        == control["runtime_receipt_sha256"]
        == runtime_file_sha256,
        "recipe_base_image_matched": recipe.get("base_image")
        == recipe_control["base_image"],
        "recipe_uv_matched": recipe.get("uv") == recipe_control["uv"],
        "recipe_python_matched": recipe.get("python")
        == recipe_control["python"],
        "recipe_source_hashes_current": all(
            recipe.get(key) == value
            for key, value in current_recipe_hashes.items()
        ),
        "execution_controls_matched": receipt.get("execution_controls")
        == container_config["execution"],
        "operator_controlled": receipt.get("operator_controlled") is True,
        "independent_execution_remains_false": receipt.get(
            "independent_execution_complete"
        )
        is False,
        "external_validation_remains_false": receipt.get(
            "external_validation_complete"
        )
        is False
        and capsule_summary.get("external_validation_complete") is False,
        "privacy_scan_passed": not private_hits,
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "receipt_path": control["receipt_path"],
        "receipt_sha256": file_sha256(path),
        "receipt_payload_sha256": receipt.get("receipt_payload_sha256"),
        "output_manifest_path": control["output_manifest_path"],
        "output_manifest_sha256": file_sha256(output_manifest_path),
        "output_manifest_entry_count": output_manifest["entry_count"],
        "output_manifest_matched_entry_count": output_manifest[
            "matched_entry_count"
        ],
        "output_manifest_mismatch_paths": output_manifest["mismatch_paths"],
        "schema": receipt.get("schema"),
        "protocol_id": receipt.get("protocol_id"),
        "status": receipt.get("status"),
        "generated_utc": receipt.get("generated_utc"),
        "source_commit": receipt.get("source_bundle", {}).get("source_commit"),
        "source_bundle_sha256": receipt.get("source_bundle", {}).get("sha256"),
        "release_manifest_sha256": receipt.get("source_bundle", {}).get(
            "release_manifest_sha256"
        ),
        "image_id": receipt.get("image", {}).get("id"),
        "runtime_check_count": len(runtime_checks),
        "runtime_check_pass_count": sum(
            value is True for value in runtime_checks.values()
        ),
        "suite_count": capsule_summary.get("suite_count"),
        "suite_pass_count": capsule_summary.get("suite_pass_count"),
        "assertion_count": capsule_summary.get("assertion_count"),
        "assertion_pass_count": capsule_summary.get("assertion_pass_count"),
        "fixture_tests_passed": capsule_summary.get("fixture_tests_passed"),
        "source_state_mode": capsule_summary.get("source_state_mode"),
        "source_state_verified": capsule_summary.get("source_state_verified"),
        "operator_controlled": receipt.get("operator_controlled"),
        "independent_execution_complete": receipt.get(
            "independent_execution_complete"
        ),
        "external_validation_complete": receipt.get(
            "external_validation_complete"
        ),
        "configured_private_pattern_hit_count": len(private_hits),
        "policy": control["policy"],
    }


def git_object_map(commit: str, relative_paths: list[str]) -> dict[str, bytes]:
    unique_paths = sorted(set(relative_paths))
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=zip",
            commit,
            "--",
            *unique_paths,
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    try:
        with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
            return {
                path: archive.read(path)
                for path in unique_paths
                if path in archive.namelist()
            }
    except zipfile.BadZipFile:
        return {}


def git_check(*args: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def portable_blob_sha256(raw: bytes, hash_mode: str) -> str | None:
    if hash_mode == "binary":
        content = raw
    elif hash_mode == "utf8_lf":
        try:
            text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            return None
        content = text.encode("utf-8")
    else:
        return None
    return hashlib.sha256(content).hexdigest()


def verify_public_commit_freeze(
    control: dict[str, Any],
    *,
    release_candidate: dict[str, Any],
    pdf_path: Path,
) -> dict[str, Any]:
    repository = control["repository_full_name"]
    commit = control["source_commit"]
    preprint_path = control["preprint_path"]
    source_url = control["source_url"]
    preprint_url = control["preprint_url"]
    expected_source_url = f"https://github.com/{repository}/commit/{commit}"
    expected_preprint_url = (
        f"https://raw.githubusercontent.com/{repository}/{commit}/{preprint_path}"
    )

    release_rows = release_candidate["bundle_inputs"]
    commit_format_valid = bool(re.fullmatch(r"[0-9a-f]{40}", commit))
    pinned_objects = (
        git_object_map(
            commit,
            [row["path"] for row in release_rows] + [preprint_path],
        )
        if commit_format_valid
        else {}
    )
    reconciliation_rows = []
    for row in release_rows:
        raw = pinned_objects.get(row["path"])
        pinned_sha256 = (
            portable_blob_sha256(raw, row["hash_mode"]) if raw is not None else None
        )
        reconciliation_rows.append(
            {
                "path": row["path"],
                "hash_mode": row["hash_mode"],
                "expected_sha256": row["sha256"],
                "pinned_commit_sha256": pinned_sha256,
                "matched": pinned_sha256 == row["sha256"],
            }
        )

    pinned_pdf = pinned_objects.get(preprint_path)
    pinned_pdf_sha256 = (
        hashlib.sha256(pinned_pdf).hexdigest() if pinned_pdf is not None else None
    )
    pinned_pdf_git_blob_sha1 = (
        hashlib.sha1(
            f"blob {len(pinned_pdf)}\0".encode("ascii") + pinned_pdf,
            usedforsecurity=False,
        ).hexdigest()
        if pinned_pdf is not None
        else None
    )
    repository_format_valid = bool(
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
    )
    preprint_path_object = PurePosixPath(preprint_path)
    preprint_path_safe = (
        bool(preprint_path)
        and not preprint_path_object.is_absolute()
        and ".." not in preprint_path_object.parts
    )
    commit_exists_local = commit_format_valid and git_check(
        "cat-file", "-e", f"{commit}^{{commit}}"
    )
    commit_is_ancestor = commit_exists_local and git_check(
        "merge-base", "--is-ancestor", commit, "HEAD"
    )
    stable_public_identifier_verified = all(
        (
            repository_format_valid,
            commit_exists_local,
            source_url == expected_source_url,
            preprint_url == expected_preprint_url,
            preprint_path_safe,
            pinned_pdf_sha256 == file_sha256(pdf_path),
            pinned_pdf_sha256 == control["preprint_sha256"],
        )
    )
    immutable_public_source_release_verified = all(
        (
            repository_format_valid,
            commit_exists_local,
            commit_is_ancestor,
            source_url == expected_source_url,
            len(release_rows) == control["release_candidate_input_count"],
            release_candidate["bundle_input_chain_sha256"]
            == control["release_candidate_input_chain_sha256"],
            all(row["matched"] for row in reconciliation_rows),
        )
    )
    checks = {
        "repository_format_valid": repository_format_valid,
        "source_commit_format_valid": commit_format_valid,
        "source_commit_exists_local": commit_exists_local,
        "source_commit_is_ancestor_of_head": commit_is_ancestor,
        "source_url_exact": source_url == expected_source_url,
        "preprint_url_exact": preprint_url == expected_preprint_url,
        "preprint_path_safe": preprint_path_safe,
        "pinned_preprint_present": pinned_pdf is not None,
        "pinned_preprint_sha256_matched": pinned_pdf_sha256
        == control["preprint_sha256"]
        == file_sha256(pdf_path),
        "pinned_preprint_public_blob_matched": pinned_pdf_git_blob_sha1
        == control["preprint_git_blob_sha1"],
        "release_candidate_input_count_matched": len(release_rows)
        == control["release_candidate_input_count"],
        "release_candidate_input_chain_matched": release_candidate[
            "bundle_input_chain_sha256"
        ]
        == control["release_candidate_input_chain_sha256"],
        "release_candidate_inputs_match_pinned_commit": all(
            row["matched"] for row in reconciliation_rows
        ),
        "stable_public_identifier_verified": stable_public_identifier_verified,
        "immutable_public_source_release_verified": immutable_public_source_release_verified,
        "external_validation_remains_false": control["external_validation_complete"]
        is False,
        "submission_authorization_remains_false": control["submission_authorized"]
        is False,
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "repository_full_name": repository,
        "source_commit": commit,
        "source_url": source_url,
        "preprint_path": preprint_path,
        "preprint_url": preprint_url,
        "preprint_sha256": pinned_pdf_sha256,
        "preprint_git_blob_sha1": pinned_pdf_git_blob_sha1,
        "public_fetch_verified_utc": control["public_fetch_verified_utc"],
        "public_fetch_verification_method": control[
            "public_fetch_verification_method"
        ],
        "release_candidate_input_count": len(release_rows),
        "release_candidate_input_chain_sha256": release_candidate[
            "bundle_input_chain_sha256"
        ],
        "release_candidate_mismatch_count": sum(
            not row["matched"] for row in reconciliation_rows
        ),
        "release_candidate_mismatch_paths": [
            row["path"] for row in reconciliation_rows if not row["matched"]
        ],
        "release_candidate_reconciliation": reconciliation_rows,
        "stable_public_identifier_verified": stable_public_identifier_verified,
        "immutable_public_source_release_verified": immutable_public_source_release_verified,
        "external_validation_complete": False,
        "submission_authorized": False,
        "policy": control["policy"],
    }


def verify_preprint_and_request(
    control: dict[str, Any],
    *,
    markdown_path: Path,
    pdf_path: Path,
    request_path: Path,
    release_candidate: dict[str, Any],
) -> dict[str, Any]:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    request_text = request_path.read_text(encoding="utf-8")
    pdf_bytes = pdf_path.read_bytes()
    pdf_page_count = len(PDF_PAGE_PATTERN.findall(pdf_bytes))
    private_hits = scan_private(
        {
            "markdown": markdown_text,
            "request": request_text,
            "pdf": pdf_bytes.decode("latin-1"),
        }
    )
    public_commit_freeze = verify_public_commit_freeze(
        control["public_commit_freeze"],
        release_candidate=release_candidate,
        pdf_path=pdf_path,
    )
    checks = {
        "source_sha256_matched": file_sha256(markdown_path)
        == control["source_sha256"],
        "pdf_sha256_matched": file_sha256(pdf_path) == control["pdf_sha256"],
        "pdf_header_present": pdf_bytes.startswith(b"%PDF-"),
        "pdf_eof_present": pdf_bytes.rstrip().endswith(b"%%EOF"),
        "pdf_page_count_matched": pdf_page_count
        == control["expected_pdf_page_count"],
        "required_manuscript_sections_present": all(
            token in markdown_text for token in PREPRINT_REQUIRED_TOKENS
        ),
        "claim_boundaries_present": all(
            token in markdown_text for token in PREPRINT_BOUNDARY_TOKENS
        ),
        "request_hold_controls_present": all(
            token in request_text for token in REQUEST_HOLD_TOKENS
        ),
        "official_launch_pad_matched": control["official_launch_pad"]
        in request_text,
        "public_commit_freeze_verified": public_commit_freeze["verified"],
        "stable_public_identifier_verified": control["stable_public_identifier"]
        == public_commit_freeze["preprint_url"]
        and public_commit_freeze["stable_public_identifier_verified"],
        "immutable_public_source_release_verified": control[
            "immutable_public_source_release"
        ]
        == public_commit_freeze["source_url"]
        and public_commit_freeze["immutable_public_source_release_verified"],
        "duplicate_request_reconciliation_open": control[
            "duplicate_request_reconciled"
        ]
        is False,
        "community_request_remains_unopened": control[
            "community_request_opened"
        ]
        is False,
        "privacy_scan_passed": not private_hits,
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "markdown_path": display_path(markdown_path),
        "markdown_sha256": file_sha256(markdown_path),
        "pdf_path": display_path(pdf_path),
        "pdf_sha256": file_sha256(pdf_path),
        "pdf_page_count": pdf_page_count,
        "paper_reference": control["paper_reference"],
        "stable_public_identifier": control["stable_public_identifier"],
        "immutable_public_source_release": control[
            "immutable_public_source_release"
        ],
        "duplicate_request_reconciled": control[
            "duplicate_request_reconciled"
        ],
        "request_path": display_path(request_path),
        "community_request_ready": False,
        "community_request_opened": control["community_request_opened"],
        "public_commit_freeze": public_commit_freeze,
        "configured_private_pattern_hit_count": len(private_hits),
        "policy": control["policy"],
    }
def build_payload(*, generated_utc: str | None = None) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    generated_utc = generated_utc or now_utc()
    bundle = config["bundle"]
    execution = config["execution"]

    codecheck_path = ROOT / bundle["codecheck_config_path"]
    codecheck = parse_codecheck_config(codecheck_path)
    expected_manifest = execution["manifest_paths"]

    authority_config_path = ROOT / bundle["authority_config_path"]
    authority_config = read_json(authority_config_path)
    authority_module = load_authority_module(ROOT / bundle["authority_builder_path"])
    archive_path = ROOT / authority_config["clean_runner_verification"]["archive_path"]
    archive = authority_module.verify_ci_bundle(
        archive_path,
        authority_config,
        root=ROOT,
    )
    archived_receipt = read_json(
        archive_path / "reviewer_reproducibility_receipt.json"
    )
    archived_summary = archived_receipt["summary"]
    source_reconciliation = reconcile_archived_sources(
        archived_receipt,
        set(
            config["archive_reconciliation"][
                "noncomputational_documentation_or_packaging_paths"
            ]
        ),
    )
    operator_clean_runner = verify_operator_clean_runner(
        config["operator_clean_runner"]
    )
    reviewer_runtime = verify_reviewer_runtime(config["reviewer_runtime"])
    container_config = read_json(
        ROOT / bundle["reviewer_container_config_path"]
    )
    operator_container_rebuild = verify_operator_container_rebuild(
        config["operator_container_rebuild"],
        container_config=container_config,
        capsule_receipt_path=ROOT / config["operator_clean_runner"]["receipt_path"],
        runtime_receipt_path=ROOT / config["reviewer_runtime"]["receipt_path"],
    )
    release_candidate_config_path = ROOT / bundle[
        "release_candidate_config_path"
    ]
    release_candidate_module = load_release_candidate_module(
        ROOT / bundle["release_candidate_builder_path"]
    )
    release_candidate = release_candidate_module.inspect_release_candidate(
        release_candidate_config_path
    )
    preprint_and_request = verify_preprint_and_request(
        config["preprint_and_request"],
        markdown_path=ROOT / bundle["preprint_markdown_path"],
        pdf_path=ROOT / bundle["preprint_pdf_path"],
        request_path=ROOT / bundle["community_request_draft_path"],
        release_candidate=release_candidate,
    )

    output_root = PurePosixPath(execution["output_root"])
    archive_relative_manifest = []
    for value in codecheck["manifest"]:
        path = PurePosixPath(value)
        try:
            archive_relative_manifest.append(path.relative_to(output_root).as_posix())
        except ValueError:
            archive_relative_manifest.append(f"<outside-output-root>/{path.as_posix()}")
    archived_computational_files = sorted(
        path.relative_to(archive_path).as_posix()
        for path in archive_path.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )

    portable_paths = [ROOT / value for value in config["portable_input_paths"]]
    required_paths = {
        ROOT / value
        for key, value in bundle.items()
        if key.endswith("_path") and key != "authority_config_path"
    }
    required_paths.add(authority_config_path)
    required_paths.add(
        ROOT / config["operator_clean_runner"]["receipt_path"]
    )
    required_paths.add(ROOT / config["reviewer_runtime"]["receipt_path"])
    required_paths.add(
        ROOT / config["operator_container_rebuild"]["receipt_path"]
    )
    required_paths.add(
        ROOT / config["operator_container_rebuild"]["output_manifest_path"]
    )
    required_paths.add(SCRIPT_PATH)
    required_paths.add(TEST_PATH)
    path_checks = {
        repo_path(path): path.is_file() for path in sorted(required_paths)
    }

    readme_text = (ROOT / bundle["readme_path"]).read_text(encoding="utf-8")
    license_text = (ROOT / bundle["license_path"]).read_text(encoding="utf-8")
    method_text = (ROOT / bundle["method_note_path"]).read_text(encoding="utf-8")
    preprint_text = (ROOT / bundle["preprint_markdown_path"]).read_text(
        encoding="utf-8"
    )
    request_text = (ROOT / bundle["community_request_draft_path"]).read_text(
        encoding="utf-8"
    )
    release_plan_text = (ROOT / bundle["release_candidate_plan_path"]).read_text(
        encoding="utf-8"
    )
    public_text_privacy_hits = scan_private(
        {
            "codecheck": codecheck_path.read_text(encoding="utf-8"),
            "readme": readme_text,
            "license": license_text,
            "method_note": method_text,
            "preprint": preprint_text,
            "community_request_draft": request_text,
            "release_candidate_plan": release_plan_text,
            "release_candidate_config": read_json(release_candidate_config_path),
        }
    )

    checks = {
        "codecheck_utf8": codecheck["utf8_decoded"],
        "codecheck_explicit_document_start": codecheck["explicit_document_start"],
        "codecheck_yaml_directive_present": codecheck["yaml_directive"] == "%YAML 1.1",
        "codecheck_spec_version_matched": codecheck["version"]
        == config["codecheck_specification"]["version"],
        "manifest_exactly_matched_protocol": codecheck["manifest"]
        == expected_manifest,
        "manifest_paths_safe": codecheck["manifest_paths_safe"],
        "manifest_paths_unique": codecheck["manifest_paths_unique"],
        "paper_title_present": codecheck["paper_title_present"],
        "paper_reference_matches_preprint": codecheck["paper_reference"]
        == config["preprint_and_request"]["paper_reference"],
        "corresponding_author_present": codecheck["corresponding_author_present"],
        "codechecker_metadata_left_external": not codecheck[
            "codechecker_metadata_present"
        ],
        "report_metadata_left_external": not codecheck["report_metadata_present"],
        "all_required_paths_present": all(path_checks.values()),
        "readme_has_exact_codecheck_command": execution["command"] in readme_text,
        "license_distinguishes_code_and_eia_data": all(
            token in license_text
            for token in (
                "Third-Party Data Notice",
                "https://www.eia.gov/about/copyrights_reuse.php",
                "https://www.eia.gov/opendata/terms-of-service.php",
            )
        ),
        "method_note_preserves_failed_gates": all(
            token in method_text
            for token in (
                "Promotion gate: failed",
                "Coverage gate: failed",
                "post-observation portability amendment",
            )
        ),
        "archive_checksum_and_identity_verified": archive["verified"] is True,
        "archive_manifest_matches_codecheck_manifest": sorted(
            archive_relative_manifest
        )
        == archived_computational_files,
        "computational_identity_has_current_verified_replay": (
            source_reconciliation["computational_identity_exact_match"]
            or (
                operator_clean_runner["verified"]
                and operator_container_rebuild["verified"]
            )
        ),
        "archived_capsule_status_matched": archived_receipt["status"]
        == execution["expected_archived_status"],
        "archived_suite_count_matched": archived_summary["suite_count"]
        == archived_summary["suite_pass_count"]
        == execution["expected_suite_count"],
        "archived_assertion_count_matched": archived_summary["assertion_count"]
        == archived_summary["assertion_pass_count"]
        == execution["expected_assertion_count"],
        "archived_receipt_keeps_external_validation_false": archived_summary[
            "external_validation_complete"
        ]
        is False,
        **{
            f"operator_clean_runner_{key}": value
            for key, value in operator_clean_runner["checks"].items()
        },
        **{
            f"reviewer_runtime_{key}": value
            for key, value in reviewer_runtime["checks"].items()
        },
        **{
            f"operator_container_rebuild_{key}": value
            for key, value in operator_container_rebuild["checks"].items()
        },
        **{
            f"preprint_request_{key}": value
            for key, value in preprint_and_request["checks"].items()
        },
        **{
            f"release_candidate_{key}": value
            for key, value in release_candidate["checks"].items()
        },
        "release_candidate_definition_ready": release_candidate[
            "internal_release_candidate_ready"
        ],
        "release_candidate_publication_remains_closed": release_candidate[
            "publication_ready"
        ]
        is False,
        "public_text_privacy_scan_passed": not public_text_privacy_hits,
    }
    internal_gate_passed = all(checks.values())

    portable_inputs = [artifact_row(path) for path in portable_paths]
    verified_gate_states = {
        "stable_public_preprint_identifier": preprint_and_request[
            "public_commit_freeze"
        ]["stable_public_identifier_verified"],
        "immutable_public_source_release": preprint_and_request[
            "public_commit_freeze"
        ]["immutable_public_source_release_verified"],
    }
    external_gates = [
        {
            **gate,
            "complete": verified_gate_states.get(gate["gate_id"], gate["complete"]),
        }
        for gate in config["external_gates"]
    ]
    configured_gate_states = {
        gate["gate_id"]: gate["complete"] for gate in config["external_gates"]
    }
    for gate_id, verified_state in verified_gate_states.items():
        checks[f"external_gate_{gate_id}_claim_matched"] = (
            configured_gate_states[gate_id] is verified_state
        )
    internal_gate_passed = all(checks.values())
    payload: dict[str, Any] = {
        "schema": "codecheck_eia_author_readiness.v1",
        "protocol_id": config["protocol_id"],
        "generated_utc": generated_utc,
        "status": (
            "AUTHOR_PACKET_READY_FOR_HUMAN_REVIEW"
            if internal_gate_passed
            else "AUTHOR_PACKET_BLOCKED"
        ),
        "summary": {
            "internal_gate_passed": internal_gate_passed,
            "internal_check_count": len(checks),
            "internal_check_pass_count": sum(checks.values()),
            "manifest_output_count": len(codecheck["manifest"]),
            "authoritative_archive_verified": archive["verified"],
            "archive_full_source_exact_match": source_reconciliation[
                "full_source_exact_match"
            ],
            "archived_computational_identity_still_matches": source_reconciliation[
                "computational_identity_exact_match"
            ],
            "archive_drift_reconciled_by_current_container_rebuild": (
                not source_reconciliation["computational_identity_exact_match"]
                and operator_clean_runner["verified"]
                and operator_container_rebuild["verified"]
            ),
            "operator_clean_runner_receipt_verified": operator_clean_runner[
                "verified"
            ],
            "operator_clean_runner_full_source_exact_match": (
                operator_clean_runner["source_reconciliation"][
                    "full_source_exact_match"
                ]
            ),
            "operator_clean_runner_computational_identity_current": (
                operator_clean_runner["source_reconciliation"][
                    "computational_identity_exact_match"
                ]
            ),
            "reviewer_runtime_receipt_verified": reviewer_runtime["verified"],
            "reviewer_runtime_check_count": reviewer_runtime[
                "runtime_check_count"
            ],
            "reviewer_runtime_check_pass_count": reviewer_runtime[
                "runtime_check_pass_count"
            ],
            "operator_container_rebuild_receipt_verified": (
                operator_container_rebuild["verified"]
            ),
            "operator_container_rebuild_suite_pass_count": (
                operator_container_rebuild["suite_pass_count"]
            ),
            "operator_container_rebuild_suite_count": (
                operator_container_rebuild["suite_count"]
            ),
            "operator_container_rebuild_assertion_pass_count": (
                operator_container_rebuild["assertion_pass_count"]
            ),
            "operator_container_rebuild_assertion_count": (
                operator_container_rebuild["assertion_count"]
            ),
            "current_commit_clean_runner_complete": False,
            "frozen_source_container_rebuild_complete": (
                operator_clean_runner["verified"]
                and operator_clean_runner["source_reconciliation"][
                    "full_source_exact_match"
                ]
                and operator_container_rebuild["verified"]
                and operator_clean_runner["source_commit"]
                == operator_container_rebuild["source_commit"]
                == preprint_and_request["public_commit_freeze"]["source_commit"]
            ),
            "public_preprint_draft_complete": preprint_and_request["verified"],
            "release_candidate_definition_ready": release_candidate[
                "internal_release_candidate_ready"
            ],
            "release_candidate_publication_ready": release_candidate[
                "publication_ready"
            ],
            "stable_public_preprint_identifier_complete": verified_gate_states[
                "stable_public_preprint_identifier"
            ],
            "immutable_public_source_release_complete": verified_gate_states[
                "immutable_public_source_release"
            ],
            "duplicate_request_reconciled": False,
            "community_request_ready": preprint_and_request[
                "community_request_ready"
            ],
            "community_request_opened": preprint_and_request[
                "community_request_opened"
            ],
            "archived_suite_pass_count": archived_summary["suite_pass_count"],
            "archived_assertion_pass_count": archived_summary[
                "assertion_pass_count"
            ],
            "human_author_review_complete": False,
            "submission_authorized": False,
            "codechecker_assigned": False,
            "independent_execution_complete": False,
            "certificate_issued": False,
            "external_validation_complete": False,
        },
        "checks": checks,
        "path_checks": path_checks,
        "codecheck_configuration": codecheck,
        "execution": execution,
        "authoritative_archive": {
            "github_run_id": authority_config["clean_runner_verification"][
                "github_run_id"
            ],
            "github_run_url": authority_config["clean_runner_verification"][
                "github_run_url"
            ],
            "commit": authority_config["clean_runner_verification"]["commit"],
            "archive_path": repo_path(archive_path),
            "verified": archive["verified"],
            "checksum_entry_count": archive["checksum_entry_count"],
            "checksum_pass_count": archive["checksum_pass_count"],
            "complete_file_coverage": archive["complete_file_coverage"],
            "capsule_sha256": archived_receipt["capsule_sha256"],
            "suite_count": archived_summary["suite_count"],
            "suite_pass_count": archived_summary["suite_pass_count"],
            "assertion_count": archived_summary["assertion_count"],
            "assertion_pass_count": archived_summary["assertion_pass_count"],
            "external_validation_complete": archived_summary[
                "external_validation_complete"
            ],
            "source_reconciliation": source_reconciliation,
        },
        "operator_clean_runner": operator_clean_runner,
        "reviewer_runtime": reviewer_runtime,
        "operator_container_rebuild": operator_container_rebuild,
        "preprint_and_request": preprint_and_request,
        "release_candidate": release_candidate,
        "external_gates": external_gates,
        "portable_inputs": portable_inputs,
        "portable_input_chain_sha256": canonical_sha256(portable_inputs),
        "live_runtime_boundary": config["live_runtime_boundary"],
        "value_bridge": config["value_bridge"],
        "claim_boundary": config["claim_boundary"],
        "privacy_scan": {
            "passed": not public_text_privacy_hits,
            "configured_pattern_hit_count": len(public_text_privacy_hits),
        },
    }
    payload["readiness_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    archive = payload["authoritative_archive"]
    operator = payload["operator_clean_runner"]
    runtime = payload["reviewer_runtime"]
    container = payload["operator_container_rebuild"]
    preprint = payload["preprint_and_request"]
    release_candidate = payload["release_candidate"]
    lines = [
        "# CODECHECK EIA Author Readiness",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["claim_boundary"],
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Internal checks: `{summary['internal_check_pass_count']}/{summary['internal_check_count']}`",
        f"- Declared reproducible outputs: `{summary['manifest_output_count']}`",
        f"- Authoritative archive verified: `{str(summary['authoritative_archive_verified']).lower()}`",
        f"- Archived full source exact match: `{str(summary['archive_full_source_exact_match']).lower()}`",
        f"- Archived computational identity still matches: `{str(summary['archived_computational_identity_still_matches']).lower()}`",
        f"- Archive drift reconciled by current container rebuild: `{str(summary['archive_drift_reconciled_by_current_container_rebuild']).lower()}`",
        f"- Operator clean-runner receipt verified: `{str(summary['operator_clean_runner_receipt_verified']).lower()}`",
        f"- Operator clean-runner full source exact match: `{str(summary['operator_clean_runner_full_source_exact_match']).lower()}`",
        f"- Operator clean-runner computational identity current: `{str(summary['operator_clean_runner_computational_identity_current']).lower()}`",
        f"- Exact reviewer runtime receipt verified: `{str(summary['reviewer_runtime_receipt_verified']).lower()}`",
        f"- Exact reviewer runtime checks: `{summary['reviewer_runtime_check_pass_count']}/{summary['reviewer_runtime_check_count']}`",
        f"- Digest-pinned container rebuild verified: `{str(summary['operator_container_rebuild_receipt_verified']).lower()}`",
        f"- Container-rebuild suites passed: `{summary['operator_container_rebuild_suite_pass_count']}/{summary['operator_container_rebuild_suite_count']}`",
        f"- Container-rebuild assertions passed: `{summary['operator_container_rebuild_assertion_pass_count']}/{summary['operator_container_rebuild_assertion_count']}`",
        f"- Current commit clean-runner complete: `{str(summary['current_commit_clean_runner_complete']).lower()}`",
        f"- Frozen reviewer source container rebuild complete: `{str(summary['frozen_source_container_rebuild_complete']).lower()}`",
        f"- Public preprint draft complete: `{str(summary['public_preprint_draft_complete']).lower()}`",
        f"- Deterministic release-candidate definition ready: `{str(summary['release_candidate_definition_ready']).lower()}`",
        f"- Release publication ready: `{str(summary['release_candidate_publication_ready']).lower()}`",
        f"- Stable public preprint identifier complete: `{str(summary['stable_public_preprint_identifier_complete']).lower()}`",
        f"- Immutable public source release complete: `{str(summary['immutable_public_source_release_complete']).lower()}`",
        f"- Duplicate request reconciled: `{str(summary['duplicate_request_reconciled']).lower()}`",
        f"- Community request ready: `{str(summary['community_request_ready']).lower()}`",
        f"- Community request opened: `{str(summary['community_request_opened']).lower()}`",
        f"- Independent execution complete: `{str(summary['independent_execution_complete']).lower()}`",
        f"- Certificate issued: `{str(summary['certificate_issued']).lower()}`",
        f"- External validation complete: `{str(summary['external_validation_complete']).lower()}`",
        f"- Readiness SHA-256: `{payload['readiness_sha256']}`",
        "",
        "An internal pass means the author-side bundle is coherent enough for Robert to review. It is not a submission receipt, external execution, or certificate.",
        "",
        "## Exact Execution",
        "",
        "```bash",
        "python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only",
        "python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py",
        "python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --requirement requirements-reviewer-ubuntu-py311.lock",
        "python -m pip check",
        payload["execution"]["command"],
        "```",
        "",
        "## Manifest",
        "",
    ]
    for path in payload["codecheck_configuration"]["manifest"]:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## Public Preprint And Request Draft",
            "",
            f"- Markdown: `{preprint['markdown_path']}`",
            f"- Markdown SHA-256: `{preprint['markdown_sha256']}`",
            f"- PDF: `{preprint['pdf_path']}`",
            f"- PDF SHA-256: `{preprint['pdf_sha256']}`",
            f"- PDF pages: `{preprint['pdf_page_count']}`",
            f"- Manifest reference: `{preprint['paper_reference']}`",
            f"- Stable public identifier: `{preprint['stable_public_identifier'] or 'not assigned'}`",
            f"- Immutable public source release: `{preprint['immutable_public_source_release'] or 'not frozen'}`",
            f"- Pinned source commit: `{preprint['public_commit_freeze']['source_commit']}`",
            f"- Public preprint Git blob: `{preprint['public_commit_freeze']['preprint_git_blob_sha1']}`",
            f"- Public fetch verified UTC: `{preprint['public_commit_freeze']['public_fetch_verified_utc']}`",
            f"- Pinned release inputs reconciled: `{preprint['public_commit_freeze']['release_candidate_input_count'] - preprint['public_commit_freeze']['release_candidate_mismatch_count']}/{preprint['public_commit_freeze']['release_candidate_input_count']}`",
            f"- Public commit freeze verified: `{str(preprint['public_commit_freeze']['verified']).lower()}`",
            f"- Duplicate request reconciled: `{str(preprint['duplicate_request_reconciled']).lower()}`",
            f"- Request draft: `{preprint['request_path']}`",
            f"- Community request ready: `{str(preprint['community_request_ready']).lower()}`",
            f"- Community request opened: `{str(preprint['community_request_opened']).lower()}`",
            "",
            preprint["policy"],
            "",
            "## Immutable Release Candidate",
            "",
            f"- Proposed tag: `{release_candidate['release']['proposed_tag']}`",
            f"- Bundle inputs: `{release_candidate['bundle_input_count']}`",
            f"- Bundle input chain SHA-256: `{release_candidate['bundle_input_chain_sha256']}`",
            f"- Internal definition ready: `{str(release_candidate['internal_release_candidate_ready']).lower()}`",
            f"- Publication ready: `{str(release_candidate['publication_ready']).lower()}`",
            f"- GitHub release published: `{str(release_candidate['publication_state']['github_release_published']).lower()}`",
            f"- Zenodo DOI issued: `{str(release_candidate['publication_state']['zenodo_doi_issued']).lower()}`",
            f"- External validation complete: `{str(release_candidate['publication_state']['external_validation_complete']).lower()}`",
            "",
            release_candidate["human_unlock_policy"],
            "",
            "## Archived Operator Execution",
            "",
            f"- GitHub run: [{archive['github_run_id']}]({archive['github_run_url']})",
            f"- Commit: `{archive['commit']}`",
            f"- Archive: `{archive['archive_path']}`",
            f"- Checksums passed: `{archive['checksum_pass_count']}/{archive['checksum_entry_count']}`",
            f"- Suites passed: `{archive['suite_pass_count']}/{archive['suite_count']}`",
            f"- Assertions passed: `{archive['assertion_pass_count']}/{archive['assertion_count']}`",
            f"- External validation complete in receipt: `{str(archive['external_validation_complete']).lower()}`",
            f"- Current-source drift paths: `{', '.join(archive['source_reconciliation']['mismatch_paths']) or 'none'}`",
            "",
            "The archive demonstrates an older operator-controlled clean-runner execution. Every later source mismatch remains listed above; the newer source-identity receipt and digest-pinned container rebuild supersede it for author-side executability only. None of these operator receipts are independent evidence. The codechecker must execute the reviewed release.",
            "",
            "## Current Source-Identity Operator Replay",
            "",
            f"- Receipt: `{operator['receipt_path']}`",
            f"- Receipt SHA-256: `{operator['receipt_sha256']}`",
            f"- Source commit: `{operator['source_commit']}`",
            f"- Source artifacts matched: `{operator['source_reconciliation']['current_match_count']}/{operator['source_reconciliation']['archived_source_count']}`",
            f"- Full source exact match: `{str(operator['source_reconciliation']['full_source_exact_match']).lower()}`",
            f"- Computational identity exact match: `{str(operator['source_reconciliation']['computational_identity_exact_match']).lower()}`",
            f"- Documentation drift paths: `{', '.join(operator['source_reconciliation']['mismatch_paths']) or 'none'}`",
            f"- Relevant source clean: `{str(operator['relevant_source_clean']).lower()}`",
            f"- Clean-runner replay: `{str(operator['clean_runner_replay']).lower()}`",
            f"- Authoritative runtime matched: `{str(operator['authoritative_runtime_match']).lower()}`",
            f"- Dependency closure matched: `{str(operator['dependency_closure_exact_match']).lower()}`",
            f"- Fixture tests passed: `{str(operator['fixture_tests_passed']).lower()}`",
            f"- Suites passed: `{operator['suite_pass_count']}/{operator['suite_count']}`",
            f"- Assertions passed: `{operator['assertion_pass_count']}/{operator['assertion_count']}`",
            f"- External validation complete in receipt: `{str(operator['external_validation_complete']).lower()}`",
            "",
            operator["execution_control"],
            "",
            operator["policy"],
            "",
            "## Exact Reviewer Runtime Receipt",
            "",
            f"- Receipt: `{runtime['receipt_path']}`",
            f"- Receipt SHA-256: `{runtime['receipt_sha256']}`",
            f"- Declared source commit: `{runtime['source_commit']}`",
            f"- Runtime checks passed: `{runtime['runtime_check_pass_count']}/{runtime['runtime_check_count']}`",
            f"- Observed OS: `{runtime['observed']['os_release']['id']} {runtime['observed']['os_release']['version_id']}`",
            f"- Observed architecture: `{runtime['observed']['machine']}`",
            f"- Observed Python: `{runtime['observed']['python']}`",
            f"- Observed libc: `{runtime['observed']['libc']['name']} {runtime['observed']['libc']['version']}`",
            f"- Operator controlled: `{str(runtime['operator_controlled']).lower()}`",
            f"- Independent execution complete: `{str(runtime['independent_execution_complete']).lower()}`",
            f"- External validation complete: `{str(runtime['external_validation_complete']).lower()}`",
            "",
            runtime["policy"],
            "",
            "## Digest-Pinned Container Rebuild",
            "",
            f"- Receipt: `{container['receipt_path']}`",
            f"- Receipt SHA-256: `{container['receipt_sha256']}`",
            f"- Source commit: `{container['source_commit']}`",
            f"- Source bundle SHA-256: `{container['source_bundle_sha256']}`",
            f"- Release manifest SHA-256: `{container['release_manifest_sha256']}`",
            f"- Image ID: `{container['image_id']}`",
            f"- Runtime checks passed: `{container['runtime_check_pass_count']}/{container['runtime_check_count']}`",
            f"- Suites passed: `{container['suite_pass_count']}/{container['suite_count']}`",
            f"- Assertions passed: `{container['assertion_pass_count']}/{container['assertion_count']}`",
            f"- Fixture tests passed: `{str(container['fixture_tests_passed']).lower()}`",
            f"- Source state: `{container['source_state_mode']}` (`verified={str(container['source_state_verified']).lower()}`)",
            f"- Operator controlled: `{str(container['operator_controlled']).lower()}`",
            f"- Independent execution complete: `{str(container['independent_execution_complete']).lower()}`",
            f"- External validation complete: `{str(container['external_validation_complete']).lower()}`",
            "",
            container["policy"],
            "",
            "## Human And External Gates",
            "",
            "| Gate | Complete | Owner | Meaning |",
            "|---|---:|---|---|",
        ]
    )
    for gate in payload["external_gates"]:
        lines.append(
            f"| `{gate['gate_id']}` | `{str(gate['complete']).lower()}` | {gate['owner']} | {gate['meaning']} |"
        )
    lines.extend(
        [
            "",
            "## Live-Lane Separation",
            "",
            payload["live_runtime_boundary"],
            "",
            "## Value Boundary",
            "",
            payload["value_bridge"],
            "",
            "## Shortest Safe Completion Sequence",
            "",
            "1. Robert reviews the preprint, method note, manifest, license, request draft, and bounded ask.",
            "2. Build the deterministic candidate with `python code/ops/BUILD_CODECHECK_EIA_RELEASE_CANDIDATE.py` and reconcile its five local assets.",
            "3. Under fresh action-time HumanUnlock, enable the required external integrations and create one draft release targeting the exact reviewed commit.",
            "4. Attach all candidate assets, reconcile their uploaded hashes, and obtain fresh HumanUnlock before publishing an immutable release.",
            "5. Record the observed stable release URL and version-specific DOI only after GitHub and Zenodo expose them.",
            "6. Recheck Gmail, GitHub, and local outreach controls for duplicates, then obtain fresh action-time HumanUnlock for one CODECHECK request.",
            "7. Open exactly one request through the current official route and record its production issue URL.",
            "8. Let the assigned codechecker execute the workflow and populate external metadata; the operator does not fill those fields.",
            "9. Cite a certificate only after CODECHECK issues a public report identifier.",
            "10. Pursue a separate statistical-method review and the preregistered prospective EIA gates; neither can be substituted by executable-computation checking.",
        ]
    )
    return "\n".join(lines) + "\n"


def published_output_differences(
    payload: dict[str, Any],
    *,
    json_path: Path = OUT_JSON,
    markdown_path: Path = OUT_MD,
) -> list[str]:
    differences: list[str] = []
    if not json_path.is_file():
        differences.append(f"missing:{display_path(json_path)}")
    elif read_json(json_path) != payload:
        differences.append(f"stale:{display_path(json_path)}")
    if not markdown_path.is_file():
        differences.append(f"missing:{display_path(markdown_path)}")
    elif markdown_path.read_text(encoding="utf-8") != render_markdown(payload):
        differences.append(f"stale:{display_path(markdown_path)}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.check_only:
        if not OUT_JSON.is_file():
            print(json.dumps({"status": "BLOCKED", "reason": "published_json_missing"}))
            return 1
        published = read_json(OUT_JSON)
        payload = build_payload(generated_utc=published.get("generated_utc"))
        differences = published_output_differences(payload)
        print(
            json.dumps(
                {
                    "status": "PASS" if not differences else "BLOCKED",
                    "differences": differences,
                    "readiness_sha256": payload["readiness_sha256"],
                },
                indent=2,
            )
        )
        return 0 if not differences else 1

    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "status": payload["status"],
                "internal_checks": payload["summary"]["internal_check_count"],
                "internal_check_passes": payload["summary"][
                    "internal_check_pass_count"
                ],
                "json": repo_path(OUT_JSON),
                "markdown": repo_path(OUT_MD),
                "readiness_sha256": payload["readiness_sha256"],
            },
            indent=2,
        )
    )
    return 0 if payload["summary"]["internal_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
