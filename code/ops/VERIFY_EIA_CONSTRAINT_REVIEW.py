"""Verify both reviewed EIA replay packets against repository-owned identities.

This supersedes the frozen runners' manifest-membership-only hash checks without
changing their source bytes or historical manifests. Trust starts with this
reviewed verifier and its pins, obtained through a trusted repository revision.
It establishes first-party artifact integrity, not external validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]
MAX_MANIFEST_BYTES = 1_048_576
MAX_ARTIFACT_BYTES = 268_435_456
COMMON_INPUTS = frozenset({
    "code/eia_grid_residual_moe_benchmark.py",
    "code/ops/REPLAY_EIA_CONSTRAINT_REVIEW.py",
    "config/eia_constraint_replay_review_v1.json",
    "config/eia_grid_residual_moe_protocol_v1.json",
    "config/reviewer_protocol_provenance_v1.json",
    "evidence/reproducibility/eia_grid_validation_panel_20260713.json.gz",
})
PACKETS = {
    "original": {
        "directory": "evidence/reproducibility/eia_constraint_review_20260921",
        "schema": "eia_constraint_replay_manifest.v1",
        "manifest_sha256": "d89c5503a5191531b66bedd22d5cda6d316a7fa12e611cff1979eb926b47f92f",
        "inputs": COMMON_INPUTS,
        "outputs": frozenset({"benchmark.json", "constraint_summary.json", "environment.json", "predictions.csv.gz"}),
    },
    "later": {
        "directory": "evidence/reproducibility/eia_constraint_later_window_20260921",
        "schema": "eia_later_window_manifest.v1",
        "manifest_sha256": "8d5804c79883236a1ca22bc87428ecb7088e788f47c145d1a2d3a6ca70784295",
        "inputs": COMMON_INPUTS | frozenset({
            "code/ops/REPLAY_EIA_LATER_WINDOW.py",
            "config/eia_later_window_review_v1.json",
            "evidence/reproducibility/eia_daily_20260713_20260908_selected.json.gz",
        }),
        "outputs": frozenset({"benchmark.json", "predictions.csv.gz"}),
    },
}


def reject_duplicate_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite JSON value: {value}")


def contained_file(base: Path, relative: str) -> Path:
    """Require one canonical relative path, without symlink indirection."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("invalid manifest path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(p in {"", ".", ".."} for p in relative.split("/")):
        raise ValueError("manifest path leaves its root or is not canonical")
    root = base.resolve()
    path = root.joinpath(*pure.parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError("manifest path leaves its root")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("symlinks are not permitted in frozen evidence paths")
    if not path.is_file():
        raise ValueError(f"required file missing: {relative}")
    return path


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_packet(packet: str, repo_root: Path = ROOT) -> dict:
    if packet not in PACKETS:
        raise ValueError("unsupported replay packet")
    contract = PACKETS[packet]
    root = repo_root.resolve()
    output = root / contract["directory"]
    manifest_path = contained_file(root, contract["directory"] + "/manifest.json")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds size limit")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw, object_pairs_hook=reject_duplicate_keys, parse_constant=reject_nonfinite)
    if not isinstance(manifest, dict) or manifest.get("schema") != contract["schema"]:
        raise ValueError("unexpected manifest schema")
    for category in ("inputs", "outputs"):
        entries = manifest.get(category)
        if not isinstance(entries, dict) or not entries or set(entries) != contract[category]:
            raise ValueError(f"{category} must contain exactly the reviewed required files")
        for relative, record in entries.items():
            if not isinstance(record, dict) or set(record) != {"sha256", "bytes"}:
                raise ValueError(f"invalid identity record: {relative}")
            if not isinstance(record["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
                raise ValueError(f"invalid SHA-256: {relative}")
            if type(record["bytes"]) is not int or not 0 <= record["bytes"] <= MAX_ARTIFACT_BYTES:
                raise ValueError(f"invalid byte count: {relative}")
            # Validate all paths before hashing any artifact contents.
            contained_file(root if category == "inputs" else output, relative)
    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    if manifest_sha256 != contract["manifest_sha256"]:
        raise ValueError("manifest differs from reviewed repository pin")
    for category, base in (("inputs", root), ("outputs", output)):
        for relative, record in manifest[category].items():
            path = contained_file(base, relative)
            if path.stat().st_size != record["bytes"] or file_digest(path) != record["sha256"]:
                raise ValueError(f"hash or size mismatch: {relative}")
    return {
        "verified": True, "packet": packet, "schema": contract["schema"],
        "input_count": len(manifest["inputs"]), "output_count": len(manifest["outputs"]),
        "manifest_sha256": manifest_sha256,
        "boundary": "Reviewed first-party artifact identities only; no external validation, scientific correctness, promotion or savings claim.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", choices=["all", *PACKETS], default="all")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    packets = list(PACKETS) if args.packet == "all" else [args.packet]
    print(json.dumps([verify_packet(name, args.repo_root) for name in packets], indent=2))
