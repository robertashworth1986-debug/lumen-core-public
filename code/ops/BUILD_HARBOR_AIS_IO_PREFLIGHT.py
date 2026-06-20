from __future__ import annotations

import argparse
import hashlib
import json
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
OUT_JSON = OUT_OPS / "harbor_ais_io_preflight_latest.json"
OUT_MD = GRANT_DIR / "NV063_AIS_IO_PREFLIGHT_2026-06-20.md"


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
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_worker_result(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    path = Path(str(spec.get("path", "")))
    expected_bytes = spec.get("expected_bytes")
    expected_sha256 = str(spec.get("expected_sha256", "") or "")
    sample_bytes = max(1, int(spec.get("sample_bytes", 4096)))
    full_hash = bool(spec.get("full_hash", False))
    result: dict[str, Any] = {
        "label": spec.get("label", ""),
        "path": str(path),
        "expected_bytes": expected_bytes,
        "expected_sha256": expected_sha256,
        "full_hash_requested": full_hash,
        "ok": False,
        "status": "unknown",
    }
    try:
        if not path.exists():
            result["status"] = "missing"
            return result
        stat = path.stat()
        result["exists"] = True
        result["actual_bytes"] = stat.st_size
        result["size_matches"] = expected_bytes is None or int(expected_bytes) == stat.st_size
        with path.open("rb") as handle:
            sample = handle.read(sample_bytes)
        result["sample_bytes_read"] = len(sample)
        result["sample_sha256"] = hashlib.sha256(sample).hexdigest()
        result["sample_read_ok"] = len(sample) > 0
        if full_hash:
            result["actual_sha256"] = _hash_file(path)
            result["sha256_matches"] = not expected_sha256 or result["actual_sha256"] == expected_sha256
        else:
            result["sha256_matches"] = None
        result["ok"] = bool(result["size_matches"] and result["sample_read_ok"])
        if full_hash:
            result["ok"] = bool(result["ok"] and result["sha256_matches"])
        result["status"] = "ok" if result["ok"] else "mismatch"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def probe_with_timeout(
    spec: dict[str, Any],
    *,
    timeout_seconds: float,
    use_subprocess: bool = True,
) -> dict[str, Any]:
    if not use_subprocess:
        return _probe_worker_result(spec)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--probe-worker-json",
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
            "path": spec.get("path", ""),
            "expected_bytes": spec.get("expected_bytes"),
            "expected_sha256": spec.get("expected_sha256", ""),
            "full_hash_requested": bool(spec.get("full_hash", False)),
            "ok": False,
            "status": "timeout",
            "timeout_seconds": timeout_seconds,
        }
    if completed.returncode != 0:
        return {
            "label": spec.get("label", ""),
            "path": spec.get("path", ""),
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
            "path": spec.get("path", ""),
            "ok": False,
            "status": "worker_bad_json",
            "error": f"{type(exc).__name__}: {exc}",
            "stdout": completed.stdout.strip()[:500],
            "stderr": completed.stderr.strip(),
        }
    return payload if isinstance(payload, dict) else {"ok": False, "status": "worker_bad_payload"}


def split_specs(split: dict[str, Any], *, include_raw: bool, full_hash: bool, sample_bytes: int) -> list[dict[str, Any]]:
    specs = []
    for label in ("development", "validation"):
        item = split.get("splits", {}).get(label, {})
        specs.append(
            {
                "label": label,
                "path": item.get("path", ""),
                "expected_bytes": item.get("bytes"),
                "expected_sha256": item.get("sha256", ""),
                "sample_bytes": sample_bytes,
                "full_hash": full_hash,
            }
        )
    if include_raw:
        raw = split.get("raw_source", {})
        specs.append(
            {
                "label": "raw_source",
                "path": raw.get("path", ""),
                "expected_bytes": raw.get("bytes"),
                "expected_sha256": raw.get("sha256", ""),
                "sample_bytes": sample_bytes,
                "full_hash": False,
            }
        )
    return specs


