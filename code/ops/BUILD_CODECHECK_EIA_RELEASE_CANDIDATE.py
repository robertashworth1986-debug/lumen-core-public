from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "codecheck_eia_release_candidate_v1.json"

PRIVATE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[/\\](?![/\\])", re.I),
    re.compile(
        r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}",
        re.I,
    ),
)
TEXT_SUFFIXES = {
    "",
    ".cff",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
ROOT_KEY_PATTERN = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?:\s|$)")


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def safe_repo_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and ":" not in value


def portable_file_bytes(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        ".gitignore",
        "LICENSE",
        "README.md",
    }:
        text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return text.encode("utf-8"), "utf8_lf"
    return raw, "binary"


def artifact_row(path: Path, relative_path: str) -> dict[str, Any]:
    content, hash_mode = portable_file_bytes(path)
    return {
        "path": relative_path,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "hash_mode": hash_mode,
    }


def scalar_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        try:
            return str(ast.literal_eval(value))
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def parse_citation(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    root_rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t", "-")):
            continue
        match = ROOT_KEY_PATTERN.match(line)
        if match:
            key = match.group("key")
            root_rows.append((key, line.split(":", 1)[1].strip()))
    keys = [key for key, _ in root_rows]
    fields = {key: scalar_value(value) for key, value in root_rows}
    keywords: list[str] = []
    in_keywords = False
    for line in text.splitlines():
        if line == "keywords:":
            in_keywords = True
            continue
        if in_keywords and line and not line.startswith((" ", "\t")):
            break
        match = re.match(r"^\s{2}-\s+(?P<value>.+?)\s*$", line)
        if in_keywords and match:
            keywords.append(scalar_value(match.group("value")))
    return {
        "utf8_decoded": True,
        "tabs_absent": "\t" not in text,
        "root_keys": keys,
        "root_keys_unique": len(keys) == len(set(keys)),
        "fields": fields,
        "authors_present": bool(
            re.search(r"^authors:\s*$", text, flags=re.MULTILINE)
            and re.search(r"^\s+-\s+family-names:\s+.+$", text, flags=re.MULTILINE)
            and re.search(r"^\s+given-names:\s+.+$", text, flags=re.MULTILINE)
        ),
        "keywords": keywords,
        "sha256": file_sha256(path),
    }


def scan_private_text(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    text = re.sub(
        r"[A-Za-z]:[/\\]+Users[/\\]+Example[/\\]",
        "<SANITIZED_TEST_FIXTURE>/",
        text,
        flags=re.I,
    )
    return [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(text)]


def inspect_release_candidate(
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    config = read_json(config_path)
    citation_control = config["citation"]
    values = config["bundle_paths"]
    path_safety = {value: safe_repo_path(value) for value in values}
    path_presence = {
        value: (ROOT / PurePosixPath(value)).is_file()
        if path_safety[value]
        else False
        for value in values
    }
    existing_rows = [
        artifact_row(ROOT / PurePosixPath(value), value)
        for value in sorted(values)
        if path_presence[value]
    ]
    citation_path = ROOT / citation_control["path"]
    citation = parse_citation(citation_path)
    fields = citation["fields"]
    abstract = fields.get("abstract", "")
    privacy_hits: list[dict[str, str]] = []
    for value in sorted(values):
        path = ROOT / PurePosixPath(value)
        if not path_presence[value]:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            ".gitignore",
            "LICENSE",
            "README.md",
        }:
            continue
        for pattern in scan_private_text(path):
            privacy_hits.append({"path": value, "pattern": pattern})
    publication_state = config["publication_state"]
    checks = {
        "bundle_paths_safe": all(path_safety.values()),
        "bundle_paths_unique": len(values) == len(set(values)),
        "bundle_paths_present": all(path_presence.values()),
        "citation_utf8": citation["utf8_decoded"],
        "citation_tabs_absent": citation["tabs_absent"],
        "citation_root_keys_unique": citation["root_keys_unique"],
        "citation_version_matched": fields.get("cff-version")
        == citation_control["expected_cff_version"],
        "citation_title_matched": fields.get("title")
        == citation_control["expected_title"],
        "citation_type_matched": fields.get("type")
        == citation_control["expected_type"],
        "citation_license_matched": fields.get("license")
        == citation_control["expected_license"],
        "citation_repository_matched": fields.get("repository-code")
        == citation_control["expected_repository_code"],
        "citation_authors_present": citation["authors_present"],
        "citation_abstract_bounded": all(
            token.lower() in abstract.lower()
            for token in citation_control["required_abstract_tokens"]
        ),
        "citation_keywords_present": all(
            keyword in citation["keywords"]
            for keyword in citation_control["required_keywords"]
        ),
        "public_text_privacy_scan_passed": not privacy_hits,
        "publication_state_fail_closed": all(
            value is False or value is None for value in publication_state.values()
        ),
        "external_validation_remains_false": publication_state[
            "external_validation_complete"
        ]
        is False,
    }
    return {
        "schema": "codecheck_eia_release_candidate_definition.v1",
        "protocol_id": config["protocol_id"],
        "release": config["release"],
        "checks": checks,
        "internal_release_candidate_ready": all(checks.values()),
        "publication_ready": False,
        "bundle_input_count": len(existing_rows),
        "bundle_inputs": existing_rows,
        "bundle_input_chain_sha256": canonical_sha256(existing_rows),
        "path_safety": path_safety,
        "path_presence": path_presence,
        "citation": citation,
        "privacy_scan": {
            "passed": not privacy_hits,
            "hit_count": len(privacy_hits),
            "hits": privacy_hits,
        },
        "publication_state": publication_state,
        "official_references": config["official_references"],
        "human_unlock_policy": config["human_unlock_policy"],
        "claim_boundary": config["claim_boundary"],
        "value_boundary": config["value_boundary"],
    }


def git_identity() -> tuple[str, str]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit_time = subprocess.run(
        ["git", "show", "-s", "--format=%cI", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit, commit_time


def validate_source_identity(commit: str, commit_time: str) -> tuple[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source commit must be a lowercase 40-character Git SHA")
    parsed = datetime.fromisoformat(commit_time.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("source commit time must include a timezone")
    normalized = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return commit, normalized


def render_release_notes(definition: dict[str, Any], commit: str, commit_time: str) -> str:
    release = definition["release"]
    return "\n".join(
        [
            f"# {release['title']}",
            "",
            f"Proposed tag: `{release['proposed_tag']}`",
            f"Reviewed source commit: `{commit}`",
            f"Source commit UTC: `{commit_time}`",
            f"Bundle input chain SHA-256: `{definition['bundle_input_chain_sha256']}`",
            "",
            "## Scope",
            "",
            "This candidate packages the bounded preprint, frozen public-data input, exact runner, hash-locked dependency specification, protocols, benchmark implementations, and tests used by the CODECHECK-ready workflow.",
            "",
            "## Claim Boundary",
            "",
            definition["claim_boundary"],
            "",
            "## Publication State",
            "",
            "- GitHub release published: `false`",
            "- Immutable release verified: `false`",
            "- Zenodo DOI issued: `false`",
            "- CODECHECK request opened: `false`",
            "- Independent execution complete: `false`",
            "- Certificate issued: `false`",
            "- External validation complete: `false`",
            "",
            "## HumanUnlock",
            "",
            definition["human_unlock_policy"],
            "",
        ]
    )


def zip_info(name: str, timestamp: tuple[int, int, int, int, int, int]) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def write_bundle(
    path: Path,
    definition: dict[str, Any],
    manifest: dict[str, Any],
    notes: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    root = definition["release"]["archive_root"]
    timestamp = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for row in definition["bundle_inputs"]:
            source = ROOT / PurePosixPath(row["path"])
            archive.writestr(
                zip_info(f"{root}/{row['path']}", timestamp),
                portable_file_bytes(source)[0],
                compresslevel=9,
            )
        archive.writestr(
            zip_info(f"{root}/RELEASE_MANIFEST.json", timestamp),
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            compresslevel=9,
        )
        archive.writestr(
            zip_info(f"{root}/RELEASE_NOTES.md", timestamp),
            notes.encode("utf-8"),
            compresslevel=9,
        )


def verify_bundle(path: Path, definition: dict[str, Any], manifest: dict[str, Any], notes: str) -> dict[str, Any]:
    root = definition["release"]["archive_root"]
    expected_names = [f"{root}/{row['path']}" for row in definition["bundle_inputs"]]
    expected_names.extend([f"{root}/RELEASE_MANIFEST.json", f"{root}/RELEASE_NOTES.md"])
    checks: dict[str, bool] = {}
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        checks["entry_names_exact"] = names == expected_names
        checks["entry_names_unique"] = len(names) == len(set(names))
        checks["entry_timestamps_fixed"] = all(
            row.date_time == (1980, 1, 1, 0, 0, 0) for row in archive.infolist()
        )
        checks["input_hashes_exact"] = all(
            hashlib.sha256(archive.read(f"{root}/{row['path']}")).hexdigest()
            == row["sha256"]
            for row in definition["bundle_inputs"]
        )
        checks["manifest_exact"] = json.loads(
            archive.read(f"{root}/RELEASE_MANIFEST.json")
        ) == manifest
        checks["notes_exact"] = archive.read(f"{root}/RELEASE_NOTES.md").decode(
            "utf-8"
        ) == notes
    return {
        "verified": all(checks.values()),
        "entry_count": len(expected_names),
        "checks": checks,
    }


def build_release_candidate(
    output_dir: Path,
    *,
    source_commit: str | None = None,
    source_commit_time: str | None = None,
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    definition = inspect_release_candidate(config_path)
    if not definition["internal_release_candidate_ready"]:
        failed = [key for key, value in definition["checks"].items() if not value]
        raise RuntimeError(f"release candidate definition failed: {', '.join(failed)}")
    if source_commit is None or source_commit_time is None:
        observed_commit, observed_time = git_identity()
        source_commit = source_commit or observed_commit
        source_commit_time = source_commit_time or observed_time
    source_commit, source_commit_time = validate_source_identity(
        source_commit, source_commit_time
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    release = definition["release"]
    notes = render_release_notes(definition, source_commit, source_commit_time)
    manifest = {
        "schema": "codecheck_eia_release_manifest.v1",
        "protocol_id": definition["protocol_id"],
        "proposed_tag": release["proposed_tag"],
        "source_commit": source_commit,
        "source_commit_utc": source_commit_time,
        "bundle_input_count": definition["bundle_input_count"],
        "bundle_inputs": definition["bundle_inputs"],
        "bundle_input_chain_sha256": definition["bundle_input_chain_sha256"],
        "claim_boundary": definition["claim_boundary"],
        "publication_state": definition["publication_state"],
    }
    bundle_path = output_dir / release["bundle_asset_name"]
    preprint_path = output_dir / release["preprint_asset_name"]
    notes_path = output_dir / release["notes_asset_name"]
    receipt_path = output_dir / release["receipt_asset_name"]
    checksums_path = output_dir / release["checksums_asset_name"]
    write_bundle(bundle_path, definition, manifest, notes)
    shutil.copyfile(
        ROOT
        / "docs"
        / "preprint"
        / "BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf",
        preprint_path,
    )
    write_text(notes_path, notes)
    bundle_verification = verify_bundle(bundle_path, definition, manifest, notes)
    receipt: dict[str, Any] = {
        "schema": "codecheck_eia_release_candidate_receipt.v1",
        "protocol_id": definition["protocol_id"],
        "status": "UNPUBLISHED_RELEASE_CANDIDATE_READY",
        "source_commit": source_commit,
        "source_commit_utc": source_commit_time,
        "proposed_tag": release["proposed_tag"],
        "bundle_input_count": definition["bundle_input_count"],
        "bundle_input_chain_sha256": definition["bundle_input_chain_sha256"],
        "bundle_asset": {
            "name": bundle_path.name,
            "bytes": bundle_path.stat().st_size,
            "sha256": file_sha256(bundle_path),
        },
        "preprint_asset": {
            "name": preprint_path.name,
            "bytes": preprint_path.stat().st_size,
            "sha256": file_sha256(preprint_path),
        },
        "notes_asset": {
            "name": notes_path.name,
            "bytes": notes_path.stat().st_size,
            "sha256": file_sha256(notes_path),
        },
        "bundle_verification": bundle_verification,
        "publication_ready": False,
        "publication_state": definition["publication_state"],
        "external_validation_complete": False,
        "human_unlock_policy": definition["human_unlock_policy"],
        "claim_boundary": definition["claim_boundary"],
        "value_boundary": definition["value_boundary"],
    }
    receipt["receipt_content_sha256"] = canonical_sha256(receipt)
    write_json(receipt_path, receipt)
    checksum_rows = [
        (file_sha256(path), path.name)
        for path in (bundle_path, preprint_path, notes_path, receipt_path)
    ]
    write_text(
        checksums_path,
        "".join(f"{digest}  {name}\n" for digest, name in checksum_rows),
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--source-commit-time")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    definition = inspect_release_candidate(args.config)
    if args.check_only:
        print(
            json.dumps(
                {
                    "status": (
                        "RELEASE_CANDIDATE_DEFINITION_READY"
                        if definition["internal_release_candidate_ready"]
                        else "RELEASE_CANDIDATE_DEFINITION_BLOCKED"
                    ),
                    "checks": definition["checks"],
                    "publication_ready": False,
                    "external_validation_complete": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if definition["internal_release_candidate_ready"] else 1

    output_dir = args.output_dir or ROOT / definition["release"]["output_directory"]
    receipt = build_release_candidate(
        output_dir,
        source_commit=args.source_commit,
        source_commit_time=args.source_commit_time,
        config_path=args.config,
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "output_directory": str(output_dir),
                "bundle_sha256": receipt["bundle_asset"]["sha256"],
                "publication_ready": False,
                "external_validation_complete": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
