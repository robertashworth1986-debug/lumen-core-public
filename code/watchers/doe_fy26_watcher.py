"""Watch the active DOE FY26 Phase I Genesis Mission solicitation.

The watcher is intentionally fail-closed. It records the current official
deadline, topic set, and application-portal state, but it cannot sign in,
upload, certify, or submit anything.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo


URL = "https://sbir-sttr.connectwerx.org/portfolio-items/fy26genesismission/"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "grants" / "doe_fy26_watch.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = "lumencore.doe_genesis_watch.v2"
OPPORTUNITY_NAME = "FY26 Phase I - Genesis Mission"
EXPECTED_TOPICS = (
    "Scaling the Biotechnology Revolution",
    "AI for Quantum Computing and Networking",
    "Designing Materials with Predictable Functionality",
    "Achieving AI-Driven Autonomous Laboratories",
)
EASTERN = ZoneInfo("America/New_York")


class GenesisParseError(ValueError):
    """Raised when the official page no longer matches required invariants."""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._current_href: str | None = None
        self._current_anchor_text: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if lowered == "a":
            attrs_by_name = {name.lower(): value for name, value in attrs}
            self._current_href = attrs_by_name.get("href")
            self._current_anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if self._ignored_depth:
            return
        if lowered == "a" and self._current_href:
            anchor_text = _normalize_text(" ".join(self._current_anchor_text))
            self.links.append((anchor_text, self._current_href))
            self._current_href = None
            self._current_anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self.text_parts.append(data)
        if self._current_href is not None:
            self._current_anchor_text.append(data)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _parse_page(html: str) -> tuple[str, list[tuple[str, str]]]:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return _normalize_text(" ".join(parser.text_parts)), parser.links


def _extract_deadline(text: str) -> tuple[str, str]:
    match = re.search(
        r"Submission Deadline:\s*"
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+"
        r"(\d{1,2}),\s+(\d{4})\s+at\s+"
        r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*ET",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise GenesisParseError("Official submission deadline was not found")

    month, day, year, hour, minute, meridiem = match.groups()
    deadline = datetime.strptime(
        f"{month} {day} {year} {hour}:{minute or '00'} {meridiem}",
        "%B %d %Y %I:%M %p",
    ).replace(tzinfo=EASTERN)
    literal = match.group(0).split(":", 1)[1].strip()
    return literal, deadline.isoformat()


def _valid_external_link(href: str) -> bool:
    resolved = urljoin(URL, href)
    split = urlsplit(resolved)
    return split.scheme == "https" and bool(split.hostname)


def _application_portal(
    text: str,
    links: list[tuple[str, str]],
) -> tuple[str, str | None]:
    if re.search(r"application link coming soon", text, flags=re.IGNORECASE):
        return "COMING_SOON", None

    for anchor_text, href in links:
        combined = f"{anchor_text} {href}".lower()
        if (
            ("application management portal" in combined or "amp" in combined)
            and _valid_external_link(href)
        ):
            return "LINKED", urljoin(URL, href)
    return "UNKNOWN", None


def _days_to_deadline(deadline_iso: str, now: datetime) -> float:
    deadline = datetime.fromisoformat(deadline_iso).astimezone(timezone.utc)
    return round((deadline - now.astimezone(timezone.utc)).total_seconds() / 86400, 3)


def detect_state(html: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Parse required Genesis fields from the official opportunity page."""

    observed = now or datetime.now(timezone.utc)
    text, links = _parse_page(html)
    if OPPORTUNITY_NAME.lower() not in text.lower():
        raise GenesisParseError("Genesis opportunity title was not found")

    active = "Active Solicitation" in text
    deadline_literal, deadline_iso = _extract_deadline(text)
    present_topics = [topic for topic in EXPECTED_TOPICS if topic.lower() in text.lower()]
    if len(present_topics) != len(EXPECTED_TOPICS):
        missing = sorted(set(EXPECTED_TOPICS) - set(present_topics))
        raise GenesisParseError(f"Required topic text missing: {missing}")

    portal_state, portal_url = _application_portal(text, links)
    if portal_state == "UNKNOWN":
        raise GenesisParseError("Application portal state could not be established")

    days_remaining = _days_to_deadline(deadline_iso, observed)
    if days_remaining < 0:
        urgency = "DEADLINE_PASSED"
    elif days_remaining <= 3:
        urgency = "DUE_WITHIN_3_DAYS"
    elif days_remaining <= 14:
        urgency = "DUE_WITHIN_14_DAYS"
    else:
        urgency = "OPEN_NOT_DUE_WITHIN_14_DAYS"

    relevant = {
        "active_solicitation": active,
        "deadline_literal": deadline_literal,
        "deadline_iso": deadline_iso,
        "topics": present_topics,
        "application_portal_state": portal_state,
        "application_portal_url": portal_url,
    }
    fingerprint = hashlib.sha256(
        json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        **relevant,
        "topic_4_present": EXPECTED_TOPICS[-1] in present_topics,
        "days_to_deadline": days_remaining,
        "urgency": urgency,
        "source_fingerprint_sha256": fingerprint,
        "parse_complete": True,
    }


def _read_previous() -> dict[str, Any] | None:
    if not OUT.is_file():
        return None
    try:
        payload = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def alert_reasons(
    state: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if state["urgency"] in {"DUE_WITHIN_3_DAYS", "DUE_WITHIN_14_DAYS"}:
        reasons.append(state["urgency"])
    if state["application_portal_state"] == "LINKED" and (
        not previous or previous.get("application_portal_state") != "LINKED"
    ):
        reasons.append("APPLICATION_PORTAL_BECAME_LINKED")
    if (
        previous
        and previous.get("schema") == SCHEMA
        and previous.get("status") == "ok"
        and previous.get("parse_complete") is True
    ):
        if previous.get("deadline_iso") != state["deadline_iso"]:
            reasons.append("DEADLINE_CHANGED")
        if previous.get("topics") != state["topics"]:
            reasons.append("TOPIC_TEXT_CHANGED")
        if previous.get("active_solicitation") != state["active_solicitation"]:
            reasons.append("ACTIVE_STATUS_CHANGED")
    return reasons


def fetch() -> str:
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "LumenCore-DOE-Genesis-Watcher/2.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    now = datetime.now(timezone.utc)
    previous = _read_previous()
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "checked_utc": now.isoformat(),
        "opportunity": OPPORTUNITY_NAME,
        "url": URL,
        "external_action_allowed": False,
        "claim_boundary": (
            "This watcher observes public opportunity metadata only. It does not "
            "establish eligibility, invitation, application readiness, award, or "
            "authority to sign in, upload, certify, or submit."
        ),
    }
    try:
        state = detect_state(fetch(), now=now)
        reasons = alert_reasons(state, previous)
        record.update(state)
        record["alert_reasons"] = reasons
        record["alert"] = bool(reasons)
        record["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        record["status"] = "error"
        record["parse_complete"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["alert_reasons"] = ["SOURCE_OR_PARSE_FAILURE"]
        record["alert"] = True

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
