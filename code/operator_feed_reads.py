"""Bounded, read-only private artifact observations; never start a producer.

These routes are NOT public products. A successful artifact read proves neither
live execution authority nor independent validation of a research result.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Mapping

FEEDS = ("live_status", "federal_brief", "evidence_summary", "executor_heartbeat")
MAX_BYTES = 1024 * 1024
MAX_RUNS = 1000
HEARTBEAT_STATES = frozenset({"blocked", "critical", "degraded", "dry_run", "error", "ok", "pending", "recovering", "running"})
RUN_ID = re.compile(r"\d{8}T\d{6}Z\Z")
ENV_PREFIX = "LUMA_PRIVATE_FEED_MAX_AGE_SECONDS_"


class Unavailable(Exception):
    """A public-safe reason code, never a path or exception message."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Unavailable("invalid_json")
        result[key] = value
    return result


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise Unavailable("invalid_json")
    return result


def _constant(value):
    raise Unavailable("invalid_json")


class ArtifactReader:
    """Open every path component with NOFOLLOW, including the configured root.

    Linux descriptor-relative reads avoid check/open symlink races. Unsupported
    platforms fail closed rather than fall back to less safe path traversal.
    """

    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    def _directory(self, relative: str = "") -> int:
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise Unavailable("filesystem_unsupported")
        pieces = (*self.root.parts[1:], *PurePosixPath(relative).parts)
        if any(p in {".", ".."} for p in pieces):
            raise Unavailable("unsafe_source")
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for piece in pieces:
                nxt = os.open(piece, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            return fd
        except BaseException:
            os.close(fd)
            raise

    def raw(self, relative: str) -> bytes:
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or not path.name:
            raise Unavailable("unsafe_source")
        directory = self._directory(str(path.parent) if str(path.parent) != "." else "")
        fd = None
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise Unavailable("unsafe_source")
            if info.st_size > MAX_BYTES:
                raise Unavailable("source_oversized")
            with os.fdopen(fd, "rb") as stream:
                fd = None
                body = stream.read(MAX_BYTES + 1)
                after = os.fstat(stream.fileno())
                if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise Unavailable("source_changed_during_read")
            if len(body) > MAX_BYTES:
                raise Unavailable("source_oversized")
            return body
        finally:
            if fd is not None:
                os.close(fd)
            os.close(directory)

    def object(self, relative: str):
        body = self.raw(relative)
        try:
            value = json.loads(body, object_pairs_hook=_pairs, parse_float=_float, parse_constant=_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise Unavailable("invalid_json") from None
        if not isinstance(value, dict):
            raise Unavailable("invalid_schema")
        return value, hashlib.sha256(body).hexdigest()

    def latest_run(self) -> str:
        fd = self._directory("dashboard/evidence/runs")
        try:
            # scandir is bounded; do not materialize an unbounded directory.
            names = []
            with os.scandir(fd) as entries:
                for index, entry in enumerate(entries):
                    if index >= MAX_RUNS:
                        raise Unavailable("source_inventory_oversized")
                    if RUN_ID.fullmatch(entry.name):
                        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                            raise Unavailable("unsafe_source")
                        names.append(entry.name)
            if not names:
                raise Unavailable("source_missing")
            return max(names)
        finally:
            os.close(fd)


def _stamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise Unavailable("source_timestamp_missing")
    try:
        if RUN_ID.fullmatch(value):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise Unavailable("source_timestamp_invalid") from None


def _fresh(value: object, now: datetime, budget: float) -> str:
    stamp = _stamp(value)
    age = (now - stamp).total_seconds()
    if age < 0:
        raise Unavailable("source_timestamp_future")
    if age > budget:
        raise Unavailable("source_stale")
    return stamp.isoformat().replace("+00:00", "Z")


def observe(feed: str, root: Path, *, environ: Mapping[str, str] | None = None,
            now: datetime | None = None) -> tuple[int, dict]:
    if feed not in FEEDS:
        raise ValueError("unknown feed")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("aware observation time required")
    result = {
        "schema": "lumencore_private_feed_observation.v1", "feed": feed,
        "access_boundary": "operator_api_v1", "observed_at": current.isoformat(),
        "data_available": False, "freshness": "unknown", "source_timestamp": None,
        "source_sha256": None, "max_age_seconds": None, "data": None,
        "freshness_basis": {"executor_heartbeat": "heartbeat_emission_time",
                            "evidence_summary": "research_run_generation_time"}.get(feed),
        "claim_boundary": "Private artifact observation only; not live execution authority, public feed restoration, or independent validation.",
    }
    try:
        if feed == "live_status":
            raise Unavailable("producer_unmapped")
        source_env = os.environ if environ is None else environ
        raw_budget = source_env.get(ENV_PREFIX + feed.upper(), "")
        try:
            budget = float(raw_budget)
        except (ValueError, TypeError):
            raise Unavailable("freshness_unconfigured") from None
        if not math.isfinite(budget) or budget <= 0:
            raise Unavailable("freshness_unconfigured")
        result["max_age_seconds"] = budget
        reader = ArtifactReader(root)
        if feed == "executor_heartbeat":
            value, digest = reader.object("out/execution/live_executor_heartbeat.json")
            state = value.get("status")
            if value.get("schema_version") != "1.0.0" or not isinstance(state, str) or state not in HEARTBEAT_STATES:
                raise Unavailable("invalid_schema")
            stamp = _fresh(value.get("timestamp_utc"), current, budget)
            data = {"schema_version": "1.0.0", "status": state, "timestamp_utc": stamp}
        elif feed == "evidence_summary":
            run = reader.latest_run()
            prefix = "dashboard/evidence/runs/" + run + "/"
            value, digest = reader.object(prefix + "summary.json")
            manifest, _ = reader.object(prefix + "manifest.sha256.json")
            if value.get("run_utc") != run or manifest.get("run_utc") != run:
                raise Unavailable("provenance_mismatch")
            if not isinstance(manifest.get("files"), dict) or manifest["files"].get("summary.json") != digest:
                raise Unavailable("provenance_mismatch")
            stamp = _fresh(run, current, budget)
            data = {"run_utc": run, "evidence_type": "retained_research_run"}
            for key in ("n_datasets_succeeded", "n_datasets_in_universe"):
                count = value.get(key)
                if type(count) is not int or count < 0:
                    raise Unavailable("invalid_schema")
                data[key] = count
            if data["n_datasets_succeeded"] > data["n_datasets_in_universe"]:
                raise Unavailable("invalid_schema")
        else:
            value, digest = reader.object("out/federal_brief.json")
            _fresh(value.get("generated_utc"), current, budget)
            # The current builder emits no binding to upstream source bytes or
            # their observation times. A fresh output is not fresh input data.
            # Do not invent a manifest contract or bless zero-filled defaults.
            raise Unavailable("source_provenance_unverified")
        result.update(data_available=True, freshness="fresh", source_timestamp=stamp,
                      source_sha256=digest, data=data, disposition="verified_artifact")
        return 200, result
    except Unavailable as exc:
        result["disposition"] = str(exc)
    except FileNotFoundError:
        result["disposition"] = "source_missing"
    except (OSError, RuntimeError):
        result["disposition"] = "source_unreadable_or_unsafe"
    return 503, result


def install_private_feed_routes(app, root: Path) -> None:
    """Install only on the operator app, behind existing outer middleware."""
    from fastapi.responses import JSONResponse

    if getattr(app, "_luma_private_feed_routes_installed", False):
        return

    def make_handler(feed):
        def handler():
            status, payload = observe(feed, root)
            return JSONResponse(payload, status_code=status, headers={"Cache-Control": "no-store"})
        return handler

    for feed in FEEDS:
        path = "/api/" + feed + ".json"
        if any(getattr(route, "path", None) == path for route in app.routes):
            raise RuntimeError("private feed route already registered")
        app.add_api_route(path, make_handler(feed), methods=["GET"], include_in_schema=False)
        # Preserve existing middleware and mount semantics; ahead of catch-all.
        app.router.routes.insert(0, app.router.routes.pop())

    app._luma_private_feed_routes_installed = True
