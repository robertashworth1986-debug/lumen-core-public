#!/usr/bin/env python3
"""One approved Nginx MIME correction; stdlib only, no shell/config dump output.

Run inspect first, then apply with its observed original SHA-256. The deployment
workflow must also hold its lumencore-production-site concurrency group. This
helper changes only four bytes (' mjs') in the uniquely inherited MIME table.
All three immutable release objects must pass disk/local-TLS/public-HTTPS checks.
No DNS, TLS keys, routes, credentials, other services, or static bytes are edited.
The advisory lock and immediate pre-replace identity check cannot exclude a
noncooperating root writer in the final check/rename interval. Other Nginx writers
must be quiescent for this bounded transaction; no kernel compare-and-swap exists.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fnmatch
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import socket
import ssl
import stat
import subprocess
import tempfile
import time
import uuid

DOMAIN = "lumen-core.ai"
CONFIG_ROOT = Path("/etc/nginx")
STATIC_ROOT = Path("/opt/lumencore/dashboard")
ROLLBACK_ROOT = Path("/var/backups/lumencore-public-mime")
LOCK = Path("/run/lock/lumencore-production-site-mime.lock")
EXPECTED = {
    "bounded-light/observatory/geometry.mjs": "645f826e9e31ba3c3f49edd63bb7b63eee8ab5f5af1593bad3b23ff426d70d1b",
    "portfolio/math-models.mjs": "a08c96232c0fe6c246fae33c68835149d5febcb3d00d35ca4add45119b336d9b",
    "portfolio/portfolio-model.mjs": "1952beb45c5526fe56a226ae256baccbaadf7f7781b864e7e73fec2396db11c8",
}
JS_TYPES = {"application/javascript", "text/javascript"}
RELOAD_PROBE_MAX_ATTEMPTS = 5
RELOAD_PROBE_MAX_SECONDS = 5.0
RELOAD_PROBE_INTERVAL_SECONDS = 0.25


class RepairError(ValueError):
    """Only fixed redacted error codes are raised."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def propose(raw):
    """Prior reviewed proposal logic: preserve every byte except inserted mjs."""
    if len(raw) > 1_000_000 or b"\x00" in raw:
        raise RepairError("unsupported_mime_bytes")
    try:
        raw.decode("utf-8")
    except UnicodeError:
        raise RepairError("unsupported_mime_encoding") from None
    clean = re.sub(rb"#[^\r\n]*", lambda m: b" " * len(m[0]), raw)
    table = re.fullmatch(rb"\s*types\s*\{(?P<body>[^{}]*)\}\s*", clean)
    if table is None:
        raise RepairError("not_standalone_types_table")
    declarations, end = [], 0
    for row in re.finditer(rb"(?P<mime>[^\s;{}]+)\s+(?P<extensions>[^;{}]+);", table["body"]):
        if table["body"][end:row.start()].strip():
            raise RepairError("unsupported_types_syntax")
        mime, extensions = row["mime"], row["extensions"].split()
        if b"/" not in mime or not extensions or any(not re.fullmatch(rb"[A-Za-z0-9_.+-]+", x) for x in extensions):
            raise RepairError("unsupported_types_declaration")
        declarations.append((row, mime, extensions))
        end = row.end()
    if table["body"][end:].strip():
        raise RepairError("unterminated_types_declaration")
    js = [x for x in declarations if b"js" in x[2]]
    if len(js) != 1 or js[0][1].decode() not in JS_TYPES:
        raise RepairError("ambiguous_or_unsupported_js_mapping")
    mjs = [x for x in declarations if b"mjs" in x[2]]
    if mjs:
        if len(mjs) == 1 and mjs[0] == js[0]:
            return raw, "ALREADY_MAPPED"
        raise RepairError("conflicting_mjs_mapping")
    insertion = table.start("body") + js[0][0].end() - 1
    return raw[:insertion] + b" mjs" + raw[insertion:], "CANDIDATE"


def tokenize(content):
    # Quoted values are preserved as single tokens; escapes remain literal.
    token = re.compile(r'''\s+|\#[^\r\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{};]|(?:\\.|[^\s{};#"'])+''')
    tokens, end = [], 0
    for match in token.finditer(content):
        if match.start() != end:
            raise RepairError("unsupported_nginx_syntax")
        end = match.end()
        value = match[0]
        if value.isspace() or value.startswith("#"):
            continue
        tokens.append(value[1:-1] if value[0] in "\"'" else value)
    if end != len(content):
        raise RepairError("unsupported_nginx_syntax")
    return tokens


