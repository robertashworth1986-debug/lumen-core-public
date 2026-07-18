from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
OUT_JSON = OUT_DIR / "OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT_2026-07-18.json"
BROWSER_QA_CAPTURE = OUT_DIR / "OPENAI_BUILD_WEEK_BROWSER_QA_CAPTURE_2026-07-18.json"
BASE_URL = "https://lumen-core.ai"
DEMO_URL = f"{BASE_URL}/build_week/prooflock_console/"

PUBLIC_FILES = (
    ("build_week/prooflock_console/app.js", "/build_week/prooflock_console/app.js"),
    ("build_week/prooflock_console/index.html", "/build_week/prooflock_console/index.html"),
    ("build_week/prooflock_console/README.md", "/build_week/prooflock_console/README.md"),
    (
        "build_week/prooflock_console/sample_receipt.json",
        "/build_week/prooflock_console/sample_receipt.json",
    ),
    ("build_week/prooflock_console/styles.css", "/build_week/prooflock_console/styles.css"),
    (
        "build_week/prooflock_console/verify_receipt.py",
        "/build_week/prooflock_console/verify_receipt.py",
    ),
    (
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.json",
        "/assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.json",
    ),
    (
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.png",
        "/assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.png",
    ),
    (
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json",
        "/assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json",
    ),
    (
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png",
        "/assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png",
    ),
)

Fetch = Callable[[str], tuple[int, bytes, str]]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_url(url: str, timeout: float = 20.0) -> tuple[int, bytes, str]:
    curl = shutil.which("curl") or shutil.which("curl.exe")
    if curl:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            output_path = Path(handle.name)
        try:
            result = subprocess.run(
                [
                    curl,
                    "-sS",
                    "-L",
                    "--max-time",
                    str(timeout),
                    "--output",
                    str(output_path),
                    "--write-out",
                    "%{http_code}\n%{url_effective}",
                    url,
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            lines = result.stdout.splitlines()
            if result.returncode != 0 or len(lines) < 2:
                raise RuntimeError(result.stderr.strip() or f"curl exit {result.returncode}")
            return int(lines[-2]), output_path.read_bytes(), lines[-1]
        finally:
            output_path.unlink(missing_ok=True)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json,image/avif,image/webp,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read(), response.geturl()


def safe_source(relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe public-demo source: {relative_path}")
    source = (ROOT / relative).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"Missing or out-of-root public-demo source: {relative_path}")
    return source


def load_browser_qa() -> dict[str, Any]:
    default = {
        "verified": False,
        "status": "BROWSER_QA_CAPTURE_MISSING",
        "capture_path": BROWSER_QA_CAPTURE.relative_to(ROOT).as_posix(),
    }
    if not BROWSER_QA_CAPTURE.is_file():
        return default
    try:
        capture = json.loads(BROWSER_QA_CAPTURE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**default, "status": "BROWSER_QA_CAPTURE_UNREADABLE"}

    unhashed = dict(capture)
    recorded_hash = unhashed.pop("capture_sha256", "")
    hash_valid = bool(recorded_hash) and recorded_hash == stable_hash(unhashed)
    desktop = capture.get("desktop", {})
    mobile = capture.get("mobile", {})
    expected_state = {
        "status": "Verified, promotion held",
        "integrity": "Verified",
        "artifact_state": "4 / 4",
        "decision": "HOLD",
        "horizontal_overflow_px": 0,
    }
    verified = all(
        (
            capture.get("schema") == "lumencore.openai_build_week_browser_qa_capture.v1",
            capture.get("demo_url") == DEMO_URL,
            hash_valid,
            all(desktop.get(key) == value for key, value in expected_state.items()),
            all(mobile.get(key) == value for key, value in expected_state.items()),
            desktop.get("viewport_width") == 1280,
            desktop.get("viewport_height") == 720,
            mobile.get("viewport_width") == 390,
            mobile.get("viewport_height") == 844,
            mobile.get("console_errors") == 0,
            mobile.get("console_warnings") == 0,
        )
    )
    return {
        "verified": verified,
        "status": "BROWSER_QA_CAPTURE_VERIFIED" if verified else "BROWSER_QA_CAPTURE_INVALID",
        "capture_path": BROWSER_QA_CAPTURE.relative_to(ROOT).as_posix(),
        "capture_sha256": recorded_hash,
        "capture_hash_valid": hash_valid,
        "capture": capture,
    }


def build_payload(
    fetcher: Fetch = fetch_url,
    *,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    browser_qa = load_browser_qa()
    artifacts = []
    for relative_path, url_path in PUBLIC_FILES:
        source = safe_source(relative_path)
        url = f"{BASE_URL}{url_path}"
        try:
            status, body, final_url = fetcher(url)
            error = ""
        except Exception as exc:  # pragma: no cover - network failures vary by host
            status, body, final_url, error = 0, b"", url, f"{type(exc).__name__}: {exc}"
        local_hash = file_sha256(source)
        remote_hash = hashlib.sha256(body).hexdigest() if body else ""
        artifacts.append(
            {
                "source": relative_path,
                "url": url,
                "final_url": final_url,
                "http_status": status,
                "local_bytes": source.stat().st_size,
                "remote_bytes": len(body),
                "local_sha256": local_hash,
                "remote_sha256": remote_hash,
                "hash_matches": status == 200 and remote_hash == local_hash,
                "error": error,
            }
        )

    all_http_200 = all(row["http_status"] == 200 for row in artifacts)
    all_hashes_match = all(row["hash_matches"] for row in artifacts)
    verified = (
        len(artifacts) == len(PUBLIC_FILES)
        and all_http_200
        and all_hashes_match
        and browser_qa["verified"]
    )
    payload: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_public_demo_receipt.v1",
        "generated_utc": generated_utc or now_utc(),
        "status": "PUBLIC_DEMO_HASH_VERIFIED" if verified else "PUBLIC_DEMO_VERIFICATION_FAILED",
        "demo_url": DEMO_URL,
        "required_file_count": len(PUBLIC_FILES),
        "http_200_count": sum(1 for row in artifacts if row["http_status"] == 200),
        "hash_match_count": sum(1 for row in artifacts if row["hash_matches"]),
        "all_http_200": all_http_200,
        "all_hashes_match": all_hashes_match,
        "browser_qa_verified": browser_qa["verified"],
        "public_demo_verified": verified,
        "artifacts": artifacts,
        "browser_qa": browser_qa,
        "claim_boundary": (
            "This receipt proves that the listed public files returned HTTP 200 and matched the "
            "local SHA-256 identities at the recorded observation time. The browser QA record "
            "captures the observed responsive verification state. It does not prove continuous "
            "availability, Devpost registration or submission, OpenAI endorsement, judging outcome, "
            "engineering validation, prototype status, safety, patent rights, funding, or value."
        ),
    }
    payload["receipt_sha256"] = stable_hash(payload)
    return payload


def write_output(payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_output(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "demo_url": payload["demo_url"],
                "http_200_count": payload["http_200_count"],
                "hash_match_count": payload["hash_match_count"],
                "receipt_sha256": payload["receipt_sha256"],
            },
            indent=2,
        )
    )
    return 0 if payload["public_demo_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
