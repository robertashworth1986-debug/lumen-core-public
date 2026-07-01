from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
GRANT_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"

SPLIT_JSON = OUT_OPS / "harbor_ais_heldout_splits_latest.json"
DEFAULT_CACHE_ROOT = ROOT / "out" / "private_data" / "harbor_ais_split_cache"
OUT_JSON = OUT_OPS / "harbor_ais_local_split_cache_latest.json"
CACHED_SPLIT_JSON = OUT_OPS / "harbor_ais_cached_split_manifest_latest.json"
OUT_MD = GRANT_DIR / "NV063_AIS_LOCAL_SPLIT_CACHE_2026-06-20.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_specs(split: dict[str, Any], cache_root: Path) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for label in ("development", "validation"):
        item = split.get("splits", {}).get(label, {})
        expected_sha = str(item.get("sha256", "") or "")
        cache_name = f"{label}_{expected_sha[:12] or 'unknown'}.csv"
        specs.append(
            {
                "label": label,
                "source_path": str(item.get("path", "")),
                "cache_path": str(cache_root / cache_name),
                "expected_bytes": item.get("bytes"),
                "expected_sha256": expected_sha,
            }
        )
    return specs


def _copy_worker_result(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    source = Path(str(spec.get("source_path", "")))
    cache = Path(str(spec.get("cache_path", "")))
    expected_bytes = spec.get("expected_bytes")
    expected_sha = str(spec.get("expected_sha256", "") or "")
    result: dict[str, Any] = {
        "label": spec.get("label", ""),
        "source_path": str(source),
        "cache_path": str(cache),
        "cache_rel_path": rel(cache),
        "expected_bytes": expected_bytes,
        "expected_sha256": expected_sha,
        "ok": False,
        "status": "unknown",
    }
    try:
        if cache.exists():
            actual_sha = sha256_file(cache)
            result["actual_bytes"] = cache.stat().st_size
            result["actual_sha256"] = actual_sha
            result["size_matches"] = expected_bytes is None or int(expected_bytes) == cache.stat().st_size
            result["sha256_matches"] = not expected_sha or actual_sha == expected_sha
            if result["size_matches"] and result["sha256_matches"]:
                result["ok"] = True
                result["status"] = "cache_hit"
                return result
        if not source.exists():
            result["status"] = "source_missing"
            return result
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(cache.name + ".part")
        with source.open("rb") as src, tmp.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        actual_sha = sha256_file(tmp)
        tmp.replace(cache)
        result["actual_bytes"] = cache.stat().st_size
        result["actual_sha256"] = actual_sha
        result["size_matches"] = expected_bytes is None or int(expected_bytes) == cache.stat().st_size
        result["sha256_matches"] = not expected_sha or actual_sha == expected_sha
        result["ok"] = bool(result["size_matches"] and result["sha256_matches"])
        result["status"] = "cached" if result["ok"] else "cached_mismatch"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def copy_with_timeout(
    spec: dict[str, Any],
    *,
    timeout_seconds: float,
    use_subprocess: bool,
) -> dict[str, Any]:
    if not use_subprocess:
        return _copy_worker_result(spec)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--copy-worker-json",
        json.dumps(spec, separators=(",", ":")),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(0.1, float(timeout_seconds)),
        )
    except subprocess.TimeoutExpired:
        return {
            "label": spec.get("label", ""),
            "source_path": spec.get("source_path", ""),
            "cache_path": spec.get("cache_path", ""),
            "cache_rel_path": rel(Path(str(spec.get("cache_path", "")))),
            "expected_bytes": spec.get("expected_bytes"),
            "expected_sha256": spec.get("expected_sha256", ""),
            "ok": False,
            "status": "timeout",
            "timeout_seconds": timeout_seconds,
        }
    if completed.returncode != 0:
        return {
            "label": spec.get("label", ""),
            "source_path": spec.get("source_path", ""),
            "cache_path": spec.get("cache_path", ""),
            "cache_rel_path": rel(Path(str(spec.get("cache_path", "")))),
            "ok": False,
            "status": "worker_failed",
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip(),
            "stdout": completed.stdout.strip()[:500],
        }
    try:
        payload = json.loads(completed.stdout)
    except Exception as exc:
        return {
            "label": spec.get("label", ""),
            "source_path": spec.get("source_path", ""),
            "cache_path": spec.get("cache_path", ""),
            "cache_rel_path": rel(Path(str(spec.get("cache_path", "")))),
            "ok": False,
            "status": "worker_bad_json",
            "error": f"{type(exc).__name__}: {exc}",
            "stdout": completed.stdout.strip()[:500],
        }
    return payload if isinstance(payload, dict) else {"ok": False, "status": "worker_bad_payload"}