def parse(content, source):
    tokens = tokenize(content)
    def block(index, nested=False):
        nodes, args = [], []
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token == "}":
                if args or not nested:
                    raise RepairError("unbalanced_nginx_block")
                return nodes, index
            if token in {";", "{"}:
                if not args:
                    raise RepairError("empty_nginx_directive")
                children = None
                if token == "{":
                    children, index = block(index, True)
                nodes.append({"args": args, "children": children, "source": source})
                args = []
            else:
                args.append(token)
        if nested or args:
            raise RepairError("unbalanced_nginx_block")
        return nodes, index
    return block(0)[0]


def location_matches(args, uri):
    """Match one top-level selector, without flattening nested Nginx rules."""
    if len(args) == 1 and args[0].startswith("@"):
        return False
    if len(args) == 1 and args[0].startswith("/"):
        return uri.startswith(args[0])
    if len(args) == 2 and args[0] in {"=", "^~"}:
        return uri == args[1] if args[0] == "=" else uri.startswith(args[1])
    if len(args) == 2 and args[0] in {"~", "~*"}:
        try:
            return re.search(args[1], uri, re.I if args[0] == "~*" else 0) is not None
        except re.error:
            raise RepairError("unsupported_location_regex") from None
    raise RepairError("unsupported_location_selector")


def bounded_route_facts(http_nodes, server):
    """Report only static-route decisions; unknown tokens are hash-only."""
    public_uris = ["/" + path for path in EXPECTED]
    safe_tokens = {"/", "/portfolio", "/portfolio/", "/bounded-light", "/bounded-light/",
                   "/bounded-light/observatory/", "$uri", "$uri/", "=404", "@gateway_fallback",
                   *public_uris}
    # Exact public static suffix patterns are useful; arbitrary regex text is not.
    safe_patterns = {r"\.mjs$", r"\.(js|mjs|css)$", r"\.(js|css)$"}
    def token_fact(value):
        if value in safe_tokens or value in safe_patterns:
            return {"value": value}
        return {"redacted": True, "sha256": digest(value.encode())}
    def directives(nodes):
        facts = []
        for node in nodes:
            kind, *args = node["args"]
            if kind == "root":
                facts.append({"kind": kind, "known_static_root": args == [STATIC_ROOT.as_posix()]})
            elif kind == "try_files":
                facts.append({"kind": kind, "tokens": [token_fact(value) for value in args[:8]], "token_count": len(args)})
            elif kind in {"types", "proxy_pass", "fastcgi_pass", "uwsgi_pass", "scgi_pass", "grpc_pass",
                          "alias", "rewrite", "return", "if", "error_page", "content_by_lua", "content_by_lua_block",
                          "content_by_lua_file", "js_content", "perl", "empty_gif", "mp4", "flv"}:
                facts.append({"kind": kind})
            if len(facts) >= 24:
                break
        return facts
    result = {"schema": "lumencore.public_mime_route_diagnostic.v1", "approved_uris": public_uris,
              "http": directives(http_nodes), "public_tls_server": directives(server), "locations": [],
              "truncated": False, "diagnostic_only": True}
    def visit(nodes, parent=None, depth=0, ancestor_uris=None):
        if ancestor_uris is None:
            ancestor_uris = public_uris
        for node in nodes:
            if node["args"][0] != "location":
                continue
            if depth > 6 or len(result["locations"]) >= 64:
                result["truncated"] = True
                return
            args = node["args"][1:]
            kind = args[0] if len(args) == 2 and args[0] in {"=", "^~", "~", "~*"} else "named" if len(args) == 1 and args[0].startswith("@") else "prefix" if len(args) == 1 and args[0].startswith("/") else "unsupported"
            row = {"id": len(result["locations"]), "parent_id": parent, "depth": depth,
                   "selector_kind": kind, "selector": token_fact(args[-1]) if args else {"redacted": True},
                   "directives": directives(node["children"] or []), "selector_matches_approved_uris": []}
            source = node["source"]
            if len(source) <= 256 and re.fullmatch(r"/etc/nginx/[A-Za-z0-9_./-]+", source) and ".." not in PurePosixPath(source).parts:
                row["source_file"] = source
            for uri in public_uris:
                try:
                    if location_matches(args, uri):
                        row["selector_matches_approved_uris"].append(uri)
                except RepairError:
                    row["selector_unresolved"] = True
            row["candidate_uris_with_ancestors"] = [uri for uri in row["selector_matches_approved_uris"] if uri in ancestor_uris]
            result["locations"].append(row)
            visit(node["children"] or [], row["id"], depth + 1, row["candidate_uris_with_ancestors"])
    visit(server)
    while len(json.dumps(result).encode()) > 65536 and result["locations"]:
        result["locations"].pop()
        result["truncated"] = True
    return result


