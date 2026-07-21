from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "codecheck_eia_mainline_integration_v1.json"
MANIFEST_FILE = re.compile(r'^\s*-\s+file:\s*["\'](?P<path>[^"\']+)["\']\s*$')
SOURCE_LINE = re.compile(r'^source:\s*["\'](?P<value>[^"\']+)["\']\s*$', re.MULTILINE)
REFERENCE_LINE = re.compile(
    r'^\s{2}reference:\s*["\'](?P<value>[^"\']+)["\']\s*$',
    re.MULTILINE,
)
CONFLICT_MARKERS = re.compile(r"^(?:<<<<<<<|=======|>>>>>>>)", re.MULTILINE)
PRIVATE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[/\\](?![/\\])", re.I),
    re.compile(
        r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}",
        re.I,
    ),
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def safe_repo_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and ":" not in value


def portable_bytes(path: Path, hash_mode: str) -> bytes:
    raw = path.read_bytes()
    if hash_mode == "binary":
        return raw
    if hash_mode != "utf8_lf":
        raise ValueError(f"unsupported hash mode: {hash_mode}")
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_frozen_file(row: dict[str, str], root: Path = ROOT) -> dict[str, Any]:
    relative = row["path"]
    safe = safe_repo_path(relative)
    path = root / PurePosixPath(relative) if safe else root / "__unsafe_path__"
    present = safe and path.is_file()
    observed = None
    error = None
    if present:
        try:
            observed = git_blob_sha1(portable_bytes(path, row["hash_mode"]))
        except (UnicodeDecodeError, ValueError) as exc:
            error = str(exc)
    return {
        "path": relative,
        "hash_mode": row["hash_mode"],
        "safe": safe,
        "present": present,
        "expected_blob_sha1": row["blob_sha1"],
        "observed_blob_sha1": observed,
        "matched": present and observed == row["blob_sha1"],
        "error": error,
    }


def parse_codecheck_manifest(text: str) -> list[str]:
    outputs: list[str] = []
    in_manifest = False
    for line in text.splitlines():
        if line == "manifest:":
            in_manifest = True
            continue
        if in_manifest and line and not line.startswith((" ", "\t")):
            break
        if in_manifest:
            match = MANIFEST_FILE.match(line)
            if match:
                outputs.append(match.group("path"))
    return outputs


