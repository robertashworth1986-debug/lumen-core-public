"""Email response watcher.

Continuously polls configured inboxes for replies, correlates them to outbound
resume dispatch events when possible, and writes deterministic response ledgers.

Outputs:
  out/opportunities/email/email_response_watcher_latest.json
  out/opportunities/email/email_response_queue_latest.json
  out/opportunities/email/email_response_ledger.jsonl
  out/ops/email_response_watcher/email_response_manifest_latest.json

Environment (primary source, no secrets committed):
  LUMA_EMAIL_IMAP_HOST
  LUMA_EMAIL_IMAP_PORT      (optional, default 993)
  LUMA_EMAIL_IMAP_USER
  LUMA_EMAIL_IMAP_PASSWORD
  LUMA_EMAIL_IMAP_FOLDER    (optional, default INBOX)
  LUMA_EMAIL_IMAP_SEARCH    (optional, default UNSEEN)

Optional config file:
  data/email_response_sources.json
"""

from __future__ import annotations

import argparse
import email
import email.policy
import hashlib
import imaplib
import json
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_EMAIL = ROOT / "out" / "opportunities" / "email"
OUT_OPS = ROOT / "out" / "ops" / "email_response_watcher"

CFG_PATH = DATA_DIR / "email_response_sources.json"
OUTBOUND_LEDGER = OUT_EMAIL / "outbound_resume_dispatch_ledger.jsonl"

STATE_PATH = OUT_EMAIL / "email_response_state.json"
LATEST_PATH = OUT_EMAIL / "email_response_watcher_latest.json"
QUEUE_PATH = OUT_EMAIL / "email_response_queue_latest.json"
LEDGER_PATH = OUT_EMAIL / "email_response_ledger.jsonl"
LATEST_MD_PATH = OUT_EMAIL / "email_response_watcher_latest.md"

MANIFEST_LATEST = OUT_OPS / "email_response_manifest_latest.json"

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
MESSAGE_ID_RE = re.compile(r"<[^>]+>")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_email(value: Any) -> str:
    _, addr = parseaddr(str(value or ""))
    addr = addr.strip().lower()
    if EMAIL_RE.match(addr):
        return addr
    return ""


def normalize_message_id(value: Any) -> str:
    txt = normalize_text(value)
    if not txt:
        return ""
    if txt.startswith("<") and txt.endswith(">"):
        return txt[1:-1].strip().lower()
    return txt.strip("<>").strip().lower()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_html(html: str) -> str:
    txt = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def extract_body_text(msg: email.message.Message) -> str:
    chunks: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = str(part.get_content_type() or "").lower()
            if ctype not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            chunks.append(strip_html(text) if ctype == "text/html" else text)
    else:
        payload = msg.get_payload(decode=True)
        if payload is not None:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            ctype = str(msg.get_content_type() or "").lower()
            chunks.append(strip_html(text) if ctype == "text/html" else text)
    body = "\n".join(chunks)
    return re.sub(r"\s+", " ", body).strip()


def extract_links(text: str) -> list[str]:
    links = re.findall(r"https?://[^\s\]\[\)\(\"'<>\{\}]+", text or "")
    out: list[str] = []
    seen: set[str] = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        out.append(link)
    return out[:30]


def classify_sentiment(blob: str) -> str:
    low = normalize_text(blob).lower()
    positive = ["interested", "next step", "schedule", "interview", "call", "approved", "proceed", "great fit"]
    negative = ["not moving forward", "decline", "rejected", "unfortunately", "not a fit"]
    for token in negative:
        if token in low:
            return "negative"
    for token in positive:
        if token in low:
            return "positive"
    return "neutral"