def discover(dump, *, verified_static_sha256=None):
    diagnostics = {}
    try:
        return discover_static_table(dump, diagnostics, verified_static_sha256 == EXPECTED)
    except RepairError as error:
        error.route_diagnostics = diagnostics
        raise


def discover_static_table(dump, diagnostics, static_files_verified=False):
    """Resolve only dump-listed includes and prove these three paths inherit it."""
    if len(dump.encode()) > 2_000_000:
        raise RepairError("configuration_size_limit")
    chunks = re.split(r"^# configuration file (.+):\s*$", dump, flags=re.M)
    sections = {}
    for index in range(1, len(chunks), 2):
        name = chunks[index]
        if name in sections or not PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise RepairError("ambiguous_dump_sections")
        sections[name] = chunks[index + 1]
    if not sections:
        raise RepairError("missing_active_configuration")
    candidates = []
    for name, content in sections.items():
        if not name.startswith("/etc/nginx/"):
            continue
        try:
            candidate, status = propose(content.encode())
            candidates.append(name)
        except RepairError as error:
            if str(error) in {"conflicting_mjs_mapping", "ambiguous_or_unsupported_js_mapping"}:
                raise
    if len(candidates) != 1:
        raise RepairError("expected_one_active_mime_table")
    target = candidates[0]
    def expand(name, stack=()):
        if name in stack or len(stack) > 20:
            raise RepairError("include_cycle_or_depth")
        def walk(nodes):
            result = []
            for node in nodes:
                if node["args"][0] == "include":
                    if len(node["args"]) != 2:
                        raise RepairError("unsupported_include")
                    pattern = node["args"][1]
                    if not pattern.startswith("/"):
                        pattern = "/etc/nginx/" + pattern
                    matches = sorted(x for x in sections if fnmatch.fnmatchcase(x, pattern))
                    if not matches and not any(c in pattern for c in "*?["):
                        raise RepairError("include_missing_from_dump")
                    for match in matches:
                        result.extend(expand(match, stack + (name,)))
                else:
                    result.append({**node, "children": walk(node["children"]) if node["children"] is not None else None})
            return result
        return walk(parse(sections[name], name))
    main = expand(next(iter(sections)))
    http = [x for x in main if x["args"] == ["http"]]
    if len(http) != 1:
        raise RepairError("unsupported_http_context")
    http_nodes = http[0]["children"]
    servers = []
    for node in http_nodes:
        if node["args"] != ["server"] or node["children"] is None:
            continue
        names = [x["args"][1:] for x in node["children"] if x["args"][0] == "server_name"]
        listeners = [x["args"][1:] for x in node["children"] if x["args"][0] == "listen"]
        if any(DOMAIN in row for row in names) and any(row and (row[0] == "443" or row[0].endswith(":443")) and "ssl" in row for row in listeners):
            servers.append(node["children"])
    if len(servers) != 1:
        raise RepairError("ambiguous_public_tls_server")
    server = servers[0]
    diagnostics.update(bounded_route_facts(http_nodes, server))
    locations = [x for x in server if x["args"][0] == "location"]
    for node in locations:
        if node["children"] is None:
            raise RepairError("unsupported_location_without_block")
        if any(x["args"][0] == "location" for x in node["children"]):
            # Nested selection has different regex precedence. Ignore an entire
            # tree only if its parent cannot match any exact approved module URI.
            if any(location_matches(node["args"][1:], "/" + relative) for relative in EXPECTED):
                raise RepairError("unsupported_relevant_nested_location")
    for relative in EXPECTED:
        uri = "/" + relative
        exact, prefixes, regexes = [], [], []
        for node in locations:
            args = node["args"][1:]
            if len(args) == 1 and args[0].startswith("@"):
                continue
            if len(args) == 1 and args[0].startswith("/"):
                if uri.startswith(args[0]):
                    prefixes.append((len(args[0]), False, node))
            elif len(args) == 2 and args[0] in {"=", "^~"}:
                if args[0] == "=" and uri == args[1]:
                    exact.append(node)
                elif args[0] == "^~" and uri.startswith(args[1]):
                    prefixes.append((len(args[1]), True, node))
            elif len(args) == 2 and args[0] in {"~", "~*"}:
                try:
                    if re.search(args[1], uri, re.I if args[0] == "~*" else 0):
                        regexes.append(node)
                except re.error:
                    raise RepairError("unsupported_location_regex") from None
            else:
                raise RepairError("unsupported_location_selector")
        if len(exact) > 1:
            raise RepairError("ambiguous_exact_location")
        prefix = max(prefixes, key=lambda x: x[0], default=None)
        selected = exact[0] if exact else (prefix[2] if prefix and prefix[1] else regexes[0] if regexes else prefix[2] if prefix else None)
        contexts = [http_nodes, server] + ([selected["children"]] if selected else [])
        effective_types, root = None, None
        for nodes in contexts:
            tables = [x for x in nodes if x["args"][0] == "types"]
            roots = [x["args"][1:] for x in nodes if x["args"][0] == "root"]
            if len(tables) > 1 or len(roots) > 1:
                raise RepairError("ambiguous_inheritance")
            if tables:
                effective_types = tables[0]["source"]
            if roots:
                root = roots[0]
            forbidden = {"proxy_pass", "fastcgi_pass", "uwsgi_pass", "scgi_pass", "grpc_pass", "alias", "rewrite", "return", "if", "error_page", "content_by_lua", "content_by_lua_block", "content_by_lua_file", "js_content", "perl", "empty_gif", "mp4", "flv"}
            if any(x["args"][0] in forbidden for x in nodes):
                raise RepairError("relevant_route_is_not_simple_static")
            for node in nodes:
                if node["args"][0] == "try_files":
                    args = node["args"][1:]
                    if args in [["$uri", "=404"], ["$uri", "$uri/", "=404"]]:
                        continue
                    named_first_file = (len(args) in {2, 3} and args[0] == "$uri"
                                        and (len(args) == 2 or args[1] == "$uri/")
                                        and re.fullmatch(r"@[A-Za-z_][A-Za-z0-9_]*", args[-1]))
                    named_targets = [location for location in locations if location["args"] == ["location", args[-1]]] if args else []
                    if not named_first_file or len(named_targets) != 1:
                        raise RepairError("unsupported_static_fallback")
                    if not static_files_verified:
                        raise RepairError("named_fallback_requires_verified_static_files")
                    # execute verifies all immutable regular files before this
                    # discovery and again before mutation. Their first $uri hit
                    # stays in this context; the named fallback is not entered.
        if effective_types != target or root != [STATIC_ROOT.as_posix()]:
            raise RepairError("mime_inheritance_or_static_root_unproven")
    return Path(target)


