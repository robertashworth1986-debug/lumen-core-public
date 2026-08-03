from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "out" / "ops" / "live_domain_service_contract_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "live_domain_service_contract.json"
OUT_MD = ROOT / "docs" / "LIVE_DOMAIN_SERVICE_CONTRACT_2026-07-25.md"

DEFAULT_DOMAIN = "lumen-core.ai"
BOUNDARY = (
    "This receipt proves only the observed public HTTP, content-type, redirect, and bounded JSON contracts at "
    "the recorded time. It does not prove service uptime outside the probe window, independent validation, "
    "model performance, realized savings, award readiness, or live-trading fitness."
)


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha256(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("contract_sha256", None)
    body = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text.rstrip() + "\n", encoding="utf-8")
    temp.replace(path)


def endpoint_specs(domain: str) -> list[dict[str, Any]]:
    public = f"https://{domain}"
    return [
        {
            "id": "public_root",
            "url": f"{public}/",
            "allowed_statuses": [200],
            "content_type_prefix": "text/html",
            "kind": "document",
            "required": True,
        },
        {
            "id": "edge_health",
            "url": f"{public}/nginx-health",
            "allowed_statuses": [200],
            "content_type_prefix": "application/json",
            "kind": "json",
            "expected_json": {"status": "ok", "platform": "nginx"},
            "required": True,
        },
        {
            "id": "gateway_health",
            "url": f"{public}/health",
            "allowed_statuses": [200],
            "content_type_prefix": "application/json",
            "kind": "json",
            "required": True,
        },
        {
            "id": "app_redirect",
            "url": f"https://app.{domain}/",
            "allowed_statuses": [301, 302, 307, 308],
            "content_type_prefix": "",
            "kind": "redirect",
            "expected_location": f"{public}/investor_command_room.html",
            "required": True,
        },
        {
            "id": "app_health",
            "url": f"https://app.{domain}/health",
            "allowed_statuses": [200],
            "content_type_prefix": "application/json",
            "kind": "json",
            "expected_json": {
                "status": "ok",
                "surface": "app",
                "mode": "reviewer_safe_redirect",
                "target": f"{public}/investor_command_room.html",
            },
            "required": True,
        },
        {
            "id": "research_redirect",
            "url": f"https://research.{domain}/",
            "allowed_statuses": [301, 302, 307, 308],
            "content_type_prefix": "",
            "kind": "redirect",
            "expected_location": f"{public}/quant_lab.html",
            "required": True,
        },
        {
            "id": "research_health",
            "url": f"https://research.{domain}/health",
            "allowed_statuses": [200],
            "content_type_prefix": "application/json",
            "kind": "json",
            "expected_json": {
                "status": "ok",
                "surface": "research",
                "mode": "reviewer_safe_redirect",
                "target": f"{public}/quant_lab.html",
            },
            "required": True,
        },
    ]


def probe_endpoint(spec: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    opener = build_opener(NoRedirectHandler())
    request = Request(
        str(spec["url"]),
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.1",
            "User-Agent": "LumenCoreServiceContract/1.0",
        },
    )
    status = 0
    headers: Any = {}
    body = b""
    error = ""
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(response.status)
            headers = response.headers
            body = response.read(262_145)
    except HTTPError as exc:
        status = int(exc.code)
        headers = exc.headers or {}
        try:
            body = exc.read(262_145)
        except OSError:
            body = b""
        error = str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        error = str(exc)

    content_type = str(headers.get("content-type", "") or "").split(";", 1)[0].strip().lower()
    location = str(headers.get("location", "") or "").strip()
    json_body: dict[str, Any] = {}
    json_error = ""
    if spec.get("kind") == "json" and body:
        try:
            decoded = json.loads(body.decode("utf-8"))
            if isinstance(decoded, dict):
                json_body = decoded
            else:
                json_error = "JSON body is not an object"
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            json_error = str(exc)

    return {
        "status": status,
        "content_type": content_type,
        "location": location,
        "body_bytes_observed": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest() if body else "",
        "json_body": json_body,
        "json_error": json_error,
        "error": error,
    }


