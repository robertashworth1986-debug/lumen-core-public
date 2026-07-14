from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "config" / "reviewer_reproducibility_protocol_v1.json"
DEFAULT_RUN_DIR = ROOT / "out" / "reproducibility" / "reviewer_capsule_latest"
PUBLISHED_JSON = ROOT / "out" / "ops" / "reviewer_reproducibility_capsule_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "reviewer_reproducibility_capsule.json"
PUBLISHED_SBOM = (
    ROOT / "evidence" / "reproducibility" / "reviewer_suite_sbom_20260714.cdx.json"
)
PUBLISHED_MD = ROOT / "docs" / "REVIEWER_REPRODUCIBILITY_CAPSULE_2026-07-14.md"

MODULE_PATHS = {
    "eia_wave": ROOT / "code" / "eia_grid_wave_champion_benchmark.py",
    "eia_residual": ROOT / "code" / "eia_grid_residual_moe_benchmark.py",
    "mda_open_set": ROOT / "code" / "mda_control_mapping_open_set_benchmark.py",
}

PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.I),
    re.compile(r"private_estate", re.I),
    re.compile(r"patent_19_281_546", re.I),
    re.compile(r"cp575notice", re.I),
    re.compile(
        r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)\s*[:=]\s*[\"']?[^\s\"']{8,}",
        re.I,
    ),
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "reviewer_reproducibility_protocol.v1":
        raise ValueError("unexpected reviewer reproducibility protocol schema")
    if "TO_BE_FROZEN" in json.dumps(payload):
        raise ValueError(
            "reviewer reproducibility protocol contains an unfrozen placeholder"
        )
    if not payload.get("suites"):
        raise ValueError("reviewer reproducibility protocol defines no suites")
    return payload


