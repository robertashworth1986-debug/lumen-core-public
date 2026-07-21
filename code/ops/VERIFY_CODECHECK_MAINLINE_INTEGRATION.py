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
CHECKBOX_LINE = re.compile(
    r"^- \[(?P<mark>[ xX])\] (?P<text>.+?)\s*$",
    re.MULTILINE,
)
NUMBERED_LINE = re.compile(r"^\d+\.\s+", re.MULTILINE)
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


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def parse_checkbox_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        match = CHECKBOX_LINE.match(line)
        if match:
            if current is not None:
                current["text"] = normalize_whitespace(current["text"])
                items.append(current)
            current = {
                "checked": bool(match.group("mark").strip()),
                "text": match.group("text"),
            }
            continue
        if current is not None and line.startswith(("  ", "\t")) and line.strip():
            current["text"] += " " + line.strip()
            continue
        if current is not None:
            current["text"] = normalize_whitespace(current["text"])
            items.append(current)
            current = None
    if current is not None:
        current["text"] = normalize_whitespace(current["text"])
        items.append(current)
    return items


def inspect_author_review(
    config: dict[str, Any],
    codecheck_text: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    control = config["author_review_control"]
    path_values = {
        key: control[key]
        for key in ("checklist_path", "request_draft_path", "license_path", "citation_path")
    }
    path_safety = {key: safe_repo_path(value) for key, value in path_values.items()}
    path_presence = {
        key: path_safety[key] and (root / PurePosixPath(value)).is_file()
        for key, value in path_values.items()
    }

    def read_control_text(key: str) -> str:
        if not path_presence[key]:
            return ""
        return (root / PurePosixPath(path_values[key])).read_text(encoding="utf-8")

    checklist_text = read_control_text("checklist_path")
    request_text = read_control_text("request_draft_path")
    license_text = read_control_text("license_path")
    citation_text = read_control_text("citation_path")
    checklist_normalized = normalize_whitespace(checklist_text)
    request_normalized = normalize_whitespace(request_text)
    license_normalized = normalize_whitespace(license_text)
    checklist_items = parse_checkbox_items(checklist_text)
    completed_items = [row for row in checklist_items if row["checked"]]

    missing_checklist_snippets = [
        value
        for value in control["required_checklist_snippets"]
        if normalize_whitespace(value) not in checklist_normalized
    ]
    missing_request_snippets = [
        value
        for value in control["required_request_snippets"]
        if normalize_whitespace(value) not in request_normalized
    ]
    missing_license_snippets = [
        value
        for value in control["required_license_snippets"]
        if normalize_whitespace(value) not in license_normalized
    ]
    author = control["expected_author_name"]
    family_name, given_name = author.split(" ", 1)[1], author.split(" ", 1)[0]
    citation_author_exact = bool(
        re.search(
            rf'^\s+-\s+family-names:\s+"{re.escape(family_name)}"\s*$',
            citation_text,
            flags=re.MULTILINE,
        )
        and re.search(
            rf'^\s+given-names:\s+"{re.escape(given_name)}"\s*$',
            citation_text,
            flags=re.MULTILINE,
        )
    )
    codecheck_author_exact = bool(
        re.search(
            rf'^\s+-\s+name:\s+"{re.escape(author)}"\s*$',
            codecheck_text,
            flags=re.MULTILINE,
        )
    )
    checklist_status_exact = (
        f"Status: `{control['expected_checklist_status']}`" in checklist_text
    )
    request_status_exact = f"Status: `{control['expected_request_status']}`" in request_text
    action_gate_count = len(NUMBERED_LINE.findall(checklist_text))
    frozen = config["frozen_target"]
    frozen_fact_checks = {
        "source_commit_bound": frozen["commit"] in checklist_text
        and frozen["commit"] in request_text,
        "preprint_hash_bound": frozen["preprint_sha256"] in checklist_text,
        "declared_output_count_bound": (
            f"Declared outputs: `{frozen['declared_output_count']}`" in checklist_text
        ),
        "suite_assertion_counts_bound": (
            f"`{frozen['suite_count']}` suites, `{frozen['assertion_count']}` assertions"
            in checklist_text
        ),
        "panel_row_count_bound": (
            f"`{frozen['frozen_panel_row_count']:,}` rows" in checklist_text
        ),
    }
    checks = {
        "control_paths_safe": all(path_safety.values()),
        "control_paths_present": all(path_presence.values()),
        "checklist_status_exact": checklist_status_exact,
        "request_status_exact": request_status_exact,
        "human_decision_count_exact": len(checklist_items)
        == control["expected_human_decision_count"],
        "checklist_has_no_completed_assertions": not completed_items,
        "action_time_gate_count_exact": action_gate_count
        == control["expected_action_time_gate_count"],
        "checklist_language_complete": not missing_checklist_snippets,
        "request_language_complete": not missing_request_snippets,
        "license_language_complete": not missing_license_snippets,
        "codecheck_author_exact": codecheck_author_exact,
        "citation_author_exact": citation_author_exact,
        "frozen_facts_bound": all(frozen_fact_checks.values()),
        "identifier_left_for_action_time": control["identifier_placeholder"] in request_text,
    }
    passed = all(checks.values())
    return {
        "schema": "codecheck_author_review_preflight.v1",
        "status": "READY_FOR_AUTHOR_REVIEW_NO_SEND" if passed else "AUTHOR_REVIEW_PREFLIGHT_BLOCKED",
        "passed": passed,
        "checks": checks,
        "machine_check_count": len(checks),
        "machine_check_pass_count": sum(bool(value) for value in checks.values()),
        "human_decision_count": len(checklist_items),
        "human_completed_item_count": len(completed_items),
        "human_author_review_complete": False,
        "human_decisions": checklist_items,
        "action_time_gate_count": action_gate_count,
        "action_time_gates_complete": False,
        "frozen_fact_checks": frozen_fact_checks,
        "missing_checklist_snippets": missing_checklist_snippets,
        "missing_request_snippets": missing_request_snippets,
        "missing_license_snippets": missing_license_snippets,
        "author_review_unlock_phrase": control["author_review_unlock_phrase"],
        "production_request_authorized": False,
    }


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
    author_review = inspect_author_review(config, codecheck_text, root)

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
        "author_review_preflight_ready": author_review["passed"],
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
        "author_review_preflight": author_review,
        "privacy_scan": {"passed": not privacy_hits, "hits": privacy_hits},
        "claim_state": claim_state,
        "human_unlock_policy": config["human_unlock_policy"],
        "claim_boundary": config["claim_boundary"],
    }


