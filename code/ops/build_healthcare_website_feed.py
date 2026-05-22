from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ENGINE_DIR = ROOT / "out" / "ops" / "healthcare_grants_engine"
ENGINE_LATEST_JSON = ENGINE_DIR / "healthcare_grants_engine_latest.json"
OUT_LATEST_JSON = ENGINE_DIR / "healthcare_website_feed_latest.json"
OUT_HEARTBEAT_JSON = ENGINE_DIR / "healthcare_website_feed_heartbeat_latest.json"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def parse_opp_from_grants_url(url: str) -> str:
    text = normalize_text(url)
    if not text:
        return ""
    match = re.search(r"search-results-detail/([^/?#]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return normalize_text(match.group(1))


def is_uuid(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            str(value or "").strip(),
            flags=re.IGNORECASE,
        )
    )


def unique_urls(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = normalize_text(value)
        if not token:
            continue
        if not re.match(r"^https?://", token, flags=re.IGNORECASE):
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def choose_primary_submit_url(number: str, source_url: str) -> tuple[str, list[str], str]:
    token = normalize_text(number)
    src = normalize_text(source_url)

    if token.upper().startswith("SKIP-"):
        primary = "https://helloskip.com/"
        alternates = unique_urls([src])
        return primary, alternates, "hello_skip"

    if re.search(r"simpler\.grants\.gov/opportunity/", src, flags=re.IGNORECASE):
        primary = src
        alternates = unique_urls(
            [
                f"https://www.grants.gov/search-results-detail/{quote(token)}" if token else "",
                src,
            ]
        )
        return primary, alternates, "simpler_opportunity"

    if re.search(r"grants\.gov/search-results-detail/", src, flags=re.IGNORECASE):
        primary = src
        alternates = unique_urls(
            [
                f"https://simpler.grants.gov/search?query={quote(token)}" if token else "",
                src,
            ]
        )
        return primary, alternates, "grants_gov_detail"

    if re.search(r"smartsimple", src, flags=re.IGNORECASE):
        primary = src
        alternates = unique_urls([src])
        return primary, alternates, "smartsimple"

    if token:
        if is_uuid(token):
            primary = f"https://simpler.grants.gov/opportunity/{quote(token)}"
            alternates = unique_urls(
                [
                    f"https://simpler.grants.gov/search?query={quote(token)}",
                    src,
                ]
            )
            return primary, alternates, "uuid_listing"

        primary = f"https://www.grants.gov/search-results-detail/{quote(token)}"
        alternates = unique_urls(
            [
                f"https://simpler.grants.gov/search?query={quote(token)}",
                src,
            ]
        )
        return primary, alternates, "opp_number_detail"

    if re.match(r"^https?://", src, flags=re.IGNORECASE):
        return src, unique_urls([src]), "source_url"

    return "https://www.grants.gov/search-grants", [], "grants_search"


def build_record(rank: int, row: dict[str, Any]) -> dict[str, Any]:
    scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
    source_url = normalize_text(row.get("url"))
    number = normalize_text(row.get("number"))
    if not number:
        number = parse_opp_from_grants_url(source_url)

    primary_submit_url, alternate_urls, submit_route = choose_primary_submit_url(number, source_url)

    grant_console_query = ""
    ai_fill_query = ""
    if number:
        safe_number = quote(number)
        grant_console_query = f"?opp={safe_number}"
        ai_fill_query = f"?opp={safe_number}&auto_fill=1"

    return {
        "rank": int(rank),
        "id": normalize_text(row.get("id")),
        "number": number,
        "title": normalize_text(row.get("title")),
        "agency": normalize_text(row.get("agency")),
        "status": normalize_text(row.get("status")),
        "action": normalize_text(row.get("action")),
        "days_to_close": int(float(row.get("days_to_close") or 0)),
        "scores": {
            "composite": float(scores.get("composite") or 0.0),
            "healthcare": float(scores.get("healthcare") or 0.0),
            "urgency": float(scores.get("urgency") or 0.0),
            "scientific": float(scores.get("scientific") or 0.0),
            "funding": float(scores.get("funding") or 0.0),
        },
        "links": {
            "submit_route": submit_route,
            "primary_submit_url": primary_submit_url,
            "alternate_urls": alternate_urls,
            "source_url": source_url,
            "grant_console_query": grant_console_query,
            "ai_fill_query": ai_fill_query,
        },
    }


def build_feed(payload: dict[str, Any], top_n: int) -> dict[str, Any]:
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    selected = [row for row in records if isinstance(row, dict)][: max(int(top_n), 1)]

    feed_records = [build_record(idx, row) for idx, row in enumerate(selected, start=1)]
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}

    generated_utc = now_utc_iso()
    out = {
        "schema": "healthcare_website_feed_v1",
        "generated_utc": generated_utc,
        "source": {
            "healthcare_engine_generated_utc": normalize_text(payload.get("generated_utc")),
            "healthcare_engine_scope": scope,
            "healthcare_engine_metrics": {
                "n_scanned": int(float(metrics.get("n_scanned") or 0)),
                "n_scored": int(float(metrics.get("n_scored") or 0)),
                "n_selected": int(float(metrics.get("n_selected") or 0)),
            },
            "source_json": str(ENGINE_LATEST_JSON),
        },
        "records": feed_records,
        "summary": {
            "n_records": len(feed_records),
            "close_7_days": sum(1 for row in feed_records if row.get("days_to_close", 9999) <= 7),
            "close_14_days": sum(1 for row in feed_records if row.get("days_to_close", 9999) <= 14),
            "immediate_or_fast": sum(
                1
                for row in feed_records
                if str(row.get("action") or "").upper() in {"IMMEDIATE_SUBMIT", "FAST_TRACK"}
            ),
        },
        "notes": {
            "submission_warning": "Some grants require login/workspace creation before final apply; open submit route first, then complete in Grants.gov or program portal.",
            "ai_fill_hint": "Set grants console base URL in widget config so AI Fill opens grants.html with auto_fill=1.",
        },
    }
    return out


def run(top_n: int) -> dict[str, Any]:
    engine_payload = read_json(ENGINE_LATEST_JSON, {})
    if not isinstance(engine_payload, dict) or not engine_payload:
        raise RuntimeError(f"healthcare engine payload missing: {ENGINE_LATEST_JSON}")

    feed_payload = build_feed(engine_payload, top_n=top_n)
    tag = now_tag()
    version_json = ENGINE_DIR / f"healthcare_website_feed_{tag}.json"

    write_json(version_json, feed_payload)
    write_json(OUT_LATEST_JSON, feed_payload)

    heartbeat = {
        "generated_utc": feed_payload.get("generated_utc"),
        "status": "ok",
        "reason": "feed_built",
        "artifacts": {
            "json": str(version_json),
            "json_latest": str(OUT_LATEST_JSON),
        },
        "summary": feed_payload.get("summary", {}),
    }
    write_json(OUT_HEARTBEAT_JSON, heartbeat)

    return {
        "generated_utc": feed_payload.get("generated_utc"),
        "artifacts": heartbeat["artifacts"],
        "heartbeat": str(OUT_HEARTBEAT_JSON),
        "summary": feed_payload.get("summary", {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build website-ready healthcare grants feed with click-through submission links.")
    parser.add_argument("--top-n", type=int, default=30, help="How many ranked healthcare opportunities to include.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(top_n=max(int(args.top_n), 1))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
