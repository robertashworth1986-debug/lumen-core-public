#!/usr/bin/env python3
"""Read-only public reachability and legacy-feed diagnostics.

Never publish fetched payloads or send operator credentials. A minimal public
status response is liveness, not evidence of the legacy data products.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ORIGIN = "https://lumen-core.ai"
MAX_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 10
HEALTH_MAX_AGE_SECONDS = 300
FEEDS = ("live_status", "federal_brief", "evidence_summary", "executor_heartbeat")
PUBLIC_FIELDS = {
    "status": "ok", "service": "luma-experience-gateway",
    "access_boundary": "operator_api_v1", "public_surface": "minimal",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def freshness(value: Any, now: datetime) -> tuple[str, float | None]:
    if not isinstance(value, str):
        return "unknown", None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return "unknown", None
        age = (now - stamp).total_seconds()
    except (ValueError, OverflowError):
        return "unknown", None
    if age < 0:
        return "future", age
    return ("fresh" if age <= HEALTH_MAX_AGE_SECONDS else "stale"), age


def fetch(path: str, *, now: datetime | None = None, opener=None) -> tuple[dict, Any]:
    """Return metadata plus transient JSON; callers must not retain the payload."""
    if path not in ("/", "/health", "/api/public/status", *(f"/api/{n}.json" for n in FEEDS)):
        raise ValueError("path outside fixed monitoring contract")
    current = now or utc_now()
    url = ORIGIN + path + "?metrics_probe=" + current.strftime("%Y%m%dT%H%M%S%fZ")
    receipt = {
        "url": ORIGIN + path, "observed_utc": iso(current), "http_status": 0,
        "transport": "unavailable", "content_type": None, "body_bytes": 0,
        "body_sha256": None, "json_object": False,
    }
    request = Request(url, headers={"Cache-Control": "no-cache", "Accept": "application/json" if path != "/" else "text/html", "User-Agent": "LumenCore-Public-Metrics/2"})
    client = opener or build_opener(NoRedirect())
    try:
        try:
            response = client.open(request, timeout=TIMEOUT_SECONDS)
        except HTTPError as exc:
            response = exc
        with response:
            receipt["http_status"] = response.code
            # Redirects are refused. Never collect from another host or route.
            if urlsplit(response.geturl()).netloc != urlsplit(ORIGIN).netloc:
                receipt["transport"] = "unexpected_origin"
                return receipt, None
            raw_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            receipt["content_type"] = raw_type if re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", raw_type) else None
            body = response.read(MAX_BYTES + 1)
        receipt["body_bytes"] = len(body)
        if len(body) > MAX_BYTES:
            receipt["transport"] = "oversized"
            return receipt, None
        receipt["body_sha256"] = hashlib.sha256(body).hexdigest()
        receipt["transport"] = "response"
        payload = None
        if receipt["content_type"] == "application/json":
            try:
                payload = json.loads(body)
            except (ValueError, UnicodeError):
                pass
        receipt["json_object"] = isinstance(payload, dict)
        return receipt, payload
    except (URLError, TimeoutError, OSError, ValueError, HTTPException) as exc:
        # Error strings may contain proxy credentials or infrastructure detail.
        receipt["error_type"] = type(exc).__name__
        return receipt, None


def assess_public(path: str, receipt: dict, payload: Any, now: datetime) -> dict:
    result = dict(receipt)
    required = set(PUBLIC_FIELDS) | ({"generated_utc"} if path == "/health" else set())
    valid = (
        receipt["transport"] == "response" and receipt["http_status"] == 200
        and isinstance(payload, dict) and set(payload) == required
        and all(payload.get(key) == value for key, value in PUBLIC_FIELDS.items())
    )
    result["contract_valid"] = valid
    result["freshness"] = "not_provided_by_contract"
    if path == "/health":
        status, age = freshness(payload.get("generated_utc") if valid else None, now)
        result["freshness"] = status
        result["age_seconds"] = age
        valid = valid and status == "fresh"
    result["ok"] = valid
    return result


def assess_feed(receipt: dict, payload: Any) -> dict:
    result = dict(receipt)
    status = receipt["http_status"]
    if receipt["transport"] != "response":
        disposition = receipt["transport"]
    elif status == 401:
        disposition = "authentication_required"
    elif status == 403:
        disposition = "forbidden"
    elif status == 503 and payload == {"detail": "operator API access unavailable"}:
        disposition = "operator_access_unconfigured"
    elif status == 404:
        disposition = "route_not_found"
    elif 300 <= status < 400:
        disposition = "redirect_refused"
    elif status != 200:
        disposition = "http_error"
    elif isinstance(payload, dict):
        disposition = "unverified_object"
    else:
        disposition = "invalid_feed_response"
    result.update({
        "disposition": disposition, "access_boundary": "operator_api_v1",
        "public_contract": "not_approved_or_mapped", "data_available": False,
        "freshness": "unknown", "source_timestamp": None,
    })
    return result


def capture(*, fetcher=fetch, now: datetime | None = None, source_commit: str = "unknown") -> dict:
    current = now or utc_now()
    site, _ = fetcher("/", now=now)
    public = {}
    for path in ("/health", "/api/public/status"):
        receipt, payload = fetcher(path, now=now)
        public[path] = assess_public(path, receipt, payload, now or utc_now())
    feeds = {}
    for name in FEEDS:
        receipt, payload = fetcher(f"/api/{name}.json", now=now)
        feeds[name] = assess_feed(receipt, payload)
    reachable = site["transport"] == "response" and site["http_status"] == 200
    gateway_ok = all(value["ok"] for value in public.values())
    return {
        "schema": "lumencore_public_metrics.v2", "snapshot_utc": iso(current),
        "source_commit": source_commit, "site_status": str(site["http_status"]).zfill(3),
        "site_reachability": "reachable" if reachable else "unavailable",
        "site": site, "public_gateway_state": "operational" if gateway_ok else "degraded",
        "public_gateway": public, "legacy_feeds": feeds,
        "available_objects": sum(value["data_available"] for value in feeds.values()),
        "legacy_feed_state": "unverified" if any(value["disposition"] == "unverified_object" for value in feeds.values()) else "unavailable",
        "legacy_feed_freshness": "unknown", "state": "degraded" if reachable else "outage",
        "claim_boundary": "Public reachability is not structured-feed availability, freshness, application recovery, sustained availability, or production authorization.",
    }


def summary(receipt: dict) -> str:
    lines = [f"## Live metrics verdict: {receipt['state']}",
             f"- Site HTTP status: `{receipt['site_status']}` (transport only)",
             f"- Minimal public gateway: `{receipt['public_gateway_state']}`",
             f"- Validated legacy feeds available: `{receipt['available_objects']}/4`",
             f"- Legacy data state: `{receipt['legacy_feed_state']}`; freshness: `{receipt['legacy_feed_freshness']}`",
             f"- Snapshot UTC: `{receipt['snapshot_utc']}`",
             "- The four legacy paths are outside the approved minimal public API; no operator authentication was attempted.",
             "", "| Legacy feed | HTTP | Disposition | Freshness |", "|---|---|---|---|"]
    for name, row in receipt["legacy_feeds"].items():
        lines.append(f"| {name} | {row['http_status']} | {row['disposition']} | {row['freshness']} |")
    lines.extend(["", "> A completed metrics capture is not evidence of a healthy deployment. Missing or unapproved feed contracts remain fail-closed.", "", "See docs/PUBLIC_METRICS_CONTRACT.md and issue #234. No repository write or deployment occurs; no credential or fetched payload is retained by this monitor."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    commit = os.environ.get("GITHUB_SHA", "unknown")
    if commit != "unknown" and not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid source identity")
    receipt = capture(source_commit=commit)
    (args.output_dir / "live_snapshot.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    badge = {"schemaVersion": 1, "label": "legacy data feeds", "message": f"{receipt['available_objects']}/4 verified · freshness unknown", "color": "yellow" if receipt["state"] == "degraded" else "red", "cacheSeconds": 3600}
    (args.output_dir / "site_health_badge.json").write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "metrics_summary.md").write_text(summary(receipt), encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            for key in ("site_status", "available_objects", "state", "public_gateway_state", "snapshot_utc"):
                stream.write(f"{key}={receipt[key]}\n")
    print(summary(receipt))
    return 0  # Capture success only. Workflow fails separately on the verdict.


if __name__ == "__main__":
    raise SystemExit(main())
