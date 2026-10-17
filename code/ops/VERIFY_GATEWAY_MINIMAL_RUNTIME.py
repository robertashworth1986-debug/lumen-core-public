#!/usr/bin/env python3
"""Verify the separate, non-operating minimal gateway serving profile.

This lock covers HTTP startup and liveness, not optional operator components,
research dependencies, providers, broker access, or deployment authorization.
--smoke starts and stops only the minimal profile on an ephemeral loopback port.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "requirements-gateway-minimal-ubuntu-py311.lock"
DIRECT = {"fastapi": "0.138.2", "uvicorn": "0.54.0"}
PIN = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9._-]*)==([a-zA-Z0-9][a-zA-Z0-9.+-]*)\s*(?:\\)?$")
HASH = re.compile(r"^\s+--hash=sha256:[0-9a-f]{64}\s*(?:\\)?$")


def lock_versions(text: str) -> dict[str, str]:
    versions = {}
    hash_counts = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = PIN.fullmatch(line)
        if match:
            current, version = match.groups()
            current = current.replace("_", "-").lower()
            if current in versions:
                raise ValueError("duplicate distribution in minimal serving lock")
            versions[current] = version
            hash_counts[current] = 0
        elif current is not None and HASH.fullmatch(line):
            hash_counts[current] += 1
        else:
            raise ValueError("minimal serving lock requires pinned packages and SHA-256 hashes only")
    if not versions or any(count < 1 for count in hash_counts.values()):
        raise ValueError("minimal serving lock lacks distribution hashes")
    if any(versions.get(name) != version for name, version in DIRECT.items()):
        raise ValueError("minimal serving direct dependency pins mismatch")
    return versions


def verify(*, check_lock_only: bool = False) -> dict:
    raw = LOCK.read_bytes()
    versions = lock_versions(raw.decode("utf-8"))
    if not check_lock_only:
        if sys.version_info[:3] != (3, 11, 9) or sys.platform != "linux" or platform.machine() != "x86_64":
            raise ValueError("minimal serving runtime requires Linux x86-64 and CPython 3.11.9")
        for name, expected in versions.items():
            if importlib.metadata.version(name) != expected:
                raise ValueError(f"minimal serving installed version mismatch: {name}")
    return {
        "schema": "lumencore_gateway_minimal_runtime_receipt_v1",
        "valid": True,
        "scope": "minimal-reviewer-http-serving",
        "lock_sha256": hashlib.sha256(raw).hexdigest(),
        "distribution_count": len(versions),
        "runtime_versions_checked": not check_lock_only,
        "python": platform.python_version(),
        "optional_operator_components": "HOLD",
        "production_authorization": "not_established",
        "external_api_calls": 0,
    }


async def smoke() -> dict:
    if "luma_experience_gateway_legacy" in sys.modules:
        raise ValueError("minimal serving smoke requires a fresh process without legacy gateway imports")
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="luma-minimal-review-") as temporary:
        os.environ["LUMA_GATEWAY_SERVING_PROFILE"] = "minimal"
        os.environ["LUMA_STACK_ROOT"] = temporary
        os.environ["LUMA_DASHBOARD_DIR"] = str(Path(temporary) / "dashboard")
        token = "synthetic-minimal-profile-token-0000"
        os.environ["LUMA_OPERATOR_API_TOKEN"] = token
        os.environ["LUMA_OPERATOR_API_TOKENS"] = ""
        sys.path.insert(0, str(ROOT / "code"))
        import luma_experience_gateway as gateway

        if "luma_experience_gateway_legacy" in sys.modules:
            raise ValueError("minimal serving profile imported operator feature graph")
        server = uvicorn.Server(uvicorn.Config(
            gateway.app, host="127.0.0.1", port=0, lifespan="on", ws="none", log_level="error",
        ))
        serving = asyncio.create_task(server.serve())
        opener = build_opener(ProxyHandler({}))

        def fetch(port: int, path: str, authenticated: bool = False):
            headers = {"Authorization": f"Bearer {token}"} if authenticated else {}
            request = Request(f"http://127.0.0.1:{port}{path}", headers=headers)
            try:
                with opener.open(request, timeout=2) as response:
                    return response.status, json.loads(response.read())
            except HTTPError as error:
                return error.code, json.loads(error.read())

        try:
            async def started():
                while not server.started:
                    if serving.done():
                        await serving
                        raise ValueError("minimal HTTP server stopped before startup")
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(started(), timeout=10)
            port = server.servers[0].sockets[0].getsockname()[1]
            health = await asyncio.to_thread(fetch, port, "/health")
            details = await asyncio.to_thread(fetch, port, "/api/operator/health", True)
            held = await asyncio.to_thread(fetch, port, "/api/scanner/smart/run", True)
            if health[0] != 200 or health[1].get("public_surface") != "minimal":
                raise ValueError("minimal liveness HTTP contract failed")
            if details[0] != 200 or details[1].get("operational_readiness") != "HOLD":
                raise ValueError("minimal profile did not retain component HOLD")
            if held[0] != 503 or details[1].get("background_workers") != "not_started":
                raise ValueError("minimal profile exposed operating components")
        finally:
            server.should_exit = True
            await asyncio.wait_for(serving, timeout=10)
        if any(Path(temporary).iterdir()):
            raise ValueError("minimal serving startup wrote runtime state")
    return {"loopback_http_start_stop": "passed", "legacy_graph_imported": False,
            "worker_tasks_started": False, "provider_or_broker_calls": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-lock-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.smoke and args.check_lock_only:
        parser.error("--smoke requires the matched installed runtime")
    try:
        receipt = verify(check_lock_only=args.check_lock_only)
        if args.smoke:
            receipt.update(asyncio.run(smoke()))
    except (OSError, ValueError, importlib.metadata.PackageNotFoundError, TimeoutError) as error:
        print(json.dumps({"valid": False, "error": str(error)}), file=sys.stderr)
        return 1
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