def checked_file(path, root, limit=4_000_000):
    if not path.is_absolute() or not path.is_relative_to(root):
        raise RepairError("file_outside_boundary")
    if root == CONFIG_ROOT:
        secure_directory(path.parent)
    for item in (path, *path.parents):
        if item.is_symlink():
            raise RepairError("symlink_path_rejected")
        if item == root:
            break
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
        raise RepairError("unsupported_file_metadata")
    if path.resolve() != path:
        raise RepairError("redirected_path_rejected")
    return path.read_bytes(), info


def command(args, *, dump=False):
    completed = subprocess.run(args, capture_output=True, timeout=30, check=False)
    if len(completed.stdout) > 2_000_000 or len(completed.stderr) > 2_000_000:
        raise RepairError("command_output_limit")
    if completed.returncode:
        raise RepairError("nginx_or_service_command_failed")
    return completed.stdout.decode("utf-8") if dump else {"passed": True, "stdout_sha256": digest(completed.stdout), "stderr_sha256": digest(completed.stderr)}


def nginx_binary():
    for value in ("/usr/sbin/nginx", "/sbin/nginx"):
        if Path(value).is_file():
            return value
    raise RepairError("nginx_binary_not_found")


def metadata(path, info):
    attrs = {name: os.getxattr(path, name) for name in os.listxattr(path)}
    return {"uid": info.st_uid, "gid": info.st_gid, "mode": stat.S_IMODE(info.st_mode), "atime_ns": info.st_atime_ns, "mtime_ns": info.st_mtime_ns, "xattrs": attrs}


