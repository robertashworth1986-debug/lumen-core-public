from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
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
    required_paths.add(SCRIPT_PATH)
    required_paths.add(TEST_PATH)
    path_checks = {
        repo_path(path): path.is_file() for path in sorted(required_paths)
    }

    readme_text = (ROOT / bundle["readme_path"]).read_text(encoding="utf-8")
    license_text = (ROOT / bundle["license_path"]).read_text(encoding="utf-8")
    method_text = (ROOT / bundle["method_note_path"]).read_text(encoding="utf-8")
    public_text_privacy_hits = scan_private(
        {
            "codecheck": codecheck_path.read_text(encoding="utf-8"),
            "readme": readme_text,
            "license": license_text,
            "method_note": method_text,
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
        "archived_computational_identity_still_matches": source_reconciliation[
            "computational_identity_exact_match"
        ],
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
        "public_text_privacy_scan_passed": not public_text_privacy_hits,
    }
    internal_gate_passed = all(checks.values())

    portable_inputs = [artifact_row(path) for path in portable_paths]
    external_gates = config["external_gates"]
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
            "current_commit_clean_runner_complete": False,
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
        f"- Current commit clean-runner complete: `{str(summary['current_commit_clean_runner_complete']).lower()}`",
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
            "The archive demonstrates an older operator-controlled clean-runner execution. Its computational identity files still match, while the README and packaging controls have moved forward. It is a feasibility reference, not a current-commit receipt or independent evidence. The codechecker must execute the reviewed current commit.",
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
            "1. Robert reviews the method note, manifest, public files, and bounded ask.",
            "2. Freeze the exact reviewed commit or release identifier.",
            "3. Obtain action-time HumanUnlock for one CODECHECK request and recheck the outreach lock before sending.",
            "4. Let the assigned codechecker execute the workflow and populate external metadata; the operator does not fill those fields.",
            "5. Cite a certificate only after CODECHECK issues a public report identifier.",
            "6. Pursue a separate statistical-method review and the preregistered prospective EIA gates; neither can be substituted by executable-computation checking.",
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
