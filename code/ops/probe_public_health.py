#!/usr/bin/env python3
"""Read-only, bounded public-contract observations; never a durable-uptime claim.

The existing site_health.json summary fields remain compatible. Endpoint rows
represent the first failed observation (or the latest success), with counts;
the JSONL journal preserves every observation even if a later round recovers.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.parse import urlencode, urlsplit, urlunsplit
import uuid

MARKERS = {
    "home": "proof-to-pilot-home-v1",
    "offer": "bounded-validation-offer-v1",
    "external_review": "external-replication-docket-v1",
    "evidence": "proof-to-pilot-evidence-v1",
    "prooflock": "<title>ProofLock Console</title>",
    "legacy_hold": "legacy-public-route-hold-v1",
}
ENDPOINTS = (
    ("portal", "https://lumen-core.ai/", "home"),
    ("www_portal", "https://www.lumen-core.ai/", "home"),
    ("proof_to_pilot", "https://lumen-core.ai/proof_to_pilot.html", "offer"),
    ("external_review", "https://lumen-core.ai/external_review.html", "external_review"),
    ("evidence", "https://lumen-core.ai/evidence/", "evidence"),
    ("prooflock_console", "https://lumen-core.ai/build_week/prooflock_console/", "prooflock"),
    ("mission_control", "https://lumen-core.ai/mission_control.html", "legacy_hold"),
    ("quant_lab", "https://lumen-core.ai/quant_lab.html", "legacy_hold"),
    ("kraken_dashboard", "https://lumen-core.ai/kraken_execution_dashboard.html", "legacy_hold"),
    ("grants", "https://lumen-core.ai/grants.html", "legacy_hold"),
    ("forecast", "https://lumen-core.ai/forecast.html", "legacy_hold"),
    ("anomalies", "https://lumen-core.ai/anomalies.html", "legacy_hold"),
    ("explain", "https://lumen-core.ai/explain.html", "legacy_hold"),
    ("lab", "https://lumen-core.ai/lab.html", "legacy_hold"),
    ("gateway_public_status", "https://lumen-core.ai/api/public/status", "public_status"),
    ("gateway_health", "https://lumen-core.ai/health", "gateway_health"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def cache_busted_url(url: str, token: str) -> str:
    parts = urlsplit(url)
    query = "&".join(filter(None, (parts.query, urlencode({"_lc_health_probe": token}))))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def same_origin(left: str, right: str) -> bool:
    try:
        a, b = urlsplit(left), urlsplit(right)
        return (a.scheme, a.hostname, a.port or 443) == (b.scheme, b.hostname, b.port or 443)
    except ValueError:
        return False


def classify(contract: str, status: int, content_type: str, body: bytes,
             *, transport_ok: bool, same_origin_ok: bool) -> dict:
    static = contract in MARKERS
    if not static and contract not in ("public_status", "gateway_health"):
        raise ValueError(f"unknown endpoint contract: {contract}")
    http_ok = transport_ok and 200 <= status < 300
    row = {"surface": "static" if static else "dynamic", "status": status,
           "status_text": f"{status:03d}", "content_type": content_type,
           "contract": contract, "http_ok": http_ok, "reachable": http_ok,
           "contract_ok": False, "ok": False}
    if static:
        row["contract_ok"] = (http_ok and same_origin_ok
                              and content_type.lower().startswith("text/html")
                              and MARKERS[contract].encode() in body)
    else:
        try:
            payload = json.loads(body) if http_ok else None
            row["json_ok"] = http_ok and isinstance(payload, dict)
        except (ValueError, UnicodeError):
            payload, row["json_ok"] = None, False
        row["reachable"] = http_ok and row["json_ok"]
        if row["json_ok"] and same_origin_ok:
            row["contract_ok"] = all(payload.get(k) == v for k, v in {
                "status": "ok", "service": "luma-experience-gateway",
                "access_boundary": "operator_api_v1", "public_surface": "minimal",
            }.items())
            if contract == "gateway_health":
                generated = payload.get("generated_utc")
                row["contract_ok"] &= isinstance(generated, str) and bool(generated)
    row["ok"] = row["contract_ok"]
    return row


def probe(endpoint: tuple[str, str, str], sample_index: int, token: str,
          timeout: int = 10, max_bytes: int = 1048576) -> dict:
    name, url, contract = endpoint
    requested_url = cache_busted_url(url, f"{token}-{sample_index}-{name}")
    started_utc, started = utc_now(), time.monotonic()
    with tempfile.TemporaryDirectory(prefix="lc-health-") as directory:
        body_path = Path(directory) / "body"
        header_path = Path(directory) / "headers"
        # No retries: a recovered retry must not erase a failed observation.
        command = ["curl", "--silent", "--show-error", "--location", "--max-redirs", "5",
                   "--proto", "=https", "--proto-redir", "=https", "--max-time", str(timeout),
                   "--max-filesize", str(max_bytes), "--header", "Cache-Control: no-cache, no-store",
                   "--header", "Pragma: no-cache", "--output", str(body_path),
                   "--dump-header", str(header_path),
                   "--write-out", "%{http_code}\n%{content_type}\n%{url_effective}\n%{time_total}\n%{remote_ip}",
                   requested_url]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 3,
                                    check=False)
            code, stderr, output = result.returncode, result.stderr, result.stdout
        except subprocess.TimeoutExpired:
            code, stderr, output = 124, "probe process exceeded its bounded deadline", ""
        except OSError as exc:
            code, stderr, output = 127, f"probe process unavailable: {exc.__class__.__name__}", ""
        if body_path.exists():
            with body_path.open("rb") as stream:
                data = stream.read(max_bytes + 1)
        else:
            data = b""
        # Public diagnostic headers only; never retain cookies or auth headers.
        response_headers = {}
        if header_path.exists():
            with header_path.open("r", encoding="utf-8", errors="replace") as stream:
                for line in stream.read(65536).splitlines():
                    if line.startswith("HTTP/"):
                        response_headers = {}
                    key, separator, value = line.partition(":")
                    if separator and key.lower() in ("server", "via", "age", "x-cache", "cf-cache-status", "cf-ray"):
                        response_headers[key.lower()] = value.strip()[:300]
    fields = output.splitlines()
    status = int(fields[0]) if fields and len(fields[0]) == 3 and fields[0].isdigit() else 0
    content_type = fields[1] if len(fields) > 1 else ""
    effective_url = fields[2] if len(fields) > 2 else ""
    origin_ok = same_origin(url, effective_url)
    transport_ok = code == 0 and len(data) <= max_bytes
    row = classify(contract, status, content_type, data,
                   transport_ok=transport_ok, same_origin_ok=origin_ok)
    row.update({"name": name, "url": url, "requested_url": requested_url,
                "effective_url": effective_url, "same_origin_ok": origin_ok,
                "sample_index": sample_index, "started_utc": started_utc,
                "completed_utc": utc_now(), "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                "curl_exit_code": code, "transport_ok": transport_ok,
                "transport_error": stderr.strip()[:1000], "response_bytes": len(data),
                "connected_peer_ip": fields[4] if len(fields) > 4 else "",
                "response_headers": response_headers,
                "response_sha256": hashlib.sha256(data).hexdigest()})
    return row


def summarize(observations: list[dict], rounds: int, interval: int,
              started_utc: str, *, endpoints=ENDPOINTS) -> dict:
    expected_names = {endpoint[0] for endpoint in endpoints}
    if any(row["name"] not in expected_names for row in observations):
        raise ValueError("unexpected endpoint observation")
    endpoint_rows = {}
    for name, url, contract in endpoints:
        rows = [row for row in observations if row["name"] == name]
        # Strict round membership: duplicates cannot conceal a missing round.
        complete = len(rows) == rounds and {r["sample_index"] for r in rows} == set(range(1, rounds + 1))
        rows.sort(key=lambda r: r["sample_index"])
        failed = [r for r in rows if not r["ok"]]
        if rows:
            representative = dict(failed[0] if failed else rows[-1])
        else:
            representative = classify(contract, 0, "", b"", transport_ok=False, same_origin_ok=False)
            representative.update({"url": url, "started_utc": None, "completed_utc": None})
        representative.update({"ok": complete and not failed, "observed_count": len(rows),
                               "successful_count": sum(r["ok"] for r in rows),
                               "samples_complete": complete,
                               "first_failure_utc": failed[0]["started_utc"] if failed else None,
                               "flapping_observed": bool(failed) and any(r["ok"] for r in rows)})
        endpoint_rows[name] = representative
    static = [r for r in endpoint_rows.values() if r["surface"] == "static"]
    dynamic = [r for r in endpoint_rows.values() if r["surface"] == "dynamic"]

    def state(rows: list[dict]) -> str:
        if not rows:
            return "outage"
        if all(r["ok"] for r in rows):
            return "operational"
        if any(r["reachable"] for r in rows):
            return "degraded"
        return "outage"

    static_state = ("operational" if all(r["ok"] for r in static) else
                    "degraded" if any(r["ok"] for r in static) else "outage")
    gateway_state = state(dynamic)
    overall = "operational" if all(r["ok"] for r in endpoint_rows.values()) else (
        "outage" if static_state == gateway_state == "outage" else "degraded")
    return {"checked_utc": started_utc, "overall": overall,
            "static_surface_state": static_state, "dynamic_gateway_state": gateway_state,
            "healthy_count": sum(r["ok"] for r in endpoint_rows.values()), "total_count": len(endpoint_rows),
            "static_healthy_count": sum(r["ok"] for r in static), "static_total_count": len(static),
            "dynamic_healthy_count": sum(r["ok"] for r in dynamic), "dynamic_total_count": len(dynamic),
            "dynamic_reachable_count": sum(r["reachable"] for r in dynamic), "endpoints": endpoint_rows,
            "observation_window": {"started_utc": started_utc, "completed_utc": utc_now(),
                "rounds_expected": rounds, "interval_seconds": interval,
                "observations_expected": rounds * len(endpoints), "observations_recorded": len(observations),
                "all_samples_complete": all(r["samples_complete"] for r in endpoint_rows.values()),
                "failed_observations": sum(not r["ok"] for r in observations),
                "flapping_endpoint_count": sum(r["flapping_observed"] for r in endpoint_rows.values()),
                "claim_boundary": "Bounded observations from one runner; not continuous uptime, origin attribution, or metrics-feed health."}}


def capture(output_dir: Path, *, rounds: int = 4, interval: int = 60,
            timeout: int = 10, max_bytes: int = 1048576,
            probe_fn=probe, sleep_fn=time.sleep, endpoints=ENDPOINTS) -> dict:
    if not 2 <= rounds <= 6 or not 60 <= interval <= 120:
        raise ValueError("observation window requires 2-6 rounds and 60-120 seconds between rounds")
    if not 1 <= timeout <= 15 or not 1024 <= max_bytes <= 1048576:
        raise ValueError("invalid request bounds")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    for filename in ("site_health.json", "uptime_badge.json", "site_health_samples.jsonl"):
        path = output_dir / filename
        if path.is_symlink():
            raise ValueError("health receipt path must not be a symbolic link")
        path.unlink(missing_ok=True)
    started_utc, token, observations = utc_now(), uuid.uuid4().hex, []
    journal = output_dir / "site_health_samples.jsonl"
    with journal.open("w", encoding="utf-8") as stream:
        for index in range(1, rounds + 1):
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(probe_fn, endpoint, index, token, timeout, max_bytes)
                           for endpoint in endpoints]
                for future in as_completed(futures):
                    row = future.result()
                    observations.append(row)
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
                    stream.flush()
            if index != rounds:
                sleep_fn(interval)
    summary = summarize(observations, rounds, interval, started_utc, endpoints=endpoints)
    (output_dir / "site_health.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    badge = {"schemaVersion": 1, "label": "status",
             "message": f"{summary['overall']} · sampled window · static={summary['static_surface_state']} · gateway={summary['dynamic_gateway_state']}",
             "color": {"operational": "brightgreen", "degraded": "yellow", "outage": "red"}[summary["overall"]],
             "cacheSeconds": 3600}
    (output_dir / "uptime_badge.json").write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--interval-seconds", type=int, default=60)
    args = parser.parse_args()
    summary = capture(args.output_dir, rounds=args.rounds, interval=args.interval_seconds)
    print(json.dumps({k: summary[k] for k in ("overall", "healthy_count", "total_count", "observation_window")}))
    return 0 if summary["overall"] == "operational" else 1


if __name__ == "__main__":
    raise SystemExit(main())