def load_sources() -> list[dict[str, Any]]:
    cfg = read_json(CFG_PATH, {})
    sources = cfg.get("sources", []) if isinstance(cfg, dict) else []
    out: list[dict[str, Any]] = []

    if isinstance(sources, list):
        for row in sources:
            if not isinstance(row, dict):
                continue
            host = os.getenv(str(row.get("imap_host_env") or "").strip(), "").strip()
            user = os.getenv(str(row.get("imap_user_env") or "").strip(), "").strip()
            pwd = os.getenv(str(row.get("imap_password_env") or "").strip(), "").strip()
            if not (host and user and pwd):
                continue
            out.append(
                {
                    "name": str(row.get("name") or "response_inbox"),
                    "host": host,
                    "port": safe_int(row.get("imap_port", 993), 993),
                    "user": user,
                    "password": pwd,
                    "folder": str(row.get("folder") or "INBOX"),
                    "search": str(row.get("search") or "UNSEEN"),
                }
            )

    env_host = (os.getenv("LUMA_EMAIL_IMAP_HOST") or os.getenv("EMAIL_IMAP_HOST") or "").strip()
    env_user = (os.getenv("LUMA_EMAIL_IMAP_USER") or os.getenv("EMAIL_IMAP_USER") or "").strip()
    env_pwd = (os.getenv("LUMA_EMAIL_IMAP_PASSWORD") or os.getenv("EMAIL_IMAP_PASSWORD") or "").strip()
    if env_host and env_user and env_pwd:
        out.append(
            {
                "name": "primary_inbox",
                "host": env_host,
                "port": safe_int(os.getenv("LUMA_EMAIL_IMAP_PORT", "993"), 993),
                "user": env_user,
                "password": env_pwd,
                "folder": os.getenv("LUMA_EMAIL_IMAP_FOLDER", "INBOX"),
                "search": os.getenv("LUMA_EMAIL_IMAP_SEARCH", "UNSEEN"),
            }
        )

    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for src in out:
        dedup[(src["host"], src["user"])] = src
    return list(dedup.values())