def render_author_review_card(receipt: dict[str, Any]) -> str:
    review = receipt["author_review_preflight"]
    target = receipt["frozen_target"]
    claim_state = receipt["claim_state"]
    machine_rows = "\n".join(
        f"- [{'x' if passed else ' '}] `{name}`"
        for name, passed in review["checks"].items()
    )
    human_rows = "\n".join(
        f"- [ ] {row['text']}" for row in review["human_decisions"]
    )
    claim_rows = "\n".join(
        f"- `{name}`: `{str(value).lower()}`" for name, value in claim_state.items()
    )
    return (
        "# CODECHECK Author Review Decision Card\n\n"
        f"Status: `{review['status']}`\n\n"
        "This card proves packet consistency only. It does not prove that Robert "
        "has read or accepted the materials, and it does not authorize a CODECHECK "
        "request or any external contact.\n\n"
        "## Frozen Target\n\n"
        f"- Source commit: `{target['commit']}`\n"
        f"- Preprint SHA-256: `{target['preprint_sha256']}`\n"
        f"- Declared outputs: `{target['declared_output_count']}`\n"
        f"- Suites and assertions: `{target['suite_count']}` / `{target['assertion_count']}`\n"
        f"- Frozen panel rows: `{target['frozen_panel_row_count']:,}`\n\n"
        "## Machine Preflight\n\n"
        f"Passed: `{review['machine_check_pass_count']}/{review['machine_check_count']}`\n\n"
        f"{machine_rows}\n\n"
        "## Human Acknowledgments\n\n"
        f"Completed by machine: `0/{review['human_decision_count']}`\n\n"
        f"{human_rows}\n\n"
        "## Claims That Remain False\n\n"
        f"{claim_rows}\n\n"
        "## Author Review Unlock\n\n"
        "After personally completing the acknowledgments above, Robert may provide "
        "this exact phrase:\n\n"
        f"`{review['author_review_unlock_phrase']}`\n\n"
        "That phrase records author review only. A fresh duplicate check, a collision-free "
        "Launch Pad identifier, and separate action-time HumanUnlock are still required "
        "before exactly one production CODECHECK request.\n"
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--author-card", type=Path)
    args = parser.parse_args()

    receipt = inspect_integration(args.config.resolve())
    if args.output:
        write_json(args.output.resolve(), receipt)
    if args.author_card:
        write_text(args.author_card.resolve(), render_author_review_card(receipt))
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "passed": receipt["passed"],
                "frozen_target_commit": receipt["frozen_target"]["commit"],
                "frozen_file_count": receipt["frozen_file_count"],
                "declared_output_count": len(receipt["manifest_outputs"]),
                "external_validation_complete": receipt["claim_state"]["external_validation_complete"],
                "author_review_status": receipt["author_review_preflight"]["status"],
                "human_author_review_complete": receipt["author_review_preflight"][
                    "human_author_review_complete"
                ],
                "failed_checks": [key for key, value in receipt["checks"].items() if not value],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
