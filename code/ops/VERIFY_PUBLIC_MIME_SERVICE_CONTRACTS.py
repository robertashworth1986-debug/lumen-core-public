#!/usr/bin/env python3
"""Bounded independent seven-route gate for the approved MIME-only repair.

Contracts reuse the canonical local BUILD_LIVE_DOMAIN_SERVICE_CONTRACT endpoint
expectations. This runner writes only its requested receipt, follows no redirect,
uses no account credentials, and proves observations rather than durable uptime.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

DOMAIN = "https://lumen-core.ai"
SPECS = (
    (DOMAIN + "/", (200,), "text/html", None, None),
    (DOMAIN + "/nginx-health", (200,), "application/json", {"status": "ok", "platform": "nginx"}, None),
    (DOMAIN + "/health", (200,), "application/json", {}, None),
    ("https://app.lumen-core.ai/", (301, 302, 307, 308), None, None, DOMAIN + "/proof_to_pilot.html"),
    ("https://app.lumen-core.ai/health", (200,), "application/json", {"status": "ok", "surface": "app", "mode": "reviewer_safe_redirect", "target": DOMAIN + "/proof_to_pilot.html"}, None),
    ("https://research.lumen-core.ai/", (301, 302, 307, 308), None, None, DOMAIN + "/quant_lab.html"),
    ("https://research.lumen-core.ai/health", (200,), "application/json", {"status": "ok", "surface": "research", "mode": "reviewer_safe_redirect", "target": DOMAIN + "/quant_lab.html"}, None),
)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def evaluate(spec, status, content_type, location, body):
    url, statuses, mime, subset, redirect = spec
    checks = {
        "status": status in statuses,
        "mime": mime is None or content_type.split(";", 1)[0].strip().lower() == mime,
        "redirect": redirect is None or location == redirect,
        "body_bound": len(body) <= 262144,
        "json": True,
    }
    if subset is not None:
        try:
            value = json.loads(body.decode("utf-8"), object_pairs_hook=unique_object,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_json")))
            checks["json"] = isinstance(value, dict) and all(value.get(k) == v for k, v in subset.items())
        except (ValueError, UnicodeError):
            checks["json"] = False
    return {"url": url, "http_status": status, "content_type": content_type,
        "body_sha256": hashlib.sha256(body).hexdigest(), "checks": checks,
        "passed": all(checks.values())}


def probe(spec):
    # curl supplies an elapsed-time limit, preserves TLS validation, follows no
    # redirects and bounds the complete body even for chunked responses.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="lumencore-service-") as folder:
        headers, body = Path(folder) / "headers", Path(folder) / "body"
        try:
            proc = subprocess.run(["curl", "--silent", "--show-error", "--noproxy", "*",
                "--connect-timeout", "5", "--max-time", "12", "--max-filesize", "262144",
                "--proto", "=https", "--dump-header", str(headers), "--output", str(body),
                "--write-out", "%{http_code}", spec[0]], capture_output=True, timeout=15, check=False)
            if proc.returncode:
                raise ValueError("transport_failed")
            with headers.open("rb") as stream:
                raw_headers = stream.read(65537)
            if len(raw_headers) > 65536:
                raise ValueError("headers_too_large")
            values = {}
            for line in raw_headers.decode("iso-8859-1").splitlines():
                if line.startswith("HTTP/"):
                    values = {}
                elif ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    if key in {"location", "content-type"} and key in values:
                        raise ValueError("ambiguous_response_header")
                    values[key] = value.strip()
            with body.open("rb") as stream:
                raw_body = stream.read(262145)
            return evaluate(spec, int(proc.stdout.strip()), values.get("content-type", ""),
                values.get("location", ""), raw_body)
        except (ValueError, OSError, subprocess.TimeoutExpired):
            return {"url": spec[0], "passed": False, "error": "BOUNDED_TRANSPORT_OR_RESPONSE_FAILURE"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit("Receipt destination must be new")
    with ThreadPoolExecutor(max_workers=7) as executor:
        rows = list(executor.map(probe, SPECS))
    receipt = {"schema": "lumencore.mime_repair_service_gate.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(), "required": len(SPECS),
        "passed": sum(row["passed"] for row in rows), "results": rows,
        "claim_boundary": "Seven bounded public observations; no continuous uptime or business outcome established."}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: receipt[k] for k in ("required", "passed", "observed_at")}))
    return 0 if receipt["passed"] == len(SPECS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
