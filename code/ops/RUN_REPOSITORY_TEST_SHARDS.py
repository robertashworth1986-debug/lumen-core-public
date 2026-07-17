from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "tests"
DEFAULT_FAST_SHARD_COUNT = 4
DEFAULT_TIMEOUT_SECONDS = 600
ISOLATED_TEST_PATHS = {
    "tests/test_locked_source_baseline_replay_sweep.py",
}
CLAIM_BOUNDARY = (
    "A passing shard receipt proves only that the listed repository tests passed "
    "for the recorded source state and runtime. It does not establish external "
    "validation, agency approval, field performance, realized savings, patent "
    "validity, production readiness, or universal model superiority."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def discover_test_paths(test_dir: Path = TEST_DIR) -> list[str]:
    return sorted(relative_path(path) for path in test_dir.glob("test_*.py"))


def build_shards(
    test_paths: Sequence[str],
    *,
    fast_shard_count: int = DEFAULT_FAST_SHARD_COUNT,
    isolated_paths: set[str] | None = None,
) -> list[dict[str, Any]]:
    if fast_shard_count < 1:
        raise ValueError("fast_shard_count must be at least 1")

    normalized = sorted(
        dict.fromkeys(str(path).replace("\\", "/") for path in test_paths)
    )
    if len(normalized) != len(test_paths):
        raise ValueError("test_paths must be unique")

    isolated = isolated_paths if isolated_paths is not None else ISOLATED_TEST_PATHS
    isolated_present = [path for path in normalized if path in isolated]
    fast_paths = [path for path in normalized if path not in isolated]
    buckets: list[list[str]] = [[] for _ in range(fast_shard_count)]
    for index, path in enumerate(fast_paths):
        buckets[index % fast_shard_count].append(path)

    shards: list[dict[str, Any]] = []
    for files in buckets:
        if files:
            shards.append(
                {
                    "kind": "balanced_fast",
                    "files": files,
                    "file_count": len(files),
                    "shard_sha256": canonical_sha256(files),
                }
            )
    for path in isolated_present:
        shards.append(
            {
                "kind": "isolated_full_universe",
                "files": [path],
                "file_count": 1,
                "shard_sha256": canonical_sha256([path]),
            }
        )

    for index, shard in enumerate(shards, start=1):
        shard["shard_number"] = index
    return shards


def build_plan(fast_shard_count: int = DEFAULT_FAST_SHARD_COUNT) -> dict[str, Any]:
    test_paths = discover_test_paths()
    shards = build_shards(test_paths, fast_shard_count=fast_shard_count)
    flattened = [path for shard in shards for path in shard["files"]]
    if sorted(flattened) != test_paths or len(flattened) != len(test_paths):
        raise RuntimeError("shard plan does not cover every test file exactly once")

    plan_core = {
        "schema": "lumencore.repository_test_shard_plan.v1",
        "test_file_count": len(test_paths),
        "shard_count": len(shards),
        "fast_shard_count": fast_shard_count,
        "isolated_test_paths": sorted(ISOLATED_TEST_PATHS.intersection(test_paths)),
        "shards": shards,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return {**plan_core, "plan_sha256": canonical_sha256(plan_core)}


def pytest_command(shard: dict[str, Any]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        *shard["files"],
        "-q",
        "--tb=short",
        "--durations=10",
    ]


def run_shard(shard: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    started_utc = now_utc()
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            pytest_command(shard),
            cwd=ROOT,
            check=False,
            timeout=timeout_seconds,
        )
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = 124
    elapsed_seconds = round(time.monotonic() - started, 3)
    return {
        "shard_number": shard["shard_number"],
        "kind": shard["kind"],
        "file_count": shard["file_count"],
        "shard_sha256": shard["shard_sha256"],
        "started_utc": started_utc,
        "finished_utc": now_utc(),
        "elapsed_seconds": elapsed_seconds,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "passed": exit_code == 0,
    }


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--list",
        action="store_true",
        help="Print the deterministic plan without running tests.",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="Run every shard sequentially.",
    )
    mode.add_argument("--shard", type=int, help="Run one 1-based shard number.")
    parser.add_argument("--fast-shards", type=int, default=DEFAULT_FAST_SHARD_COUNT)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    plan = build_plan(args.fast_shards)
    if args.list:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    if args.shard is not None:
        if args.shard < 1 or args.shard > plan["shard_count"]:
            parser.error(f"--shard must be between 1 and {plan['shard_count']}")
        selected = [plan["shards"][args.shard - 1]]
    else:
        selected = plan["shards"]

    results = [run_shard(shard, args.timeout_seconds) for shard in selected]
    receipt_core = {
        "schema": "lumencore.repository_test_shard_receipt.v1",
        "generated_utc": now_utc(),
        "plan_sha256": plan["plan_sha256"],
        "selected_shards": [row["shard_number"] for row in results],
        "all_passed": all(row["passed"] for row in results),
        "results": results,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt = {**receipt_core, "receipt_sha256": canonical_sha256(receipt_core)}
    if args.receipt:
        write_receipt(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