def xattr_digest(meta):
    return digest(json.dumps({key: value.hex() for key, value in meta["xattrs"].items()}, sort_keys=True, separators=(",", ":")).encode())


def same_preserved_metadata(left, right):
    return all(left[key] == right[key] for key in ("uid", "gid", "mode", "mtime_ns", "xattrs"))


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def file_version(raw, info, meta):
    return {"sha256": digest(raw), "identity": tuple(getattr(info, key) for key in
            ("st_dev", "st_ino", "st_uid", "st_gid", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")),
            "xattrs": meta["xattrs"]}


def install_bytes(path, raw, meta, *, expected_current=None):
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".mime-repair-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fchown(stream.fileno(), meta["uid"], meta["gid"])
            os.fchmod(stream.fileno(), meta["mode"])
            for key, value in meta["xattrs"].items():
                os.setxattr(stream.fileno(), key, value)
            os.utime(stream.fileno(), ns=(meta["atime_ns"], meta["mtime_ns"]))
            os.fsync(stream.fileno())
        if expected_current is not None:
            current, current_info = checked_file(path, CONFIG_ROOT)
            if file_version(current, current_info, metadata(path, current_info)) != expected_current:
                raise RepairError("active_file_changed_during_staging")
        os.replace(name, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class LocalTLS(http.client.HTTPSConnection):
    def connect(self):
        sock = socket.create_connection(("127.0.0.1", 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=DOMAIN)


@contextmanager
def total_deadline(seconds):
    """Linux process timer also bounds slow-trickle reads and DNS/TLS setup."""
    previous = signal.getsignal(signal.SIGALRM)
    def expired(_signum, _frame):
        raise RepairError("https_probe_total_deadline")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def probe(relative, expected, local, token, *, timeout_seconds=20):
    connection = None
    try:
        with total_deadline(timeout_seconds):
            connection = (LocalTLS if local else http.client.HTTPSConnection)(DOMAIN, timeout=min(15, timeout_seconds), context=ssl.create_default_context())
            connection.request("GET", "/" + relative + "?mime_repair=" + token,
                               headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache", "User-Agent": "LumenCore-Approved-MIME-Verification/1"})
            response = connection.getresponse()
            body = response.read(4_000_001)
            mime = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            actual = digest(body)
            return {"path": relative, "route": "local_tls" if local else "public_https", "http_status": response.status,
                    "mime": mime if re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", mime) else "unsupported",
                    "sha256": actual, "expected_sha256": expected,
                    "passed": len(body) <= 4_000_000 and response.status == 200 and actual == expected and mime in JS_TYPES}
    finally:
        if connection is not None:
            connection.close()


def probe_after_reload(relative, expected, local, token, attempts):
    """Allow only the prior MIME value to settle; every call opens new TLS.

    Each route has one five-second elapsed budget including probes and sleeps.
    Passing the remaining budget into probe avoids nested SIGALRM timers.
    Nginx reload starts new workers asynchronously; this does not establish that
    any particular old-MIME observation was caused by a reload race.
    """
    started = time.monotonic()
    last = None
    for number in range(1, RELOAD_PROBE_MAX_ATTEMPTS + 1):
        remaining = RELOAD_PROBE_MAX_SECONDS - (time.monotonic() - started)
        if remaining <= 0:
            raise RepairError("post_reload_settle_deadline")
        try:
            row = probe(relative, expected, local, token + "-" + str(number), timeout_seconds=remaining)
        except BaseException as error:
            attempts.append({"path": relative, "route": "local_tls" if local else "public_https",
                             "attempt": number, "passed": False,
                             "elapsed_seconds": round(time.monotonic() - started, 6),
                             "error_code": str(error) if isinstance(error, RepairError) else type(error).__name__})
            raise
        elapsed = time.monotonic() - started
        attempts.append({**row, "attempt": number, "elapsed_seconds": round(elapsed, 6)})
        if elapsed >= RELOAD_PROBE_MAX_SECONDS:
            raise RepairError("post_reload_settle_deadline")
        if row["passed"]:
            return row
        last = row
        retryable = (row.get("http_status") == 200 and row.get("sha256") == expected
                     and row.get("expected_sha256") == expected
                     and row.get("mime") == "application/octet-stream")
        if not retryable or number == RELOAD_PROBE_MAX_ATTEMPTS:
            return row
        remaining = RELOAD_PROBE_MAX_SECONDS - (time.monotonic() - started)
        if remaining <= RELOAD_PROBE_INTERVAL_SECONDS:
            return row
        time.sleep(RELOAD_PROBE_INTERVAL_SECONDS)
    return last


def verify_static():
    results = []
    for relative, expected in EXPECTED.items():
        raw, _ = checked_file(STATIC_ROOT / relative, STATIC_ROOT)
        results.append({"path": relative, "sha256": digest(raw), "expected_sha256": expected, "passed": digest(raw) == expected})
    if not all(row["passed"] for row in results):
        raise RepairError("static_release_hash_mismatch")
    return results


@contextmanager
def exclusive_lock():
    import fcntl
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise RepairError("unsafe_lock_metadata")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RepairError("competing_mime_repair") from None
        yield
    finally:
        os.close(fd)


def secure_directory(path):
    for directory in (path, *path.parents):
        info = directory.lstat()
        if directory.is_symlink() or info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022:
            raise RepairError("unsafe_rollback_directory")


def create_rollback():
    ROLLBACK_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    secure_directory(ROLLBACK_ROOT)
    directory = ROLLBACK_ROOT / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex)
    directory.mkdir(mode=0o700)
    return directory


def require_root():
    if os.name != "posix" or os.geteuid() != 0:
        raise RepairError("requires_linux_root")


def execute(mode, expected_sha256=None):
    result = {"schema": "lumencore.approved_public_mime_repair.v1", "mode": mode,
              "generated_utc": datetime.now(timezone.utc).isoformat(), "configuration_modified": False,
              "service_reloaded": False, "rollback": "NOT_NEEDED", "full_manifest_audit_required": True}
    require_root()
    nginx = nginx_binary()
    with exclusive_lock():
        result["initial_nginx_test"] = command([nginx, "-t"])
        initial_dump = command([nginx, "-T"], dump=True)
        result["initial_configuration_sha256"] = digest(initial_dump.encode())
        result["static_files"] = verify_static()
        try:
            target = discover(initial_dump, verified_static_sha256={row["path"]: row["sha256"] for row in result["static_files"]})
        except RepairError as error:
            # This explicit phase precedes all target writes and reloads. Retain
            # enough redacted route facts to explain a fail-closed inspection.
            result.update(status="FAILED_STATE_REVIEW_REQUIRED", error_code=str(error),
                          phase="STATIC_ROUTE_DISCOVERY", route_diagnostics=getattr(error, "route_diagnostics", {}))
            return result
        raw, info = checked_file(target, CONFIG_ROOT, 1_000_000)
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022:
            raise RepairError("unsafe_active_mime_owner_or_mode")
        candidate, status = propose(raw)
        meta = metadata(target, info)
        result.update(active_file=str(target), original_sha256=digest(raw), candidate_sha256=digest(candidate),
                      original_metadata={k: v for k, v in meta.items() if k != "xattrs"},
                      original_xattrs_sha256=xattr_digest(meta), preserved_xattr_count=len(meta["xattrs"]), proposal_status=status, inserted_bytes=len(candidate) - len(raw))
        result["static_files"] = verify_static()
        if mode == "inspect":
            result["status"] = "INSPECTED"
            return result
        if not expected_sha256 or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256) or digest(raw) != expected_sha256:
            raise RepairError("approved_original_hash_mismatch")
        if status == "ALREADY_MAPPED":
            raise RepairError("already_mapped_no_change_required")
        directory = create_rollback()
        result["rollback_directory"] = str(directory)
        result["rollback_id"] = directory.name
        install_bytes(directory / "original.mime", raw, meta)
        install_bytes(directory / "candidate.mime", candidate, meta)
        if digest((directory / "original.mime").read_bytes()) != digest(raw):
            raise RepairError("rollback_copy_hash_mismatch")
        changed = False
        try:
            if digest(command([nginx, "-T"], dump=True).encode()) != result["initial_configuration_sha256"]:
                raise RepairError("active_configuration_changed_before_install")
            if digest(checked_file(target, CONFIG_ROOT)[0]) != expected_sha256:
                raise RepairError("active_file_changed_before_install")
            changed = True  # covers interruption immediately after atomic replace
            install_bytes(target, candidate, meta, expected_current=file_version(raw, info, meta))
            result["configuration_modified"] = True
            result["candidate_nginx_test"] = command([nginx, "-t"])
            command(["/usr/bin/systemctl", "reload", "nginx"])
            result["service_reloaded"] = True
            command(["/usr/bin/systemctl", "is-active", "--quiet", "nginx"])
            result["static_files"] = verify_static()
            result["http_checks"] = []
            result["http_probe_attempts"] = []
            result["reload_probe_policy"] = {"max_attempts_per_route": RELOAD_PROBE_MAX_ATTEMPTS,
                                           "max_seconds_per_route": RELOAD_PROBE_MAX_SECONDS,
                                           "interval_seconds": RELOAD_PROBE_INTERVAL_SECONDS,
                                           "retryable_mime": "application/octet-stream"}
            token = uuid.uuid4().hex
            for local in (True, False):
                for relative, expected in EXPECTED.items():
                    row = probe_after_reload(relative, expected, local, token, result["http_probe_attempts"])
                    result["http_checks"].append(row)
                    if not row["passed"]:
                        raise RepairError("post_reload_http_verification_failed")
            current, current_info = checked_file(target, CONFIG_ROOT)
            current_meta = metadata(target, current_info)
            if digest(current) != digest(candidate) or any(current_meta[k] != meta[k] for k in ("uid", "gid", "mode", "mtime_ns", "xattrs")):
                raise RepairError("post_reload_active_metadata_mismatch")
            result.update(status="REPAIRED_THREE_FILES_VERIFIED", active_sha256=digest(current))
        except BaseException as error:
            result["status"] = "FAILED"
            result["error_code"] = str(error) if isinstance(error, RepairError) else type(error).__name__
            if changed:
                # Do not let a second termination interrupt the bounded recovery.
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                    signal.signal(sig, signal.SIG_IGN)
                try:
                    current, current_info = checked_file(target, CONFIG_ROOT)
                    current_meta = metadata(target, current_info)
                    if not same_preserved_metadata(current_meta, meta):
                        raise RepairError("concurrent_metadata_edit_rollback_refused")
                    if digest(current) == digest(raw):
                        result["rollback"] = "ORIGINAL_ALREADY_PRESENT"
                    elif digest(current) != digest(candidate):
                        raise RepairError("concurrent_edit_rollback_refused")
                    else:
                        install_bytes(target, raw, meta, expected_current=file_version(current, current_info, current_meta))
                        result["rollback"] = "ORIGINAL_RESTORED"
                    result["rollback_nginx_test"] = command([nginx, "-t"])
                    command(["/usr/bin/systemctl", "reload", "nginx"])
                    command(["/usr/bin/systemctl", "is-active", "--quiet", "nginx"])
                    if digest(checked_file(target, CONFIG_ROOT)[0]) != digest(raw):
                        raise RepairError("rollback_hash_verification_failed")
                    result["rollback"] = "RESTORED_VALIDATED_RELOADED"
                    result["active_sha256"] = digest(raw)
                except BaseException as recovery:
                    result["rollback"] = "FAILED_MANUAL_REVIEW_REQUIRED"
                    result["rollback_error_code"] = str(recovery) if isinstance(recovery, RepairError) else type(recovery).__name__
        # Private receipt contains only allowlisted metadata; never raw config.
        receipt = directory / "execution.json"
        try:
            with receipt.open("x") as stream:
                json.dump(result, stream, sort_keys=True, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(receipt, 0o600)
            fsync_directory(directory)
        except OSError:
            result["receipt_persistence_failed"] = True
            result["status"] = "FAILED_RECEIPT_PERSISTENCE_REVIEW_REQUIRED"
        return result


def explicit_rollback(rollback_id, original_sha256, candidate_sha256):
    """Rollback only this receipt's MIME change after the independent full gate."""
    require_root()
    if not isinstance(rollback_id, str) or not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{32}", rollback_id):
        raise RepairError("invalid_rollback_id")
    if any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in (original_sha256, candidate_sha256)):
        raise RepairError("invalid_rollback_hash")
    directory = ROLLBACK_ROOT / rollback_id
    result = {"schema": "lumencore.approved_public_mime_rollback.v1", "rollback_id": rollback_id,
              "scope": "MIME_TABLE_ONLY", "configuration_modified": False, "full_release_rollback_claimed": False}
    with exclusive_lock():
        secure_directory(directory)
        receipt_raw, receipt_info = checked_file(directory / "execution.json", ROLLBACK_ROOT)
        if receipt_info.st_uid != 0 or stat.S_IMODE(receipt_info.st_mode) != 0o600:
            raise RepairError("unsafe_rollback_receipt")
        try:
            receipt = json.loads(receipt_raw)
        except (ValueError, UnicodeError):
            raise RepairError("invalid_rollback_receipt") from None
        if not isinstance(receipt, dict) or receipt.get("rollback_id") != rollback_id or receipt.get("original_sha256") != original_sha256 or receipt.get("candidate_sha256") != candidate_sha256:
            raise RepairError("rollback_receipt_binding_mismatch")
        nginx = nginx_binary()
        result["static_files"] = verify_static()
        target = discover(command([nginx, "-T"], dump=True),
                          verified_static_sha256={row["path"]: row["sha256"] for row in result["static_files"]})
        if receipt.get("active_file") != str(target):
            raise RepairError("rollback_active_target_mismatch")
        original, original_info = checked_file(directory / "original.mime", ROLLBACK_ROOT)
        candidate, _ = checked_file(directory / "candidate.mime", ROLLBACK_ROOT)
        if digest(original) != original_sha256 or digest(candidate) != candidate_sha256 or propose(original)[0] != candidate:
            raise RepairError("rollback_backup_binding_mismatch")
        original_meta = metadata(directory / "original.mime", original_info)
        if original_info.st_uid != 0 or stat.S_IMODE(original_info.st_mode) & 0o022:
            raise RepairError("unsafe_rollback_backup_metadata")
        if any(original_meta[key] != receipt.get("original_metadata", {}).get(key) for key in ("uid", "gid", "mode", "mtime_ns")) or xattr_digest(original_meta) != receipt.get("original_xattrs_sha256"):
            raise RepairError("rollback_backup_metadata_mismatch")
        current, current_info = checked_file(target, CONFIG_ROOT)
        if digest(current) not in {candidate_sha256, original_sha256}:
            raise RepairError("concurrent_edit_rollback_refused")
        current_meta = metadata(target, current_info)
        if not same_preserved_metadata(current_meta, original_meta):
            raise RepairError("concurrent_metadata_edit_rollback_refused")
        try:
            if digest(current) == candidate_sha256:
                result["configuration_modified"] = True
                install_bytes(target, original, original_meta, expected_current=file_version(current, current_info, current_meta))
            result["nginx_test"] = command([nginx, "-t"])
            command(["/usr/bin/systemctl", "reload", "nginx"])
            command(["/usr/bin/systemctl", "is-active", "--quiet", "nginx"])
            if digest(checked_file(target, CONFIG_ROOT)[0]) != original_sha256:
                raise RepairError("rollback_hash_verification_failed")
            result.update(status="MIME_ROLLBACK_VALIDATED_RELOADED", active_sha256=original_sha256)
        except BaseException as error:
            result.update(status="MIME_ROLLBACK_FAILED_MANUAL_REVIEW_REQUIRED",
                          error_code=str(error) if isinstance(error, RepairError) else type(error).__name__)
        # Keep original execution receipt immutable; return distinct recovery proof.
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "apply", "rollback"))
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-candidate-sha256")
    parser.add_argument("--rollback-id")
    args = parser.parse_args()
    def interrupted(_signum, _frame):
        raise RepairError("interrupted")
    if os.name == "posix":
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, interrupted)
    try:
        result = explicit_rollback(args.rollback_id, args.expected_sha256, args.expected_candidate_sha256) if args.mode == "rollback" else execute(args.mode, args.expected_sha256)
    except BaseException as error:
        # A signal or unexpected exception can escape after an atomic replacement
        # or reload. Without a returned phase receipt, report unknown, never false.
        result = {"status": "FAILED_STATE_REVIEW_REQUIRED", "error_code": str(error) if isinstance(error, RepairError) else type(error).__name__, "configuration_modified": None}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] in {"INSPECTED", "REPAIRED_THREE_FILES_VERIFIED", "MIME_ROLLBACK_VALIDATED_RELOADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