def build_preflight(
    split_json: Path = SPLIT_JSON,
    *,
    timeout_seconds: float = 5.0,
    sample_bytes: int = 4096,
    full_hash: bool = False,
    include_raw: bool = False,
    use_subprocess: bool = True,
    write_outputs: bool = True,
) -> dict[str, Any]:
    split = read_json(split_json)
    specs = split_specs(split, include_raw=include_raw, full_hash=full_hash, sample_bytes=sample_bytes)
    probes = [
        probe_with_timeout(spec, timeout_seconds=timeout_seconds, use_subprocess=use_subprocess)
        for spec in specs
    ]
    required = [row for row in probes if row.get("label") in {"development", "validation"}]
    all_required_ok = bool(required) and all(bool(row.get("ok")) for row in required)
    any_timeout = any(row.get("status") == "timeout" for row in probes)
    posture = "PUBLIC_AIS_SPLIT_IO_READY" if all_required_ok else "PUBLIC_AIS_SPLIT_IO_BLOCKED"
    payload = {
        "generated_utc": now_utc(),
        "schema": "harbor_ais_io_preflight_v1",
        "posture": posture,
        "source_split_manifest": rel(split_json),
        "timeout_seconds": timeout_seconds,
        "sample_bytes": sample_bytes,
        "full_hash": full_hash,
        "include_raw": include_raw,
        "selected_region": split.get("selected_region", {}),
        "probes": probes,
        "summary": {
            "required_files": len(required),
            "required_ok": sum(1 for row in required if row.get("ok")),
            "all_required_ok": all_required_ok,
            "any_timeout": any_timeout,
        },
        "next_gate": (
            "Use full-hash recheck, stronger baselines, and labeled or adjudicated validation "
            "before claiming precision, false-positive rate, multi-source fusion, ADS-B/radar "
            "validation, or field performance."
        ),
        "claim_boundary": (
            "This preflight only proves that the frozen public AIS split files are reachable and "
            "sample-readable within the configured timeout. Unless full_hash is true, it does not "
            "rehash the complete files. It does not establish HarborSentinel detection performance, "
            "multi-source fusion, ADS-B or radar validation, Navy/SSDS integration, field performance, "
            "or operational suitability."
        ),
    }
    if write_outputs:
        write_json(OUT_JSON, payload)
        write_text(OUT_MD, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HarborSentinel AIS Split I/O Preflight",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        f"Posture: `{payload['posture']}`",
        "",
        "## Summary",
        "",
        f"- Required split files OK: {payload['summary']['required_ok']}/{payload['summary']['required_files']}",
        f"- Any timeout: {payload['summary']['any_timeout']}",
        f"- Timeout seconds: {payload['timeout_seconds']}",
        f"- Sample bytes: {payload['sample_bytes']}",
        f"- Full hash requested: {payload['full_hash']}",
        "",
        "## Probes",
        "",
    ]
    for row in payload["probes"]:
        lines.extend(
            [
                f"### {row.get('label')}",
                "",
                f"- status: `{row.get('status')}`",
                f"- ok: {row.get('ok')}",
                f"- path: `{row.get('path')}`",
                f"- expected bytes: {row.get('expected_bytes')}",
                f"- actual bytes: {row.get('actual_bytes', 'n/a')}",
                f"- size matches: {row.get('size_matches', 'n/a')}",
                f"- sample bytes read: {row.get('sample_bytes_read', 'n/a')}",
                f"- elapsed seconds: {row.get('elapsed_seconds', 'n/a')}",
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
    parser = argparse.ArgumentParser(description="Preflight frozen HarborSentinel AIS split file I/O.")
    parser.add_argument("--split-json", default=str(SPLIT_JSON))
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--sample-bytes", type=int, default=4096)
    parser.add_argument("--full-hash", action="store_true")
    parser.add_argument("--include-raw", action="store_true")
    parser.add_argument("--probe-worker-json", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.probe_worker_json:
        print(json.dumps(_probe_worker_result(json.loads(args.probe_worker_json)), separators=(",", ":")))
        return 0
    payload = build_preflight(
        Path(args.split_json),
        timeout_seconds=float(args.timeout_seconds),
        sample_bytes=max(1, int(args.sample_bytes)),
        full_hash=bool(args.full_hash),
        include_raw=bool(args.include_raw),
    )
    print(
        json.dumps(
            {
                "posture": payload["posture"],
                "required_ok": payload["summary"]["required_ok"],
                "required_files": payload["summary"]["required_files"],
                "any_timeout": payload["summary"]["any_timeout"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
