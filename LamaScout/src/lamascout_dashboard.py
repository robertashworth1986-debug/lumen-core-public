"""
LamaScout Artist Intelligence Dashboard
Panel + Plotly institutional-grade UI — same harmonic aesthetic as the Trading dashboard.
Port 5017.

Run via:
    panel serve LamaScout/src/lamascout_dashboard.py --port 5017 --allow-websocket-origin=*
"""
from __future__ import annotations

import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import panel as pn
import plotly.graph_objects as go

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).resolve().parents[1]
REP    = ROOT / "reports"
DATA   = ROOT / "data" / "normalized"

SUMMARY_FILE      = REP / "artist_scout_summary.json"
TOP10_FILE        = REP / "top10_unsigned_production.csv"
SNAPSHOT_FILE     = REP / "top10_unsigned_snapshot.csv"
DELTA_FILE        = REP / "delta_history.json"
ALERTS_FILE       = REP / "artist_ping_alerts.txt"
PROOF_FILE        = REP / "artist_scout_run_proof.json"
ROLLUP_FILE       = DATA / "artist_rollup.csv"
HTML_OUT          = ROOT.parent / "dashboard" / "lamascout_dashboard.html"
HEARTBEAT_FILE    = REP / "lamascout_dashboard_heartbeat.json"

pn.extension("plotly", sizing_mode="stretch_width")

# ── colour palette (matches trading dashboard) ────────────────────────────────
VIOLET = "#9e7bdc"
GOLD   = "#dfbb6b"
TEAL   = "#56d7cb"
ICE    = "#d8e6f7"
ICE2   = "#a8c4e4"
ROSE   = "#e07baa"
WARN   = "#ffbd66"
CRIT   = "#ff7a66"
BG     = "#060b12"
LINE   = "rgba(126,172,214,0.22)"

# ── CSS — same design language as trading dashboard ───────────────────────────
SCOUT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg-main:        #060b12;
    --bg-panel:       rgba(12, 19, 29, 0.82);
    --bg-panel-soft:  rgba(16, 24, 36, 0.70);
    --line-soft:      rgba(126, 172, 214, 0.26);
    --gold:           #dfbb6b;
    --teal:           #56d7cb;
    --violet:         #9e7bdc;
    --rose:           #e07baa;
    --ice:            #d8e6f7;
    --ice2:           #a8c4e4;
    --warn:           #ffbd66;
    --crit:           #ff7a66;
}

body, .bk-root {
    background:
        radial-gradient(1200px 700px at 15% -5%,  rgba(158,123,220,0.13), transparent 55%),
        radial-gradient(900px  520px at 90% 15%,  rgba(224,123,170,0.10), transparent 50%),
        radial-gradient(600px  400px at 50% 100%, rgba(86,215,203,0.09),  transparent 46%),
        linear-gradient(145deg, #060b12 0%, #0a121d 100%);
    color: var(--ice);
    font-family: 'IBM Plex Sans', sans-serif;
}

* { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

.bk-root, .bk-root * { color: var(--ice); }

.bk-markdown, .bk-markup,
.bk-panel-models-markup-Markdown,
.bk-panel-models-markup-HTML {
    color: var(--ice) !important;
    font-size: 15px;
    line-height: 1.5;
}

.bk-markdown p, .bk-markdown li,
.bk-markdown span, .bk-markdown strong { color: var(--ice) !important; }

.bk-markdown h1, .bk-markdown h2, .bk-markdown h3 {
    font-family: 'Space Grotesk', sans-serif;
    letter-spacing: 0.2px;
}

.bk-markdown h2 { font-size: 30px; font-weight: 700; }
.bk-markdown h3 { font-size: 22px; font-weight: 700; }

.bk-Row, .bk-Column { gap: 14px; }

/* ── hero card ── */
.scout-hero {
    background: linear-gradient(120deg,
        rgba(158,123,220,0.17),
        rgba(224,123,170,0.13) 42%,
        rgba(10,18,29,0.88));
    border: 1px solid rgba(158,123,220,0.34);
    border-radius: 20px;
    padding: 20px 24px;
    box-shadow: 0 18px 60px rgba(0,0,0,0.35);
    position: relative;
    overflow: hidden;
}

.scout-hero::after {
    content: '';
    position: absolute;
    right: -70px; top: -70px;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(158,123,220,0.34), transparent 65%);
    animation: pulseOrb 4.2s ease-in-out infinite;
}

/* ── kpi grid ── */
.hero-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(120px, 1fr));
    gap: 12px;
    margin-top: 12px;
}

