from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
OUT_JSON = OUT_DIR / "NASHVILLE_EC_LIVE_DEADLINE_RECEIPT_2026-07-17.json"
OUT_MD = OUT_DIR / "NASHVILLE_EC_LIVE_DEADLINE_RECEIPT_2026-07-17.md"

OFFICIAL_SOURCES = {
    "homepage": "https://ec.co/",
    "application": "https://ec.co/apply/",
    "takeoff": "https://ec.co/accelerators/takeoff/",
}
EXPECTED_MARKERS = {
    "homepage": (
        "Fall 2026 Accelerators",
        "July 17",
        "Apply Now",
    ),
    "application": (
        "Start Your Application",
        "Save your progress",
    ),
    "takeoff": (
        "TakeOff Accelerator",
        "Applications for the Fall 2026 Cohort are open",
        "September",
    ),
}
ALLOWED_HOSTS = {"ec.co", "www.ec.co"}
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
TIME_PATTERN = re.compile(
    r"\b(?:0?[1-9]|1[0-2]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
PRIVATE_MARKERS = (
    "meeting id",
    "passcode",
    "client_secret",
    "refresh_token",
    "api_key",
    "private key",
    "full legal party name",
    "business address",
    "signatory email",
)
CLAIM_BOUNDARY = (
    "This receipt records a direct HTTPS retrieval of public Nashville Entrepreneur Center pages "
    "and the presence or absence of bounded text markers at that time. It does not prove that a "
    "portal submission occurred, that every conditional question is known, that the application "
    "will remain open until midnight, or that LumenCore will be accepted, funded, validated, "
    "endorsed, contracted, or awarded an Impact Grant."
)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self._text: list[str] = []
        self._title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title.append(data)
        self._text.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._text)).strip()

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._title)).strip()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_page(url: str, timeout: float = 20.0) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "LumenCore-Public-Deadline-Receipt/1.0 (+https://lumen-core.ai)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError(f"Official page exceeded {MAX_RESPONSE_BYTES} bytes: {url}")
        final_url = response.geturl()
        parsed = urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected official-page redirect: {final_url}")
        return {
            "requested_url": url,
            "final_url": final_url,
            "http_status": int(response.status),
            "content_type": response.headers.get_content_type(),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "raw": raw,
        }


def deadline_time_candidates(text: str, deadline_text: str = "July 17") -> list[str]:
    candidates: list[str] = []
    lowered = text.lower()
    needle = deadline_text.lower()
    start = 0
    while True:
        index = lowered.find(needle, start)
        if index < 0:
            break
        window = text[max(0, index - 120) : min(len(text), index + len(needle) + 120)]
        candidates.extend(match.group(0) for match in TIME_PATTERN.finditer(window))
        start = index + len(needle)
    return sorted(set(candidates), key=str.lower)


def analyze_page(source_id: str, fetched: dict[str, Any], retrieved_utc: str) -> dict[str, Any]:
    raw = fetched["raw"]
    if not isinstance(raw, bytes):
        raise TypeError("Fetcher raw value must be bytes")
    parser = VisibleTextParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    text = parser.text
    markers = {
        marker: marker.casefold() in text.casefold()
        for marker in EXPECTED_MARKERS[source_id]
    }
    page = {
        "source_id": source_id,
        "requested_url": fetched["requested_url"],
        "final_url": fetched["final_url"],
        "retrieved_utc": retrieved_utc,
        "http_status": fetched["http_status"],
        "content_type": fetched["content_type"],
        "bytes": len(raw),
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "etag": fetched.get("etag"),
        "last_modified": fetched.get("last_modified"),
        "page_title": parser.title,
        "expected_markers": markers,
        "all_expected_markers_present": all(markers.values()),
        "deadline_date_marker_present": "july 17" in text.casefold(),
        "deadline_time_candidates_near_date": deadline_time_candidates(text),
        "raw_html_stored": False,
    }
    page["receipt_sha256"] = stable_hash(page)
    return page


