from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

DASH = Path(r"C:\LumaTrader\dashboard")
OUT = DASH / "luma_experience.html"


def main() -> None:
    DASH.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>LumaCore Immersive Experience</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
  <link href=\"https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap\" rel=\"stylesheet\" />
  <style>
    :root {{
      --bg0:#04060d;
      --bg1:#091f2f;
      --ink:#ecf4ff;
      --muted:#97abc1;
      --teal:#66f8d7;
      --gold:#ffdc7c;
      --panel:rgba(8,17,34,.58);
      --line:rgba(130,200,255,.22);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; color:var(--ink); font-family:'Sora',Segoe UI,sans-serif; background:linear-gradient(155deg,var(--bg0),var(--bg1)); overflow:hidden; }}
    #scene {{ position:fixed; inset:0; z-index:0; }}
    .hud {{ position:relative; z-index:2; display:grid; grid-template-columns:1.2fr .8fr; gap:16px; height:100vh; padding:20px; }}
    .glass {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; backdrop-filter: blur(8px); box-shadow:0 24px 60px rgba(0,0,0,.45); }}
    .left {{ padding:22px; display:flex; flex-direction:column; }}
    .right {{ padding:18px; overflow:auto; }}
    .tag {{ display:inline-flex; padding:8px 12px; border-radius:999px; border:1px solid rgba(255,255,255,.12); color:var(--gold); font-family:'Space Grotesk',sans-serif; font-size:.74rem; letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ margin:12px 0 8px 0; font-size:clamp(1.9rem,3.5vw,3.3rem); line-height:1.02; letter-spacing:-.02em; }}
    p {{ margin:0; color:var(--muted); line-height:1.6; }}
    .kpis {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }}
    .kpi {{ padding:14px; border-radius:14px; border:1px solid rgba(255,255,255,.11); background:rgba(255,255,255,.03); }}
    .k-label {{ color:var(--muted); font-size:.72rem; letter-spacing:.11em; text-transform:uppercase; font-family:'Space Grotesk',sans-serif; }}
    .k-value {{ margin-top:6px; font-size:1.45rem; font-weight:800; color:var(--teal); }}
    .k-value.warn {{ color:#ff8f8f; }}
    .control-row {{ margin-top:16px; display:flex; flex-wrap:wrap; gap:10px; }}
    .btn {{ border:0; border-radius:12px; padding:10px 14px; font:inherit; font-weight:700; cursor:pointer; }}
    .btn.primary {{ color:#051220; background:linear-gradient(135deg,var(--gold),#fff0b4); }}
    .btn.ghost {{ color:var(--ink); border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.03); }}
    .log {{ margin-top:14px; border:1px solid rgba(255,255,255,.11); border-radius:12px; padding:12px; max-height:34vh; overflow:auto; background:rgba(6,12,24,.55); font-size:.88rem; color:#cde5ff; }}
    .voice {{ margin-top:14px; display:grid; gap:10px; }}
    select,input[type=range] {{ width:100%; background:rgba(255,255,255,.08); color:var(--ink); border:1px solid rgba(255,255,255,.15); border-radius:8px; padding:8px; }}
    .small {{ font-size:.78rem; color:var(--muted); }}
    /* Harmonic edge panel */
    .harmonic-panel {{ margin-top:18px; }}
    .h-row {{ display:grid; grid-template-columns:2fr 1fr 1fr; gap:6px; padding:7px 10px; border-radius:9px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.03); margin-bottom:5px; font-size:.78rem; }}
    .h-row:hover {{ background:rgba(102,248,215,.06); }}
    .h-domain {{ display:inline-block; padding:1px 7px; border-radius:99px; font-size:.66rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }}
    .hd-crypto  {{ background:rgba(102,248,215,.18); color:#66f8d7; }}
    .hd-sports  {{ background:rgba(255,220,124,.18); color:#ffdc7c; }}
    .hd-infra   {{ background:rgba(167,139,250,.18); color:#a78bfa; }}
    .hd-other   {{ background:rgba(255,255,255,.12); color:#cde5ff; }}
    .h-score    {{ font-weight:800; color:var(--teal); text-align:right; }}
    .h-edge     {{ font-weight:600; color:var(--gold); text-align:right; }}
    .h-asset    {{ color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .h-phi-bar  {{ height:4px; border-radius:2px; background:linear-gradient(90deg,#66f8d7,#ffdc7c); margin-top:8px; transition:width .6s ease; }}
    .section-head {{ font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-family:'Space Grotesk',sans-serif; margin:14px 0 6px; }}
    @media (max-width:1100px) {{ .hud {{ grid-template-columns:1fr; overflow:auto; }} body {{ overflow:auto; }} }}
  </style>
</head>
<body>
  <canvas id=\"scene\"></canvas>
  <div class=\"hud\">
    <section class=\"left glass\">
      <span class=\"tag\">Luma Immersive Beta</span>
      <h1>LumaCore Experience Console</h1>
      <p>Luma is your active front-end guide. This scene streams live portfolio, infrastructure, and scout intelligence from your stack in real time.</p>
      <div class=\"kpis\">
        <div class=\"kpi\"><div class=\"k-label\">Paper Equity</div><div id=\"kEquity\" class=\"k-value\">$0</div></div>
        <div class=\"kpi\"><div class=\"k-label\">Net PnL</div><div id=\"kPnl\" class=\"k-value\">$0</div></div>
        <div class=\"kpi\"><div class=\"k-label\">Top Lane</div><div id=\"kLane\" class=\"k-value\">n/a</div></div>
        <div class=\"kpi\"><div class=\"k-label\">Closed Trades</div><div id=\"kTrades\" class=\"k-value\">0</div></div>
        <div class=\"kpi\"><div class=\"k-label\">Top Artist</div><div id=\"kArtist\" class=\"k-value\">n/a</div></div>
        <div class=\"kpi\"><div class=\"k-label\">Status</div><div id=\"kStatus\" class=\"k-value\">CONNECTING</div></div>
      </div>
      <div class=\"control-row\">
        <button id=\"speak\" class=\"btn primary\">Speak Luma Brief</button>
        <button id=\"stop\" class=\"btn ghost\">Stop</button>
        <button id=\"askAnalyst\" class=\"btn ghost\">Analyst Mode</button>
        <button id=\"askPitch\" class=\"btn ghost\">Pitch Mode</button>
      </div>
      <div id=\"log\" class=\"log\"></div>
      <div class=\"small\" style=\"margin-top:10px;\">Generated UTC: {generated}</div>
    </section>
    <aside class=\"right glass\">
      <span class=\"tag\">Voice Controls</span>
      <div class=\"voice\">
        <label class=\"small\">Voice</label>
        <select id=\"voiceSelect\"><option value=\"default\">Default OS Voice</option></select>
        <label class=\"small\">Speed</label>
        <input id=\"speed\" type=\"range\" min=\"0.5\" max=\"1.8\" step=\"0.1\" value=\"1.0\" />
        <label class=\"small\">Volume</label>
        <input id=\"volume\" type=\"range\" min=\"0\" max=\"1\" step=\"0.1\" value=\"1\" />
      </div>
      <div style=\"margin-top:16px;\" class=\"small\">Roadmap hooks ready for XR hand tracking, suit haptics, and spatial audio routing through Unity or OpenXR runtimes.</div>      <div class="section-head">&#9670; Live Harmonic Edge Signals</div>
      <div class="kpis" style="grid-template-columns:repeat(3,1fr);margin-bottom:10px">
        <div class="kpi"><div class="k-label">Top Score</div><div id="hTopScore" class="k-value">--</div></div>
        <div class="kpi"><div class="k-label">Domain</div><div id="hTopDomain" class="k-value" style="font-size:1rem">--</div></div>
        <div class="kpi"><div class="k-label">Total Signals</div><div id="hTotalSigs" class="k-value">0</div></div>
      </div>
      <div class="h-phi-bar" id="hPhiBar" style="width:0%"></div>
      <div class="harmonic-panel" id="harmonicList"></div>    </aside>
  </div>

  <script src=\"https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.min.js\"></script>
  <script>
    const logEl = document.getElementById('log');
    const API_BASE = window.location.port === '8787' ? '' : 'http://127.0.0.1:8787';
    const kEquity = document.getElementById('kEquity');
    const kPnl = document.getElementById('kPnl');
    const kLane = document.getElementById('kLane');
    const kTrades = document.getElementById('kTrades');
    const kArtist = document.getElementById('kArtist');
    const kStatus = document.getElementById('kStatus');
    const voiceSelect = document.getElementById('voiceSelect');
    // Harmonic panel elements
    const hTopScore  = document.getElementById('hTopScore');
    const hTopDomain = document.getElementById('hTopDomain');
    const hTotalSigs = document.getElementById('hTotalSigs');
    const hPhiBar    = document.getElementById('hPhiBar');
    const harmonicList = document.getElementById('harmonicList');
    const speed = document.getElementById('speed');
    const volume = document.getElementById('volume');
    let snapshot = null;
    const sceneCue = {{
      intensity: 0.5,
      warning: false,
      pulseUntil: 0,
    }};

    function log(message) {{
      const row = document.createElement('div');
      row.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
      logEl.prepend(row);
    }}

    function setStatus(text, danger=false) {{
      kStatus.textContent = text;
      kStatus.classList.toggle('warn', danger);
    }}

    function applySnapshot(data) {{
      snapshot = data;
      kEquity.textContent = data.paper.equity_text;
      kPnl.textContent = data.paper.net_pnl_text;
      kPnl.classList.toggle('warn', Number(data.paper.net_pnl || 0) < 0);
      kLane.textContent = data.infra.top_lane || 'n/a';
      kTrades.textContent = String(data.paper.closed_trades || 0);
      kArtist.textContent = data.scout.top_artist || 'n/a';
      setStatus('LIVE', false);
      if (data.harmonic) applyHarmonic(data.harmonic);
    }}

    function domainClass(d) {{
      if (d === 'crypto') return 'hd-crypto';
      if (d === 'sports') return 'hd-sports';
      if (d === 'infra')  return 'hd-infra';
      return 'hd-other';
    }}

    function applyHarmonic(h) {{
      if (!h) return;
      const score = Number(h.top_score || 0);
      hTopScore.textContent  = score.toFixed(1);
      hTopDomain.textContent = (h.top_domain || 'n/a').toUpperCase();
      hTotalSigs.textContent = String(h.total_signals || 0);
      hPhiBar.style.width    = score + '%';
      // Render top signal rows
      const signals = h.top_signals || [];
      harmonicList.innerHTML = signals.slice(0, 8).map(function(sig) {{
        var ff    = sig.flowform || {{}};
        var sc    = Number(ff.hybrid_harmonic_score || 0).toFixed(1);
        var ep    = Number(sig.edge_pct || 0).toFixed(2);
        var asset = String(sig.asset || '').substring(0, 32);
        var dCls  = domainClass(sig.domain || '');
        return '<div class="h-row">' +
          '<span class="h-asset"><span class="h-domain ' + dCls + '">' + (sig.domain || '?') + '</span> ' + asset + '</span>' +
          '<span class="h-score">' + sc + '</span>' +
          '<span class="h-edge">' + ep + '%</span>' +
        '</div>';
      }}).join('');
    }}

    function loadVoices() {{
      if (!('speechSynthesis' in window)) return;
      const voices = speechSynthesis.getVoices();
      if (!voices.length) {{ setTimeout(loadVoices, 120); return; }}
      voiceSelect.innerHTML = '<option value="default">Default OS Voice</option>';
      voices.forEach((v, i) => {{
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = `${{v.name}} (${{v.lang}})`;
        voiceSelect.appendChild(opt);
      }});
    }}

    function speak(text) {{
      if (!('speechSynthesis' in window)) return;
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = parseFloat(speed.value);
      u.volume = parseFloat(volume.value);
      u.pitch = 1.0;
      if (voiceSelect.value !== 'default') {{
        const voices = speechSynthesis.getVoices();
        const idx = parseInt(voiceSelect.value, 10);
        if (voices[idx]) u.voice = voices[idx];
      }}
      speechSynthesis.speak(u);
    }}

    async function askGuide(mode) {{
      try {{
        const r = await fetch(`${{API_BASE}}/api/guide/respond`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ prompt: 'brief', mode }}),
        }});
        const payload = await r.json();
        log(payload.response);
        speak(payload.response);
        await sendSessionEvent('guide_request', {{ mode, history_size: payload.history_size || 0 }});
      }} catch (err) {{
        log('Guide request failed: ' + err);
      }}
    }}

    async function sendSessionEvent(eventName, detail = {{}}) {{
      try {{
        await fetch(`${{API_BASE}}/api/session/event`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ event: eventName, source: 'immersive_web', detail }}),
        }});
      }} catch (err) {{
        log('Session event failed: ' + err);
      }}
    }}

    function applySceneCue(data) {{
      const cue = (data && data.cue) ? String(data.cue) : 'pulse';
      const intensity = Number((data && data.intensity) || 0.5);
      sceneCue.intensity = Math.max(0.05, Math.min(1.0, intensity));
      sceneCue.warning = cue.includes('warning') || cue.includes('loss') || cue.includes('critical');
      sceneCue.pulseUntil = performance.now() + 2200;
      log(`Scene cue: ${{cue}} @ ${{sceneCue.intensity.toFixed(2)}}`);
      document.body.style.transition = 'filter 180ms ease';
      document.body.style.filter = sceneCue.warning ? 'saturate(1.2) contrast(1.08)' : 'saturate(1.05)';
      setTimeout(() => {{ document.body.style.filter = ''; }}, 1200);
    }}

    async function bootSnapshot() {{
      try {{
        const r = await fetch(`${{API_BASE}}/api/snapshot`);
        applySnapshot(await r.json());
        log('Loaded initial snapshot');
      }} catch (err) {{
        setStatus('OFFLINE', true);
        log('Initial snapshot failed: ' + err);
      }}
    }}

    function connectWs() {{
      const wsUrl = API_BASE ? API_BASE.replace('http', 'ws') + '/ws/live' : `${{window.location.protocol === 'https:' ? 'wss' : 'ws'}}://${{window.location.host}}/ws/live`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => {{ setStatus('LIVE', false); log('WS connected'); ws.send('hello'); }};
      ws.onmessage = (evt) => {{
        try {{
          const msg = JSON.parse(evt.data);
          if (msg.type === 'snapshot' && msg.data) applySnapshot(msg.data);
          if (msg.type === 'scene_cue' && msg.data) applySceneCue(msg.data);
          if (msg.type === 'nodered_signal' && msg.data && msg.data.data) applyHarmonic(msg.data.data);
          if (msg.type === 'keepalive') return;
        }} catch (err) {{
          log('WS parse error: ' + err);
        }}
      }};
      ws.onclose = () => {{ setStatus('RETRY', true); log('WS closed, reconnecting'); setTimeout(connectWs, 1800); }};
      ws.onerror = () => {{ setStatus('ERROR', true); }};
      setInterval(() => {{ if (ws.readyState === WebSocket.OPEN) ws.send('ping'); }}, 4000);
    }}

    function setupScene() {{
      const canvas = document.getElementById('scene');
      const renderer = new THREE.WebGLRenderer({{ canvas, antialias:true, alpha:true }});
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.set(0, 0, 10);

      const geom = new THREE.IcosahedronGeometry(2.4, 2);
      const mat = new THREE.MeshStandardMaterial({{
        color: 0x59f3d0,
        emissive: 0x124245,
        roughness: 0.2,
        metalness: 0.6,
        wireframe: true,
      }});
      const core = new THREE.Mesh(geom, mat);
      scene.add(core);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(3.5, 0.05, 16, 130),
        new THREE.MeshBasicMaterial({{ color: 0xffdc7c }})
      );
      ring.rotation.x = 1.2;
      scene.add(ring);

      const lightA = new THREE.PointLight(0x66f8d7, 1.3, 60);
      lightA.position.set(5, 4, 8);
      scene.add(lightA);
      const lightB = new THREE.PointLight(0x5b86ff, 1.1, 60);
      lightB.position.set(-6, -4, 5);
      scene.add(lightB);
      const bgColor = new THREE.Color(0x091f2f);

      function resize() {{
        const w = window.innerWidth;
        const h = window.innerHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }}
      resize();
      window.addEventListener('resize', resize);

      function animate(t) {{
        const n = t * 0.001;
        const pulse = performance.now() < sceneCue.pulseUntil ? (0.55 + 0.45 * Math.sin(n * 6.5)) : 0.0;
        const cuePower = sceneCue.intensity * (0.35 + pulse);
        core.rotation.x = n * 0.22;
        core.rotation.y = n * 0.31;
        ring.rotation.z = n * 0.35;
        ring.rotation.y = Math.sin(n * 0.7) * 0.45;
        const tone = sceneCue.warning ? new THREE.Color(1.0, 0.28, 0.28) : new THREE.Color(0.35, 0.95, 0.84);
        mat.color.lerp(tone, 0.08);
        mat.emissive.setRGB(tone.r * cuePower, tone.g * cuePower, tone.b * cuePower);
        lightA.color = tone;
        lightA.intensity = 1.1 + 2.4 * cuePower;
        lightB.intensity = 0.8 + 1.7 * cuePower;
        renderer.setClearColor(bgColor, 0.0);
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
      }}
      requestAnimationFrame(animate);
    }}

    document.getElementById('speak').addEventListener('click', () => askGuide('concierge'));
    document.getElementById('askAnalyst').addEventListener('click', () => askGuide('analyst'));
    document.getElementById('askPitch').addEventListener('click', () => askGuide('pitch'));
    document.getElementById('stop').addEventListener('click', () => speechSynthesis && speechSynthesis.cancel());

    setupScene();
    loadVoices();
    if ('onvoiceschanged' in speechSynthesis) speechSynthesis.onvoiceschanged = loadVoices;
    sendSessionEvent('immersive_loaded', {{ page: 'luma_experience' }});
    bootSnapshot();
    connectWs();
  </script>
</body>
</html>
"""

    OUT.write_text(html, encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