def evaluate(spec: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "status": int(observation.get("status") or 0) in spec["allowed_statuses"],
        "content_type": (
            not spec.get("content_type_prefix")
            or str(observation.get("content_type") or "").startswith(
                str(spec["content_type_prefix"])
            )
        ),
        "location": (
            not spec.get("expected_location")
            or str(observation.get("location") or "") == str(spec["expected_location"])
        ),
        "json": True,
    }
    expected_json = spec.get("expected_json")
    if isinstance(expected_json, dict):
        actual_json = observation.get("json_body")
        checks["json"] = isinstance(actual_json, dict) and all(
            actual_json.get(key) == value for key, value in expected_json.items()
        )
    elif spec.get("kind") == "json":
        checks["json"] = isinstance(observation.get("json_body"), dict) and not observation.get(
            "json_error"
        )

    passed = all(checks.values())
    failures = [name for name, ok in checks.items() if not ok]
    return {
        "id": spec["id"],
        "url": spec["url"],
        "kind": spec["kind"],
        "required": bool(spec["required"]),
        "expected": {
            "allowed_statuses": spec["allowed_statuses"],
            "content_type_prefix": spec.get("content_type_prefix", ""),
            "location": spec.get("expected_location", ""),
            "json_subset": spec.get("expected_json", {}),
        },
        "observed": observation,
        "checks": checks,
        "passed": passed,
        "failures": failures,
    }


def skipped_observation() -> dict[str, Any]:
    return {
        "status": 0,
        "content_type": "",
        "location": "",
        "body_bytes_observed": 0,
        "body_sha256": "",
        "json_body": {},
        "json_error": "",
        "error": "live check skipped",
    }


def build_payload(
    *,
    domain: str | None = None,
    check_live: bool = True,
    timeout: int = 10,
) -> dict[str, Any]:
    selected_domain = (domain or os.environ.get("LUMA_PUBLIC_DOMAIN") or DEFAULT_DOMAIN).strip()
    rows: list[dict[str, Any]] = []
    for spec in endpoint_specs(selected_domain):
        observation = probe_endpoint(spec, timeout) if check_live else skipped_observation()
        rows.append(evaluate(spec, observation))

    required = [row for row in rows if row["required"]]
    passed = [row for row in required if row["passed"]]
    failed = [row for row in required if not row["passed"]]
    contract_pass = check_live and len(passed) == len(required)

    failed_ids = [row["id"] for row in failed]
    if "gateway_health" in failed_ids:
        next_action = (
            "Authenticate to the VPS, inspect luma-gateway service logs and free space, then restore the "
            "gateway before any API-health claim or full deployment."
        )
    elif any(item in failed_ids for item in ("app_health", "research_health")):
        next_action = (
            "Deploy the reviewed edge configuration so app and research health paths return their bounded "
            "JSON redirect-surface contracts, then rerun this read-only probe."
        )
    elif failed:
        next_action = "Resolve the listed public contract failures and rerun this read-only probe."
    else:
        next_action = (
            "Keep this receipt current after deployments. Treat it as reachability evidence only, never as "
            "performance or independent-validation evidence."
        )

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "live_domain_service_contract_v1",
        "purpose": "Fail-closed public service and redirect contract verification.",
        "boundary": BOUNDARY,
        "domain": selected_domain,
        "live_check_performed": check_live,
        "summary": {
            "required_endpoint_count": len(required),
            "passed_endpoint_count": len(passed),
            "failed_endpoint_count": len(failed),
            "contract_pass": contract_pass,
            "status": (
                "LIVE_DOMAIN_SERVICE_CONTRACT_PASS"
                if contract_pass
                else "LIVE_DOMAIN_SERVICE_CONTRACT_BLOCKED"
            ),
            "failed_endpoint_ids": failed_ids,
            "safe_next_action": next_action,
            "performance_claim_allowed": False,
            "independent_validation_claim_allowed": False,
        },
        "endpoints": rows,
    }
    payload["contract_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# LumenCore Live-Domain Service Contract",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Status: `{summary['status']}`",
        f"- Required endpoints passed: `{summary['passed_endpoint_count']}/{summary['required_endpoint_count']}`",
        f"- Contract SHA-256: `{payload['contract_sha256']}`",
        "",
        "## Endpoint Matrix",
        "",
        "| Endpoint | Result | HTTP | Content type | Redirect |",
        "|---|---:|---:|---|---|",
    ]
    for row in payload["endpoints"]:
        observed = row["observed"]
        lines.append(
            f"| `{row['id']}` | `{'PASS' if row['passed'] else 'BLOCK'}` | "
            f"`{observed['status']}` | `{observed['content_type'] or '-'}` | "
            f"`{observed['location'] or '-'}` |"
        )
    lines.extend(
        [
            "",
            "## Safest Next Action",
            "",
            str(summary["safe_next_action"]),
            "",
            "## Boundary",
            "",
            str(payload["boundary"]),
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the public live-domain service contract receipt.")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--skip-live-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(
        domain=args.domain,
        check_live=not args.skip_live_check,
        timeout=max(1, args.timeout),
    )
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
