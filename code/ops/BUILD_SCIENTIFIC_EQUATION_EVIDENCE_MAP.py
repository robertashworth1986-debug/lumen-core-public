from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "scientific_equation_registry_v1.json"
OUT_JSON = ROOT / "evidence" / "reviewer" / "scientific_equation_evidence_map_20260716.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "scientific_equation_evidence_map.json"
OUT_MD = ROOT / "docs" / "SCIENTIFIC_EQUATION_EVIDENCE_MAP_2026-07-16.md"

IMPLEMENTATION_CLASSES = {
    "EXACT_STANDARD_METHOD",
    "OPERATIONAL_DEFINITION",
    "HEURISTIC_ANALOGUE",
    "EXPLORATORY_HEURISTIC",
}
EVIDENCE_ORDER = {
    "E0_CONCEPT_ONLY": 0,
    "E1_INTERNAL_IMPLEMENTATION": 1,
    "E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC": 2,
    "E3_INDEPENDENT_REPRODUCTION": 3,
    "E4_FIELD_OR_ACCEPTANCE_VALIDATED": 4,
}
CLAIM_ORDER = {
    "C0_CONCEPT_ONLY": 0,
    "C1_INTERNAL_IMPLEMENTATION": 1,
    "C2_FROZEN_INTERNAL_EVIDENCE": 2,
    "C3_INDEPENDENT_REPRODUCTION": 3,
    "C4_FIELD_OR_ACCEPTANCE": 4,
}

FORCED_CLASSIFICATIONS = {
    ("code/geometry_wave_resonance_timing_benchmark.py", "strategy_kuramoto_phase_coupling"): "HEURISTIC_ANALOGUE",
    ("code/geometry_optimal_curve_transport_benchmark.py", "strategy_brachistochrone_descent"): "HEURISTIC_ANALOGUE",
    ("code/geometry_thermal_ventilation_benchmark.py", "strategy_thermal_plume_convection"): "HEURISTIC_ANALOGUE",
    ("code/nv065_sensor_tasking_benchmark.py", "expected_contribution"): "EXPLORATORY_HEURISTIC",
    ("code/missionweave_benchmark.py", "_priority"): "EXPLORATORY_HEURISTIC",
    ("code/universal_harmonic_edge_core.py", "phi_resonance_bonus"): "EXPLORATORY_HEURISTIC",
    ("code/universal_harmonic_edge_core.py", "score_signal"): "EXPLORATORY_HEURISTIC",
}


