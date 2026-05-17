"""Email resume dispatcher.

Takes scored opportunities from the email opportunity queue and sends an updated
resume package to matching contacts using SMTP.

Outputs:
  out/opportunities/email/outbound_resume_dispatch_latest.json
  out/opportunities/email/outbound_resume_dispatch_queue_latest.json
  out/opportunities/email/outbound_resume_dispatch_ledger.jsonl
  out/ops/email_resume_dispatcher/email_resume_dispatch_manifest_latest.json

Environment (primary source, no secrets committed):
  LUMA_SMTP_HOST
  LUMA_SMTP_PORT            (optional, default 587)
  LUMA_SMTP_USER            (optional)
  LUMA_SMTP_PASSWORD        (optional)
  LUMA_SMTP_FROM            (optional; falls back to company email)
  LUMA_SMTP_STARTTLS        (optional, default true)
  LUMA_SMTP_USE_SSL         (optional, default false)

Safety:
  - Does not resend the same opportunity id once marked sent.
  - Supports --dry-run for non-destructive validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from pathlib import Path
from typing import Any

from application_context_resolver import load_application_profile


ROOT = Path(__file__).resolve().parents[1]
OUT_EMAIL = ROOT / "out" / "opportunities" / "email"
OUT_OPS = ROOT / "out" / "ops" / "email_resume_dispatcher"

EMAIL_QUEUE_PATH = OUT_EMAIL / "email_opportunity_queue_latest.json"
PUBLIC_TRUTH_PATH = ROOT / "out" / "ops" / "public_truth" / "public_truth_latest.json"
RESUME_MD_PATH = ROOT / "RESUME_LUMENCORE.md"
RESUME_PDF_PATH = ROOT / "out" / "resume" / "RESUME_LUMENCORE_ELITE.pdf"

STATE_PATH = OUT_EMAIL / "outbound_resume_dispatch_state.json"
LATEST_PATH = OUT_EMAIL / "outbound_resume_dispatch_latest.json"
QUEUE_PATH = OUT_EMAIL / "outbound_resume_dispatch_queue_latest.json"
LEDGER_PATH = OUT_EMAIL / "outbound_resume_dispatch_ledger.jsonl"
LATEST_MD_PATH = OUT_EMAIL / "outbound_resume_dispatch_latest.md"

MANIFEST_LATEST = OUT_OPS / "email_resume_dispatch_manifest_latest.json"
KNOWN_ENV_FILES = [
    ROOT / "config" / "luma_outreach_keys.env",
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".env",
]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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


def load_env_file(path: Path) -> list[str]:
    loaded: list[str] = []
    if not path.exists():
        return loaded
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip()
        env_val = value.strip().strip('"').strip("'")
        if not env_key or not env_val:
            continue
        if env_key not in os.environ:
            os.environ[env_key] = env_val
            loaded.append(env_key)
    return loaded


def hydrate_known_env() -> dict[str, list[str]]:
    detail: dict[str, list[str]] = {}
    for path in KNOWN_ENV_FILES:
        loaded = load_env_file(path)
        if loaded:
            detail[str(path)] = loaded
    return detail


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_email(value: Any) -> str:
    _, addr = parseaddr(str(value or ""))
    addr = addr.strip().lower()
    if EMAIL_RE.match(addr):
        return addr
    return ""


def load_smtp_config() -> dict[str, Any]:
    hydrate_known_env()

    host = (os.getenv("LUMA_SMTP_HOST") or os.getenv("EMAIL_SMTP_HOST") or "").strip()
    user = (os.getenv("LUMA_SMTP_USER") or os.getenv("EMAIL_SMTP_USER") or "").strip()
    password = (os.getenv("LUMA_SMTP_PASSWORD") or os.getenv("EMAIL_SMTP_PASSWORD") or "").strip()
    from_addr = (os.getenv("LUMA_SMTP_FROM") or os.getenv("EMAIL_SMTP_FROM") or "").strip()
    port = safe_int(os.getenv("LUMA_SMTP_PORT", "587"), 587)

    starttls_raw = (os.getenv("LUMA_SMTP_STARTTLS") or "true").strip().lower()
    use_ssl_raw = (os.getenv("LUMA_SMTP_USE_SSL") or "false").strip().lower()
    use_outlook_raw = (os.getenv("LUMA_USE_OUTLOOK_COM") or "true").strip().lower()
    starttls = starttls_raw in {"1", "true", "yes", "y"}
    use_ssl = use_ssl_raw in {"1", "true", "yes", "y"}
    use_outlook = use_outlook_raw in {"1", "true", "yes", "y"}

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "starttls": starttls,
        "use_ssl": use_ssl,
        "use_outlook": use_outlook,
    }


def smtp_send(message: EmailMessage, smtp_cfg: dict[str, Any]) -> None:
    host = str(smtp_cfg.get("host") or "")
    port = safe_int(smtp_cfg.get("port"), 587)
    user = str(smtp_cfg.get("user") or "")
    password = str(smtp_cfg.get("password") or "")
    starttls = bool(smtp_cfg.get("starttls", True))
    use_ssl = bool(smtp_cfg.get("use_ssl", False))

    if use_ssl:
        with smtplib.SMTP_SSL(host=host, port=port, timeout=45, context=ssl.create_default_context()) as server:
            if user:
                server.login(user, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host=host, port=port, timeout=45) as server:
        server.ehlo()
        if starttls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        if user:
            server.login(user, password)
        server.send_message(message)


def build_subject(row: dict[str, Any]) -> str:
    source_subject = normalize_text(row.get("subject"))
    if source_subject:
        return f"Re: {source_subject} | Updated Luma Resume"
    return "Luma Resume Package"


def outlook_send(*, recipient: str, subject: str, body: str) -> dict[str, Any]:
    try:
        import win32com.client  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"outlook_com_import_failed:{exc}")

    try:
        app = win32com.client.Dispatch("Outlook.Application")
        mail = app.CreateItem(0)
        mail.To = recipient
        mail.Subject = subject
        mail.Body = body

        if RESUME_MD_PATH.exists():
            mail.Attachments.Add(str(RESUME_MD_PATH))
        if RESUME_PDF_PATH.exists():
            mail.Attachments.Add(str(RESUME_PDF_PATH))

        mail.Send()
        synthetic_id = make_msgid(domain="outlook.local")
        return {"ok": True, "message_id": synthetic_id}
    except Exception as exc:
        raise RuntimeError(f"outlook_com_send_failed:{exc}")


def truth_snippet() -> dict[str, Any]:
    truth = read_json(PUBLIC_TRUTH_PATH, {})
    if not isinstance(truth, dict):
        truth = {}
    claims = truth.get("claims", {}) if isinstance(truth.get("claims"), dict) else {}
    chain = truth.get("chain", {}) if isinstance(truth.get("chain"), dict) else {}
    return {
        "status": str(truth.get("status") or ""),
        "policy": str(truth.get("policy") or "current_production_truth_only"),
        "entry_sha256": str(chain.get("entry_sha256") or ""),
        "master_valuation_proxy_usd": safe_float(claims.get("master_valuation_proxy_usd"), 0.0),
        "valuation_increment_usd": safe_float(claims.get("valuation_increment_usd"), 0.0),
        "opportunities_total": safe_int(claims.get("opportunities_total"), 0),
        "email_queue_total": safe_int(claims.get("email_queue_total"), 0),
    }


def build_body(profile: dict[str, Any], truth: dict[str, Any], row: dict[str, Any]) -> str:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}

    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    title = str(pi.get("title") or company.get("founder_role") or "Principal Quant Systems Engineer")
    email = str(company.get("email") or "robertashworth4444@gmail.com")
    phone = str(company.get("phone") or "615-438-2502")
    website = str(company.get("website") or "https://lumen-core.ai")

    opp_type = str(row.get("opportunity_type") or "opportunity")
    opp_score = safe_float(row.get("fit_score"), safe_float(row.get("raw_score"), 0.0) / 15.0)

    lines = [
        "Hello,",
        "",
        "I am sharing my updated resume package in response to this opportunity.",
        "",
        f"Opportunity type: {opp_type}",
        f"Opportunity fit score: {opp_score:.2f}",
        "",
        "Current production truth snapshot:",
        f"- Policy: {truth.get('policy', 'current_production_truth_only')}",
        f"- Status: {truth.get('status', 'UNKNOWN')}",
        f"- Chain entry SHA256: {truth.get('entry_sha256', '')}",
        f"- Master valuation proxy USD: {truth.get('master_valuation_proxy_usd', 0.0):,.2f}",
        f"- Valuation increment USD: {truth.get('valuation_increment_usd', 0.0):,.2f}",
        f"- Opportunities total: {truth.get('opportunities_total', 0)}",
        "",
        "Attached:",
        "- Resume (markdown)",
        "- Resume (pdf, when available)",
        "",
        "Thank you for your time.",
        "",
        f"{name}",
        title,
        f"Email: {email}",
        f"Phone: {phone}",
        f"Website: {website}",
    ]
    return "\n".join(lines)


def make_message(
    *,
    sender: str,
    recipient: str,
    row: dict[str, Any],
    profile: dict[str, Any],
    truth: dict[str, Any],
) -> EmailMessage:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    sender_name = str(pi.get("name") or company.get("founder_pi") or "Luma Opportunity Engine")

    subject = build_subject(row)

    message = EmailMessage()
    message["From"] = f"{sender_name} <{sender}>"
    message["To"] = recipient
    message["Subject"] = subject

    src_message_id = normalize_text(row.get("message_id"))
    if src_message_id:
        message["In-Reply-To"] = src_message_id
        message["References"] = src_message_id

    sender_domain = sender.split("@", 1)[1] if "@" in sender else "lumen-core.ai"
    message["Message-ID"] = make_msgid(domain=sender_domain)

    body = build_body(profile, truth, row)
    message.set_content(body)

    if RESUME_MD_PATH.exists():
        md_text = RESUME_MD_PATH.read_text(encoding="utf-8", errors="ignore")
        message.add_attachment(md_text.encode("utf-8"), maintype="text", subtype="plain", filename="RESUME_LUMENCORE.md")

    if RESUME_PDF_PATH.exists():
        message.add_attachment(RESUME_PDF_PATH.read_bytes(), maintype="application", subtype="pdf", filename="RESUME_LUMENCORE_ELITE.pdf")

    return message


def render_markdown(summary: dict[str, Any], queue_rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Email Resume Dispatcher")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc', '')}")
    lines.append(f"Status: {summary.get('status', '')}")
    lines.append(f"Dispatch mode: {summary.get('dispatch_mode', '')}")
    lines.append(f"New sends this cycle: {summary.get('sent_count', 0)}")
    lines.append(f"Dry-run candidates this cycle: {summary.get('dry_run_count', 0)}")
    lines.append(f"Skipped this cycle: {summary.get('skipped_count', 0)}")
    lines.append(f"Total sent IDs tracked: {summary.get('sent_total', 0)}")
    lines.append("")
    lines.append("## Recent Queue")
    lines.append("")
    for row in queue_rows[:25]:
        lines.append(
            f"- id={row.get('id','')} fit={safe_float(row.get('fit_score')):.2f} "
            f"recipient={row.get('recipient','')} outcome={row.get('outcome','')}"
        )
    lines.append("")
    return "\n".join(lines)


def run_cycle(*, min_fit_score: float, limit: int, dry_run: bool) -> dict[str, Any]:
    OUT_EMAIL.mkdir(parents=True, exist_ok=True)
    OUT_OPS.mkdir(parents=True, exist_ok=True)

    queue_raw = read_json(EMAIL_QUEUE_PATH, [])
    queue_rows = [row for row in queue_raw if isinstance(row, dict)] if isinstance(queue_raw, list) else []

    profile = load_application_profile()
    truth = truth_snippet()

    state = read_json(STATE_PATH, {})
    sent_ids = state.get("sent_ids", []) if isinstance(state, dict) else []
    if not isinstance(sent_ids, list):
        sent_ids = []
    sent_set = set(str(x) for x in sent_ids)

    smtp_cfg = load_smtp_config()
    sender = str(smtp_cfg.get("from_addr") or "").strip() or str((profile.get("company") or {}).get("email") or "").strip()
    smtp_ready = bool(str(smtp_cfg.get("host") or "").strip() and sender)
    outlook_ready = bool(smtp_cfg.get("use_outlook", False))
    if dry_run:
        dispatch_mode = "dry_run"
    elif smtp_ready:
        dispatch_mode = "smtp_live"
    elif outlook_ready:
        dispatch_mode = "outlook_live"
    else:
        dispatch_mode = "disabled"

    rows_sorted = sorted(queue_rows, key=lambda r: safe_float(r.get("raw_score"), 0.0), reverse=True)

    events: list[dict[str, Any]] = []
    queue_preview: list[dict[str, Any]] = []

    sent_count = 0
    dry_run_count = 0
    skipped_count = 0
    error_count = 0

    evaluated = 0
    for row in rows_sorted:
        if evaluated >= max(1, limit):
            break

        opp_id = normalize_text(row.get("id"))
        if not opp_id:
            continue
        if opp_id in sent_set:
            continue

        fit_score = safe_float(row.get("fit_score"), min(1.0, safe_float(row.get("raw_score"), 0.0) / 15.0))
        if fit_score < min_fit_score:
            continue

        recipient = parse_email(row.get("from"))
        outcome = "pending"
        note = ""
        message_id = ""

        evaluated += 1
        if not recipient:
            outcome = "skipped"
            note = "missing_valid_recipient"
            skipped_count += 1
        else:
            try:
                msg = make_message(sender=sender, recipient=recipient, row=row, profile=profile, truth=truth)
                message_id = str(msg.get("Message-ID") or "")
                if dry_run:
                    outcome = "dry_run"
                    dry_run_count += 1
                elif smtp_ready:
                    smtp_send(msg, smtp_cfg)
                    outcome = "sent"
                    sent_count += 1
                    sent_set.add(opp_id)
                else:
                    if not outlook_ready:
                        outcome = "skipped"
                        note = "no_transport_configured"
                        skipped_count += 1
                    else:
                        subject = build_subject(row)
                        body = build_body(profile, truth, row)
                        o = outlook_send(recipient=recipient, subject=subject, body=body)
                        message_id = str(o.get("message_id") or message_id)
                        outcome = "sent"
                        note = "transport=outlook_com"
                        sent_count += 1
                        sent_set.add(opp_id)
            except Exception as exc:
                outcome = "error"
                note = str(exc)[:500]
                error_count += 1

        event = {
            "generated_utc": now_iso(),
            "action": outcome,
            "opportunity_id": opp_id,
            "recipient": recipient,
            "mailbox": normalize_text(row.get("mailbox")),
            "source_message_id": normalize_text(row.get("message_id")),
            "outbound_message_id": message_id,
            "subject": normalize_text(row.get("subject")),
            "fit_score": round(fit_score, 4),
            "opportunity_type": normalize_text(row.get("opportunity_type")),
            "note": note,
            "truth_chain_entry_sha256": str(truth.get("entry_sha256") or ""),
        }
        events.append(event)

        queue_preview.append(
            {
                "id": opp_id,
                "recipient": recipient,
                "fit_score": round(fit_score, 4),
                "opportunity_type": normalize_text(row.get("opportunity_type")),
                "outcome": outcome,
                "note": note,
            }
        )

    state_out = {
        "generated_utc": now_iso(),
        "schema": "email_resume_dispatch_state_v1",
        "sent_ids": list(sent_set)[-50000:],
        "sent_count": len(sent_set),
    }
    write_json(STATE_PATH, state_out)

    append_jsonl(LEDGER_PATH, events)

    queue_payload = {
        "generated_utc": now_iso(),
        "schema": "email_resume_dispatch_queue_v1",
        "items": queue_preview,
        "count": len(queue_preview),
    }
    write_json(QUEUE_PATH, queue_payload)

    status = "ok"
    if not dry_run and not smtp_ready and not outlook_ready:
        status = "no_transport_configured"

    summary = {
        "generated_utc": now_iso(),
        "scope": "email_resume_dispatch_cycle",
        "status": status,
        "dispatch_mode": dispatch_mode,
        "smtp_configured": smtp_ready,
        "outlook_com_enabled": outlook_ready,
        "sender": sender,
        "queue_loaded": len(queue_rows),
        "evaluated": evaluated,
        "sent_count": sent_count,
        "dry_run_count": dry_run_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "sent_total": len(sent_set),
        "min_fit_score": min_fit_score,
        "limit": limit,
        "truth": truth,
        "artifacts": {
            "latest": str(LATEST_PATH),
            "queue": str(QUEUE_PATH),
            "ledger": str(LEDGER_PATH),
            "state": str(STATE_PATH),
            "latest_markdown": str(LATEST_MD_PATH),
        },
        "events": events[:250],
    }
    write_json(LATEST_PATH, summary)
    write_text(LATEST_MD_PATH, render_markdown(summary, queue_preview))

    tag = now_tag()
    manifest = {
        "generated_utc": now_iso(),
        "schema": "email_resume_dispatch_manifest_v1",
        "status": status,
        "summary": {
            "sent_count": sent_count,
            "dry_run_count": dry_run_count,
            "skipped_count": skipped_count,
            "sent_total": len(sent_set),
        },
        "paths": {
            "latest": str(LATEST_PATH),
            "queue": str(QUEUE_PATH),
            "ledger": str(LEDGER_PATH),
            "state": str(STATE_PATH),
            "latest_markdown": str(LATEST_MD_PATH),
        },
        "sha256": {},
    }

    for p in [LATEST_PATH, QUEUE_PATH, LEDGER_PATH, STATE_PATH, LATEST_MD_PATH]:
        if p.exists():
            manifest["sha256"][str(p)] = sha256_file(p)

    manifest_tag = OUT_OPS / f"email_resume_dispatch_manifest_{tag}.json"
    write_json(manifest_tag, manifest)
    write_json(MANIFEST_LATEST, manifest)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch updated resume packets to scored email opportunities.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--interval-sec", type=int, default=300, help="Polling interval in continuous mode.")
    parser.add_argument("--min-fit-score", type=float, default=0.42, help="Minimum opportunity fit score to dispatch.")
    parser.add_argument("--limit", type=int, default=20, help="Max opportunities to evaluate per cycle.")
    parser.add_argument("--dry-run", action="store_true", help="Build dispatch candidates but do not send SMTP mail.")
    args = parser.parse_args()

    if args.once:
        summary = run_cycle(min_fit_score=args.min_fit_score, limit=args.limit, dry_run=args.dry_run)
        print(f"EMAIL_RESUME_DISPATCH_LATEST={LATEST_PATH}")
        print(f"EMAIL_RESUME_DISPATCH_QUEUE={QUEUE_PATH}")
        print(f"EMAIL_RESUME_DISPATCH_MANIFEST={MANIFEST_LATEST}")
        print(f"EMAIL_RESUME_DISPATCH_SENT={summary.get('sent_count', 0)}")
        return 0

    while True:
        try:
            summary = run_cycle(min_fit_score=args.min_fit_score, limit=args.limit, dry_run=args.dry_run)
            print(
                json.dumps(
                    {
                        "generated_utc": summary.get("generated_utc"),
                        "status": summary.get("status"),
                        "sent_count": summary.get("sent_count"),
                        "dry_run_count": summary.get("dry_run_count"),
                        "sent_total": summary.get("sent_total"),
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
