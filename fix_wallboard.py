#!/usr/bin/env python3
"""Upgrade investor_wallboard.html with LumaDS integrations."""
from pathlib import Path

SRC = Path("dashboard/investor_wallboard.html")

with open(SRC, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add luma_design_system.js before </head>
content = content.replace(
    "</head>",
    '  <script src="js/luma_design_system.js"></script>\n</head>',
    1
)

# 2. Add Node-RED status indicator below LIVE SYSTEM badge
content = content.replace(
    '      <span class="live-badge"><span class="live-dot-g"></span>LIVE SYSTEM</span>',
    '      <span class="live-badge"><span class="live-dot-g"></span>LIVE SYSTEM</span>\n'
    '      <div id="nr-hdr" style="margin-top:6px;font-size:11px"></div>'
)

# 3. Integration panels to insert before refresh-bar
integration_panels = """
  <!-- Gateway Snapshot KPIs -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0;">
    <div class="kpi-card"><div class="kpi-lbl">Gateway Equity</div><div class="kpi-val" id="snapEquity">—</div></div>
    <div class="kpi-card teal"><div class="kpi-lbl">Gateway PnL</div><div class="kpi-val" id="snapPnl">—</div></div>
    <div class="kpi-card green"><div class="kpi-lbl">Win Rate</div><div class="kpi-val" id="snapWinRate">—</div></div>
    <div class="kpi-card violet"><div class="kpi-lbl">Closed Trades</div><div class="kpi-val" id="snapClosedTrades">—</div></div>
  </div>

  <!-- Unity + Node-RED row -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:0 0 24px;">
    <div class="panel-card">
      <div class="panel-header">
        <div>
          <div class="panel-title">Unity Edge Intelligence</div>
          <div class="panel-sub">XR harmonic node network &middot; live &phi; topology</div>
        </div>
      </div>
      <div style="padding:16px;">
        <div style="font-size:13px;color:var(--ice2)">Node Count: <span id="unityNodeCount" style="color:var(--teal);font-weight:700">—</span></div>
        <div id="unity-top" style="margin-top:10px;font-size:12px;color:var(--ice2)">Awaiting Unity edge data&hellip;</div>
      </div>
    </div>
    <div class="panel-card">
      <div class="panel-header">
        <div>
          <div class="panel-title">Node-RED Live Feed</div>
          <div class="panel-sub">Real-time ingest bus &middot; ws://localhost:7700/ws</div>
        </div>
      </div>
      <div style="padding:16px;">
        <div id="nr-main" style="font-size:12px;"></div>
        <div id="nr-events" style="margin-top:10px;font-size:11px;color:var(--ice2);max-height:80px;overflow:hidden;">Waiting for events&hellip;</div>
      </div>
    </div>
  </div>

  <!-- Luma AI Explainer -->
  <div class="panel-card" style="margin:0 0 24px;">
    <div class="panel-header">
      <div>
        <div class="panel-title">Luma AI Explainer</div>
        <div class="panel-sub">Ask about strategy, signals, or request an investor pitch</div>
      </div>
    </div>
    <div id="luma-explainer-panel" style="min-height:80px;"></div>
  </div>

"""
content = content.replace('  <div class="refresh-bar">', integration_panels + '  <div class="refresh-bar">', 1)

# 4. Add LumaDS wiring at start of script block
luma_init = """// === LumaDS Integration ===
document.addEventListener('DOMContentLoaded', function() {
  if (window.LumaDS) {
    LumaDS.mount({ intervalSec: 20, particleCount: 0 });
    LumaDS.mountNodeRedStatus('nr-hdr');
    LumaDS.mountNodeRedStatus('nr-main');
    LumaDS.mountExplainer('luma-explainer-panel', 'pitch');
    async function loadUnity() {
      var d = await LumaDS.gwUnityEdge();
      if (!d) return;
      LumaDS.setText('unityNodeCount', String(d.node_count || 0));
      var top = document.getElementById('unity-top');
      if (top && d.nodes && d.nodes.length) {
        top.innerHTML = d.nodes.slice(0, 3).map(function(n) {
          return '<div style="margin-bottom:4px">' + n.asset + ' — edge: ' + (n.edge_pct || 0).toFixed(1) + '% | harmonic: ' + (n.harmonic_score || 0).toFixed(2) + '</div>';
        }).join('');
      }
    }
    loadUnity(); setInterval(loadUnity, 30000);
    LumaDS.gwOnWs(function(evt, data) {
      if (evt !== 'message') return;
      var el = document.getElementById('nr-events');
      if (el) el.innerHTML = new Date().toLocaleTimeString() + ' \u2192 ' + JSON.stringify(data).slice(0, 60) + '<br/>' + el.innerHTML;
    });
  }
});

"""

content = content.replace(
    "<script>\n// \u2500\u2500 Clock",
    "<script>\n" + luma_init + "// \u2500\u2500 Clock"
)

# 5. Truncate at first </html>
idx = content.find("</html>")
content = content[:idx + 7]

with open(SRC, "w", encoding="utf-8") as f:
    f.write(content)

line_count = content.count("\n")
print(f"investor_wallboard.html upgraded: ~{line_count} lines")
print("Added: LumaDS script, Node-RED status, Unity panel, Explainer, Gateway KPIs")
print("Removed: orphaned duplicate HTML at end of file")