def load_module(module_id: str) -> Any:
    path = MODULE_PATHS[module_id]
    spec = importlib.util.spec_from_file_location(f"reviewer_capsule_{module_id}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def source_artifacts(
    protocol: dict[str, Any], protocol_path: Path
) -> list[dict[str, Any]]:
    paths = {
        protocol_path.resolve(),
        (ROOT / protocol["environment"]["requirements_path"]).resolve(),
        Path(__file__).resolve(),
    }
    for frozen in protocol["frozen_inputs"]:
        paths.add((ROOT / frozen["path"]).resolve())
    for suite in protocol["suites"]:
        for source in suite["source_paths"]:
            paths.add((ROOT / source).resolve())
    for control in protocol.get("control_paths", []):
        paths.add((ROOT / control).resolve())
    for command_part in protocol.get("fixture_test_command", []):
        if isinstance(command_part, str) and command_part.endswith(".py"):
            paths.add((ROOT / command_part).resolve())

    artifacts = []
    for path in sorted(paths, key=lambda item: repo_path(item)):
        if not path.is_file():
            raise FileNotFoundError(
                f"required capsule artifact is missing: {repo_path(path)}"
            )
        artifacts.append(
            {
                "path": repo_path(path),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return artifacts


def observed_dependencies(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for expected in protocol["dependencies"]:
        distribution = str(expected["distribution"])
        try:
            metadata = importlib.metadata.metadata(distribution)
            version = importlib.metadata.version(distribution)
            publisher = (
                metadata.get("Author")
                or metadata.get("Maintainer")
                or metadata.get("Name")
                or distribution
            )
            installed = True
        except importlib.metadata.PackageNotFoundError:
            version = ""
            publisher = ""
            installed = False
        rows.append(
            {
                **expected,
                "installed": installed,
                "observed_version": version,
                "version_match": installed and version == str(expected["version"]),
                "publisher": publisher,
                "purl": (
                    f"pkg:pypi/{distribution.lower().replace('_', '-')}@{version}"
                    if installed
                    else ""
                ),
            }
        )
    return rows


def build_sbom(
    protocol: dict[str, Any], dependencies: list[dict[str, Any]], generated_utc: str
) -> dict[str, Any]:
    root_ref = (
        f"pkg:generic/lumencore/reviewer-reproducibility@{protocol['protocol_id']}"
    )
    expected = {canonicalize_name(row["distribution"]): row for row in dependencies}
    components_by_name: dict[str, dict[str, Any]] = {}
    dependency_refs: dict[str, set[str]] = {}
    queue = list(expected)

    while queue:
        requested_name = canonicalize_name(queue.pop(0))
        if requested_name in components_by_name:
            continue
        expected_row = expected.get(requested_name)
        try:
            distribution = importlib.metadata.distribution(requested_name)
        except importlib.metadata.PackageNotFoundError:
            version = str(expected_row["version"]) if expected_row else "unknown"
            ref = f"missing:{requested_name}@{version}"
            components_by_name[requested_name] = {
                "type": "library",
                "bom-ref": ref,
                "name": requested_name,
                "version": version,
                "publisher": "unknown",
                "properties": [
                    {"name": "lumencore:relationship", "value": "direct_missing"},
                    {"name": "lumencore:installed", "value": "false"},
                ],
            }
            dependency_refs[ref] = set()
            continue

        project_name = str(distribution.metadata.get("Name") or requested_name)
        normalized_name = canonicalize_name(project_name)
        version = distribution.version
        purl = f"pkg:pypi/{normalized_name}@{version}"
        relationship = (
            str(expected_row["relationship"]) if expected_row else "transitive"
        )
        expected_version = str(expected_row["version"]) if expected_row else version
        properties = [
            {"name": "lumencore:expected-version", "value": expected_version},
            {"name": "lumencore:relationship", "value": relationship},
            {
                "name": "lumencore:version-match",
                "value": str(version == expected_version).lower(),
            },
        ]
        components_by_name[normalized_name] = {
            "type": "library",
            "bom-ref": purl,
            "name": project_name,
            "version": version,
            "publisher": distribution.metadata.get("Author") or project_name,
            "purl": purl,
            "properties": properties,
        }

        children = set()
        for requirement_text in distribution.requires or []:
            requirement = Requirement(requirement_text)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            child_name = canonicalize_name(requirement.name)
            try:
                child_distribution = importlib.metadata.distribution(child_name)
                child_project = str(
                    child_distribution.metadata.get("Name") or child_name
                )
                child_normalized = canonicalize_name(child_project)
                child_ref = f"pkg:pypi/{child_normalized}@{child_distribution.version}"
                children.add(child_ref)
                if child_normalized not in components_by_name:
                    queue.append(child_normalized)
            except importlib.metadata.PackageNotFoundError:
                children.add(f"missing:{child_name}")
        dependency_refs[purl] = children

    components = sorted(components_by_name.values(), key=lambda row: row["bom-ref"])
    root_dependencies = sorted(
        components_by_name[name]["bom-ref"]
        for name in expected
        if name in components_by_name
    )
    dependency_rows = [{"ref": root_ref, "dependsOn": root_dependencies}]
    dependency_rows.extend(
        {
            "ref": component["bom-ref"],
            "dependsOn": sorted(dependency_refs.get(component["bom-ref"], set())),
        }
        for component in components
    )
    serial_seed = canonical_json(
        {
            "protocol_id": protocol["protocol_id"],
            "components": [(row["name"], row["version"]) for row in components],
        }
    )
    serial = uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": generated_utc,
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "name": "LumenCore reviewer reproducibility capsule",
                "version": protocol["protocol_id"],
                "supplier": {"name": "LumenCore"},
            },
            "properties": [
                {"name": "lumencore:scope", "value": "reviewer-suite-only"},
                {
                    "name": "lumencore:artifact-hash-lock-complete",
                    "value": str(
                        protocol["environment"]["artifact_hash_lock_complete"]
                    ).lower(),
                },
            ],
        },
        "components": components,
        "dependencies": dependency_rows,
    }