class RegistryValidationError(ValueError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RegistryValidationError(f"expected object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_path(raw: str, root: Path = ROOT) -> Path:
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RegistryValidationError(f"path escapes repository: {raw}") from exc
    return candidate


def build_file_hash_audit(
    registry: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return a deterministic, non-mutating audit of registered file hashes."""
    files = registry.get("files")
    records: list[dict[str, Any]] = []
    files_valid = isinstance(files, dict) and bool(files)
    if files_valid:
        for relative in sorted(files):
            metadata = files[relative]
            record: dict[str, Any] = {
                "path": relative,
                "role": metadata.get("role") if isinstance(metadata, dict) else None,
                "expected_sha256": None,
                "observed_sha256": None,
                "byte_count": None,
                "status": "INVALID_METADATA",
            }
            if not isinstance(metadata, dict):
                records.append(record)
                continue

            expected = str(metadata.get("sha256") or "").lower()
            record["expected_sha256"] = expected or None
            try:
                path = repo_path(relative, root)
            except RegistryValidationError:
                record["status"] = "INVALID_PATH"
                records.append(record)
                continue
            if not path.is_file():
                record["status"] = "MISSING"
                records.append(record)
                continue

            record["byte_count"] = path.stat().st_size
            record["observed_sha256"] = sha256_file(path)
            if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
                record["status"] = "INVALID_EXPECTED_HASH"
            elif record["observed_sha256"] == expected:
                record["status"] = "CURRENT"
            else:
                record["status"] = "DRIFT"
            records.append(record)

    status_counts = Counter(record["status"] for record in records)
    summary = {
        "registry_files_valid": files_valid,
        "file_count": len(records),
        "current_count": status_counts["CURRENT"],
        "drift_count": status_counts["DRIFT"],
        "missing_count": status_counts["MISSING"],
        "invalid_metadata_count": status_counts["INVALID_METADATA"],
        "invalid_path_count": status_counts["INVALID_PATH"],
        "invalid_expected_hash_count": status_counts["INVALID_EXPECTED_HASH"],
    }
    summary["all_current"] = files_valid and summary["current_count"] == summary["file_count"]
    audit_core = {
        "schema": "lumencore_scientific_equation_registry_hash_audit_v1",
        "summary": summary,
        "records": records,
    }
    return {**audit_core, "audit_sha256": canonical_sha256(audit_core)}


def find_symbol(tree: ast.Module, dotted: str) -> ast.AST | None:
    parts = dotted.split(".")
    body: list[ast.stmt] = tree.body
    node: ast.AST | None = None
    for part in parts:
        node = next(
            (
                item
                for item in body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and item.name == part
            ),
            None,
        )
        if node is None:
            return None
        body = node.body if isinstance(node, ast.ClassDef) else []
    return node


def referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, ast.Attribute):
            names.add(item.attr)
    return names


def _validate_files(registry: dict[str, Any], root: Path, verify_hashes: bool) -> list[str]:
    failures: list[str] = []
    files = registry.get("files")
    if not isinstance(files, dict) or not files:
        return ["registry.files must be a nonempty object"]
    audit = build_file_hash_audit(registry, root=root)
    for record in audit["records"]:
        relative = record["path"]
        status = record["status"]
        if status == "INVALID_METADATA":
            failures.append(f"file metadata is not an object: {relative}")
        elif status == "INVALID_PATH":
            failures.append(f"path escapes repository: {relative}")
        elif status == "MISSING":
            failures.append(f"registered file is missing: {relative}")
        elif status == "INVALID_EXPECTED_HASH":
            failures.append(f"registered file SHA-256 is invalid: {relative}")
        elif status == "DRIFT" and verify_hashes:
            failures.append(f"registered file SHA-256 mismatch: {relative}")
    return failures


def validate_registry(
    registry: dict[str, Any],
    *,
    root: Path = ROOT,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    failures = _validate_files(registry, root, verify_hashes)
    if registry.get("schema") != "lumencore_scientific_equation_registry_v1":
        failures.append("unexpected registry schema")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("registry.entries must be a nonempty list")
        entries = []
    files = registry.get("files") if isinstance(registry.get("files"), dict) else {}
    ids: set[str] = set()
    ast_cache: dict[str, ast.Module] = {}

    def tree_for(relative: str) -> ast.Module | None:
        if relative not in files:
            failures.append(f"entry references unregistered file: {relative}")
            return None
        if relative not in ast_cache:
            path = repo_path(relative, root)
            if path.is_file():
                try:
                    ast_cache[relative] = ast.parse(path.read_text(encoding="utf-8-sig"))
                except (SyntaxError, UnicodeError) as exc:
                    failures.append(f"cannot parse {relative}: {exc}")
                    return None
        return ast_cache.get(relative)

    for index, raw in enumerate(entries):
        prefix = f"entry[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{prefix} is not an object")
            continue
        equation_id = str(raw.get("equation_id") or "")
        if not equation_id:
            failures.append(f"{prefix} has no equation_id")
        elif equation_id in ids:
            failures.append(f"duplicate equation_id: {equation_id}")
        ids.add(equation_id)

        implementation_class = str(raw.get("implementation_class") or "")
        if implementation_class not in IMPLEMENTATION_CLASSES:
            failures.append(f"{equation_id}: invalid implementation_class")
        if len(str(raw.get("formal_expression") or "")) < 8:
            failures.append(f"{equation_id}: formal_expression is missing or too weak")
        if not isinstance(raw.get("symbols"), dict) or not raw.get("symbols"):
            failures.append(f"{equation_id}: symbols must be a nonempty object")
        if not isinstance(raw.get("constants"), list):
            failures.append(f"{equation_id}: constants must be a list")
        evidence_class = str(raw.get("evidence_class") or "")
        claim_level = str(raw.get("claim_level") or "")
        if evidence_class not in EVIDENCE_ORDER:
            failures.append(f"{equation_id}: invalid evidence_class")
        if claim_level not in CLAIM_ORDER:
            failures.append(f"{equation_id}: invalid claim_level")
        if evidence_class in EVIDENCE_ORDER and claim_level in CLAIM_ORDER:
            if CLAIM_ORDER[claim_level] > EVIDENCE_ORDER[evidence_class]:
                failures.append(f"{equation_id}: claim level exceeds evidence class")

        source = raw.get("source")
        if not isinstance(source, dict):
            failures.append(f"{equation_id}: source is missing")
            continue
        source_path = str(source.get("path") or "")
        source_symbol = str(source.get("symbol") or "")
        source_tree = tree_for(source_path)
        source_node = find_symbol(source_tree, source_symbol) if source_tree and source_symbol else None
        if source_node is None:
            failures.append(f"{equation_id}: source symbol not found: {source_path}:{source_symbol}")
        forced = FORCED_CLASSIFICATIONS.get((source_path, source_symbol))
        if forced and implementation_class != forced:
            failures.append(
                f"{equation_id}: {source_symbol} must be classified as {forced}, not {implementation_class}"
            )

        tests = raw.get("tests")
        if not isinstance(tests, list) or not tests:
            failures.append(f"{equation_id}: at least one test binding is required")
            tests = []
        source_leaf = source_symbol.split(".")[-1]
        for test in tests:
            if not isinstance(test, dict):
                failures.append(f"{equation_id}: invalid test binding")
                continue
            test_path = str(test.get("path") or "")
            test_symbol = str(test.get("symbol") or "")
            test_tree = tree_for(test_path)
            test_node = find_symbol(test_tree, test_symbol) if test_tree and test_symbol else None
            if test_node is None:
                failures.append(f"{equation_id}: test symbol not found: {test_path}:{test_symbol}")
            elif source_leaf not in referenced_names(test_node):
                failures.append(
                    f"{equation_id}: test {test_symbol} does not reference source symbol {source_leaf}"
                )

        bindings = raw.get("bindings")
        if not isinstance(bindings, list) or not bindings:
            failures.append(f"{equation_id}: at least one protocol/evidence binding is required")
        else:
            for binding in bindings:
                if str(binding) not in files:
                    failures.append(f"{equation_id}: unregistered binding file: {binding}")

        blocked = raw.get("blocked_claims")
        if not isinstance(blocked, list) or not blocked:
            failures.append(f"{equation_id}: blocked_claims must be nonempty")
        boundary = str(raw.get("claim_boundary") or "")
        if len(boundary) < 30:
            failures.append(f"{equation_id}: claim_boundary is too weak")
        if implementation_class == "HEURISTIC_ANALOGUE" and "not a governing-equation solver" not in boundary.lower():
            failures.append(f"{equation_id}: analogue boundary must say it is not a governing-equation solver")

        ip = raw.get("ip_position")
        if not isinstance(ip, dict):
            failures.append(f"{equation_id}: ip_position is required")
        else:
            if ip.get("patent_counsel_review_required") is not True:
                failures.append(f"{equation_id}: patent counsel review must remain required")
            if implementation_class == "EXACT_STANDARD_METHOD":
                if ip.get("novelty_claim_allowed") is not False:
                    failures.append(f"{equation_id}: standard method cannot be marked novel alone")
                if ip.get("prior_art_position") != "STANDARD_METHOD_NOT_NOVEL_ALONE":
                    failures.append(f"{equation_id}: standard-method prior-art position is missing")

        if EVIDENCE_ORDER.get(evidence_class, 0) >= 3:
            external = raw.get("external_validation")
            if not isinstance(external, dict) or external.get("receipt_path") not in files:
                failures.append(f"{equation_id}: E3/E4 requires a registered external receipt")
        external = raw.get("external_validation")
        if not isinstance(external, dict) or not external.get("status"):
            failures.append(f"{equation_id}: external_validation status is required")
        elif EVIDENCE_ORDER.get(evidence_class, 0) < 3 and external.get("status") not in {
            "INTERNAL_ONLY",
            "SOURCE_AUTHENTIC_NOT_INDEPENDENTLY_VALIDATED",
            "INDEPENDENT_REPRODUCTION_PENDING",
        }:
            failures.append(f"{equation_id}: invalid pre-E3 external-validation status")

    if failures:
        raise RegistryValidationError("; ".join(failures))
    return {
        "entry_count": len(entries),
        "file_count": len(files),
        "equation_ids": sorted(ids),
    }


def build_chain(entries: list[dict[str, Any]]) -> tuple[list[dict[str, str]], str]:
    previous = "0" * 64
    chain: list[dict[str, str]] = []
    for entry in sorted(entries, key=lambda row: row["equation_id"]):
        entry_hash = canonical_sha256(entry)
        chain_hash = hashlib.sha256(f"{previous}:{entry_hash}".encode("ascii")).hexdigest()
        chain.append(
            {
                "equation_id": entry["equation_id"],
                "entry_sha256": entry_hash,
                "chain_sha256": chain_hash,
            }
        )
        previous = chain_hash
    return chain, previous


def current_git_head(root: Path = ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_payload(registry_path: Path = DEFAULT_REGISTRY, *, root: Path = ROOT) -> dict[str, Any]:
    registry = read_json(registry_path)
    validation = validate_registry(registry, root=root)
    file_hash_audit = build_file_hash_audit(registry, root=root)
    files = registry["files"]
    entries: list[dict[str, Any]] = []
    for raw in registry["entries"]:
        source = raw["source"]
        source_tree = ast.parse(repo_path(source["path"], root).read_text(encoding="utf-8-sig"))
        source_node = find_symbol(source_tree, source["symbol"])
        assert source_node is not None
        entry = dict(raw)
        entry["source"] = {
            **source,
            "line": int(getattr(source_node, "lineno", 0)),
            "file_sha256": files[source["path"]]["sha256"],
        }
        enriched_tests = []
        for test in raw["tests"]:
            tree = ast.parse(repo_path(test["path"], root).read_text(encoding="utf-8-sig"))
            node = find_symbol(tree, test["symbol"])
            assert node is not None
            enriched_tests.append(
                {
                    **test,
                    "line": int(getattr(node, "lineno", 0)),
                    "file_sha256": files[test["path"]]["sha256"],
                }
            )
        entry["tests"] = enriched_tests
        entry["bindings"] = [
            {"path": path, "sha256": files[path]["sha256"], "role": files[path]["role"]}
            for path in raw["bindings"]
        ]
        entries.append(entry)

    implementation_counts = Counter(row["implementation_class"] for row in entries)
    evidence_counts = Counter(row["evidence_class"] for row in entries)
    claim_counts = Counter(row["claim_level"] for row in entries)
    chain, terminal = build_chain(entries)
    payload = {
        "schema": "lumencore_scientific_equation_evidence_map_v1",
        "generated_utc": now_utc(),
        "registry": {
            "path": str(registry_path.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(registry_path),
        },
        "builder": {
            "path": str(Path(__file__).resolve().relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "repository_head_at_generation": current_git_head(root),
        "truth_line": (
            "This map distinguishes exact standard methods, operational definitions, heuristic analogues, "
            "and exploratory heuristics. It is an internal traceability artifact, not patentability, agency "
            "acceptance, independent validation, field validation, or performance certification."
        ),
        "summary": {
            **validation,
            "implementation_class_counts": dict(sorted(implementation_counts.items())),
            "evidence_class_counts": dict(sorted(evidence_counts.items())),
            "claim_level_counts": dict(sorted(claim_counts.items())),
            "independently_reproduced_entry_count": sum(
                EVIDENCE_ORDER[row["evidence_class"]] >= 3 for row in entries
            ),
            "field_or_acceptance_validated_entry_count": sum(
                EVIDENCE_ORDER[row["evidence_class"]] >= 4 for row in entries
            ),
            "patentability_determined": False,
            "external_validation_claim_allowed": False,
            "field_validation_claim_allowed": False,
        },
        "file_hash_audit": file_hash_audit,
        "entries": entries,
        "chain": chain,
        "terminal_chain_sha256": terminal,
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Scientific Equation Evidence Map",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Registry SHA-256: `{payload['registry']['sha256']}`",
        f"Builder SHA-256: `{payload['builder']['sha256']}`",
        f"Terminal chain SHA-256: `{payload['terminal_chain_sha256']}`",
        "",
        "## Truth Line",
        "",
        payload["truth_line"],
        "",
        "## Maturity Wall",
        "",
        f"- Registered entries: `{summary['entry_count']}`",
        f"- Registered files: `{summary['file_count']}`",
        f"- Registry files current: `{str(payload['file_hash_audit']['summary']['all_current']).lower()}`",
        f"- Registry hash drift count: `{payload['file_hash_audit']['summary']['drift_count']}`",
        f"- Independently reproduced entries: `{summary['independently_reproduced_entry_count']}`",
        f"- Field or acceptance validated entries: `{summary['field_or_acceptance_validated_entry_count']}`",
        "- Patentability determined: `false`",
        "- External validation claim allowed: `false`",
        "- Field validation claim allowed: `false`",
        "",
        "## Equation And Algorithm Ledger",
        "",
        "| ID | Name | Class | Evidence | Claim ceiling | Source | Allowed now |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in payload["entries"]:
        source = entry["source"]
        lines.append(
            "| "
            f"`{entry['equation_id']}` | {entry['name']} | `{entry['implementation_class']}` | "
            f"`{entry['evidence_class']}` | `{entry['claim_level']}` | "
            f"`{source['path']}:{source['line']}::{source['symbol']}` | {entry['allowed_claim']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `EXACT_STANDARD_METHOD` means the implementation follows a named standard method; it is not claimed as novel by itself.",
            "- `OPERATIONAL_DEFINITION` means the formula is a transparent project-specific metric, scale, feature, or gate.",
            "- `HEURISTIC_ANALOGUE` means the name is inspiration only; it is not a numerical solution of the governing equation.",
            "- `EXPLORATORY_HEURISTIC` means implemented code exists, but empirical promotion and external validation remain blocked.",
            "- E2 may support a frozen internal or source-authentic implementation claim. It does not imply independent endorsement.",
            "- No entry in this release reaches E3 independent reproduction or E4 field/acceptance validation.",
            "",
            "## Patent Boundary",
            "",
            "Standard equations and algorithms are prior art and are not asserted as novel alone. Any protectable position would require counsel to assess the specific system combination, routing, controls, data contracts, and claimed implementation details against prior art. This map is technical provenance, not a patentability opinion.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the fail-closed scientific equation evidence map.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument(
        "--hash-audit-only",
        action="store_true",
        help="Print a non-mutating registered-file hash audit and fail on drift.",
    )
    args = parser.parse_args()
    if args.hash_audit_only:
        audit = build_file_hash_audit(read_json(args.registry.resolve()))
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["summary"]["all_current"] else 1
    payload = build_payload(args.registry.resolve())
    if not args.check_only:
        write_outputs(payload)
        print(OUT_JSON)
        print(DASHBOARD_JSON)
        print(OUT_MD)
    print(
        json.dumps(
            {
                "entry_count": payload["summary"]["entry_count"],
                "terminal_chain_sha256": payload["terminal_chain_sha256"],
                "independently_reproduced_entry_count": payload["summary"]["independently_reproduced_entry_count"],
                "field_or_acceptance_validated_entry_count": payload["summary"]["field_or_acceptance_validated_entry_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