.hero-kpi {
    background: rgba(6,11,18,0.48);
    border: 1px solid var(--line-soft);
    border-radius: 12px;
    padding: 10px;
}

.hero-kpi-label {
    font-size: 11px;
    opacity: 0.8;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-family: 'IBM Plex Mono', monospace;
}

.hero-kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: var(--violet);
}

/* ── section headers ── */
.panel-section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    color: var(--ice2);
    padding: 8px 0 6px;
    border-bottom: 1px solid var(--line-soft);
    margin-bottom: 4px;
}

/* ── artist table ── */
.artist-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid rgba(126,172,214,0.10);
}

.artist-rank {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--ice2);
    min-width: 24px;
    text-align: right;
}

.artist-name-tag {
    font-weight: 600;
    color: var(--violet);
    font-size: 14px;
    flex: 1;
}

.score-bar-wrap {
    width: 90px;
    height: 6px;
    background: rgba(158,123,220,0.15);
    border-radius: 3px;
    overflow: hidden;
}

.score-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--violet), var(--rose));
}

/* ── tier badge ── */
.tier-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid rgba(158,123,220,0.36);
    background: rgba(158,123,220,0.12);
    color: var(--violet);
    white-space: nowrap;
}

.tier-badge.hot    { border-color: rgba(224,123,170,0.5); background: rgba(224,123,170,0.14); color: var(--rose); }
.tier-badge.pass   { border-color: rgba(126,172,214,0.3); background: rgba(126,172,214,0.08); color: var(--ice2);}

/* ── marquee ── */
.scout-marquee {
    overflow: hidden;
    padding: 8px 0;
    border-top:    1px solid var(--line-soft);
    border-bottom: 1px solid var(--line-soft);
    margin: 8px 0;
}

.scout-marquee-inner {
    display: inline-flex;
    gap: 48px;
    white-space: nowrap;
    animation: marqueeScroll 28s linear infinite;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--ice2);
    letter-spacing: 0.3px;
}

.scout-marquee-inner span { color: var(--violet); margin-right: 4px; }

/* ── phi badge ── */
.phi-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    background: rgba(158,123,220,0.12);
    border: 1px solid rgba(158,123,220,0.28);
    border-radius: 22px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--violet);
    letter-spacing: 0.3px;
}

/* ── animations ── */
@keyframes pulseOrb {
    0%, 100% { transform: scale(1);   opacity: 0.7; }
    50%       { transform: scale(1.18); opacity: 1; }
}

