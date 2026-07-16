#!/usr/bin/env python3
"""Build a bounded public-intelligence snapshot of the Open Power AI Consortium.

The collector is intentionally read-only. It crawls only public, allow-listed pages,
checks robots.txt, rate-limits requests, hashes source pages, and never submits forms,
logs in, bypasses access controls, or collects private member data.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from typing import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

SCHEMA = "lumencore.opai_public_intelligence.v1"
DEFAULT_BASE_URL = "https://openpowerai.org/"
DEFAULT_SEEDS = (
    "https://openpowerai.org/",
    "https://openpowerai.org/about",
    "https://openpowerai.org/consortium-membership",
    "https://openpowerai.org/group-materials-and-meetings",
    "https://openpowerai.org/events",
    "https://openpowerai.org/research-and-results",
    "https://openpowerai.org/news-and-newsletters",
)
DEFAULT_USER_AGENT = (
    "LumenCore-OPAI-PublicIntelligence/1.0 "
    "(+https://lumen-core.ai; contact=robertashworth4444@gmail.com)"
)
PUBLIC_BOUNDARY = (
    "Public, read-only consortium intelligence. No authentication, form submission, "
    "access-control bypass, private member data collection, credential use, or automated outreach."
)

DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2}(?:\s*-\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+)?\d{1,2})?,\s+\d{4}\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")

GENERIC_IMAGE_ALT = {
    "image",
    "op ai",
    "facebook",
    "twitter",
    "linkedin",
    "youtube",
    "work group image",
    "datasets visualization",
    "3 color nodes expanding",
    "turbine inspection",
    "worker looking at monitors",
    "data-sharing-main-lock",
}

KNOWN_WORK_GROUPS = (
    "Member Representative Committee",
    "Domain-Specific Model Work Group",
    "Use Case Work Group",
    "Implementation Work Group",
    "Data Sharing Work Group",
)


@dataclass(frozen=True)
class Block:
    tag: str
    text: str


@dataclass
class ParsedPage:
    url: str
    title: str = ""
    blocks: list[Block] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    image_alts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks if block.text)


@dataclass(frozen=True)
class FetchedDocument:
    url: str
    body: bytes
    content_type: str = "text/html"
    status: int = 200


class PublicPageParser(HTMLParser):
    """Extract visible ordered blocks, links, image alt text, and title."""

    BLOCK_TAGS = {
        "title",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "td",
        "th",
        "figcaption",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page = ParsedPage(url=page_url)
        self._skip_depth = 0
        self._active_tag: str | None = None
        self._active_parts: list[str] = []
        self._active_link: dict[str, str] | None = None
        self._link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._flush_block()
            self._active_tag = tag
            self._active_parts = []
        if tag == "a":
            self._active_link = {"href": attr_map.get("href", "")}
            self._link_parts = []
        if tag == "img":
            alt = normalize_text(attr_map.get("alt", ""))
            if alt:
                self.page.image_alts.append(alt)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "a" and self._active_link is not None:
            text = normalize_text(" ".join(self._link_parts))
            href = self._active_link.get("href", "")
            if href:
                self.page.links.append({"text": text, "href": href})
            self._active_link = None
            self._link_parts = []
        if tag == self._active_tag:
            self._flush_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._active_tag is not None:
            self._active_parts.append(data)
        if self._active_link is not None:
            self._link_parts.append(data)

    def close(self) -> None:
        self._flush_block()
        super().close()

    def _flush_block(self) -> None:
        if self._active_tag is None:
            return
        text = normalize_text(" ".join(self._active_parts))
        if text:
            if self._active_tag == "title":
                self.page.title = text
            else:
                self.page.blocks.append(Block(self._active_tag, text))
        self._active_tag = None
        self._active_parts = []


def normalize_text(value: str) -> str:
    return SPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def canonical_url(url: str) -> str:
    clean, _fragment = urldefrag(url.strip())
    parsed = urlparse(clean)
    scheme = parsed.scheme.lower() or "https"
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(scheme=scheme, netloc=host, path=path, fragment="").geturl()


def is_public_crawl_url(url: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    parsed = urlparse(url)
    base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != base.netloc.lower():
        return False
    lowered_path = parsed.path.lower()
    sensitive_segment = re.search(
        r"(?:^|[-_/])(login|signin|account|admin|user|form)(?:$|[-_/])",
        lowered_path,
    )
    return sensitive_segment is None


def parse_html(document: FetchedDocument) -> ParsedPage:
    parser = PublicPageParser(document.url)
    parser.feed(document.body.decode("utf-8", errors="replace"))
    parser.close()
    normalized_links: list[dict[str, str]] = []
    for link in parser.page.links:
        href = canonical_url(urljoin(document.url, link["href"]))
        normalized_links.append({"text": normalize_text(link["text"]), "href": href})
    parser.page.links = normalized_links
    return parser.page


def clean_organization_name(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\s+logo\s*$", "", value, flags=re.IGNORECASE)
    return value.strip(" -|:")


def extract_organizations(page: ParsedPage) -> list[str]:
    if "consortium-membership" not in urlparse(page.url).path:
        return []
    names: set[str] = set()
    for alt in page.image_alts:
        name = clean_organization_name(alt)
        lowered = name.lower()
        if not name or lowered in GENERIC_IMAGE_ALT:
            continue
        if lowered.startswith("image:"):
            name = clean_organization_name(name.split(":", 1)[1])
            lowered = name.lower()
        if not name or lowered in GENERIC_IMAGE_ALT or len(name) > 140:
            continue
        names.add(name)
    return sorted(names, key=str.casefold)


def _find_block_index(page: ParsedPage, text: str) -> int | None:
    needle = normalize_text(text).casefold()
    for index, block in enumerate(page.blocks):
        if block.text.casefold() == needle:
            return index
    return None


def extract_work_groups(page: ParsedPage) -> list[dict[str, str]]:
    if "group-materials-and-meetings" not in urlparse(page.url).path:
        return []
    results: list[dict[str, str]] = []
    for name in KNOWN_WORK_GROUPS:
        start = _find_block_index(page, name)
        if start is None:
            continue
        lead = ""
        description_parts: list[str] = []
        for block in page.blocks[start + 1 : start + 15]:
            if block.tag.startswith("h") and block.text in KNOWN_WORK_GROUPS:
                break
            if block.text.lower().startswith("lead:"):
                lead = normalize_text(block.text.split(":", 1)[1])
                break
            if block.tag in {"p", "li"} and not block.text.lower().startswith("see more"):
                description_parts.append(block.text)
        results.append(
            {
                "name": name,
                "lead": lead,
                "description": normalize_text(" ".join(description_parts))[:1200],
            }
        )
    return results


def _previous_heading(blocks: Sequence[Block], index: int) -> str:
    for block in reversed(blocks[:index]):
        if block.tag.startswith("h"):
            return block.text
    return ""


def extract_events(page: ParsedPage) -> list[dict[str, str]]:
    if urlparse(page.url).path.rstrip("/") != "/events":
        return []
    events: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, block in enumerate(page.blocks):
        match = DATE_RE.search(block.text)
        if not match:
            continue
        title = _previous_heading(page.blocks, index)
        date_text = match.group(0)
        key = (title.casefold(), date_text.casefold())
        if not title or key in seen:
            continue
        seen.add(key)
        description = ""
        if index + 1 < len(page.blocks) and page.blocks[index + 1].tag == "p":
            description = page.blocks[index + 1].text
        events.append({"title": title, "date": date_text, "description": description})
    return events


def _section_bounds(page: ParsedPage, heading: str) -> tuple[int, int] | None:
    start = _find_block_index(page, heading)
    if start is None:
        return None
    start_level = int(page.blocks[start].tag[1]) if page.blocks[start].tag.startswith("h") else 2
    end = len(page.blocks)
    for index in range(start + 1, len(page.blocks)):
        block = page.blocks[index]
        if block.tag.startswith("h") and int(block.tag[1]) <= start_level:
            end = index
            break
    return start + 1, end


def extract_models(page: ParsedPage) -> list[dict[str, str]]:
    if "research-and-results" not in urlparse(page.url).path:
        return []
    bounds = _section_bounds(page, "Models")
    if bounds is None:
        return []
    start, end = bounds
    blocks = page.blocks[start:end]
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for index in range(len(blocks) - 1):
        name = blocks[index].text
        detail = blocks[index + 1].text
        if not detail.lower().startswith("type:"):
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        results.append({"name": name, "type_and_description": detail[5:].strip()})
    return results


def extract_datasets(page: ParsedPage) -> list[dict[str, str]]:
    if "research-and-results" not in urlparse(page.url).path:
        return []
    bounds = _section_bounds(page, "Datasets")
    if bounds is None:
        return []
    start, end = bounds
    blocks = page.blocks[start:end]
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for index in range(len(blocks) - 1):
        name = blocks[index].text
        source_line = blocks[index + 1].text
        if not source_line.lower().startswith("source:"):
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        description = ""
        if index + 2 < len(blocks) and not blocks[index + 2].text.lower().startswith("source:"):
            description = blocks[index + 2].text
        results.append(
            {
                "name": name,
                "source_and_license": source_line[7:].strip(),
                "description": description,
            }
        )
    return results


def extract_documents(pages: Iterable[ParsedPage]) -> list[dict[str, str]]:
    documents: dict[str, dict[str, str]] = {}
    for page in pages:
        for link in page.links:
            href = link["href"]
            parsed = urlparse(href)
            if parsed.path.lower().endswith(".pdf") or (
                parsed.netloc.lower() == "restservice.epri.com"
                and "/publicattachment/" in parsed.path.lower()
            ):
                documents[href] = {
                    "title": link["text"] or Path(parsed.path).name,
                    "url": href,
                    "discovered_on": page.url,
                }
    return sorted(documents.values(), key=lambda row: (row["title"].casefold(), row["url"]))


def extract_contacts(pages: Iterable[ParsedPage]) -> list[str]:
    contacts: set[str] = set()
    for page in pages:
        contacts.update(match.lower() for match in EMAIL_RE.findall(page.text))
        for link in page.links:
            href = link["href"]
            if href.lower().startswith("mailto:"):
                contacts.add(href.split(":", 1)[1].split("?", 1)[0].lower())
    return sorted(contacts)


def build_snapshot_from_documents(
    documents: Sequence[FetchedDocument],
    *,
    base_url: str = DEFAULT_BASE_URL,
    generated_utc: str | None = None,
    robots_status: str = "not_applicable_fixture",
    errors: Sequence[Mapping[str, str]] = (),
) -> dict:
    parsed_pages = [parse_html(document) for document in documents]
    page_rows: list[dict[str, object]] = []
    organizations: set[str] = set()
    work_groups: dict[str, dict[str, str]] = {}
    events: dict[tuple[str, str], dict[str, str]] = {}
    models: dict[str, dict[str, str]] = {}
    datasets: dict[str, dict[str, str]] = {}

    for document, page in zip(documents, parsed_pages, strict=True):
        page_rows.append(
            {
                "url": page.url,
                "title": page.title,
                "content_type": document.content_type,
                "status": document.status,
                "source_sha256": sha256(document.body).hexdigest(),
                "headings": [block.text for block in page.blocks if block.tag.startswith("h")],
                "link_count": len(page.links),
                "image_alt_count": len(page.image_alts),
            }
        )
        organizations.update(extract_organizations(page))
        for row in extract_work_groups(page):
            work_groups[row["name"]] = row
        for row in extract_events(page):
            events[(row["title"], row["date"])] = row
        for row in extract_models(page):
            models[row["name"]] = row
        for row in extract_datasets(page):
            datasets[row["name"]] = row

    stable = {
        "schema": SCHEMA,
        "source": {
            "base_url": canonical_url(base_url),
            "robots_status": robots_status,
            "boundary": PUBLIC_BOUNDARY,
        },
        "pages": sorted(page_rows, key=lambda row: str(row["url"])),
        "organizations": sorted(organizations, key=str.casefold),
        "work_groups": sorted(work_groups.values(), key=lambda row: row["name"].casefold()),
        "events": sorted(events.values(), key=lambda row: (row["date"], row["title"].casefold())),
        "models": sorted(models.values(), key=lambda row: row["name"].casefold()),
        "datasets": sorted(datasets.values(), key=lambda row: row["name"].casefold()),
        "documents": extract_documents(parsed_pages),
        "official_contacts": extract_contacts(parsed_pages),
        "errors": [dict(error) for error in errors],
    }
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot = {
        **stable,
        "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256(canonical).hexdigest(),
    }
    return snapshot


class NetworkCollector:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 25.0,
        delay_seconds: float = 1.0,
        max_bytes: int = 8_000_000,
        allow_on_robots_error: bool = False,
        opener: Callable[..., object] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = canonical_url(base_url)
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay_seconds = max(0.0, delay_seconds)
        self.max_bytes = max_bytes
        self.allow_on_robots_error = allow_on_robots_error
        self.opener = opener
        self.sleeper = sleeper
        self._last_request_at: float | None = None
        self.robots = RobotFileParser()
        self.robots_status = "unchecked"

    def _request(self, url: str) -> FetchedDocument:
        if self._last_request_at is not None and self.delay_seconds:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.delay_seconds:
                self.sleeper(self.delay_seconds - elapsed)
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response = self.opener(request, timeout=self.timeout)
        self._last_request_at = time.monotonic()
        status = int(getattr(response, "status", 200))
        headers = getattr(response, "headers", {})
        content_type = "text/html"
        if hasattr(headers, "get_content_type"):
            content_type = headers.get_content_type()
        elif hasattr(headers, "get"):
            content_type = str(headers.get("Content-Type", "text/html")).split(";", 1)[0]
        body = response.read(self.max_bytes + 1)
        if hasattr(response, "close"):
            response.close()
        if len(body) > self.max_bytes:
            raise ValueError(f"response exceeds max_bytes={self.max_bytes}: {url}")
        return FetchedDocument(
            url=canonical_url(url),
            body=body,
            content_type=content_type,
            status=status,
        )

    def load_robots(self) -> None:
        robots_url = urljoin(self.base_url + "/", "robots.txt")
        try:
            document = self._request(robots_url)
            lines = document.body.decode("utf-8", errors="replace").splitlines()
            self.robots.set_url(robots_url)
            self.robots.parse(lines)
            self.robots_status = "enforced"
        except Exception as exc:
            self.robots_status = f"unavailable:{type(exc).__name__}"
            if not self.allow_on_robots_error:
                raise RuntimeError(
                    "robots.txt could not be checked; rerun only after review with "
                    "--allow-on-robots-error"
                ) from exc

    def allowed(self, url: str) -> bool:
        if not is_public_crawl_url(url, self.base_url):
            return False
        if self.robots_status == "enforced":
            return self.robots.can_fetch(self.user_agent, url)
        return self.allow_on_robots_error

    def crawl(
        self,
        seeds: Sequence[str],
        max_pages: int = 40,
    ) -> tuple[list[FetchedDocument], list[dict[str, str]]]:
        self.load_robots()
        queue = [canonical_url(urljoin(self.base_url + "/", seed)) for seed in seeds]
        seen: set[str] = set()
        documents: list[FetchedDocument] = []
        errors: list[dict[str, str]] = []

        while queue and len(documents) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if not self.allowed(url):
                errors.append({"url": url, "error": "blocked_by_scope_or_robots"})
                continue
            try:
                document = self._request(url)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
                continue
            if "html" not in document.content_type.lower():
                continue
            documents.append(document)
            page = parse_html(document)
            for link in page.links:
                candidate = link["href"]
                if candidate not in seen and self.allowed(candidate):
                    queue.append(candidate)

        return documents, errors


def write_snapshot(path: Path, snapshot: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--seed", action="append", dest="seeds")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--allow-on-robots-error", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/opai/opai_public_intelligence.json"),
    )
    args = parser.parse_args()

    seeds = tuple(args.seeds or DEFAULT_SEEDS)
    collector = NetworkCollector(
        base_url=args.base_url,
        timeout=args.timeout,
        delay_seconds=args.delay_seconds,
        allow_on_robots_error=args.allow_on_robots_error,
    )
    documents, errors = collector.crawl(seeds, max_pages=args.max_pages)
    snapshot = build_snapshot_from_documents(
        documents,
        base_url=args.base_url,
        robots_status=collector.robots_status,
        errors=errors,
    )
    write_snapshot(args.output, snapshot)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "pages": len(snapshot["pages"]),
                "organizations": len(snapshot["organizations"]),
                "models": len(snapshot["models"]),
                "datasets": len(snapshot["datasets"]),
                "manifest_sha256": snapshot["manifest_sha256"],
                "boundary": snapshot["source"]["boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