def build_payload(
    fetcher: Callable[[str], dict[str, Any]] = fetch_page,
    retrieved_utc: str | None = None,
) -> dict[str, Any]:
    retrieved = retrieved_utc or now_utc()
    pages = [
        analyze_page(source_id, fetcher(url), retrieved)
        for source_id, url in OFFICIAL_SOURCES.items()
    ]
    by_id = {page["source_id"]: page for page in pages}
    exact_time_candidates = sorted(
        {
            candidate
            for page in pages
            for candidate in page["deadline_time_candidates_near_date"]
        },
        key=str.lower,
    )
    all_fetches_ok = all(
        page["http_status"] == 200 and page["content_type"] == "text/html"
        for page in pages
    )
    homepage_deadline_confirmed = (
        by_id["homepage"]["deadline_date_marker_present"]
        and by_id["homepage"]["expected_markers"]["Fall 2026 Accelerators"]
    )
    application_open_signal = (
        by_id["application"]["expected_markers"]["Start Your Application"]
        and by_id["application"]["expected_markers"]["Save your progress"]
    )
    takeoff_open_signal = by_id["takeoff"]["expected_markers"][
        "Applications for the Fall 2026 Cohort are open"
    ]
    if not all_fetches_ok:
        status = "OFFICIAL_SOURCE_FETCH_INCOMPLETE_REVIEW_REQUIRED"
    elif not (homepage_deadline_confirmed and application_open_signal and takeoff_open_signal):
        status = "OFFICIAL_MARKERS_INCOMPLETE_REVIEW_REQUIRED"
    elif exact_time_candidates:
        status = "OFFICIAL_OPEN_TIME_TEXT_DETECTED_REVIEW_REQUIRED"
    else:
        status = "OFFICIAL_OPEN_DATE_ONLY_DEADLINE_HUMAN_FACTS_REQUIRED"

    payload: dict[str, Any] = {
        "schema": "lumencore.nashville_ec_live_deadline_receipt.v1",
        "generated_utc": now_utc(),
        "retrieved_utc": retrieved,
        "status": status,
        "direct_answer": (
            "The official Nashville Entrepreneur Center pages showed the Fall 2026 application "
            "and TakeOff cohort open with a July 17 deadline at retrieval time. No exact closing "
            "hour was detected near the deadline date, so the safe operational instruction is to "
            "complete the founder-fact gate and submit early rather than assume midnight."
        ),
        "deadline": {
            "date": "2026-07-17",
            "date_status": (
                "CONFIRMED_ON_OFFICIAL_HOMEPAGE"
                if homepage_deadline_confirmed
                else "NOT_CONFIRMED_REVIEW_REQUIRED"
            ),
            "time": None,
            "time_status": (
                "TIME_TEXT_DETECTED_NEAR_DATE_REVIEW_REQUIRED"
                if exact_time_candidates
                else "NO_CLOSE_TIME_DETECTED_ON_FETCHED_OFFICIAL_PAGES"
            ),
            "time_candidates_near_date": exact_time_candidates,
            "operational_rule": "SUBMIT_EARLY_NO_MIDNIGHT_ASSUMPTION",
        },
        "application": {
            "open_signal_present": application_open_signal,
            "takeoff_open_signal_present": takeoff_open_signal,
            "portal_final_submission_verified": False,
            "human_facts_resolved": False,
            "final_submit_allowed_without_human": False,
            "fee_or_terms_acceptance_allowed_without_human": False,
        },
        "integrity": {
            "source_count": len(pages),
            "all_fetches_http_200_html": all_fetches_ok,
            "all_expected_markers_present": all(
                page["all_expected_markers_present"] for page in pages
            ),
            "raw_html_stored": False,
            "network_route": "DIRECT_HTTPS_NO_SESSION_BROWSER",
            "browser_navigation_performed": False,
        },
        "sources": pages,
        "required_next_action": (
            "Collect the six founder confirmations, review every populated portal field and any "
            "terms or fee, then obtain action-time approval before final submission."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {
            "json": OUT_JSON.relative_to(ROOT).as_posix(),
            "markdown": OUT_MD.relative_to(ROOT).as_posix(),
        },
    }
    payload["receipt_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    deadline = payload["deadline"]
    application = payload["application"]
    integrity = payload["integrity"]
    lines = [
        "# Nashville EC Live Deadline Receipt - 2026-07-17",
        "",
        payload["direct_answer"],
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Retrieved UTC: `{payload['retrieved_utc']}`",
        f"- Deadline date: `{deadline['date']}`",
        f"- Date status: `{deadline['date_status']}`",
        f"- Deadline time: `{deadline['time']}`",
        f"- Time status: `{deadline['time_status']}`",
        f"- Operational rule: `{deadline['operational_rule']}`",
        f"- Application-open signal: `{str(application['open_signal_present']).lower()}`",
        f"- TakeOff-open signal: `{str(application['takeoff_open_signal_present']).lower()}`",
        f"- Human facts resolved: `{str(application['human_facts_resolved']).lower()}`",
        f"- Final submit without human: `{str(application['final_submit_allowed_without_human']).lower()}`",
        f"- Fee or terms acceptance without human: `{str(application['fee_or_terms_acceptance_allowed_without_human']).lower()}`",
        f"- Session-browser navigation performed: `{str(integrity['browser_navigation_performed']).lower()}`",
        f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
        "",
        "## Official Source Receipts",
        "",
        "| Source | HTTP | Bytes | Markers | Content SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for page in payload["sources"]:
        lines.append(
            f"| [{page['source_id']}]({page['final_url']}) | `{page['http_status']}` | "
            f"`{page['bytes']}` | `{str(page['all_expected_markers_present']).lower()}` | "
            f"`{page['content_sha256']}` |"
        )
    lines.extend(["", "## Marker Detail", ""])
    for page in payload["sources"]:
        lines.extend(
            [
                f"### {page['source_id']}",
                "",
                f"- Requested URL: {page['requested_url']}",
                f"- Final URL: {page['final_url']}",
                f"- Page title: {page['page_title']}",
                f"- Raw HTML stored: `{str(page['raw_html_stored']).lower()}`",
                f"- Receipt SHA-256: `{page['receipt_sha256']}`",
            ]
        )
        for marker, present in page["expected_markers"].items():
            lines.append(f"- Marker `{marker}`: `{str(present).lower()}`")
        lines.append("")
    lines.extend(
        [
            "## Required Next Action",
            "",
            payload["required_next_action"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def ensure_public_safe(text: str) -> None:
    lowered = text.lower()
    hits = sorted(marker for marker in PRIVATE_MARKERS if marker in lowered)
    if hits:
        raise ValueError(f"Refusing to write private markers: {hits}")


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    ensure_public_safe(json.dumps(payload, sort_keys=True))
    ensure_public_safe(markdown)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "deadline_date_status": payload["deadline"]["date_status"],
                "deadline_time_status": payload["deadline"]["time_status"],
                "application_open_signal": payload["application"]["open_signal_present"],
                "all_fetches_http_200_html": payload["integrity"]["all_fetches_http_200_html"],
                "browser_navigation_performed": payload["integrity"]["browser_navigation_performed"],
                "json": OUT_JSON.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
