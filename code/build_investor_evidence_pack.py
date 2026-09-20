"""Package explicitly selected local evidence bytes; never infer investment performance.

This replaces the legacy runtime-root collector. A manifest proves the captured
bytes in this archive, not their truth, source authenticity, or scientific merit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from datetime import datetime, timezone
import zipfile

MAX_FILES = 128
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_SELECTION_BYTES = 64 * 1024
MANIFEST_NAME = "artifact_hash_manifest.json"
LEDGER_NAME = "artifact_hash_ledger.csv"
ARCHIVE_NAME = "institutional_evidence_pack.zip"
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON value")


def _plain_chain(path: Path, *, directory: bool = False) -> Path:
    """Reject observed links/reparse points; no concurrent-writer exclusion claim."""
    path = Path(os.path.abspath(path))
    for item in reversed([path, *path.parents]):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked/reparse paths are not eligible")
        if item != path or directory:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("Expected a plain directory")
        elif not stat.S_ISREG(info.st_mode):
            raise ValueError("Expected a regular file")
    return path


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def capture_file(path: Path, limit: int) -> tuple[bytes, dict]:
    path = _plain_chain(path)
    before = path.stat()
    if before.st_size > limit:
        raise ValueError("Source exceeds byte limit")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode) or _identity(before) != _identity(opened):
            raise ValueError("Source identity changed before capture")
        raw = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
    _plain_chain(path)
    final = path.stat()
    if (len(raw) > limit or len(raw) != opened.st_size or
            _identity(opened) != _identity(after) or _identity(after) != _identity(final)):
        raise ValueError("Source changed during capture or exceeded its limit")
    return raw, {"bytes": len(raw), "sha256": digest(raw),
                 "observed_modified_utc": datetime.fromtimestamp(
                     opened.st_mtime, timezone.utc).isoformat()}


def validate_names(names) -> list[str]:
    if not isinstance(names, list) or not 1 <= len(names) <= MAX_FILES:
        raise ValueError(f"Selection must contain 1..{MAX_FILES} relative paths")
    seen = set()
    result = []
    for name in names:
        if not isinstance(name, str) or not name or len(name) > 240:
            raise ValueError("Invalid relative artifact path")
        parts = name.split("/")
        if (len(parts) > 16 or any(not part or part in {".", ".."} for part in parts)
                or PurePosixPath(name).is_absolute() or "\\" in name
                or any(ord(ch) < 32 or ch in ':*?"<>|' for ch in name)
                or any(part[0] in " =+-@" or part.endswith((".", " "))
                       or part.split(".")[0].upper() in RESERVED
                       for part in parts)):
            raise ValueError("Artifact path is not portable and traversal-free")
        folded = name.casefold()
        if folded in seen:
            raise ValueError("Duplicate/case-colliding artifact path")
        seen.add(folded)
        result.append(name)
    return sorted(result)


def load_selection(path: Path) -> tuple[list[str], dict]:
    raw, receipt = capture_file(path, MAX_SELECTION_BYTES)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_pairs,
                           parse_constant=_reject_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Selection is not bounded UTF-8 JSON") from exc
    return validate_names(value), receipt


def _json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def summarize_trade_log(path=None) -> dict:
    """Compatibility hold: no file reads and no unreconciled account metrics."""
    return {"trades": None, "wins": None, "losses": None, "win_rate": None,
            "realized_pnl": None, "broker_reconciled": False,
            "investment_ready": False, "status": "NOT_EVALUATED"}


def build_pack(*, source_root: Path, artifact_paths: Path, output_dir: Path) -> dict:
    source_root = _plain_chain(source_root, directory=True)
    names, selection_receipt = load_selection(artifact_paths)
    output_dir = Path(os.path.abspath(output_dir))
    _plain_chain(output_dir.parent, directory=True)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("Output directory must be new")
    captured = {}
    artifacts = []
    total = 0
    for name in names:
        raw, record = capture_file(source_root.joinpath(*name.split("/")),
                                   min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total))
        total += len(raw)
        captured["sources/" + name] = raw
        artifacts.append({"path": name, "archive_path": "sources/" + name, **record})
    manifest = {
        "schema": "lumencore.explicit_evidence_pack.v2", "pack_version": "2.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(artifacts), "total_source_bytes": total,
        "selection_source": selection_receipt, "artifacts": artifacts,
        "performance_summary": summarize_trade_log(),
        "evidence_class": "CAPTURED_SOURCE_BYTES_ONLY",
        "external_validation": False, "live_execution_authority": False,
        "source_authenticity_verified": False, "content_claims_verified": False,
        "snapshot_boundary": "Per-file bounded capture; not an atomic multi-file snapshot. "
            "Observed metadata changes and links are rejected; concurrent writers are not excluded.",
        "claim_boundary": "Hashes bind the packaged bytes. Filenames, timestamps and contained "
            "claims do not establish freshness, financial performance, readiness, valuation, "
            "independent validation or permission to distribute the source contents.",
        "self_hash_rule": "SHA-256 of UTF-8 JSON without manifest_sha256, keys sorted, "
            "indent=2, ensure_ascii=true, allow_nan=false, one trailing LF.",
    }
    manifest["manifest_sha256"] = digest(_json_bytes(manifest))
    manifest_raw = _json_bytes(manifest)
    ledger = io.StringIO(newline="")
    writer = csv.writer(ledger, lineterminator="\n")
    writer.writerow(["path", "archive_path", "bytes", "sha256", "observed_modified_utc"])
    for item in artifacts:
        writer.writerow([item[key] for key in
                         ("path", "archive_path", "bytes", "sha256", "observed_modified_utc")])
    ledger_raw = ledger.getvalue().encode("utf-8")
    # Hashes, ledger, and archive use the same captured buffers; never re-open sources.
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in [(MANIFEST_NAME, manifest_raw), (LEDGER_NAME, ledger_raw),
                          *sorted(captured.items())]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    _plain_chain(output_dir.parent, directory=True)
    output_dir.mkdir(exist_ok=False)
    # I/O failure may leave a partial new directory; existing output is never reused.
    for name, raw in [(MANIFEST_NAME, manifest_raw), (LEDGER_NAME, ledger_raw),
                      (ARCHIVE_NAME, archive_buffer.getvalue())]:
        with (output_dir / name).open("xb") as handle:
            handle.write(raw)
    return {"artifact_count": len(artifacts), "total_source_bytes": total,
            "archive_sha256": digest(archive_buffer.getvalue()),
            "manifest_sha256": digest(manifest_raw),
            "evidence_class": manifest["evidence_class"],
            "performance_summary": manifest["performance_summary"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--artifacts-json", required=True, type=Path,
                        help="UTF-8 JSON list of 1..128 explicit relative paths")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="New directory under an existing plain parent")
    args = parser.parse_args(argv)
    try:
        receipt = build_pack(source_root=args.source_root, artifact_paths=args.artifacts_json,
                             output_dir=args.output_dir)
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        print(f"Evidence pack HOLD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