def assertion(
    assertion_id: str,
    actual: Any,
    expected: Any,
    *,
    tolerance: float | None = None,
    relative_tolerance: float | None = None,
) -> dict[str, Any]:
    absolute_difference: float | None = None
    relative_difference: float | None = None
    if tolerance is None and relative_tolerance is None:
        passed = actual == expected
    else:
        try:
            actual_float = float(actual)
            expected_float = float(expected)
            absolute_difference = abs(actual_float - expected_float)
            if expected_float == 0.0:
                relative_difference = 0.0 if absolute_difference == 0.0 else None
            else:
                relative_difference = absolute_difference / abs(expected_float)
            absolute_pass = tolerance is not None and absolute_difference <= tolerance
            relative_pass = (
                relative_tolerance is not None
                and relative_difference is not None
                and relative_difference <= relative_tolerance
            )
            passed = absolute_pass or relative_pass
        except (TypeError, ValueError, OverflowError):
            passed = False
    row = {
        "assertion_id": assertion_id,
        "actual": actual,
        "expected": expected,
        "passed": bool(passed),
    }
    if tolerance is not None:
        row["absolute_tolerance"] = tolerance
    if relative_tolerance is not None:
        row["relative_tolerance"] = relative_tolerance
    if absolute_difference is not None:
        row["absolute_difference"] = absolute_difference
    if relative_difference is not None:
        row["relative_difference"] = relative_difference
    return row


def execute_captured(
    runner: Callable[[], dict[str, Any]], log_path: Path
) -> tuple[dict[str, Any], float]:
    buffer = io.StringIO()
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            result = runner()
        return result, time.perf_counter() - started
    except Exception:
        traceback.print_exc(file=buffer)
        raise
    finally:
        write_text(log_path, redact_text(buffer.getvalue()))


def _run_module_benchmark(
    module: Any, panel: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, Any]:
    report, rows = module.run_benchmark(panel, protocol)
    return {"report": report, "rows": rows}


def run_eia_wave(
    panel: dict[str, Any], suite: dict[str, Any], run_dir: Path
) -> dict[str, Any]:
    module = load_module("eia_wave")
    expected = suite["expected"]
    protocol = module.load_protocol()
    captured, elapsed = execute_captured(
        lambda: _run_module_benchmark(module, panel, protocol),
        run_dir / "logs" / "eia_wave.log",
    )
    report = captured["report"]
    rows = captured["rows"]
    leaderboard = report["holdout_leaderboard"]
    best = leaderboard[0]
    kuramoto = next(
        row for row in leaderboard if row["strategy"] == "kuramoto_phase_coupling"
    )
    checks = [
        assertion(
            "panel_rows",
            report["panel"]["quality"]["row_count"],
            expected["panel_rows"],
        ),
        assertion("holdout_rows", best["row_count"], expected["holdout_rows"]),
        assertion(
            "holdout_authorities",
            best["authority_count"],
            expected["holdout_authorities"],
        ),
        assertion(
            "selected_candidate",
            report["selection"]["selected_wave_candidate"],
            expected["selected_candidate"],
        ),
        assertion("best_strategy", best["strategy"], expected["best_strategy"]),
        assertion(
            "best_mase",
            best["mean_seasonal_mase_7"],
            expected["best_mase"],
            tolerance=expected["tolerance"],
        ),
        assertion(
            "kuramoto_mase",
            kuramoto["mean_seasonal_mase_7"],
            expected["kuramoto_mase"],
            tolerance=expected["tolerance"],
        ),
        assertion(
            "promotion_gate_passed",
            report["promotion_gate"]["protocol_grade_internal_champion"],
            expected["promotion_gate_passed"],
        ),
        assertion(
            "field_validation_complete",
            report["promotion_gate"]["field_validation_complete"],
            expected["field_validation_complete"],
        ),
    ]
    facts = {
        "evaluation_rows": len(rows),
        "selected_candidate": report["selection"]["selected_wave_candidate"],
        "best_strategy": best["strategy"],
        "best_mase": best["mean_seasonal_mase_7"],
        "kuramoto_mase": kuramoto["mean_seasonal_mase_7"],
        "baseline_comparison_count": len(report["baseline_comparisons"]),
        "promotion_gate_passed": report["promotion_gate"][
            "protocol_grade_internal_champion"
        ],
        "field_validation_complete": report["promotion_gate"][
            "field_validation_complete"
        ],
    }
    return suite_result(suite, facts, checks, elapsed_seconds=elapsed)


