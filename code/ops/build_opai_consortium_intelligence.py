from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, build_opener
from urllib.robotparser import RobotFileParser


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_START_URL = "https://openpowerai.org/"
DEFAULT_OUT = ROOT / "out" / "opai" / "opai_consortium_intelligence_latest.json"
DEFAULT_DASHBOARD_OUT = ROOT / "dashboard" / "data" / "opai_consortium_intelligence.json"
DEFAULT_USER_AGENT = "LumenCorePublicIntelligence/1.0 (+https://lumen-core.ai/)"
DEFAULT_ALLOWED_HOSTS = (
    "openpowerai.org",
    "www.openpowerai.org",
)

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:\s*[-–]\s*\d{1,2})?(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")

GENERIC_IMAGE_ALTS = {
    "",
    "image",
    "logo",
    "op ai",
    "open power ai consortium",
    "epri",
    "facebook",
    "twitter",
    "linkedin",
    "youtube",
}

WORKING_GROUP_NAMES = {
    "member representative committee",
    "data sharing",
    "domain-specific model",
    "implementation",
    "use case",
}

PUBLIC_ATTACHMENT_HOSTS = {
    "restservice.epri.com",
    "www.epri.com",
    "epri.com",
    "epri.brightidea.com",
    "interactive.epri.com",
}


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    content_type: str
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass
class PageRecord:
    url: str
    final_url: str
    status: int
    content_type: str
    title: str
    meta_description: str
    headings: list[str]
    links: list[dict[str, str]]
    image_alts: list[str]
    contact_emails: list[str]
    date_mentions: list[str]
    form_actions: list[str]
    text_preview: str
    raw_sha256: str
    page_type: str


@dataclass
class CrawlError:
    url: str
    stage: str
    error_type: str
    detail: str


@dataclass
class CrawlResult:
    pages: list[PageRecord]
    errors: list[CrawlError]
    skipped_external_urls: list[str]
    skipped_disallowed_urls: list[str]


class PublicPageParser(HTMLParser):
    """Extract public, reviewer-safe structure without executing scripts or forms."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._skip_depth = 0
        self._title_depth = 0
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []

        self.title_parts: list[str] = []
        self.meta_description = ""
        self.headings: list[str] = []
        self.links: list[dict[str, str]] = []
        self.image_alts: list[str] = []
        self.text_parts: list[str] = []
        self.form_actions: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()

        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "title":
            self._title_depth += 1
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag == "a":
            self._anchor_href = attrs_map.get("href", "")
            self._anchor_parts = []
        elif tag == "img":
            alt = normalize_text(attrs_map.get("alt", ""))
            if alt:
                self.image_alts.append(alt)
        elif tag == "meta":
            name = attrs_map.get("name", "").lower()
            prop = attrs_map.get("property", "").lower()
            if name == "description" or prop == "og:description":
                description = normalize_text(attrs_map.get("content", ""))
                if description and not self.meta_description:
                    self.meta_description = description
        elif tag == "form":
            action = normalize_url(self.base_url, attrs_map.get("action", ""))
            self.form_actions.append(action or "(current page)")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return

        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        elif self._heading_tag == tag:
            heading = normalize_text(" ".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_tag = None
            self._heading_parts = []
        elif tag == "a" and self._anchor_href is not None:
            href = normalize_url(self.base_url, self._anchor_href)
            text = normalize_text(" ".join(self._anchor_parts))
            if href:
                self.links.append({"url": href, "text": text})
            self._anchor_href = None
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = normalize_text(data)
        if not text:
            return
        self.text_parts.append(text)
        if self._title_depth:
            self.title_parts.append(text)
        if self._heading_tag:
            self._heading_parts.append(text)
        if self._anchor_href is not None:
            self._anchor_parts.append(text)


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def normalize_url(base_url: str, href: str) -> str:
    href = (href or "").strip()
    if not href or href.startswith(("javascript:", "data:", "tel:")):
        return ""
    joined = urljoin(base_url, href)
    clean, _fragment = urldefrag(joined)
    return clean


def canonical_host(host: str) -> str:
    return (host or "").lower().rstrip(".")


def is_allowed_url(url: str, allowed_hosts: Iterable[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    allowed = {canonical_host(host) for host in allowed_hosts}
    return canonical_host(parsed.hostname or "") in allowed


def looks_like_html(content_type: str, url: str) -> bool:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type in {"text/html", "application/xhtml+xml"}:
        return True
    if not media_type:
        suffix = Path(urlparse(url).path).suffix.lower()
        return suffix in {"", ".html", ".htm"}
    return False


def classify_page(url: str, title: str, headings: Sequence[str]) -> str:
    haystack = " ".join([url, title, *headings]).lower()
    if "consortium-membership" in haystack or "consortium membership" in haystack:
        return "membership"
    if "group-materials" in haystack or any(name in haystack for name in WORKING_GROUP_NAMES):
        return "working_group"
    if "meeting" in haystack or "event" in haystack:
        return "events"
    if "research" in haystack or "results" in haystack:
        return "research"
    if "news" in haystack or "newsletter" in haystack:
        return "news"
    if "about" in haystack:
        return "about"
    if url.rstrip("/") == DEFAULT_START_URL.rstrip("/"):
        return "home"
    return "other"


def parse_public_page(response: HttpResponse, preview_chars: int = 600) -> PageRecord:
    body_text = response.body.decode("utf-8", errors="replace")
    parser = PublicPageParser(response.url)
    parser.feed(body_text)
    parser.close()

    full_text = normalize_text(" ".join(parser.text_parts))
    contact_emails = sorted(
        {
            match.lower()
            for match in EMAIL_RE.findall(full_text)
        }
        | {
            urlparse(link["url"]).path.lower()
            for link in parser.links
            if link["url"].lower().startswith("mailto:")
        }
    )
    contact_emails = [email for email in contact_emails if EMAIL_RE.fullmatch(email)]

    date_mentions = []
    seen_dates: set[str] = set()
    for match in DATE_RE.findall(full_text):
        normalized = normalize_text(match)
        key = normalized.lower()
        if key not in seen_dates:
            seen_dates.add(key)
            date_mentions.append(normalized)

    title = normalize_text(" ".join(parser.title_parts))
    return PageRecord(
        url=response.url,
        final_url=response.url,
        status=response.status,
        content_type=response.content_type,
        title=title,
        meta_description=parser.meta_description,
        headings=dedupe_preserve_order(parser.headings),
        links=dedupe_links(parser.links),
        image_alts=dedupe_preserve_order(parser.image_alts),
        contact_emails=contact_emails,
        date_mentions=date_mentions,
        form_actions=dedupe_preserve_order(parser.form_actions),
        text_preview=full_text[:preview_chars],
        raw_sha256=hashlib.sha256(response.body).hexdigest(),
        page_type=classify_page(response.url, title, parser.headings),
    )


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            output.append(normalized)
    return output


def dedupe_links(links: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        url = link.get("url", "")
        text = normalize_text(link.get("text", ""))
        key = (url, text.casefold())
        if url and key not in seen:
            seen.add(key)
            output.append({"url": url, "text": text})
    return output


def extract_member_candidates(pages: Sequence[PageRecord]) -> list[str]:
    candidates: list[str] = []
    for page in pages:
        if page.page_type not in {"membership", "home"}:
            continue
        for alt in page.image_alts:
            normalized = normalize_text(alt)
            key = normalized.casefold()
            if key in GENERIC_IMAGE_ALTS:
                continue
            if len(normalized) < 2 or normalized.isdigit():
                continue
            candidates.append(normalized)
    return sorted(dedupe_preserve_order(candidates), key=str.casefold)


def extract_working_groups(pages: Sequence[PageRecord]) -> list[dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    for page in pages:
        for link in page.links:
            text = normalize_text(link.get("text", ""))
            key = text.casefold()
            if key in WORKING_GROUP_NAMES:
                groups[key] = {"name": text, "url": link["url"]}
        for heading in page.headings:
            key = heading.casefold()
            if key in WORKING_GROUP_NAMES and key not in groups:
                groups[key] = {"name": heading, "url": page.url}
    return [groups[key] for key in sorted(groups)]


def extract_public_documents(pages: Sequence[PageRecord]) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in pages:
        for link in page.links:
            parsed = urlparse(link["url"])
            host = canonical_host(parsed.hostname or "")
            suffix = Path(parsed.path).suffix.lower()
            is_public_attachment = (
                host == "restservice.epri.com"
                and "/publicattachment/" in parsed.path.lower()
            )
            is_challenge_asset = (
                host == "epri.brightidea.com"
                and parsed.path.lower().startswith("/aiforpower")
            )
            is_interactive_asset = host == "interactive.epri.com"
            is_document = suffix in {".pdf", ".csv", ".json", ".xlsx", ".docx"}
            if not (
                is_public_attachment
                or is_challenge_asset
                or is_interactive_asset
                or is_document
            ):
                continue
            if link["url"] in seen:
                continue
            seen.add(link["url"])
            documents.append(
                {
                    "title": link.get("text", "") or Path(parsed.path).name or host,
                    "url": link["url"],
                    "source_page": page.url,
                }
            )
    return sorted(documents, key=lambda row: (row["title"].casefold(), row["url"]))


def extract_event_mentions(pages: Sequence[PageRecord]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for page in pages:
        if page.page_type not in {"events", "home", "news"} or not page.date_mentions:
            continue
        events.append(
            {
                "source_page": page.url,
                "page_title": page.title,
                "dates": page.date_mentions,
                "headings": page.headings[:20],
            }
        )
    return events


def canonical_json_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_intelligence_payload(
    result: CrawlResult,
    *,
    generated_utc: str | None = None,
    start_url: str = DEFAULT_START_URL,
    allowed_hosts: Sequence[str] = DEFAULT_ALLOWED_HOSTS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, object]:
    generated_utc = generated_utc or datetime.now(timezone.utc).isoformat()
    pages = sorted(result.pages, key=lambda page: page.url)
    members = extract_member_candidates(pages)
    groups = extract_working_groups(pages)
    documents = extract_public_documents(pages)
    events = extract_event_mentions(pages)
    emails = sorted({email for page in pages for email in page.contact_emails})

    stable_core = {
        "schema": "opai_consortium_intelligence_v1",
        "start_url": start_url,
        "allowed_hosts": sorted(set(allowed_hosts)),
        "pages": [asdict(page) for page in pages],
        "errors": [asdict(error) for error in result.errors],
        "skipped_external_urls": sorted(set(result.skipped_external_urls)),
        "skipped_disallowed_urls": sorted(set(result.skipped_disallowed_urls)),
        "member_candidates": members,
        "working_groups": groups,
        "public_documents": documents,
        "event_mentions": events,
        "contact_emails": emails,
    }
    stable_hash = canonical_json_hash(stable_core)

    return {
        "schema": stable_core["schema"],
        "generated_utc": generated_utc,
        "intelligence_hash_sha256": stable_hash,
        "source_policy": {
            "start_url": start_url,
            "allowed_hosts": sorted(set(allowed_hosts)),
            "user_agent": user_agent,
            "read_only": True,
            "forms_submitted": False,
            "authentication_attempted": False,
            "robots_respected": True,
        },
        "summary": {
            "pages_fetched": len(pages),
            "pages_failed": len(result.errors),
            "member_candidates": len(members),
            "working_groups": len(groups),
            "public_documents": len(documents),
            "event_pages": len(events),
            "contact_emails": len(emails),
        },
        "working_groups": groups,
        "member_candidates": members,
        "contact_emails": emails,
        "event_mentions": events,
        "public_documents": documents,
        "pages": [asdict(page) for page in pages],
        "errors": [asdict(error) for error in result.errors],
        "skipped_external_urls": sorted(set(result.skipped_external_urls)),
        "skipped_disallowed_urls": sorted(set(result.skipped_disallowed_urls)),
        "claim_boundary": (
            "This artifact summarizes public website content only. It does not prove consortium "
            "membership, endorsement, private-data access, working-group acceptance, pilot selection, "
            "or external validation. The crawler performs read-only GET requests, respects robots.txt, "
            "never submits forms, and never attempts authentication."
        ),
    }


class HttpFetcher:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 20.0,
        max_bytes: int = 2_000_000,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.opener = build_opener()

    def __call__(self, url: str) -> HttpResponse:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
            },
            method="GET",
        )
        with self.opener.open(request, timeout=self.timeout_seconds) as response:
            body = response.read(self.max_bytes + 1)
            if len(body) > self.max_bytes:
                raise ValueError(f"response exceeds max_bytes={self.max_bytes}")
            headers = {key.lower(): value for key, value in response.headers.items()}
            return HttpResponse(
                url=response.geturl(),
                status=int(getattr(response, "status", 200)),
                content_type=headers.get("content-type", ""),
                body=body,
                headers=headers,
            )


class RobotsGate:
    """Conservative robots gate: 404 means no policy; other fetch failures fail closed."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float = 10.0,
        fetch_bytes: int = 512_000,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.fetch_bytes = fetch_bytes
        self._policies: dict[str, RobotFileParser] = {}
        self._errors: dict[str, str] = {}

    def _load(self, url: str) -> None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._policies or origin in self._errors:
            return

        robots_url = urljoin(origin, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        request = Request(robots_url, headers={"User-Agent": self.user_agent}, method="GET")
        try:
            with build_opener().open(request, timeout=self.timeout_seconds) as response:
                body = response.read(self.fetch_bytes + 1)
                if len(body) > self.fetch_bytes:
                    self._errors[origin] = "robots.txt exceeds safety limit"
                    return
                text = body.decode("utf-8", errors="replace")
                parser.parse(text.splitlines())
                self._policies[origin] = parser
        except HTTPError as exc:
            if exc.code == 404:
                parser.parse([])
                self._policies[origin] = parser
            else:
                self._errors[origin] = f"HTTP {exc.code} fetching robots.txt"
        except (URLError, OSError, ValueError) as exc:
            self._errors[origin] = f"{type(exc).__name__}: {exc}"

    def can_fetch(self, url: str) -> bool:
        self._load(url)
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._errors:
            return False
        policy = self._policies.get(origin)
        return bool(policy and policy.can_fetch(self.user_agent, url))

    def error_for(self, url: str) -> str | None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return self._errors.get(origin)


class CrawlEngine:
    def __init__(
        self,
        *,
        fetcher: Callable[[str], HttpResponse],
        robots_can_fetch: Callable[[str], bool],
        allowed_hosts: Sequence[str] = DEFAULT_ALLOWED_HOSTS,
        max_pages: int = 40,
        delay_seconds: float = 1.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if delay_seconds < 0:
            raise ValueError("delay_seconds cannot be negative")
        self.fetcher = fetcher
        self.robots_can_fetch = robots_can_fetch
        self.allowed_hosts = tuple(allowed_hosts)
        self.max_pages = max_pages
        self.delay_seconds = delay_seconds
        self.sleeper = sleeper

    def crawl(self, start_url: str = DEFAULT_START_URL) -> CrawlResult:
        queue: deque[str] = deque([normalize_url(start_url, start_url)])
        queued: set[str] = set(queue)
        visited: set[str] = set()
        pages: list[PageRecord] = []
        errors: list[CrawlError] = []
        skipped_external: set[str] = set()
        skipped_disallowed: set[str] = set()

        while queue and len(pages) < self.max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if not is_allowed_url(url, self.allowed_hosts):
                skipped_external.add(url)
                continue
            if not self.robots_can_fetch(url):
                skipped_disallowed.add(url)
                continue

            if pages and self.delay_seconds:
                self.sleeper(self.delay_seconds)

            try:
                response = self.fetcher(url)
            except Exception as exc:  # noqa: BLE001 - recorded as bounded crawl evidence.
                errors.append(
                    CrawlError(
                        url=url,
                        stage="fetch",
                        error_type=type(exc).__name__,
                        detail=str(exc)[:500],
                    )
                )
                continue

            if not is_allowed_url(response.url, self.allowed_hosts):
                skipped_external.add(response.url)
                errors.append(
                    CrawlError(
                        url=url,
                        stage="redirect",
                        error_type="ExternalRedirectBlocked",
                        detail=response.url,
                    )
                )
                continue
            if not self.robots_can_fetch(response.url):
                skipped_disallowed.add(response.url)
                continue
            if not looks_like_html(response.content_type, response.url):
                errors.append(
                    CrawlError(
                        url=url,
                        stage="content_type",
                        error_type="NonHtmlSkipped",
                        detail=response.content_type or "unknown content type",
                    )
                )
                continue

            try:
                page = parse_public_page(response)
            except Exception as exc:  # noqa: BLE001 - parser failures are evidence, not fatal.
                errors.append(
                    CrawlError(
                        url=url,
                        stage="parse",
                        error_type=type(exc).__name__,
                        detail=str(exc)[:500],
                    )
                )
                continue

            page.url = url
            page.final_url = response.url
            pages.append(page)

            for link in page.links:
                discovered = link["url"]
                if discovered.lower().startswith("mailto:"):
                    continue
                if not is_allowed_url(discovered, self.allowed_hosts):
                    skipped_external.add(discovered)
                    continue
                if discovered not in visited and discovered not in queued:
                    queued.add(discovered)
                    queue.append(discovered)

        return CrawlResult(
            pages=pages,
            errors=errors,
            skipped_external_urls=sorted(skipped_external),
            skipped_disallowed_urls=sorted(skipped_disallowed),
        )


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a public-safe Open Power AI Consortium intelligence asset. "
            "The crawler is read-only, same-origin allowlisted, robots-aware, and never submits forms."
        )
    )
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dashboard-out", type=Path, default=DEFAULT_DASHBOARD_OUT)
    parser.add_argument("--no-dashboard", action="store_true")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--allow-host",
        action="append",
        dest="allowed_hosts",
        default=list(DEFAULT_ALLOWED_HOSTS),
        help="Additional exact host to allow. May be repeated.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    allowed_hosts = tuple(sorted({canonical_host(host) for host in args.allowed_hosts}))
    fetcher = HttpFetcher(
        user_agent=args.user_agent,
        timeout_seconds=args.timeout_seconds,
        max_bytes=args.max_bytes,
    )
    robots = RobotsGate(
        user_agent=args.user_agent,
        timeout_seconds=min(args.timeout_seconds, 10.0),
    )
    engine = CrawlEngine(
        fetcher=fetcher,
        robots_can_fetch=robots.can_fetch,
        allowed_hosts=allowed_hosts,
        max_pages=args.max_pages,
        delay_seconds=args.delay_seconds,
    )
    result = engine.crawl(args.start_url)
    payload = build_intelligence_payload(
        result,
        start_url=args.start_url,
        allowed_hosts=allowed_hosts,
        user_agent=args.user_agent,
    )
    write_json(args.out, payload)
    if not args.no_dashboard:
        write_json(args.dashboard_out, payload)

    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "pages_fetched": payload["summary"]["pages_fetched"],
                "pages_failed": payload["summary"]["pages_failed"],
                "member_candidates": payload["summary"]["member_candidates"],
                "working_groups": payload["summary"]["working_groups"],
                "intelligence_hash_sha256": payload["intelligence_hash_sha256"],
                "out": str(args.out),
                "dashboard_out": None if args.no_dashboard else str(args.dashboard_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["summary"]["pages_fetched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