@keyframes marqueeScroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
"""


# ── helpers ───────────────────────────────────────────────────────────────────
PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_summary() -> dict:
    try:
        return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_top10() -> pd.DataFrame:
    try:
        df = pd.read_csv(TOP10_FILE)
        return df
    except Exception:
        return pd.DataFrame()


def _load_rollup() -> pd.DataFrame:
    try:
        df = pd.read_csv(ROLLUP_FILE)
        return df
    except Exception:
        return pd.DataFrame()


def _load_delta() -> list:
    try:
        return json.loads(DELTA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_alerts() -> str:
    try:
        return ALERTS_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "No alerts file found."


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return not df.empty and all(col in df.columns for col in columns)


def _pick_chart_frame(top10: pd.DataFrame, rollup: pd.DataFrame) -> pd.DataFrame:
    top10_required = ["artist_name", "champion_score"]
    if all(col in top10.columns for col in top10_required):
        return top10
    return rollup


def _phi_color(score: float) -> str:
    """Map score 0-100 to a phi-scaled colour between crit → violet → teal."""
    t = max(0.0, min(1.0, score / 100.0))
    # apply phi compression: emphasise upper band
    t_phi = t ** (1.0 / PHI)
    r = int(255 * (1 - t_phi) * 0.78)
    g = int(200 * t_phi * 0.55)
    b = int(220 * t_phi + 60 * (1 - t_phi))
    return f"rgb({r},{g},{b})"


# ── chart builders ────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Sans", color=ICE, size=12),
    margin=dict(l=8, r=8, t=32, b=8),
    xaxis=dict(showgrid=False, zeroline=False, color=ICE2, tickfont=dict(size=11)),
    yaxis=dict(showgrid=True,  zeroline=False, color=ICE2, tickfont=dict(size=11),
               gridcolor="rgba(126,172,214,0.10)"),
)


def _chart_top10_scores(df: pd.DataFrame) -> go.Figure:
    if not _has_columns(df, ["artist_name", "champion_score"]):
        return go.Figure(layout=PLOTLY_LAYOUT)

    names  = df["artist_name"].astype(str).tolist()[:15]
    scores = df["champion_score"].astype(float).tolist()[:15]
    colors = [_phi_color(s) for s in scores]

    fig = go.Figure(go.Bar(
        x=scores,
        y=names,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
        textfont=dict(color=ICE, size=11),
        hovertemplate="%{y}<br>Champion Score: %{x:.2f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Champion Score — φ-weighted Harmonic Ranking",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        yaxis=dict(autorange="reversed", showgrid=False, zeroline=False,
                   color=ICE2, tickfont=dict(size=11)),
        xaxis=dict(range=[0, 110], showgrid=True, zeroline=False,
                   gridcolor="rgba(126,172,214,0.10)", color=ICE2),
        height=400,
    )
    return fig


def _chart_engagement_velocity(df: pd.DataFrame) -> go.Figure:
    if not _has_columns(df, ["engagement_velocity", "artist_name", "cross_platform_strength"]):
        return go.Figure(layout=PLOTLY_LAYOUT)

    sub = df.dropna(subset=["engagement_velocity","artist_name"]).head(20)
    names = sub["artist_name"].astype(str).tolist()
    ev    = sub["engagement_velocity"].astype(float).tolist()
    cps   = sub["cross_platform_strength"].astype(float).tolist()

    # phi-scale dot size by cross-platform strength
    sizes = [max(6, min(30, (c * PHI * 20))) for c in cps]

    fig = go.Figure(go.Scatter(
        x=ev, y=names,
        mode="markers",
        marker=dict(
            size=sizes,
            color=[_phi_color(v * 100) for v in ev],
            line=dict(width=1, color="rgba(158,123,220,0.4)"),
            opacity=0.88,
        ),
        text=[f"{n}<br>EV: {v:.3f} | CPS: {c:.2f}" for n,v,c in zip(names,ev,cps)],
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Engagement Velocity vs Cross-Platform Strength (dot size = CPS)",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        yaxis=dict(autorange="reversed", showgrid=False, zeroline=False,
                   color=ICE2, tickfont=dict(size=10)),
        height=420,
    )
    return fig


def _chart_follower_distribution(df: pd.DataFrame) -> go.Figure:
    if not _has_columns(df, ["followers_current_total"]):
        return go.Figure(layout=PLOTLY_LAYOUT)

    vals = df["followers_current_total"].astype(float)
    vals = vals[vals > 0]

    # phi-harmonic bins: 0,1k,φk,2.6k,...  use log scale
    fig = go.Figure(go.Histogram(
        x=vals,
        nbinsx=28,
        marker=dict(
            color=VIOLET,
            line=dict(color="rgba(158,123,220,0.4)", width=0.8),
            opacity=0.78,
        ),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Follower Distribution — Active Unsigned Artists",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        xaxis=dict(type="log", title="Total Followers (log scale)", color=ICE2,
                   showgrid=True, gridcolor="rgba(126,172,214,0.10)"),
        yaxis=dict(title="Count", color=ICE2, showgrid=True,
                   gridcolor="rgba(126,172,214,0.10)"),
        height=320,
    )
    return fig


def _chart_platform_radar(df: pd.DataFrame) -> go.Figure:
    """Radar of average score components across all artists."""
    if df.empty:
        return go.Figure(layout=PLOTLY_LAYOUT)

    score_cols = [c for c in df.columns if c.startswith("score_")]
    if not score_cols:
        return go.Figure(layout=PLOTLY_LAYOUT)

    avgs  = df[score_cols].astype(float).mean().tolist()
    labels = [c.replace("score_","").replace("_"," ").title() for c in score_cols]

    # phi-close the loop
    avgs_r  = avgs   + [avgs[0]]
    labels_r = labels + [labels[0]]

    fig = go.Figure(go.Scatterpolar(
        r=avgs_r,
        theta=labels_r,
        fill="toself",
        fillcolor="rgba(158,123,220,0.18)",
        line=dict(color=VIOLET, width=2),
        marker=dict(size=5, color=ROSE),
        hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,100], color=ICE2,
                            gridcolor="rgba(126,172,214,0.14)", tick0=0, dtick=20),
            angularaxis=dict(color=ICE2, gridcolor="rgba(126,172,214,0.14)"),
        ),
        title=dict(text="Signal Dimension Radar — φ-Weighted Score Components",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


def _chart_delta_stability(deltas: list) -> go.Figure:
    if not deltas:
        return go.Figure(layout=PLOTLY_LAYOUT)

    rows = [d for d in deltas if d.get("stability_score") is not None][-60:]
    if not rows:
        return go.Figure(layout=PLOTLY_LAYOUT)

    xs = [r.get("generated_utc","")[:16] for r in rows]
    ys = [float(r.get("stability_score", 0)) for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        fill="tozeroy",
        fillcolor="rgba(86,215,203,0.08)",
        line=dict(color=TEAL, width=1.6),
        marker=dict(size=4, color=TEAL),
        hovertemplate="%{x}<br>Stability: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(
        title=dict(text="Delta Stability Score — Hash-Verified Proof Chain",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        yaxis=dict(range=[0,105], title="Stability %", color=ICE2, showgrid=True,
                   gridcolor="rgba(126,172,214,0.10)"),
        xaxis=dict(color=ICE2, showgrid=False, tickangle=-38),
        height=300,
    )
    return fig


def _chart_score_heatmap(df: pd.DataFrame) -> go.Figure:
    """Score component heatmap for top 20 artists."""
    if df.empty:
        return go.Figure(layout=PLOTLY_LAYOUT)

    score_cols = [c for c in df.columns if c.startswith("score_")][:12]
    if not score_cols:
        return go.Figure(layout=PLOTLY_LAYOUT)

    sub = df.head(20)
    z   = sub[score_cols].astype(float).values.tolist()
    y   = sub["artist_name"].astype(str).tolist()
    x   = [c.replace("score_","").replace("_"," ").title() for c in score_cols]

    fig = go.Figure(go.Heatmap(
        z=z, x=x, y=y,
        colorscale=[
            [0,   "rgba(6,11,18,0.9)"],
            [0.25, "rgba(158,123,220,0.5)"],
            [0.5,  "rgba(158,123,220,0.85)"],
            [0.75, "rgba(224,123,170,0.85)"],
            [1.0,  "rgba(86,215,203,1)"],
        ],
        zmin=0, zmax=100,
        hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Score Heatmap — Top 20 Artists × Signal Dimensions",
                   font=dict(family="Space Grotesk", size=13, color=ICE), x=0),
        xaxis=dict(side="bottom", tickangle=-35, color=ICE2, showgrid=False),
        yaxis=dict(autorange="reversed", color=ICE2, showgrid=False, tickfont=dict(size=10)),
        height=480,
        margin=dict(l=120, r=8, t=40, b=80),
    )
    return fig


# ── panel component builders ──────────────────────────────────────────────────

def _build_hero(summary: dict) -> pn.pane.HTML:
    ts  = summary.get("generated_utc", _now_utc())[:19].replace("T"," ")
    top = summary.get("top_live_artist", "—")
    total   = summary.get("total_artists", 0)
    live    = summary.get("live_artists",  0)
    prod    = summary.get("production_candidate_count", 0)
    top10   = summary.get("production_top10_count", 0)

    html = f"""
