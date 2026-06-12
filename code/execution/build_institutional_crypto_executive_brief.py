import json
import os
import time
from pathlib import Path


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parents[2]))
).expanduser().resolve()
EXEC_OUT = ROOT / "out" / "execution"

REPORT_FILE = EXEC_OUT / "institutional_crypto_paper_report.json"
STATUS_FILE = EXEC_OUT / "multi_exchange_paper_ticker_status.json"
HASH_FILE = EXEC_OUT / "institutional_crypto_paper_report_sha256.json"
PDF_FILE = EXEC_OUT / "institutional_crypto_executive_brief.pdf"
MD_FILE = EXEC_OUT / "institutional_crypto_executive_brief.md"


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _f(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _fmt_usd(value: float) -> str:
    return f"${value:,.0f}"


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:,.2f}%"


def build_markdown(report: dict, status: dict, hashes: dict) -> str:
    portfolio = report.get("portfolio", {})
    audit = report.get("decision_audit", {})
    event = audit.get("last_event", {})
    seed = _f(report.get("seed_request", {}).get("active_initial_cash_usd"), 0.0)
    equity = _f(portfolio.get("equity_usd"), 0.0)
    ret = _f(portfolio.get("return_pct"), 0.0)

    lines = [
        "# Institutional Crypto Paper - Executive Brief",
        "",
        f"Generated UTC: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Mode: {report.get('mode', 'unknown')}",
        f"Profile: {report.get('profile', 'unknown')}",
        "",
        "## Portfolio",
        f"- Seed Capital: {_fmt_usd(seed)}",
        f"- Equity: {_fmt_usd(equity)}",
        f"- Cash: {_fmt_usd(_f(portfolio.get('cash_usd'), 0.0))}",
        f"- Gross Position Value: {_fmt_usd(_f(portfolio.get('gross_position_value_usd'), 0.0))}",
        f"- Realized PnL: {_fmt_usd(_f(portfolio.get('realized_pnl_usd'), 0.0))}",
        f"- Unrealized PnL: {_fmt_usd(_f(portfolio.get('unrealized_pnl_usd'), 0.0))}",
        f"- Return Since Seed: {_fmt_pct(ret)}",
        "",
        "## Decision Audit",
        f"- Regime: {audit.get('regime', 'n/a')}",
        f"- Cycle: {audit.get('cycle', 'n/a')}",
        f"- Hybrid Weight: {_f(audit.get('hybrid_weight'), 0.0):.4f}",
        f"- Breadth Positive 24h: {_fmt_pct(_f(audit.get('breadth_pos_pct24'), 0.0))}",
        f"- Last Action: {event.get('action', 'HOLD')} {event.get('symbol', '')}",
        f"- Last Notional: {_fmt_usd(_f(event.get('notional_usd'), 0.0))}",
        f"- Last Edge: {_f(event.get('edge'), 0.0):.4f}",
        "",
        "## Artifacts",
        f"- Report: {REPORT_FILE}",
        f"- Status: {STATUS_FILE}",
        f"- Hashes: {HASH_FILE}",
        f"- Dashboard: {ROOT / 'dashboard' / 'institutional_crypto_paper_dashboard.html'}",
        "",
        "## Hashes",
    ]

    for item in hashes.get("files", []):
        lines.append(f"- {Path(item.get('path', '')).name}: {item.get('sha256', '')}")

    return "\n".join(lines) + "\n"


