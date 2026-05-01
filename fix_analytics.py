#!/usr/bin/env python3
"""Upgrade dashboard_analytics.html with LumaDS gateway integrations."""
from pathlib import Path

SRC = Path("dashboard_analytics.html")

with open(SRC, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add LumaDS script before </head>
if "luma_design_system.js" not in content:
    content = content.replace(
        "</head>",
        '  <script src="dashboard/js/luma_design_system.js"></script>\n</head>',
        1
    )

# 2. Build the integration section
integration = '''
  <!-- ── LumaTrader Gateway Intelligence Services ──────────────────────── -->
  <div id="analytics-integrations" style="max-width:1600px;margin:0 auto;padding:0 32px 40px;">
    <div style="font-family:'Space Grotesk',sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#56d7cb;margin-bottom:14px;padding-top:32px;border-top:1px solid rgba(126,172,214,0.18);">
      Gateway Intelligence Services
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
      <div style="background:rgba(12,19,29,0.88);border:1px solid rgba(126,172,214,0.18);border-radius:12px;padding:20px;">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:15px;font-weight:600;color:#dfbb6b;margin-bottom:4px">Node-RED Live Feed</div>
        <div style="font-size:12px;color:#a8c4e4;margin-bottom:12px">Real-time ingest bus &middot; ws://localhost:7700/ws</div>
        <div id="nr-analytics" style="font-size:12px;"></div>
        <div id="nr-analytics-events" style="margin-top:10px;font-size:11px;color:#a8c4e4;max-height:80px;overflow:hidden;">Waiting for events&hellip;</div>
      </div>
      <div style="background:rgba(12,19,29,0.88);border:1px solid rgba(126,172,214,0.18);border-radius:12px;padding:20px;">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:15px;font-weight:600;color:#dfbb6b;margin-bottom:4px">Unity Edge Intelligence</div>
        <div style="font-size:12px;color:#a8c4e4;margin-bottom:12px">XR harmonic node network &middot; live phi topology</div>
        <div style="font-size:13px;color:#a8c4e4">Node Count: <span id="unityNodeCount" style="color:#56d7cb;font-weight:700">--</span></div>
        <div id="unity-analytics" style="margin-top:10px;font-size:12px;color:#a8c4e4">Awaiting Unity edge data...</div>
      </div>
    </div>

    <div style="background:rgba(12,19,29,0.88);border:1px solid rgba(126,172,214,0.18);border-radius:12px;padding:20px;">
      <div style="font-family:'Space Grotesk',sans-serif;font-size:15px;font-weight:600;color:#dfbb6b;margin-bottom:4px">Luma AI Explainer</div>
      <div style="font-size:12px;color:#a8c4e4;margin-bottom:12px">Ask about signals, edge, strategy, or request an investor pitch</div>
      <div id="luma-explainer-panel" style="min-height:80px;"></div>
    </div>
  </div>

  <script>
  document.addEventListener("DOMContentLoaded", function() {
    if (!window.LumaDS) return;
    LumaDS.mount({ intervalSec: 30, particleCount: 0 });
    LumaDS.mountNodeRedStatus("nr-analytics");
    LumaDS.mountExplainer("luma-explainer-panel", "analyst");
    function loadUnity() {
      LumaDS.gwUnityEdge().then(function(d) {
        if (!d) return;
        LumaDS.setText("unityNodeCount", String(d.node_count || 0));
        var top = document.getElementById("unity-analytics");
        if (top && d.nodes && d.nodes.length) {
          top.innerHTML = d.nodes.slice(0, 3).map(function(n) {
            return "<div style='margin-bottom:4px'>" + n.asset + " -- edge: " + (n.edge_pct || 0).toFixed(1) + "% | harmonic: " + (n.harmonic_score || 0).toFixed(2) + "</div>";
          }).join("");
        }
      });
    }
    loadUnity();
    setInterval(loadUnity, 30000);
    LumaDS.gwOnWs(function(evt, data) {
      if (evt !== "message") return;
      var el = document.getElementById("nr-analytics-events");
      if (el) el.innerHTML = new Date().toLocaleTimeString() + " >> " + JSON.stringify(data).slice(0, 60) + "<br/>" + el.innerHTML;
    });
  });
  </script>

'''

# Insert before </body>
content = content.replace("</body>", integration + "</body>", 1)

with open(SRC, "w", encoding="utf-8") as f:
    f.write(content)

markers = ["luma_design_system.js", "nr-analytics", "luma-explainer-panel", "unity-analytics"]
for m in markers:
    print(m + ": " + ("FOUND" if m in content else "MISSING"))
print("Lines: " + str(content.count("\n")))
