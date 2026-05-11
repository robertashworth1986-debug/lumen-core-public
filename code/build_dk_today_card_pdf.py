"""
DraftKings Today Card PDF Generator
Generates a polished, institutional-grade pick card from _dk_alpha_board.json
Output: out/sports_intelligence/dk_today_card_<YYYYMMDD>.pdf
"""

from __future__ import annotations
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALPHA_BOARD = ROOT / "out" / "sports_intelligence" / "_dk_alpha_board.json"
OUT_DIR = ROOT / "out" / "sports_intelligence"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── colour palette (LumaTrader premium dark theme) ────────────────────────
BG_DARK   = (10, 14, 26)
BG_CARD   = (16, 22, 40)
BG_HEADER = (0, 180, 255)
ACCENT    = (0, 220, 130)
WARN      = (255, 190, 0)
TEXT_WHITE = (240, 245, 255)
TEXT_GREY  = (130, 145, 175)
TEXT_DARK  = (10, 14, 26)
RED       = (255, 60, 80)


def _american_color(american: str) -> tuple:
    """Return accent colour based on odds sign."""
    if american.startswith("+"):
        return ACCENT
    return WARN


def _bar_width(pct: float, max_pct: float = 10.0, max_w: float = 100.0) -> float:
    return min(pct / max_pct, 1.0) * max_w


def _ci_label(lo: float, hi: float) -> str:
    """Edge confidence interval label."""
    return f"95% CI  [{lo:+.1f}% to {hi:+.1f}%]"