def scan_public_text(paths: list[str], root: Path = ROOT) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for relative in paths:
        if not safe_repo_path(relative):
            hits.append({"path": relative, "kind": "unsafe_path"})
            continue
        path = root / PurePosixPath(relative)
        if not path.is_file():
            hits.append({"path": relative, "kind": "missing"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            hits.append({"path": relative, "kind": "non_utf8"})
            continue
        if CONFLICT_MARKERS.search(text):
            hits.append({"path": relative, "kind": "conflict_marker"})
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                hits.append({"path": relative, "kind": "private_pattern"})
    return hits


def inspect_first_party_receipts(root: Path = ROOT) -> dict[str, Any]:
    receipt_root = root / "evidence" / "reproducibility" / "codecheck_reviewer_container_1c0eb517_20260721"
    container = read_json(receipt_root / "container_rebuild_receipt.json")
    runtime = read_json(receipt_root / "runtime_receipt.json")
    replay = read_json(receipt_root / "reviewer_reproducibility_receipt.json")
    replay_summary = replay.get("summary", {})
    checks = {
        "container_passed": container.get("passed") is True,
        "container_operator_controlled": container.get("operator_controlled") is True,
        "container_independence_false": container.get("independent_execution_complete") is False,
        "container_external_validation_false": container.get("external_validation_complete") is False,
        "runtime_passed": runtime.get("passed") is True,
        "runtime_operator_controlled": runtime.get("operator_controlled") is True,
        "runtime_independence_false": runtime.get("independent_execution_complete") is False,
        "runtime_external_validation_false": runtime.get("external_validation_complete") is False,
        "replay_status_bounded": replay.get("status") == "BOUNDED_REPRODUCIBILITY_PASS",
        "replay_suites_exact": replay_summary.get("suite_count") == 3
        and replay_summary.get("suite_pass_count") == 3,
        "replay_assertions_exact": replay_summary.get("assertion_count") == 31
        and replay_summary.get("assertion_pass_count") == 31,
        "replay_external_validation_false": replay_summary.get("external_validation_complete") is False,
    }
    return {"checks": checks, "passed": all(checks.values())}


def inspect_integration(config_path: Path = DEFAULT_CONFIG, root: Path = ROOT) -> dict[str, Any]:
    config = read_json(config_path)
    frozen = config["frozen_target"]
    frozen_rows = [inspect_frozen_file(row, root) for row in config["exact_frozen_files"]]
    frozen_paths = [row["path"] for row in config["exact_frozen_files"]]
    required_paths = config["required_integration_paths"]
    drift_paths = config["allowed_integration_drift_paths"]
    required_presence = {
        value: safe_repo_path(value) and (root / PurePosixPath(value)).is_file()
        for value in required_paths
    }

    codecheck_path = root / "codecheck.yml"
    codecheck_text = codecheck_path.read_text(encoding="utf-8") if codecheck_path.is_file() else ""
    manifest_outputs = parse_codecheck_manifest(codecheck_text)
    expected_outputs = config["manifest_outputs"]
    source = SOURCE_LINE.search(codecheck_text)
    reference = REFERENCE_LINE.search(codecheck_text)
    privacy_hits = scan_public_text(config["public_text_scan_paths"], root)
    receipts = inspect_first_party_receipts(root)

    preprint_path = root / PurePosixPath(frozen["preprint_path"])
    preprint_sha = file_sha256(preprint_path) if preprint_path.is_file() else None
    protocol = read_json(root / "config" / "reviewer_reproducibility_protocol_v1.json")
    protocol_input = protocol.get("frozen_inputs", [{}])[0]
    claim_state = config["claim_state"]

    checks = {
        "frozen_paths_safe": all(row["safe"] for row in frozen_rows),
        "frozen_paths_unique": len(frozen_paths) == len(set(frozen_paths)),
        "frozen_files_present": all(row["present"] for row in frozen_rows),
        "frozen_files_byte_identical": all(row["matched"] for row in frozen_rows),
        "required_paths_safe": all(safe_repo_path(value) for value in required_paths),
        "required_paths_unique": len(required_paths) == len(set(required_paths)),
        "required_paths_present": all(required_presence.values()),
        "drift_paths_safe": all(safe_repo_path(value) for value in drift_paths),
        "drift_paths_unique": len(drift_paths) == len(set(drift_paths)),
        "drift_disjoint_from_frozen_core": not set(drift_paths).intersection(frozen_paths),
        "manifest_outputs_exact": manifest_outputs == expected_outputs,
        "manifest_outputs_unique": len(manifest_outputs) == len(set(manifest_outputs)),
        "manifest_outputs_safe": all(safe_repo_path(value) for value in manifest_outputs),
        "manifest_count_exact": len(manifest_outputs) == frozen["declared_output_count"],
        "codecheck_source_bound": bool(source) and source.group("value") == frozen["source_url"],
        "codecheck_preprint_bound": bool(reference)
        and reference.group("value") == frozen["preprint_url"],
        "preprint_sha256_exact": preprint_sha == frozen["preprint_sha256"],
        "protocol_suite_count_exact": len(protocol.get("suites", [])) == frozen["suite_count"],
        "protocol_panel_row_count_exact": protocol_input.get("row_count")
        == frozen["frozen_panel_row_count"],
        "claim_state_fail_closed": bool(claim_state)
        and all(value is False for value in claim_state.values()),
        "public_text_scan_passed": not privacy_hits,
        "first_party_receipts_bounded": receipts["passed"],
    }
    return {
        "schema": "codecheck_eia_mainline_integration_receipt.v1",
        "protocol_id": config["protocol_id"],
        "status": "MAINLINE_INTEGRATION_READY" if all(checks.values()) else "MAINLINE_INTEGRATION_BLOCKED",
        "checks": checks,
        "passed": all(checks.values()),
        "frozen_target": frozen,
        "frozen_file_count": len(frozen_rows),
        "frozen_files": frozen_rows,
        "required_integration_presence": required_presence,
        "allowed_integration_drift_paths": drift_paths,
        "manifest_outputs": manifest_outputs,
        "preprint_observed_sha256": preprint_sha,
        "first_party_receipts": receipts,
        "privacy_scan": {"passed": not privacy_hits, "hits": privacy_hits},
        "claim_state": claim_state,
        "human_unlock_policy": config["human_unlock_policy"],
        "claim_boundary": config["claim_boundary"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    receipt = inspect_integration(args.config.resolve())
    if args.output:
        write_json(args.output.resolve(), receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "passed": receipt["passed"],
                "frozen_target_commit": receipt["frozen_target"]["commit"],
                "frozen_file_count": receipt["frozen_file_count"],
                "declared_output_count": len(receipt["manifest_outputs"]),
                "external_validation_complete": receipt["claim_state"]["external_validation_complete"],
                "failed_checks": [key for key, value in receipt["checks"].items() if not value],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
