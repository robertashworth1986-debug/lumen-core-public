from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import json
import pandas as pd
from .settings import OUT, REP
from .filters import apply_filters

app = FastAPI(title="LumaScout Dashboard")


def read_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sort_by_available_columns(df: pd.DataFrame, columns, ascending=True):
    available = [col for col in columns if col in df.columns]
    if not available:
        return df
    return df.sort_values(available, ascending=ascending)


@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/ui")


@app.get("/ui", response_class=HTMLResponse)
def ui():
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LumenCore Talent Radar</title>
  <style>
    body { font-family: Inter, system-ui, sans-serif; background: #060814; color: #eef2ff; margin: 0; padding: 0; }
    header { padding: 24px; background: #0f172a; border-bottom: 1px solid #334155; }
    h1 { margin: 0 0 8px; font-size: 2rem; }
    p { margin: 0; color: #94a3b8; }
    .container { padding: 24px; }
    label { display: block; margin: 12px 0 4px; font-size: 0.95rem; color: #cbd5e1; }
    input, select { width: 100%; max-width: 320px; padding: 10px 12px; border: 1px solid #334155; border-radius: 10px; background: #0f172a; color: #f8fafc; }
    button { margin-top: 16px; padding: 12px 18px; border: none; border-radius: 10px; background: #2563eb; color: #fff; cursor: pointer; font-weight: 600; }
    button:hover { background: #1d4ed8; }
    .preset-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
    .preset-row button { background: #0f172a; border: 1px solid #334155; color: #cbd5e1; }
    .preset-row button:hover { background: #1e293b; color: #fff; }
    .status-bar { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; padding: 14px 18px; border-radius: 16px; background: #0f172a; border: 1px solid #334155; }
    .status-bar span { color: #cbd5e1; font-size: 0.95rem; }
    .status-bar span strong { color: #fff; }
    .playbook { padding: 18px; border-radius: 18px; background: rgba(31, 41, 55, 0.95); border: 1px solid #334155; margin-top: 20px; }
    .playbook h2 { margin: 0 0 10px; font-size: 1.15rem; }
    .playbook ul { margin: 0; padding-left: 18px; color: #cbd5e1; }
    .playbook li { margin-bottom: 8px; }
    .legend { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin-top: 16px; }
    .legend span { display: inline-flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 999px; background: #0f172a; color: #cbd5e1; border: 1px solid #334155; }
    .legend .hot { border-color: #ea580c; color: #fed7aa; }
    .legend .breakout { border-color: #2563eb; color: #bfdbfe; }
    .legend .live { border-color: #16a34a; color: #bbf7d0; }
    .grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); margin-top: 24px; }
    .card { padding: 18px; border-radius: 18px; background: rgba(15, 23, 42, 0.92); border: 1px solid #334155; }
    .card strong { display: block; margin-bottom: 8px; font-size: 1rem; }
    .metric { margin: 8px 0; }
    .metric span { display: inline-block; min-width: 90px; color: #cbd5e1; }
    .bar { height: 10px; border-radius: 999px; background: #0f172a; overflow: hidden; margin-top: 6px; }
    .bar-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #7c3aed); }
    .row { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; }
    .small { color: #94a3b8; }
    .badge { display: inline-flex; align-items: center; gap: 6px; background: #111827; padding: 6px 10px; border-radius: 999px; font-size: 0.82rem; }
    .badge.success { background: #14532d; color: #a7f3d0; }
    .badge.warn { background: #78350f; color: #fed7aa; }
    .research-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin-top: 16px; }
    .research-metric { padding: 16px; border-radius: 16px; background: rgba(30, 41, 59, 0.95); border: 1px solid #1e293b; }
    .research-metric strong { display: block; font-size: 0.95rem; margin-bottom: 8px; color: #e2e8f0; }
    .research-metric span { font-size: 1.4rem; color: #ffffff; }
    .research-chart { width: 100%; height: auto; margin-top: 18px; }
    .research-pill { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; background: rgba(15, 23, 42, 0.95); border: 1px solid #334155; color: #cbd5e1; font-size: 0.85rem; }
    .research-pill span { width: 10px; height: 10px; border-radius: 999px; display: inline-block; }
    .research-pill.live span { background: #22c55e; }
    .research-pill.breakout span { background: #60a5fa; }
    .research-pill.proof span { background: #fcd34d; }
    .research-pill.ideas span { background: #a78bfa; }
  </style>
</head>
<body>
  <header>
    <h1>LumaScout Prospect Radar</h1>
    <p>US-wide rolling top-20 unsigned breakout performers ready for first-call outreach.</p>
  </header>
  <div class="container">
    <div class="row">
      <div>
        <label for="genre">Genre</label>
        <input id="genre" placeholder="hiphop, country, pop" />
      </div>
      <div>
        <label for="city">City</label>
        <input id="city" placeholder="Little Rock, Nashville, Austin" />
      </div>
      <div>
        <label for="state">State</label>
        <input id="state" placeholder="Arkansas, Texas" />
      </div>
      <div>
        <label for="agt_stage">AGT Stage</label>
        <select id="agt_stage">
          <option value="">Any stage</option>
          <option value="audition">Audition</option>
          <option value="judge cuts">Judge cuts</option>
          <option value="semifinal">Semifinal</option>
          <option value="final">Final</option>
        </select>
      </div>
      <div>
        <label>&nbsp;</label>
        <button id="refresh">Refresh Top 20</button>
      </div>
    </div>
    <div class="preset-row">
      <button id="allUsa">All USA</button>
      <button id="unsignedBreakout">Unsigned Breakout</button>
      <button id="liveEventSurge">Live Event Surge</button>
      <button id="trendSurge">Trend Surge</button>
      <button id="openRadar">Open Hot Radar</button>
    </div>
    <div class="status-bar" id="statusBar">
      <span><strong>Live status:</strong> loading...</span>
      <span><strong>Scope:</strong> US-wide</span>
    </div>
    <div class="playbook">
      <h2>LumenCore Quick-Start Playbook</h2>
      <ul>
        <li><strong>All USA</strong> — scan the entire U.S. for breakout talent before the major labels catch on.</li>
        <li><strong>Unsigned Breakout</strong> — surface artists with rapid momentum but no label signal.</li>
        <li><strong>Live Event Surge</strong> — prioritize artists showing new venue or festival traction.</li>
        <li><strong>Trend Surge</strong> — surface cross-platform momentum picks with rising buzz.</li>
      </ul>
      <div class="legend">
        <span class="hot">Hot Priority</span>
        <span class="breakout">Breakout Score</span>
        <span class="live">Live Momentum</span>
      </div>
    </div>
    <div id="researchCard" class="card" style="margin-top: 24px;"></div>
    <div id="summary" class="card" style="margin-top: 24px;"></div>
    <div id="prospectGrid" class="grid"></div>
  </div>
  <script>
    const researchCard = document.getElementById('researchCard');
    const summaryEl = document.getElementById('summary');
    const prospectGrid = document.getElementById('prospectGrid');
    const genreInput = document.getElementById('genre');
    const cityInput = document.getElementById('city');
    const stateInput = document.getElementById('state');
    const agtStageInput = document.getElementById('agt_stage');
    const refreshButton = document.getElementById('refresh');

    async function loadTruth() {
      try {
        const response = await fetch('/truth');
        if (!response.ok) throw new Error('Truth data unavailable');
        const data = await response.json();
        const pulse = Math.min(100, Math.max(0, data.truth_confidence || 0));
        const ideaChips = (data.active_strategies || []).map(cluster => `<span class="research-pill ideas"><span></span>${cluster}</span>`).join('');
        const focusChips = [
          'Live Event Surge',
          'Trend Surge',
          'Unsigned Breakout',
          'Audit Proof',
        ].map(item => `<span class="research-pill breakout"><span></span>${item}</span>`).join('');
        researchCard.innerHTML = `
          <strong>Truth Dashboard</strong>
          <div class="research-grid">
            <div class="research-metric"><strong>Total artists scanned</strong><span>${data.total_artists}</span></div>
            <div class="research-metric"><strong>Live signal</strong><span>${data.live_artists}</span></div>
            <div class="research-metric"><strong>Truth confidence</strong><span>${pulse}%</span></div>
            <div class="research-metric"><strong>Strategy count</strong><span>${data.strategy_count || 0}</span></div>
          </div>
          <div class="bar" style="margin-top: 18px;">
            <div class="bar-fill" style="width:${pulse}%; background: linear-gradient(90deg, #f97316, #8b5cf6);"></div>
          </div>
          <div class="small" style="margin-top: 8px;">Truth confidence: ${pulse}% — rolling engine results from the Luma registry of live and portfolio strategies.</div>
          <div class="row" style="margin-top: 14px;">
            ${focusChips}
          </div>
          <div class="row" style="margin-top: 12px;">
            ${ideaChips}
          </div>
        `;
      } catch (error) {
        researchCard.innerHTML = '<strong>Truth Dashboard</strong><p class="small">Unable to load truth metrics. Check that the truth engine summary file exists and the dashboard API is running.</p>';
      }
    }

    async function loadSummary() {
      try {
        const response = await fetch('/summary');
        if (!response.ok) return null;
        return await response.json();
      } catch (error) {
        return null;
      }
    }

    async function loadProspects() {
      const params = new URLSearchParams();
      params.set('not_signed', 'true');
      params.set('top_n', '20');
      params.set('country', 'usa');
      if (genreInput.value) params.set('genre', genreInput.value);
      if (cityInput.value) params.set('city', cityInput.value);
      if (stateInput.value) params.set('state', stateInput.value);
      if (agtStageInput.value) params.set('agt_stage', agtStageInput.value);

      const url = `/prospects?${params.toString()}`;
      const [response, summary] = await Promise.all([fetch(url), loadSummary()]);
      const data = await response.json();
      prospectGrid.innerHTML = '';
      if (!data || data.length === 0) {
        summaryEl.innerHTML = '<strong>No unsigned breakout prospects found.</strong><p>Try widening the filters or loading more data.</p>';
        researchCard.innerHTML = '<strong>Truth Dashboard</strong><p class="small">No active prospects currently match your live research filters.</p>';
        return;
      }
      const summaryText = summary
        ? `<div class="row"><span class="badge success">${summary.hot_radar_count ?? 0} hot prospects</span><span class="badge">${summary.top_prospect_count ?? 0} breakout candidates</span></div>`
        : '';
      const lastRun = summary?.generated_utc ? new Date(summary.generated_utc).toLocaleString() : 'unknown';
      document.getElementById('statusBar').innerHTML = `
        <span><strong>Live status:</strong> ready</span>
        <span><strong>Last run:</strong> ${lastRun}</span>
        <span><strong>Hot radar:</strong> ${summary?.hot_radar_count ?? '–'}</span>
      `;
      summaryEl.innerHTML = `<strong>Top ${data.length} unsigned breakthrough prospects</strong><p>US-wide, ready for first-call outreach.</p>${summaryText}`;
      data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        const scoreBar = Math.min(100, Math.max(0, item.score_breakout || 0));
        card.innerHTML = `
          <strong>${item.artist_name}</strong>
          <div class="small">${item.genre || 'unknown genre'} • ${item.city || 'unknown city'}, ${item.state || 'unknown state'}</div>
          <div class="metric"><span>Score</span>${item.champion_score?.toFixed(1) || '0'} / 100</div>
          <div class="metric"><span>Breakout</span>${item.score_breakout?.toFixed(1) || '0'} / 100</div>
          <div class="bar"><div class="bar-fill" style="width:${scoreBar}%;"></div></div>
          <div class="metric"><span>Forecast</span>${item.predicted_breakout?.toFixed(2) || '0.00'}</div>
          <div class="metric"><span>Followers</span>${item.followers_current_total || 0}</div>
          <div class="row">
            <span class="badge ${item.label_interest ? 'warn' : 'success'}">${item.label_interest || 'Unsigned'}</span>
            <span class="badge">${item.agt_stage || 'No stage'}</span>
          </div>
        `;
        prospectGrid.appendChild(card);
      });
      loadTruth();
    }

    refreshButton.addEventListener('click', loadProspects);
    document.getElementById('allUsa').addEventListener('click', () => {
      genreInput.value = '';
      cityInput.value = '';
      stateInput.value = '';
      agtStageInput.value = '';
      loadProspects();
    });
    document.getElementById('unsignedBreakout').addEventListener('click', () => {
      genreInput.value = '';
      cityInput.value = '';
      stateInput.value = '';
      agtStageInput.value = '';
      loadProspects();
    });
    document.getElementById('liveEventSurge').addEventListener('click', () => {
      genreInput.value = '';
      cityInput.value = '';
      stateInput.value = '';
      agtStageInput.value = 'audition';
      loadProspects();
    });
    document.getElementById('trendSurge').addEventListener('click', () => {
      genreInput.value = 'hiphop';
      cityInput.value = '';
      stateInput.value = '';
      agtStageInput.value = '';
      loadProspects();
    });
    document.getElementById('openRadar').addEventListener('click', () => {
      window.location.href = '/radar';
    });
    loadProspects();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/health")
def health():
    return {"status": "ok", "service": "LumaScout"}


@app.get("/champions")
def champions(top_n: int = Query(50, ge=1, le=200)):
    path = OUT / "artist_champion_rankings.csv"
    df = read_csv(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Champion file not found")
    return df.head(top_n).to_dict(orient="records")


@app.get("/summary")
def summary():
    data = read_json(REP / "artist_scout_summary.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Summary file not found")
    return data


@app.get("/research")
def research():
    data = read_json(REP / "artist_scout_summary.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Research summary file not found")

    research_score = min(
        100,
        int(
            (data.get("hot_radar_count", 0) * 12)
            + (data.get("top_prospect_count", 0) * 8)
            + (data.get("live_artists", 0) * 3)
            + (data.get("champions", 0) * 5)
        )
    )
    return {
        "generated_utc": data.get("generated_utc"),
        "total_artists": data.get("total_artists", 0),
        "live_artists": data.get("live_artists", 0),
        "hot_radar_count": data.get("hot_radar_count", 0),
        "top_prospect_count": data.get("top_prospect_count", 0),
        "research_score": research_score,
        "current_focus": ["Live Event Surge", "Trend Surge", "Unsigned Breakout", "Audit Proof"],
        "idea_clusters": ["Venue scouting", "Platform velocity", "Label signal", "Evidence proof"],
    }


@app.get("/truth")
def truth():
    data = read_json(OUT / "truth_engine_summary.json")
    if data is None:
        data = read_json(REP / "artist_scout_summary.json")
        if data is None:
            raise HTTPException(status_code=404, detail="Truth summary file not found")
        return {
            "generated_utc": data.get("generated_utc"),
            "total_artists": data.get("total_artists", 0),
            "live_artists": data.get("live_artists", 0),
            "champions": data.get("champions", 0),
            "watchlist": data.get("watchlist", 0),
            "portfolio_size": data.get("portfolio_size", 0),
            "truth_confidence": 0,
            "rolling_truth_mean": 0,
            "rolling_truth_stdev": 0,
            "strategy_count": 0,
            "active_strategies": [],
            "monte_carlo": {},
            "evolutionary": {},
            "notes": "Truth engine summary is not yet available. Run the pipeline to generate truth metrics.",
        }
    return data


@app.get("/audit")
def audit():
    path = REP / "artist_scout_run_proof.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=404, detail="Run proof file not found")
    return payload


@app.get("/search")
def search(
    genre: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    age_group: str | None = None,
    agt_stage: str | None = None,
    tier: str | None = None,
    label_interest: str | None = None,
    not_signed: bool | None = Query(None, description="Return only unsigned prospects when true"),
    today: str | None = None,
    tomorrow: str | None = None,
    scope: str | None = None,
    top_n: int = Query(20, ge=1, le=200),
):
    path = OUT / "artist_champion_rankings.csv"
    df = read_csv(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Champion file not found")

    filtered = apply_filters(
        df,
        genre=genre,
        city=city,
        state=state,
        country=country,
        age_group=age_group,
        agt_stage=agt_stage,
        tier=tier,
        label_interest=label_interest,
        not_signed=not_signed,
        today=today,
        tomorrow=tomorrow,
        scope=scope,
    )
    return filtered.head(top_n).to_dict(orient="records")


@app.get("/prospects")
def prospects(
    genre: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    age_group: str | None = None,
    agt_stage: str | None = None,
    not_signed: bool | None = Query(True, description="Only unsigned prospects when true"),
    top_n: int = Query(20, ge=1, le=50),
):
    path = OUT / "artist_champion_rankings.csv"
    df = read_csv(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Champion file not found")

    if not country:
        country = "usa"
    filtered = apply_filters(
        df,
        genre=genre,
        city=city,
        state=state,
        country=country,
        age_group=age_group,
        agt_stage=agt_stage,
        not_signed=not_signed,
    )
    prospects_df = sort_by_available_columns(filtered, ["hot_priority", "score_breakout", "predicted_breakout"], ascending=[False, False, False]).head(top_n)
    return prospects_df.to_dict(orient="records")


@app.get("/radar")
def radar(
    genre: str | None = None,
    state: str | None = None,
    country: str | None = None,
    top_n: int = Query(20, ge=1, le=50),
):
    path = OUT / "artist_champion_rankings.csv"
    df = read_csv(path)
    if df is None:
        raise HTTPException(status_code=404, detail="Champion file not found")
    if not country:
        country = "usa"

    filtered = apply_filters(
        df,
        genre=genre,
        state=state,
        country=country,
        not_signed=True,
    )
    radar_df = sort_by_available_columns(filtered, ["hot_priority", "score_breakout", "predicted_breakout"], ascending=[False, False, False]).head(top_n)
    return radar_df.to_dict(orient="records")


@app.get("/top")
def top_by_field(
    field: str = Query(..., description="field to rank by, such as genre or city"),
    value: str = Query(..., description="value to filter on"),
    top_n: int = Query(10, ge=1, le=200),
):
    allowed = ["genre", "city", "state", "age_group", "agt_stage", "agt_age_group"]
    if field not in allowed:
        raise HTTPException(status_code=400, detail=f"Field must be one of {allowed}")
    path = OUT / f"artist_top10_by_{field}.csv"
    df = read_csv(path)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Top 10 by {field} file not found")

    filtered = df[df[field].astype(str).str.lower() == value.strip().lower()]
    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"No matching top results for {field}={value}")
    return filtered.head(top_n).to_dict(orient="records")