def build_pdf(report: dict, status: dict, hashes: dict) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    portfolio = report.get("portfolio", {})
    audit = report.get("decision_audit", {})
    event = audit.get("last_event", {})

    c = canvas.Canvas(str(PDF_FILE), pagesize=letter)
    w, h = letter

    y = h - 48
    c.setFillColor(colors.HexColor("#0E141B"))
    c.rect(0, 0, w, h, stroke=0, fill=1)

    c.setFillColor(colors.HexColor("#D8B46B"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(42, y, "Institutional Crypto Paper - Executive Brief")
    y -= 22

    c.setFillColor(colors.HexColor("#F3EFE5"))
    c.setFont("Helvetica", 10)
    c.drawString(42, y, f"Generated UTC: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    y -= 16
    c.drawString(42, y, f"Mode: {report.get('mode', 'unknown')} | Profile: {report.get('profile', 'unknown')} | Regime: {audit.get('regime', 'n/a')}")

    y -= 26
    c.setFillColor(colors.HexColor("#D8B46B"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y, "Capital Snapshot")

    y -= 16
    c.setFillColor(colors.HexColor("#F3EFE5"))
    c.setFont("Helvetica", 10)
    rows = [
        f"Seed Capital: {_fmt_usd(_f(report.get('seed_request', {}).get('active_initial_cash_usd'), 0.0))}",
        f"Equity: {_fmt_usd(_f(portfolio.get('equity_usd'), 0.0))}",
        f"Cash: {_fmt_usd(_f(portfolio.get('cash_usd'), 0.0))}",
        f"Gross Position Value: {_fmt_usd(_f(portfolio.get('gross_position_value_usd'), 0.0))}",
        f"Realized PnL: {_fmt_usd(_f(portfolio.get('realized_pnl_usd'), 0.0))}",
        f"Unrealized PnL: {_fmt_usd(_f(portfolio.get('unrealized_pnl_usd'), 0.0))}",
        f"Return Since Seed: {_fmt_pct(_f(portfolio.get('return_pct'), 0.0))}",
    ]
    for row in rows:
        c.drawString(48, y, row)
        y -= 14

    y -= 10
    c.setFillColor(colors.HexColor("#D8B46B"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y, "Decision Audit")

    y -= 16
    c.setFillColor(colors.HexColor("#F3EFE5"))
    c.setFont("Helvetica", 10)
    rows = [
        f"Cycle: {audit.get('cycle', 'n/a')}",
        f"Hybrid Weight: {_f(audit.get('hybrid_weight'), 0.0):.4f}",
        f"Breadth Positive 24h: {_fmt_pct(_f(audit.get('breadth_pos_pct24'), 0.0))}",
        f"Last Action: {event.get('action', 'HOLD')} {event.get('symbol', '')}",
        f"Last Notional: {_fmt_usd(_f(event.get('notional_usd'), 0.0))}",
        f"Last Edge: {_f(event.get('edge'), 0.0):.4f}",
    ]
    for row in rows:
        c.drawString(48, y, row)
        y -= 14

    y -= 10
    c.setFillColor(colors.HexColor("#D8B46B"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y, "Chain of Custody (Top Hashes)")

    y -= 16
    c.setFillColor(colors.HexColor("#F3EFE5"))
    c.setFont("Helvetica", 8)
    for item in hashes.get("files", [])[:6]:
        name = Path(item.get("path", "")).name
        digest = str(item.get("sha256", ""))
        c.drawString(48, y, f"{name}: {digest[:56]}...")
        y -= 12

    c.setStrokeColor(colors.HexColor("#3A4652"))
    c.line(42, 38, w - 42, 38)
    c.setFillColor(colors.HexColor("#A8A198"))
    c.setFont("Helvetica", 8)
    c.drawString(42, 24, "Prepared for institutional presentation. All metrics are paper-execution artifacts with live market data inputs.")

    c.showPage()
    c.save()
    return str(PDF_FILE)


def main() -> int:
    report = load_json(REPORT_FILE, {})
    status = load_json(STATUS_FILE, {})
    hashes = load_json(HASH_FILE, {})
    if not report:
        raise SystemExit("Missing institutional crypto paper report")

    md = build_markdown(report, status, hashes)
    MD_FILE.write_text(md, encoding="utf-8")

    pdf_ok = True
    pdf_error = ""
    try:
        build_pdf(report, status, hashes)
    except Exception as exc:
        pdf_ok = False
        pdf_error = str(exc)

    summary = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "report_file": str(REPORT_FILE),
        "status_file": str(STATUS_FILE),
        "hash_file": str(HASH_FILE),
        "markdown_file": str(MD_FILE),
        "pdf_file": str(PDF_FILE),
        "pdf_ok": pdf_ok,
        "pdf_error": pdf_error,
    }
    print(json.dumps(summary, indent=2))
    # The markdown brief is the required artifact; PDF is an optional enhancement.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