def run_eia_residual(
    panel: dict[str, Any], suite: dict[str, Any], run_dir: Path
) -> dict[str, Any]:
    module = load_module("eia_residual")
    expected = suite["expected"]
    protocol = module.load_protocol()
    captured, elapsed = execute_captured(
        lambda: _run_module_benchmark(module, panel, protocol),
        run_dir / "logs" / "eia_residual.log",
    )
    report = captured["report"]
    rows = captured["rows"]
    leaderboard = report["holdout_leaderboard"]
    best = leaderboard[0]
    checks = [
        assertion(
            "panel_rows", report["frozen_panel"]["row_count"], expected["panel_rows"]
        ),
        assertion("holdout_rows", best["row_count"], expected["holdout_rows"]),
        assertion(
            "holdout_authorities",
            best["authority_count"],
            expected["holdout_authorities"],
        ),
        assertion(
            "selected_candidate",
            report["selection"]["selected_candidate"],
            expected["selected_candidate"],
        ),
        assertion("best_strategy", best["strategy"], expected["best_strategy"]),
        assertion(
            "best_mase",
            best["mean_seasonal_mase_7"],
            expected["best_mase"],
            relative_tolerance=expected["relative_tolerance"],
        ),
        assertion(
            "baseline_comparison_count",
            len(report["baseline_comparisons"]),
            expected["baseline_comparison_count"],
        ),
        assertion(
            "promotion_gate_passed",
            report["promotion_gate"]["protocol_grade_internal_champion"],
            expected["promotion_gate_passed"],
        ),
        assertion(
            "coverage_gate_passed",
            report["promotion_gate"]["coverage_pass"],
            expected["coverage_gate_passed"],
        ),
        assertion(
            "field_validation_complete",
            report["promotion_gate"]["field_validation_complete"],
            expected["field_validation_complete"],
        ),
    ]
    facts = {
        "evaluation_rows": len(rows),
        "selected_candidate": report["selection"]["selected_candidate"],
        "best_strategy": best["strategy"],
        "best_mase": best["mean_seasonal_mase_7"],
        "baseline_comparison_count": len(report["baseline_comparisons"]),
        "holm_positive_point_improvement_count": sum(
            1
            for row in report["baseline_comparisons"]
            if row["mean_skill_delta"] > 0 and row["holm_adjusted_p_value"] <= 0.05
        ),
        "promotion_gate_passed": report["promotion_gate"][
            "protocol_grade_internal_champion"
        ],
        "coverage_gate_passed": report["promotion_gate"]["coverage_pass"],
        "field_validation_complete": report["promotion_gate"][
            "field_validation_complete"
        ],
    }
    return suite_result(suite, facts, checks, elapsed_seconds=elapsed)


