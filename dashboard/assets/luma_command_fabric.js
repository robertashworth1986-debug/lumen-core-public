(function () {
  "use strict";

  if (window.__LUMA_COMMAND_FABRIC__) return;
  window.__LUMA_COMMAND_FABRIC__ = true;

  try {
    if (window.self !== window.top) return;
  } catch (_) {
    return;
  }

  var ROUTES = [
    { label: "Home", href: "/operator_home.html", hint: "Plain-English platform, proof, and readiness map" },
    { label: "Mission", href: "/mission_control.html", hint: "System health and evidence control" },
    { label: "Quant", href: "/quant_lab.html", hint: "Unified research and operator cockpit" },
    { label: "Trade", href: "/kraken_execution_dashboard.html", hint: "Kraken paper and execution evidence" },
    { label: "Grants", href: "/grants.html", hint: "Grant readiness and submission factory" },
    { label: "Forecast", href: "/forecast.html", hint: "Forecast and scenario console" },
    { label: "Explain", href: "/explain.html", hint: "Router and evidence explainer" },
  ];

  var isFile = location.protocol === "file:";
  var currentFile = (location.pathname.replace(/\\/g, "/").split("/").pop() || "").toLowerCase();
  var apiBase = typeof window.LUMA_API_BASE === "string"
    ? window.LUMA_API_BASE.trim().replace(/\/$/, "")
    : "";
  var state = {
    mode: "checking",
    modeTone: "warn",
    freshness: "checking",
    freshnessTone: "warn",
    health: null,
    snapshot: null,
  };

  function hrefFor(path) {
    if (!isFile) return path;
    return "." + path;
  }

  function apiUrl(path) {
    if (/^https?:\/\//i.test(path)) return path;
    if (apiBase) return apiBase + path;
    if (isFile) return "https://lumen-core.ai" + path;
    return path;
  }

  async function fetchJson(path) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 5000);
    try {
      var response = await fetch(apiUrl(path), {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function deriveMode(snapshot) {
    var gate = snapshot && snapshot.runtime && snapshot.runtime.execution_gate;
    if (gate) {
      if (gate.execution_authorized || gate.armed) return { label: "LIVE", tone: "good" };
      if (gate.paper_enabled || String(gate.mode || "").toLowerCase() === "paper") {
        return { label: "PAPER", tone: "paper" };
      }
      return { label: "SHADOW", tone: "shadow" };
    }

    var timing = snapshot && snapshot.awareness && snapshot.awareness.timing_edge_context;
    if (timing && timing.execution_authorized === false) {
      return { label: "SHADOW", tone: "shadow" };
    }
    return { label: "DISARMED", tone: "warn" };
  }

  function deriveFreshness(health) {
    if (!health || health.status !== "ok") return { label: "OFFLINE", tone: "bad" };
    var artifacts = health.artifacts || {};
    var rows = Object.keys(artifacts).map(function (key) { return artifacts[key]; });
    var allFresh = rows.length > 0 && rows.every(function (row) { return row && row.fresh === true; });
    return allFresh
      ? { label: "DATA FRESH", tone: "good" }
      : { label: "DATA STALE", tone: "warn" };
  }

  function syncLegacyModeBadges() {
    document.querySelectorAll(".lc-live, [data-runtime-mode]").forEach(function (badge) {
      badge.textContent = state.mode;
      badge.dataset.mode = state.mode.toLowerCase();
      badge.title = "Execution mode from the public runtime safety gate";
    });
  }

  function renderStatus() {
    var mode = document.getElementById("lcf-mode");
    var fresh = document.getElementById("lcf-freshness");
    if (mode) {
      mode.textContent = state.mode;
      mode.dataset.tone = state.modeTone;
    }
    if (fresh) {
      fresh.textContent = state.freshness;
      fresh.dataset.tone = state.freshnessTone;
    }
    syncLegacyModeBadges();
  }

  function updateStatus() {
    return Promise.allSettled([
      fetchJson("/health"),
      fetchJson("/api/snapshot"),
    ]).then(function (results) {
      state.health = results[0].status === "fulfilled" ? results[0].value : null;
      state.snapshot = results[1].status === "fulfilled" ? results[1].value : null;

      var mode = state.snapshot
        ? deriveMode(state.snapshot)
        : { label: "OFFLINE", tone: "bad" };
      var freshness = deriveFreshness(state.health);
      state.mode = mode.label;
      state.modeTone = mode.tone;
      state.freshness = freshness.label;
      state.freshnessTone = freshness.tone;
      renderStatus();

      window.dispatchEvent(new CustomEvent("luma:fabric-status", {
        detail: {
          mode: state.mode,
          freshness: state.freshness,
          health: state.health,
          snapshot: state.snapshot,
        },
      }));
    });
  }

  function buildRail() {
    var rail = document.createElement("aside");
    rail.className = "lcf-rail";
    rail.setAttribute("aria-label", "Luma command fabric");

    var nav = document.createElement("nav");
    nav.className = "lcf-nav";
    ROUTES.forEach(function (route) {
      var link = document.createElement("a");
      var file = route.href.split("/").pop().toLowerCase();
      link.className = "lcf-link" + (file === currentFile ? " active" : "");
      link.href = hrefFor(route.href);
      link.textContent = route.label;
      link.title = route.hint;
      nav.appendChild(link);
    });

    var status = document.createElement("div");
    status.className = "lcf-status";
    status.innerHTML = [
      '<span class="lcf-chip" id="lcf-mode" data-tone="warn">CHECKING</span>',
      '<span class="lcf-chip" id="lcf-freshness" data-tone="warn">CHECKING</span>',
      '<button class="lcf-command-button" id="lcf-open" type="button">Command <kbd>Ctrl K</kbd></button>',
    ].join("");

    rail.appendChild(nav);
    rail.appendChild(status);
    document.body.appendChild(rail);
  }

  function buildPalette() {
    var palette = document.createElement("div");
    palette.className = "lcf-palette";
    palette.id = "lcf-palette";
    palette.setAttribute("aria-hidden", "true");
    palette.innerHTML = [
      '<div class="lcf-dialog" role="dialog" aria-modal="true" aria-label="Luma command palette">',
      '<input class="lcf-search" id="lcf-search" type="search" autocomplete="off" placeholder="Open a command surface...">',
      '<div class="lcf-results" id="lcf-results"></div>',
      "</div>",
    ].join("");
    document.body.appendChild(palette);

    var search = document.getElementById("lcf-search");
    var results = document.getElementById("lcf-results");
    var activeIndex = 0;
    var filtered = ROUTES.slice();

    function renderResults() {
      results.innerHTML = filtered.map(function (route, index) {
        return [
          '<button class="lcf-result', index === activeIndex ? " active" : "", '" type="button" data-href="',
          escapeHtml(route.href), '">',
          "<span><strong>", escapeHtml(route.label), "</strong><span>", escapeHtml(route.hint), "</span></span>",
          "<code>", escapeHtml(route.href), "</code>",
          "</button>",
        ].join("");
      }).join("") || '<div class="lcf-result"><span><strong>No matching surface</strong></span></div>';
    }

    function openPalette() {
      palette.classList.add("open");
      palette.setAttribute("aria-hidden", "false");
      search.value = "";
      filtered = ROUTES.slice();
      activeIndex = 0;
      renderResults();
      setTimeout(function () { search.focus(); }, 0);
    }

    function closePalette() {
      palette.classList.remove("open");
      palette.setAttribute("aria-hidden", "true");
    }

    function openActive() {
      var route = filtered[activeIndex];
      if (route) location.href = hrefFor(route.href);
    }

    search.addEventListener("input", function () {
      var query = search.value.trim().toLowerCase();
      filtered = ROUTES.filter(function (route) {
        return (route.label + " " + route.hint + " " + route.href).toLowerCase().includes(query);
      });
      activeIndex = 0;
      renderResults();
    });

    search.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        activeIndex = Math.min(filtered.length - 1, activeIndex + 1);
        renderResults();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activeIndex = Math.max(0, activeIndex - 1);
        renderResults();
      } else if (event.key === "Enter") {
        event.preventDefault();
        openActive();
      } else if (event.key === "Escape") {
        closePalette();
      }
    });

    results.addEventListener("click", function (event) {
      var button = event.target.closest("[data-href]");
      if (button) location.href = hrefFor(button.dataset.href);
    });

    palette.addEventListener("click", function (event) {
      if (event.target === palette) closePalette();
    });

    document.getElementById("lcf-open").addEventListener("click", openPalette);
    document.addEventListener("keydown", function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        palette.classList.contains("open") ? closePalette() : openPalette();
      } else if (event.key === "Escape" && palette.classList.contains("open")) {
        closePalette();
      }
    });
  }

  function start() {
    buildRail();
    buildPalette();
    renderStatus();
    updateStatus();
    setInterval(updateStatus, 15000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