<div class="scout-hero">
  <div style="position:relative;z-index:1;">
    <div style="font-family:'Space Grotesk',sans-serif;font-size:13px;color:#9e7bdc;
                letter-spacing:1.2px;text-transform:uppercase;margin-bottom:6px;">
      LamaScout · Artist Intelligence Dashboard
    </div>
    <h2 style="font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700;
               color:#d8e6f7;margin:0 0 6px;">
      Breakout Discovery Engine
    </h2>
    <div style="font-size:13px;color:#a8c4e4;margin-bottom:10px;">
      φ-weighted harmonic scoring · unsigned prospect pipeline · cross-platform velocity analysis
    </div>
    <div class="phi-badge">
      φ = 1.6180339887 &nbsp;·&nbsp; Fibonacci harmonic scoring &nbsp;·&nbsp; Bubble lattice topology &nbsp;·&nbsp; {ts} UTC
    </div>
    <div class="hero-kpis">
      <div class="hero-kpi">
        <div class="hero-kpi-label">Total Artists</div>
        <div class="hero-kpi-value">{total}</div>
      </div>
      <div class="hero-kpi">
        <div class="hero-kpi-label">Live Artists</div>
        <div class="hero-kpi-value">{live}</div>
      </div>
      <div class="hero-kpi">
        <div class="hero-kpi-label">Production Candidates</div>
        <div class="hero-kpi-value">{prod}</div>
      </div>
      <div class="hero-kpi">
        <div class="hero-kpi-label">Top Prospect</div>
        <div class="hero-kpi-value" style="font-size:14px;color:#e07baa;">{top[:18]}</div>
      </div>
    </div>
    <div class="scout-marquee" style="margin-top:12px;">
      <div class="scout-marquee-inner">
        <span>TOP 10</span> {"  ·  ".join([
            f"#{i+1} {r['artist_name'][:16]}" for i, r in
            pd.read_csv(TOP10_FILE).head(10).iterrows()
        ] if TOP10_FILE.exists() else ["—"])}
        &nbsp;&nbsp;&nbsp;
        <span>TOP 10</span> {"  ·  ".join([
            f"#{i+1} {r['artist_name'][:16]}" for i, r in
            pd.read_csv(TOP10_FILE).head(10).iterrows()
        ] if TOP10_FILE.exists() else ["—"])}
      </div>
    </div>
  </div>