def run_mda_open_set(suite: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    module = load_module("mda_open_set")
    expected = suite["expected"]
    with tempfile.TemporaryDirectory(prefix="luma-reviewer-mda-") as temporary:
        base = Path(temporary)
        result, elapsed = execute_captured(
            lambda: module.run_benchmark(
                output_dir=base / "out",
                doc_path=base / "mda_result.md",
            ),
            run_dir / "logs" / "mda_open_set.log",
        )
    candidate = result["holdout_metrics"]["hybrid_static_then_open_set_lexical_v2"]
    checks = [
        assertion(
            "fixture_count",
            result["fixture_counts"]["total"],
            expected["fixture_count"],
        ),
        assertion(
            "holdout_count",
            result["fixture_counts"]["blind_holdout"],
            expected["holdout_count"],
        ),
        assertion(
            "candidate_micro_f1",
            candidate["micro_f1"],
            expected["candidate_micro_f1"],
            tolerance=expected["tolerance"],
        ),
        assertion(
            "candidate_supported_coverage",
            candidate["supported_coverage"],
            expected["candidate_supported_coverage"],
            tolerance=expected["tolerance"],
        ),
        assertion(
            "candidate_unsupported_mapping_rate",
            candidate["unsupported_mapping_rate"],
            expected["candidate_unsupported_mapping_rate"],
            tolerance=expected["tolerance"],
        ),
        assertion(
            "promotion_gate_passed",
            result["gate"]["passed"],
            expected["promotion_gate_passed"],
        ),
        assertion(
            "operational_or_field_claim_allowed",
            result["gate"]["operational_or_field_claim_allowed"],
            expected["operational_or_field_claim_allowed"],
        ),
    ]
    facts = {
        "fixture_chain_sha256": result["fixture_chain_sha256"],
        "fixture_count": result["fixture_counts"]["total"],
        "holdout_count": result["fixture_counts"]["blind_holdout"],
        "candidate_micro_f1": candidate["micro_f1"],
        "candidate_supported_coverage": candidate["supported_coverage"],
        "candidate_unsupported_mapping_rate": candidate["unsupported_mapping_rate"],
        "promotion_gate_passed": result["gate"]["passed"],
        "operational_or_field_claim_allowed": result["gate"][
            "operational_or_field_claim_allowed"
        ],
    }
    return suite_result(suite, facts, checks, elapsed_seconds=elapsed)


def suite_result(
    suite: dict[str, Any],
    facts: dict[str, Any],
    checks: list[dict[str, Any]],
    *,
    elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "suite_id": suite["suite_id"],
        "kind": suite["kind"],
        "runner": suite["runner"],
        "passed": all(row["passed"] for row in checks),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "fact_projection": facts,
        "fact_projection_sha256": canonical_sha256(facts),
        "assertions": checks,
    }


def failed_suite_result(suite: dict[str, Any], error: Exception) -> dict[str, Any]:
    error_record = {
        "type": type(error).__name__,
        "message": redact_text(str(error)),
    }
    return {
        "suite_id": suite["suite_id"],
        "kind": suite["kind"],
        "runner": suite["runner"],
        "passed": False,
        "elapsed_seconds": None,
        "fact_projection": {},
        "fact_projection_sha256": canonical_sha256({}),
        "assertions": [],
        "error": error_record,
    }


def load_frozen_panel(
    protocol: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    frozen = protocol["frozen_inputs"][0]
    path = ROOT / frozen["path"]
    compressed = path.read_bytes()
    compressed_sha256 = hashlib.sha256(compressed).hexdigest()
    raw = gzip.decompress(compressed)
    uncompressed_sha256 = hashlib.sha256(raw).hexdigest()
    panel = json.loads(raw.decode("utf-8"))
    row_chain_sha256 = canonical_sha256(panel["rows"])
    checks = [
        assertion("compressed_sha256", compressed_sha256, frozen["compressed_sha256"]),
        assertion(
            "uncompressed_sha256", uncompressed_sha256, frozen["uncompressed_sha256"]
        ),
        assertion("row_chain_sha256", row_chain_sha256, frozen["row_chain_sha256"]),
        assertion("row_count", panel["quality"]["row_count"], frozen["row_count"]),
        assertion(
            "credential_serialized", panel["source"]["credential_serialized"], False
        ),
    ]
    return (
        panel,
        {
            "input_id": frozen["input_id"],
            "path": frozen["path"],
            "passed": all(row["passed"] for row in checks),
            "assertions": checks,
        },
        raw,
    )


@contextlib.contextmanager
def materialize_frozen_panel(protocol: dict[str, Any], raw: bytes):
    frozen = protocol["frozen_inputs"][0]
    target = (ROOT / frozen["materialized_path"]).resolve()
    target.relative_to(ROOT.resolve())
    existed = target.is_file()
    if existed:
        if file_sha256(target) != frozen["uncompressed_sha256"]:
            raise ValueError(
                "existing materialized EIA panel does not match the frozen input"
            )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    try:
        yield target
    finally:
        if not existed and target.is_file():
            target.unlink()


def run_fixture_tests(protocol: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable if part == "python" else part
        for part in protocol["fixture_test_command"]
    ]
    environment = deterministic_environment(protocol)
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - started
    log = redact_text(result.stdout + ("\n" + result.stderr if result.stderr else ""))
    log_path = run_dir / "logs" / "fixture_tests.log"
    write_text(log_path, log)
    return {
        "command": ["python", *protocol["fixture_test_command"][1:]],
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "elapsed_seconds": round(elapsed, 3),
        "log_path": repo_path(log_path),
        "log_sha256": file_sha256(log_path),
    }


def deterministic_environment(protocol: dict[str, Any]) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = protocol["environment"]["pythonhashseed"]
    environment["TZ"] = protocol["environment"]["timezone"]
    environment.update(protocol["environment"]["thread_limits"])
    return environment


def runtime_environment_receipt(protocol: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "PYTHONHASHSEED": protocol["environment"]["pythonhashseed"],
        "TZ": protocol["environment"]["timezone"],
        **protocol["environment"]["thread_limits"],
    }
    observed = {key: os.environ.get(key, "") for key in expected}
    return {
        "expected": expected,
        "observed": observed,
        "matches": all(observed[key] == value for key, value in expected.items()),
    }


def git_state(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    paths = [row["path"] for row in artifacts]
    porcelain = safe_git(["status", "--porcelain", "--", *paths])
    return {
        "commit": safe_git(["rev-parse", "HEAD"]),
        "branch": safe_git(["branch", "--show-current"]),
        "relevant_source_clean": not bool(porcelain),
        "relevant_change_line_count": len(porcelain.splitlines()) if porcelain else 0,
        "relevant_change_digest": canonical_sha256(porcelain.splitlines()),
    }


def redact_text(text: str) -> str:
    redacted = text.replace(str(ROOT), "<repo>").replace(str(Path.home()), "<home>")
    redacted = re.sub(r"[A-Za-z]:[/\\][^\r\n\t ]+", "<local-path>", redacted)
    return redacted


def scan_private(payload: Any) -> list[str]:
    rendered = json.dumps(payload, sort_keys=True)
    return [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(rendered)]


def build_capsule(
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    run_dir: Path = DEFAULT_RUN_DIR,
    with_fixture_tests: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = load_protocol(protocol_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    generated_utc = now_utc()
    artifacts = source_artifacts(protocol, protocol_path)
    dependencies = observed_dependencies(protocol)
    panel, input_receipt, panel_raw = load_frozen_panel(protocol)
    suites = []
    with materialize_frozen_panel(protocol, panel_raw):
        for suite in protocol["suites"]:
            runner = suite["runner"]
            try:
                if runner == "eia_wave":
                    suites.append(run_eia_wave(panel, suite, run_dir))
                elif runner == "eia_residual":
                    suites.append(run_eia_residual(panel, suite, run_dir))
                elif runner == "mda_open_set":
                    suites.append(run_mda_open_set(suite, run_dir))
                else:
                    raise ValueError(f"unsupported reviewer capsule runner: {runner}")
            except Exception as error:
                suites.append(failed_suite_result(suite, error))

    fixture_tests = (
        run_fixture_tests(protocol, run_dir)
        if with_fixture_tests
        else {"executed": False, "passed": None}
    )
    dependencies_match = all(row["version_match"] for row in dependencies)
    suites_pass = all(row["passed"] for row in suites)
    fixture_tests_pass = fixture_tests.get("passed") is not False
    source_state = git_state(artifacts)
    runtime_environment = runtime_environment_receipt(protocol)
    sbom = build_sbom(protocol, dependencies, generated_utc)
    status = (
        "BOUNDED_REPRODUCIBILITY_PASS"
        if input_receipt["passed"]
        and dependencies_match
        and suites_pass
        and fixture_tests_pass
        and runtime_environment["matches"]
        else "BOUNDED_REPRODUCIBILITY_FAIL"
    )
    capsule = {
        "schema": "reviewer_reproducibility_capsule.v1",
        "protocol_id": protocol["protocol_id"],
        "generated_utc": generated_utc,
        "status": status,
        "summary": {
            "suite_count": len(suites),
            "suite_pass_count": sum(1 for row in suites if row["passed"]),
            "assertion_count": sum(len(row["assertions"]) for row in suites)
            + len(input_receipt["assertions"]),
            "assertion_pass_count": sum(
                sum(1 for check in row["assertions"] if check["passed"])
                for row in suites
            )
            + sum(1 for check in input_receipt["assertions"] if check["passed"]),
            "frozen_input_passed": input_receipt["passed"],
            "dependency_count": len(dependencies),
            "dependency_version_match_count": sum(
                1 for row in dependencies if row["version_match"]
            ),
            "dependency_versions_exact_match": dependencies_match,
            "sbom_component_count": len(sbom["components"]),
            "deterministic_environment_match": runtime_environment["matches"],
            "artifact_hash_lock_complete": protocol["environment"][
                "artifact_hash_lock_complete"
            ],
            "fixture_tests_executed": bool(with_fixture_tests),
            "fixture_tests_passed": fixture_tests.get("passed"),
            "relevant_source_clean": source_state["relevant_source_clean"],
            "clean_runner_replay": source_state["relevant_source_clean"]
            and with_fixture_tests,
            "external_validation_complete": False,
            "agency_certification_complete": False,
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "pythonhashseed": protocol["environment"]["pythonhashseed"],
            "timezone": protocol["environment"]["timezone"],
            "thread_limits": protocol["environment"]["thread_limits"],
            "runtime_control": runtime_environment,
        },
        "git": source_state,
        "frozen_input": input_receipt,
        "dependencies": dependencies,
        "source_artifacts": artifacts,
        "source_chain_sha256": canonical_sha256(artifacts),
        "suites": suites,
        "fixture_tests": fixture_tests,
        "standards_references": protocol["standards_references"],
        "protocol_amendment": protocol.get("amendment"),
        "excluded_full_replays": protocol["excluded_full_replays"],
        "known_gap": protocol["environment"]["artifact_hash_lock_gap"],
        "claim_boundary": protocol["claim_boundary"],
    }
    private_hits = scan_private({"capsule": capsule, "sbom": sbom})
    capsule["privacy_scan"] = {
        "passed": not private_hits,
        "configured_pattern_hit_count": len(private_hits),
    }
    if private_hits:
        capsule["status"] = "BOUNDED_REPRODUCIBILITY_FAIL"
    capsule["capsule_sha256"] = canonical_sha256(capsule)
    return capsule, sbom


def render_markdown(capsule: dict[str, Any]) -> str:
    summary = capsule["summary"]
    lines = [
        "# Reviewer Reproducibility Capsule - 2026-07-14",
        "",
        "Purpose: let a technical reviewer replay selected public-safe evidence from a frozen public input and a version-pinned Python environment.",
        "",
        capsule["claim_boundary"],
        "",
        "## Result",
        "",
        f"- Status: `{capsule['status']}`",
        f"- Suites passed: `{summary['suite_pass_count']}/{summary['suite_count']}`",
        f"- Assertions passed: `{summary['assertion_pass_count']}/{summary['assertion_count']}`",
        f"- Dependency versions matched: `{summary['dependency_version_match_count']}/{summary['dependency_count']}`",
        f"- Scoped SBOM components: `{summary['sbom_component_count']}`",
        f"- Deterministic environment matched: `{str(summary['deterministic_environment_match']).lower()}`",
        f"- Frozen input passed: `{str(summary['frozen_input_passed']).lower()}`",
        f"- Relevant source clean: `{str(summary['relevant_source_clean']).lower()}`",
        f"- Clean-runner replay: `{str(summary['clean_runner_replay']).lower()}`",
        f"- Artifact hash lock complete: `{str(summary['artifact_hash_lock_complete']).lower()}`",
        f"- External validation complete: `{str(summary['external_validation_complete']).lower()}`",
        f"- Agency certification complete: `{str(summary['agency_certification_complete']).lower()}`",
        f"- Fixture tests executed: `{str(summary['fixture_tests_executed']).lower()}`",
        f"- Fixture tests passed: `{str(summary['fixture_tests_passed']).lower()}`",
        f"- Source chain SHA-256: `{capsule['source_chain_sha256']}`",
        f"- Capsule SHA-256: `{capsule['capsule_sha256']}`",
        "",
        "## Protocol Amendment",
        "",
        f"- {capsule['protocol_amendment']['preregistration_boundary']}",
        f"- Policy: {capsule['protocol_amendment']['policy']}",
        f"- Preserved failed GitHub runs: `{', '.join(str(value) for value in capsule['protocol_amendment']['failed_github_run_ids'])}`",
        "",
        "## Replayed Suites",
        "",
    ]
    for suite in capsule["suites"]:
        lines.extend(
            [
                f"### `{suite['suite_id']}`",
                "",
                f"- Kind: `{suite['kind']}`",
                f"- Passed: `{str(suite['passed']).lower()}`",
                f"- Elapsed seconds: `{suite['elapsed_seconds']}`",
                f"- Fact projection SHA-256: `{suite['fact_projection_sha256']}`",
                "- Facts:",
            ]
        )
        for key, value in suite["fact_projection"].items():
            lines.append(f"  - `{key}`: `{value}`")
        lines.append("- Assertions:")
        for check in suite["assertions"]:
            tolerance_text = ""
            if "absolute_tolerance" in check:
                tolerance_text += f" absolute_tolerance=`{check['absolute_tolerance']}`"
            if "relative_tolerance" in check:
                tolerance_text += f" relative_tolerance=`{check['relative_tolerance']}`"
            if "relative_difference" in check:
                tolerance_text += f" relative_difference=`{check['relative_difference']}`"
            lines.append(
                f"  - `{check['assertion_id']}` passed=`{str(check['passed']).lower()}` actual=`{check['actual']}` expected=`{check['expected']}`{tolerance_text}"
            )
        lines.append("")

    lines.extend(
        [
            "## Supply-Chain Boundary",
            "",
            f"- {capsule['known_gap']}",
            "- The CycloneDX inventory covers the reviewer suite, not every component in the wider repository or deployed service.",
            "",
            "## Excluded Full Replays",
            "",
        ]
    )
    for row in capsule["excluded_full_replays"]:
        lines.append(f"- `{row['lane']}`: {row['reason']}")
    lines.extend(["", "## Standards References", ""])
    for row in capsule["standards_references"]:
        lines.append(f"- [{row['name']}]({row['url']}): {row['use']}")
    return "\n".join(lines) + "\n"


def publish(capsule: dict[str, Any], sbom: dict[str, Any]) -> None:
    write_json(PUBLISHED_JSON, capsule)
    write_json(DASHBOARD_JSON, capsule)
    write_json(PUBLISHED_SBOM, sbom)
    write_text(PUBLISHED_MD, render_markdown(capsule))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--with-fixture-tests", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    protocol = load_protocol(args.protocol)
    runtime_environment = runtime_environment_receipt(protocol)
    if not runtime_environment["matches"]:
        if os.environ.get("LUMA_REVIEWER_CAPSULE_CHILD") == "1":
            print(
                json.dumps(
                    {
                        "status": "BOUNDED_REPRODUCIBILITY_FAIL",
                        "reason": "deterministic runtime environment did not apply",
                        "runtime_environment": runtime_environment,
                    },
                    indent=2,
                )
            )
            return 1
        child_environment = deterministic_environment(protocol)
        child_environment["LUMA_REVIEWER_CAPSULE_CHILD"] = "1"
        return subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=ROOT,
            env=child_environment,
            check=False,
        ).returncode

    capsule, sbom = build_capsule(
        protocol_path=args.protocol,
        run_dir=args.run_dir,
        with_fixture_tests=args.with_fixture_tests,
    )
    write_json(args.run_dir / "reviewer_reproducibility_receipt.json", capsule)
    write_json(args.run_dir / "reviewer_suite_sbom.cdx.json", sbom)
    if args.publish:
        publish(capsule, sbom)
    print(
        json.dumps(
            {
                "status": capsule["status"],
                "suites": capsule["summary"]["suite_count"],
                "suite_passes": capsule["summary"]["suite_pass_count"],
                "assertion_passes": capsule["summary"]["assertion_pass_count"],
                "assertions": capsule["summary"]["assertion_count"],
                "receipt": repo_path(
                    args.run_dir / "reviewer_reproducibility_receipt.json"
                ),
            },
            indent=2,
        )
    )
    return 0 if capsule["status"] == "BOUNDED_REPRODUCIBILITY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