def cached_split_manifest(split: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    cached = copy.deepcopy(split)
    cached["source_split_manifest"] = rel(SPLIT_JSON)
    cached["cache_manifest"] = rel(OUT_JSON)
    cached["cache_boundary"] = (
        "Split paths in this manifest point to private local cached CSV copies whose SHA-256 values "
        "match the frozen split manifest. Do not commit the cached CSVs."
    )
    for entry in entries:
        label = str(entry.get("label", ""))
        if not entry.get("ok") or label not in cached.get("splits", {}):
            continue
        cached["splits"][label]["path"] = str(entry.get("cache_path", ""))
        cached["splits"][label]["cache_rel_path"] = str(entry.get("cache_rel_path", ""))
    return cached


def build_cache(
    split_json: Path = SPLIT_JSON,
    *,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    timeout_seconds: float = 10.0,
    use_subprocess: bool = True,
    write_outputs: bool = True,
) -> dict[str, Any]:
    split = read_json(split_json)
    specs = split_specs(split, cache_root)
    entries = [
        copy_with_timeout(spec, timeout_seconds=timeout_seconds, use_subprocess=use_subprocess)
        for spec in specs
    ]
    required_ok = sum(1 for row in entries if row.get("ok"))
    all_required_ok = required_ok == len(entries) and bool(entries)
    cached_manifest_path = CACHED_SPLIT_JSON if all_required_ok else None
    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_local_split_cache_v1",
        "posture": "PUBLIC_AIS_LOCAL_SPLIT_CACHE_READY" if all_required_ok else "PUBLIC_AIS_LOCAL_SPLIT_CACHE_BLOCKED",
        "source_split_manifest": rel(split_json),
        "cache_root": rel(cache_root),
        "timeout_seconds": timeout_seconds,
        "entries": entries,
        "summary": {
            "required_files": len(entries),
            "required_ok": required_ok,
            "all_required_ok": all_required_ok,
            "any_timeout": any(row.get("status") == "timeout" for row in entries),
        },
        "cached_split_manifest": rel(cached_manifest_path) if cached_manifest_path else "",
        "next_gate": (
            "Run AIS I/O preflight and the HarborSentinel controlled-injection benchmark against "
            "the cached split manifest only after the cache is ready."
        ),
        "claim_boundary": (
            "This cache proves only that local private copies of the frozen public AIS split files "
            "match the recorded SHA-256 hashes. It does not establish HarborSentinel detection "
            "performance, multi-source fusion, ADS-B or radar validation, Navy/SSDS integration, "
            "field performance, or operational suitability."
        ),
    }
    if write_outputs:
        write_json(OUT_JSON, payload)
        if all_required_ok:
            write_json(CACHED_SPLIT_JSON, cached_split_manifest(split, entries))
        write_text(OUT_MD, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HarborSentinel AIS Local Split Cache",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        f"Posture: `{payload['posture']}`",
        "",
        "## Summary",
        "",
        f"- Required split files OK: {payload['summary']['required_ok']}/{payload['summary']['required_files']}",
        f"- Any timeout: {payload['summary']['any_timeout']}",
        f"- Cached split manifest: `{payload.get('cached_split_manifest') or 'not ready'}`",
        "",
        "## Entries",
        "",
    ]
    for entry in payload["entries"]:
        lines.extend(
            [
                f"### {entry.get('label')}",
                "",
                f"- status: `{entry.get('status')}`",
                f"- ok: {entry.get('ok')}",
                f"- cache: `{entry.get('cache_rel_path')}`",
                f"- expected bytes: {entry.get('expected_bytes')}",
                f"- actual bytes: {entry.get('actual_bytes', 'n/a')}",
                f"- SHA-256 matches: {entry.get('sha256_matches', 'n/a')}",
                f"- elapsed seconds: {entry.get('elapsed_seconds', 'n/a')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Next Gate",
            "",
            payload["next_gate"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache frozen HarborSentinel AIS split CSVs locally.")
    parser.add_argument("--split-json", default=str(SPLIT_JSON))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE_ROOT))
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--no-subprocess", action="store_true")
    parser.add_argument("--copy-worker-json", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.copy_worker_json:
        print(json.dumps(_copy_worker_result(json.loads(args.copy_worker_json)), separators=(",", ":")))
        return 0
    payload = build_cache(
        Path(args.split_json),
        cache_root=Path(args.cache_root),
        timeout_seconds=float(args.timeout_seconds),
        use_subprocess=not bool(args.no_subprocess),
    )
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "required_ok": payload["summary"]["required_ok"],
                "required_files": payload["summary"]["required_files"],
                "any_timeout": payload["summary"]["any_timeout"],
                "cache_json": rel(OUT_JSON),
                "cached_split_manifest": payload.get("cached_split_manifest", ""),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