def fetch_messages(source: dict[str, Any], max_per_cycle: int) -> list[email.message.Message]:
    host = str(source.get("host") or "")
    port = safe_int(source.get("port"), 993)
    user = str(source.get("user") or "")
    password = str(source.get("password") or "")
    folder = str(source.get("folder") or "INBOX")
    search = str(source.get("search") or "UNSEEN")

    conn = imaplib.IMAP4_SSL(host, port)
    try:
        conn.login(user, password)
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            return []

        status, data = conn.search(None, search)
        if status != "OK":
            status, data = conn.search(None, "ALL")
            if status != "OK":
                return []

        ids = data[0].split() if data and data[0] else []
        ids = ids[-max_per_cycle:]

        out: list[email.message.Message] = []
        parser = email.parser.BytesParser(policy=email.policy.default)
        for msg_id in ids:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw_bytes = b""
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], (bytes, bytearray)):
                    raw_bytes += bytes(part[1])
            if not raw_bytes:
                continue
            out.append(parser.parsebytes(raw_bytes))
        return out
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def fingerprint(msg: email.message.Message, mailbox_name: str) -> str:
    key = "|".join(
        [
            mailbox_name,
            str(msg.get("Message-ID") or ""),
            str(msg.get("Date") or ""),
            str(msg.get("From") or ""),
            str(msg.get("Subject") or ""),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_ref_ids(msg: email.message.Message) -> list[str]:
    refs: list[str] = []
    for key in ["In-Reply-To", "References"]:
        raw = str(msg.get(key) or "")
        if not raw:
            continue
        for token in MESSAGE_ID_RE.findall(raw):
            mid = normalize_message_id(token)
            if mid:
                refs.append(mid)
    out: list[str] = []
    seen: set[str] = set()
    for mid in refs:
        if mid in seen:
            continue
        seen.add(mid)
        out.append(mid)
    return out


def load_outbound_index() -> dict[str, Any]:
    rows = read_jsonl(OUTBOUND_LEDGER)
    by_msg_id: dict[str, dict[str, Any]] = {}
    by_recipient: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        if str(row.get("action") or "") != "sent":
            continue
        msg_id = normalize_message_id(row.get("outbound_message_id"))
        recipient = normalize_email(row.get("recipient"))

        if msg_id:
            by_msg_id[msg_id] = row
        if recipient:
            by_recipient.setdefault(recipient, []).append(row)

    for recipient in by_recipient:
        by_recipient[recipient].sort(key=lambda r: str(r.get("generated_utc") or ""), reverse=True)

    return {
        "rows": rows,
        "by_msg_id": by_msg_id,
        "by_recipient": by_recipient,
    }


def correlate_outbound(
    *,
    sender_email: str,
    ref_ids: list[str],
    outbound_idx: dict[str, Any],
) -> dict[str, Any]:
    by_msg_id = outbound_idx.get("by_msg_id", {}) if isinstance(outbound_idx.get("by_msg_id"), dict) else {}
    by_recipient = outbound_idx.get("by_recipient", {}) if isinstance(outbound_idx.get("by_recipient"), dict) else {}

    for rid in ref_ids:
        if rid in by_msg_id:
            row = by_msg_id[rid]
            return {
                "matched": True,
                "match_type": "message_id",
                "outbound": row,
            }

    if sender_email and sender_email in by_recipient:
        row = by_recipient[sender_email][0]
        return {
            "matched": True,
            "match_type": "recipient",
            "outbound": row,
        }

    return {"matched": False, "match_type": "none", "outbound": {}}


def render_markdown(summary: dict[str, Any], queue_rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Email Response Watcher")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc', '')}")
    lines.append(f"Status: {summary.get('status', '')}")
    lines.append(f"Sources configured: {summary.get('sources_configured', 0)}")
    lines.append(f"New responses: {summary.get('new_responses', 0)}")
    lines.append(f"Queue count: {summary.get('queue_count', 0)}")
    lines.append(f"Matched outbound responses: {summary.get('matched_outbound_count', 0)}")
    lines.append("")
    lines.append("## Recent Responses")
    lines.append("")
    for row in queue_rows[:25]:
        lines.append(
            f"- sentiment={row.get('sentiment','neutral')} from={row.get('sender_email','')} "
            f"matched={row.get('matched_outbound', False)} subject={row.get('subject','')}"
        )
    lines.append("")
    return "\n".join(lines)


def run_cycle(*, max_per_cycle: int) -> dict[str, Any]:
    OUT_EMAIL.mkdir(parents=True, exist_ok=True)
    OUT_OPS.mkdir(parents=True, exist_ok=True)

    state = read_json(STATE_PATH, {})
    seen_ids = state.get("seen_ids", []) if isinstance(state, dict) else []
    if not isinstance(seen_ids, list):
        seen_ids = []
    seen_set = set(str(x) for x in seen_ids)

    prev_queue = read_json(QUEUE_PATH, [])
    queue_rows: list[dict[str, Any]] = [r for r in prev_queue if isinstance(r, dict)] if isinstance(prev_queue, list) else []
    queue_by_id = {str(r.get("id") or ""): r for r in queue_rows if str(r.get("id") or "")}

    sources = load_sources()
    outbound_idx = load_outbound_index()

    fetched_total = 0
    parsed_total = 0
    new_rows: list[dict[str, Any]] = []
    source_errors: list[dict[str, str]] = []

    for source in sources:
        name = str(source.get("name") or "inbox")
        try:
            messages = fetch_messages(source, max_per_cycle=max_per_cycle)
        except Exception as exc:
            source_errors.append({"source": name, "error": str(exc)[:500]})
            continue

        fetched_total += len(messages)
        for msg in messages:
            parsed_total += 1
            msg_fp = fingerprint(msg, name)
            if msg_fp in seen_set:
                continue

            from_raw = str(msg.get("From") or "")
            sender_email = normalize_email(from_raw)
            subject = normalize_text(msg.get("Subject"))
            body = extract_body_text(msg)
            links = extract_links(body)
            ref_ids = extract_ref_ids(msg)
            correlation = correlate_outbound(sender_email=sender_email, ref_ids=ref_ids, outbound_idx=outbound_idx)
            outbound_row = correlation.get("outbound", {}) if isinstance(correlation.get("outbound"), dict) else {}

            row = {
                "id": msg_fp,
                "generated_utc": now_iso(),
                "mailbox": name,
                "message_id": normalize_text(msg.get("Message-ID")),
                "date": normalize_text(msg.get("Date")),
                "from": from_raw,
                "sender_email": sender_email,
                "subject": subject,
                "sentiment": classify_sentiment("\n".join([subject, body])),
                "links": links,
                "snippet": (body or "")[:900],
                "matched_outbound": bool(correlation.get("matched")),
                "matched_type": str(correlation.get("match_type") or "none"),
                "matched_outbound_message_id": normalize_text(outbound_row.get("outbound_message_id")),
                "matched_opportunity_id": normalize_text(outbound_row.get("opportunity_id")),
                "matched_recipient": normalize_email(outbound_row.get("recipient")),
                "ref_ids": ref_ids,
                "state": "NEW_RESPONSE",
            }
            seen_set.add(msg_fp)
            new_rows.append(row)

            existing = queue_by_id.get(msg_fp)
            if existing:
                existing["last_seen_utc"] = row["generated_utc"]
            else:
                queue_by_id[msg_fp] = row

    queue_rows = sorted(queue_by_id.values(), key=lambda r: str(r.get("generated_utc") or ""), reverse=True)[:4000]

    state_out = {
        "generated_utc": now_iso(),
        "schema": "email_response_state_v1",
        "seen_ids": list(seen_set)[-50000:],
        "seen_count": len(seen_set),
        "queue_count": len(queue_rows),
    }
    write_json(STATE_PATH, state_out)

    append_jsonl(LEDGER_PATH, new_rows)
    write_json(QUEUE_PATH, queue_rows)

    matched_count = sum(1 for row in new_rows if bool(row.get("matched_outbound")))

    summary = {
        "generated_utc": now_iso(),
        "scope": "email_response_watcher_cycle",
        "status": "ok" if len(sources) > 0 else "no_sources_configured",
        "sources_configured": len(sources),
        "fetched_messages": fetched_total,
        "parsed_messages": parsed_total,
        "new_responses": len(new_rows),
        "queue_count": len(queue_rows),
        "matched_outbound_count": matched_count,
        "source_errors": source_errors,
        "artifacts": {
            "latest": str(LATEST_PATH),
            "latest_markdown": str(LATEST_MD_PATH),
            "queue": str(QUEUE_PATH),
            "ledger": str(LEDGER_PATH),
            "state": str(STATE_PATH),
        },
        "new_rows": new_rows[:250],
    }
    write_json(LATEST_PATH, summary)
    write_text(LATEST_MD_PATH, render_markdown(summary, queue_rows))

    tag = now_tag()
    manifest = {
        "generated_utc": now_iso(),
        "schema": "email_response_manifest_v1",
        "status": summary.get("status"),
        "summary": {
            "new_responses": len(new_rows),
            "queue_count": len(queue_rows),
            "matched_outbound_count": matched_count,
            "sources_configured": len(sources),
        },
        "paths": {
            "latest": str(LATEST_PATH),
            "latest_markdown": str(LATEST_MD_PATH),
            "queue": str(QUEUE_PATH),
            "ledger": str(LEDGER_PATH),
            "state": str(STATE_PATH),
        },
        "sha256": {},
    }

    for p in [LATEST_PATH, LATEST_MD_PATH, QUEUE_PATH, LEDGER_PATH, STATE_PATH]:
        if p.exists():
            manifest["sha256"][str(p)] = sha256_file(p)

    manifest_tag = OUT_OPS / f"email_response_manifest_{tag}.json"
    write_json(manifest_tag, manifest)
    write_json(MANIFEST_LATEST, manifest)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch inbox replies and correlate to resume dispatch pipeline.")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit.")
    parser.add_argument("--interval-sec", type=int, default=240, help="Polling interval for continuous mode.")
    parser.add_argument("--max-per-cycle", type=int, default=120, help="Maximum messages fetched per source.")
    args = parser.parse_args()

    if args.once:
        summary = run_cycle(max_per_cycle=args.max_per_cycle)
        print(f"EMAIL_RESPONSE_LATEST={LATEST_PATH}")
        print(f"EMAIL_RESPONSE_QUEUE={QUEUE_PATH}")
        print(f"EMAIL_RESPONSE_MANIFEST={MANIFEST_LATEST}")
        print(f"EMAIL_RESPONSE_NEW={summary.get('new_responses', 0)}")
        return 0

    while True:
        try:
            summary = run_cycle(max_per_cycle=args.max_per_cycle)
            print(
                json.dumps(
                    {
                        "generated_utc": summary.get("generated_utc"),
                        "status": summary.get("status"),
                        "sources_configured": summary.get("sources_configured"),
                        "new_responses": summary.get("new_responses"),
                        "matched_outbound_count": summary.get("matched_outbound_count"),
                    }
                )
            )
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print(json.dumps({"generated_utc": now_iso(), "error": str(exc)[:500]}))
        time.sleep(max(20, args.interval_sec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