</div>
"""
    return pn.pane.HTML(html, sizing_mode="stretch_width")


def _build_top10_table(df: pd.DataFrame) -> pn.pane.HTML:
    if df.empty:
        return pn.pane.HTML("<p style='color:#a8c4e4'>No data.</p>")

    cols = ["artist_name","champion_score","hot_priority","followers_current_total",
            "engagement_velocity","cross_platform_strength","tier","unsigned_prospect"]
    sub  = df[[c for c in cols if c in df.columns]].head(20)

    rows_html = ""
    for i, (_, row) in enumerate(sub.iterrows()):
        name    = str(row.get("artist_name",""))[:28]
        score   = float(row.get("champion_score", 0))
        tier    = str(row.get("tier","PASS"))
        hot     = float(row.get("hot_priority", 0))
        foll    = int(float(row.get("followers_current_total", 0)))
        ev      = float(row.get("engagement_velocity", 0))
        cps     = float(row.get("cross_platform_strength", 0))
        bar_pct = max(0, min(100, score))
        tier_cls = "hot" if hot > 0 else ("pass" if tier == "PASS" else "")
        rows_html += f"""
<div class="artist-row">
  <div class="artist-rank">#{i+1}</div>
  <div class="artist-name-tag">{name}</div>
  <div style="min-width:100px;">
    <div class="score-bar-wrap">
      <div class="score-bar-fill" style="width:{bar_pct}%"></div>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#9e7bdc;margin-top:2px;">{score:.1f}</div>
  </div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#a8c4e4;min-width:80px;">
    EV {ev:.3f}
  </div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#a8c4e4;min-width:80px;">
    {foll:,} followers
  </div>
  <div class="tier-badge {tier_cls}">{tier}</div>
</div>"""

    html = f"""
<div style="background:rgba(12,19,29,0.82);border:1px solid rgba(126,172,214,0.22);
            border-radius:16px;padding:18px 20px;">
  <div class="panel-section-header">🎵 Top 20 Production Candidates · φ-Harmonic Ranked</div>
  {rows_html}
</div>"""
    return pn.pane.HTML(html, sizing_mode="stretch_width")


def _build_alerts_panel(alerts_text: str) -> pn.pane.HTML:
    lines = [ln.strip() for ln in alerts_text.split("\n") if ln.strip()][:15]
    inner = "".join(
        f'<div style="padding:5px 0;border-bottom:1px solid rgba(126,172,214,0.1);'
        f'font-family:\'IBM Plex Mono\',monospace;font-size:12px;color:#a8c4e4;">{ln}</div>'
        for ln in lines
    ) or '<div style="color:#a8c4e4;font-size:13px;">No active alerts.</div>'

    html = f"""
<div style="background:rgba(12,19,29,0.82);border:1px solid rgba(158,123,220,0.26);
            border-radius:14px;padding:16px 18px;">
  <div class="panel-section-header">🔔 Artist Ping Alerts</div>
  {inner}
</div>"""
    return pn.pane.HTML(html, sizing_mode="stretch_width")


def _build_phi_legend() -> pn.pane.HTML:
    html = """