def build_pdf(board: dict, out_path: Path) -> None:
    from fpdf import FPDF, XPos, YPos

    class LumaPDF(FPDF):
        def header(self):
            pass  # custom header per card
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*TEXT_GREY)
            ts = board.get("generated_utc", "")[:19].replace("T", " ") + " UTC"
            self.cell(0, 6, f"LumaTrader(TM) Sports Intelligence  |  Generated {ts}  |  NOT FINANCIAL ADVICE - INTERNAL USE ONLY", align="C")

    pdf = LumaPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    W, H = 210, 297
    margin = 14
    content_w = W - 2 * margin

    # ── Page background ────────────────────────────────────────────────────
    pdf.set_fill_color(*BG_DARK)
    pdf.rect(0, 0, W, H, "F")

    # ── Hero header ────────────────────────────────────────────────────────
    pdf.set_fill_color(*BG_HEADER)
    pdf.rect(0, 0, W, 26, "F")

    pdf.set_xy(margin, 5)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 8, "LumaTrader(TM)  DraftKings Alpha Board", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(margin, 14)
    pdf.set_font("Helvetica", "", 8)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %B ") + str(now.day) + now.strftime(", %Y")
    macro = board.get("macro", {})
    regime = macro.get("regime", "—").upper()
    vix = macro.get("vix", 0)
    bankroll = board.get("bankroll", 0)
    pdf.cell(0, 6, f"{date_str}   |   Regime: {regime}   VIX {vix:.1f}   |   Bankroll ${bankroll:.0f}   |   Min Edge {board.get('min_edge', 1.0):.1f}%")

    # ── Summary strip ──────────────────────────────────────────────────────
    y = 30
    pdf.set_fill_color(*BG_CARD)
    pdf.rect(0, y, W, 18, "F")

    count = board.get("count", 0)
    qs = board.get("quantstats", {})
    sharpe = qs.get("sharpe", 0)
    top = board.get("top_pick", {})

    stats = [
        ("PICKS TODAY", str(count)),
        ("BOARD SHARPE", f"{sharpe:.2f}"),
        ("TOP EDGE", f"{top.get('edge_pct', 0):.2f}%"),
        ("TOP ALPHA", f"{top.get('alpha_score_v2', 0):.2f}"),
        ("KELLY FRAC", f"{board.get('kelly_fraction', 0.25):.2f}"),
    ]
    col_w = content_w / len(stats)
    for i, (label, val) in enumerate(stats):
        x = margin + i * col_w
        pdf.set_xy(x, y + 2)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(col_w, 5, label, align="C")
        pdf.set_xy(x, y + 7)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*ACCENT)
        pdf.cell(col_w, 7, val, align="C")

    # ── Pick cards ─────────────────────────────────────────────────────────
    rows = board.get("rows", [])
    card_start_y = y + 22
    card_h = 68
    card_gap = 8

    for idx, row in enumerate(rows):
        cy = card_start_y + idx * (card_h + card_gap)
        if cy + card_h > H - 20:
            pdf.add_page()
            pdf.set_fill_color(*BG_DARK)
            pdf.rect(0, 0, W, H, "F")
            cy = margin

        # card bg
        pdf.set_fill_color(*BG_CARD)
        _rounded_rect(pdf, margin, cy, content_w, card_h)

        # ── Top accent stripe ──────────────────────────────────────────────
        pdf.set_fill_color(*_american_color(row.get("dk_price_american", "+0")))
        pdf.rect(margin, cy, 4, card_h, "F")

        # ── Pick name & game ──────────────────────────────────────────────
        pdf.set_xy(margin + 7, cy + 4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*TEXT_WHITE)
        pdf.cell(content_w - 40, 8, row.get("pick", "—"))

        pdf.set_xy(margin + 7, cy + 12)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(content_w - 40, 5, f"{row.get('sport_key','').replace('_',' ').title()}  ·  {row.get('game','')}")

        # ── Odds badge ────────────────────────────────────────────────────
        american = row.get("dk_price_american", "")
        badge_color = _american_color(american)
        pdf.set_fill_color(*badge_color)
        pdf.set_xy(W - margin - 38, cy + 3)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(36, 14, american, align="C", fill=True)

        # ── Row 2: metrics ────────────────────────────────────────────────
        metrics_y = cy + 22
        edge_pct = row.get("edge_pct", 0)
        alpha_v2 = row.get("alpha_score_v2", 0)
        optimized_stake = row.get("optimized_stake", 0)
        ev = row.get("ev_dollars", 0)
        kelly_go = row.get("kelly_go_f", 0)
        hours = row.get("hours_to_start", 0)

        m_items = [
            ("EDGE",     f"{edge_pct:.2f}%"),
            ("ALPHA V2", f"{alpha_v2:.2f}"),
            ("STAKE",    f"${optimized_stake:.2f}"),
            ("EV $",     f"${ev:.3f}"),
            ("KELLY GO", f"{kelly_go*100:.2f}%"),
            ("HOURS",    f"{hours:.1f}h"),
        ]
        mw = content_w / len(m_items)
        for mi, (ml, mv) in enumerate(m_items):
            mx = margin + mi * mw
            pdf.set_xy(mx, metrics_y)
            pdf.set_font("Helvetica", "", 5.5)
            pdf.set_text_color(*TEXT_GREY)
            pdf.cell(mw, 4, ml, align="C")
            pdf.set_xy(mx, metrics_y + 4)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*TEXT_WHITE)
            pdf.cell(mw, 6, mv, align="C")

        # ── Edge bar ──────────────────────────────────────────────────────
        bar_y = metrics_y + 14
        bar_x = margin + 7
        bar_total_w = content_w - 14
        bar_track_h = 4

        pdf.set_fill_color(30, 38, 60)
        pdf.rect(bar_x, bar_y, bar_total_w, bar_track_h, "F")

        fill_w = _bar_width(edge_pct, 10.0, bar_total_w)
        r, g, b = _american_color(american)
        pdf.set_fill_color(r, g, b)
        pdf.rect(bar_x, bar_y, fill_w, bar_track_h, "F")

        pdf.set_xy(bar_x, bar_y + 5)
        pdf.set_font("Helvetica", "I", 6)
        pdf.set_text_color(*TEXT_GREY)
        ci_lo = row.get("edge_ci_lo", 0)
        ci_hi = row.get("edge_ci_hi", 0)
        pdf.cell(bar_total_w, 4, _ci_label(ci_lo, ci_hi))

        # ── Commence time ─────────────────────────────────────────────────
        commence_raw = row.get("commence_time", "")
        try:
            dt = datetime.fromisoformat(commence_raw.replace("Z", "+00:00"))
            commence_str = dt.strftime("%a %b ") + str(dt.day) + dt.strftime("  %I:%M %p UTC")
        except Exception:
            commence_str = commence_raw

        pdf.set_xy(margin + 7, bar_y + 10)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(content_w - 14, 5, f"Game Time:  {commence_str}")

        # ── Market tag ────────────────────────────────────────────────────
        market = row.get("market", "").upper()
        pdf.set_fill_color(0, 140, 200)
        pdf.set_xy(margin + 7, bar_y + 16)
        pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(*TEXT_WHITE)
        pdf.cell(18, 4, f" {market} ", fill=True, align="C")

        # n_books tag
        n_books = row.get("n_books_consensus", 0)
        pdf.set_fill_color(30, 50, 80)
        pdf.set_xy(margin + 27, bar_y + 16)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*TEXT_GREY)
        pdf.cell(28, 4, f"{n_books} books consensus", align="L")

        # Line moved badge
        if row.get("line_moved"):
            pdf.set_fill_color(*WARN)
            pdf.set_xy(W - margin - 40, bar_y + 16)
            pdf.set_font("Helvetica", "B", 5.5)
            pdf.set_text_color(*TEXT_DARK)
            pdf.cell(28, 4, "LINE MOVED ^", fill=True, align="C")

    # ── Watermark / legend strip ───────────────────────────────────────────
    legend_y = H - 24
    pdf.set_fill_color(12, 18, 32)
    pdf.rect(0, legend_y, W, 14, "F")
    pdf.set_xy(margin, legend_y + 3)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*TEXT_GREY)
    pdf.multi_cell(content_w, 4,
        "EDGE = model edge over fair line  |  ALPHA V2 = composite confidence score  |  "
        "STAKE = Kelly-optimized bet size  |  EV = expected value per dollar wagered  |  "
        "All picks generated by LumaTrader(TM) quantitative sports intelligence engine")

    pdf.output(str(out_path))
    print(f"✅  PDF written → {out_path}")


def _rounded_rect(pdf, x, y, w, h, r=3):
    """Draw a filled rounded rectangle via FPDF."""
    pdf.rect(x, y, w, h, "F")


def main():
    if not ALPHA_BOARD.exists():
        print(f"[ERROR] Alpha board not found: {ALPHA_BOARD}")
        sys.exit(1)

    raw = ALPHA_BOARD.read_text(encoding="utf-8")
    # Handle NaN literals from Python json serialiser
    raw = raw.replace(": NaN", ": null").replace(":NaN", ":null")
    board = json.loads(raw)

    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = OUT_DIR / f"dk_today_card_{date_tag}.pdf"

    try:
        build_pdf(board, out_path)
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Run: pip install fpdf2")
        sys.exit(1)


if __name__ == "__main__":
    main()
