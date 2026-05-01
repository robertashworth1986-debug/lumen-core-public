#!/usr/bin/env python3
"""Upgrade index.html with LumaDS integrations while preserving existing content."""
from pathlib import Path

SRC = Path("dashboard/index.html")

with open(SRC, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add luma_design_system.js before </head>
content = content.replace(
    "</head>",
    '  <script src="js/luma_design_system.js"></script>\n</head>',
    1
)

# 2. Add Node-RED status next to live dot in header
content = content.replace(
    '<span id="clock" class="clock-gold">--:--:-- UTC</span>',
    '<span id="clock" class="clock-gold">--:--:-- UTC</span>\n      <div id="nr-hdr" style="margin-top:6px;font-size:11px;text-align:right"></div>'
)

# 3. Integration panels to insert before footer
integration_panels = """
  <!-- Gateway Snapshot / Institutional KPIs -->
  <div style="margin:32px 0 0;padding:0;">
    <div style="font-family:\'Space Grotesk\',sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--teal);margin-bottom:14px;">
      Live Gateway Intelligence
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;">
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;">
        <div style="font-size:11px;text-transform:uppercase;color:var(--ice2);margin-bottom:6px">Equity</div>
        <div style="font-size:22px;font-weight:700;color:var(--gold);font-family:\'IBM Plex Mono\',monospace" id="snapEquity">—</div>
      </div>
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;">
        <div style="font-size:11px;text-transform:uppercase;color:var(--ice2);margin-bottom:6px">PnL</div>
        <div style="font-size:22px;font-weight:700;color:var(--teal);font-family:\'IBM Plex Mono\',monospace" id="snapPnl">—</div>
      </div>
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;">
        <div style="font-size:11px;text-transform:uppercase;color:var(--ice2);margin-bottom:6px">Win Rate</div>
        <div style="font-size:22px;font-weight:700;color:#4ade80;font-family:\'IBM Plex Mono\',monospace" id="snapWinRate">—</div>
      </div>
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;">
        <div style="font-size:11px;text-transform:uppercase;color:var(--ice2);margin-bottom:6px">Closed Trades</div>
        <div style="font-size:22px;font-weight:700;color:var(--ice);font-family:\'IBM Plex Mono\',monospace" id="snapClosedTrades">—</div>
      </div>
    </div>

    <!-- Unity + Node-RED -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;">
        <div style="font-family:\'Space Grotesk\',sans-serif;font-size:15px;font-weight:600;color:var(--gold);margin-bottom:4px">Unity Edge Intelligence</div>
        <div style="font-size:12px;color:var(--ice2);margin-bottom:12px">XR harmonic node network &middot; live &phi; topology</div>
        <div style="font-size:13px;color:var(--ice2)">Node Count: <span id="unityNodeCount" style="color:var(--teal);font-weight:700">—</span></div>
        <div id="unity-top" style="margin-top:10px;font-size:12px;color:var(--ice2)">Awaiting Unity edge data&hellip;</div>
      </div>
      <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;">
        <div style="font-family:\'Space Grotesk\',sans-serif;font-size:15px;font-weight:600;color:var(--gold);margin-bottom:4px">Node-RED Live Feed</div>
        <div style="font-size:12px;color:var(--ice2);margin-bottom:12px">Real-time ingest bus &middot; ws://localhost:7700/ws</div>
        <div id="nr-main" style="font-size:12px;"></div>
        <div id="nr-events" style="margin-top:10px;font-size:11px;color:var(--ice2);max-height:80px;overflow:hidden;">Waiting for events&hellip;</div>
      </div>
    </div>

    <!-- Luma AI Explainer -->
    <div style="background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:20px;">
      <div style="font-family:\'Space Grotesk\',sans-serif;font-size:15px;font-weight:600;color:var(--gold);margin-bottom:4px">Luma AI Explainer</div>
      <div style="font-size:12px;color:var(--ice2);margin-bottom:12px">Platform intelligence &middot; concierge / analyst / pitch modes</div>
      <div id="luma-explainer-panel" style="min-height:80px;"></div>
    </div>
  </div>

"""
content = content.replace('  <!-- ── footer', integration_panels + '  <!-- \u2500\u2500 footer', 1)

# 4. Add LumaDS wiring after existing script block
luma_script = """
// === LumaDS Integration ===
document.addEventListener('DOMContentLoaded', function() {
  if (window.LumaDS) {
    LumaDS.mount({ intervalSec: 30, particleCount: 0 });
    LumaDS.mountNodeRedStatus('nr-hdr');
    LumaDS.mountNodeRedStatus('nr-main');
    LumaDS.mountExplainer('luma-explainer-panel', 'analyst');
    async function loadUnity() {
      var d = await LumaDS.gwUnityEdge();
      if (!d) return;
      LumaDS.setText('unityNodeCount', String(d.node_count || 0));
      var top = document.getElementById('unity-top');
      if (top && d.nodes && d.nodes.length) {
        top.innerHTML = d.nodes.slice(0, 3).map(function(n) {
          return '<div style="margin-bottom:4px">' + n.asset + ' \u2014 edge: ' + (n.edge_pct || 0).toFixed(1) + '% | harmonic: ' + (n.harmonic_score || 0).toFixed(2) + '</div>';
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

content = content.replace("</script>\n\n</body>", luma_script + "\n</script>\n\n</body>", 1)

with open(SRC, "w", encoding="utf-8") as f:
    f.write(content)

line_count = content.count("\n")
print(f"index.html upgraded: ~{line_count} lines")
print("Added: LumaDS script, Node-RED status, Unity panel, Explainer, Gateway KPIs")