<div style="background:rgba(12,19,29,0.6);border:1px solid rgba(158,123,220,0.20);
            border-radius:12px;padding:14px 18px;">
  <div class="panel-section-header">Mathematical Foundation</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-top:8px;">
    <div style="text-align:center;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;color:#dfbb6b;">φ 1.618</div>
      <div style="font-size:10px;color:#a8c4e4;text-transform:uppercase;letter-spacing:0.7px;">Golden Ratio · Score Weighting</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;color:#9e7bdc;">∮ ƒ(z)</div>
      <div style="font-size:10px;color:#a8c4e4;text-transform:uppercase;letter-spacing:0.7px;">Harmonic Signal Integral</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;color:#56d7cb;">⬡ lattice</div>
      <div style="font-size:10px;color:#a8c4e4;text-transform:uppercase;letter-spacing:0.7px;">Bubble Lattice · Non-Euclidean</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;color:#e07baa;">🌀 spiral</div>
      <div style="font-size:10px;color:#a8c4e4;text-transform:uppercase;letter-spacing:0.7px;">Logarithmic Spiral Efficiency</div>
    </div>
  </div>
</div>"""
    return pn.pane.HTML(html, sizing_mode="stretch_width")


# ── main layout builder ───────────────────────────────────────────────────────

def build_dashboard() -> pn.Column:
    summary = _load_summary()
    top10   = _load_top10()
    rollup  = _load_rollup()
    deltas  = _load_delta()
    alerts  = _load_alerts()

    df_chart = _pick_chart_frame(top10, rollup)

    hero          = _build_hero(summary)
    top10_table   = _build_top10_table(top10)
    alerts_panel  = _build_alerts_panel(alerts)
    phi_legend    = _build_phi_legend()

    chart_scores   = pn.pane.Plotly(_chart_top10_scores(df_chart),    height=420, sizing_mode="stretch_width")
    chart_ev       = pn.pane.Plotly(_chart_engagement_velocity(df_chart), height=440, sizing_mode="stretch_width")
    chart_dist     = pn.pane.Plotly(_chart_follower_distribution(df_chart), height=340, sizing_mode="stretch_width")
    chart_radar    = pn.pane.Plotly(_chart_platform_radar(df_chart),   height=420, sizing_mode="stretch_width")
    chart_stability = pn.pane.Plotly(_chart_delta_stability(deltas),   height=320, sizing_mode="stretch_width")
    chart_heatmap  = pn.pane.Plotly(_chart_score_heatmap(df_chart),    height=500, sizing_mode="stretch_width")

    layout = pn.Column(
        hero,
        pn.Row(chart_scores, chart_radar, sizing_mode="stretch_width"),
        pn.Row(top10_table,  sizing_mode="stretch_width"),
        pn.Row(chart_ev,     chart_dist,  sizing_mode="stretch_width"),
        chart_heatmap,
        pn.Row(chart_stability, alerts_panel, sizing_mode="stretch_width"),
        phi_legend,
        sizing_mode="stretch_width",
    )
    return layout


# ── static HTML export ────────────────────────────────────────────────────────

def write_static_html() -> None:
    pn.config.raw_css = [SCOUT_CSS]
    template = pn.template.FastListTemplate(
        title="LamaScout · Artist Intelligence",
        raw_css=[SCOUT_CSS],
        theme_toggle=False,
        main=[build_dashboard()],
        header_background="#060b12",
        accent_base_color=VIOLET,
    )
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    template.save(str(HTML_OUT))
    print(f"[LamaScout] Static HTML -> {HTML_OUT}")


# ── Panel serve entry-point ───────────────────────────────────────────────────

def _heartbeat_loop() -> None:
    while True:
        try:
            HEARTBEAT_FILE.write_text(
                json.dumps({"ts": _now_utc(), "status": "alive"}), encoding="utf-8"
            )
        except Exception:
            pass
        time.sleep(30)


pn.config.raw_css = [SCOUT_CSS]

threading.Thread(target=_heartbeat_loop, daemon=True).start()

template = pn.template.FastListTemplate(
    title="LamaScout · Artist Intelligence",
    raw_css=[SCOUT_CSS],
    theme_toggle=False,
    main=[build_dashboard()],
    header_background="#060b12",
    accent_base_color=VIOLET,
)
template.servable()


if __name__ == "__main__":
    write_static_html()
