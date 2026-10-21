/* Mission Control review: one-time public snapshots, no runtime or order APIs. */
(() => {
  "use strict";

  const SOURCE_COMMIT = "e706e91de133e039cc16ed25ec5021a293edbf2b";
  const REPO_BASE = "https://github.com/robertashworth1986-debug/lumen-core-public/";
  const views = ["overview", "trading", "forecast", "grants", "evidence"];
  const viewTitles = { overview: "Overview", trading: "Trading research", forecast: "Forecast & constraints", grants: "Grant Factory", evidence: "Evidence library" };
  const tabs = Array.from(document.querySelectorAll("[data-view]"));
  const dialog = document.getElementById("evidence-dialog");
  const detail = document.getElementById("evidence-detail");
  let catalogue = [];
  let dialogOpener = null;

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  }

  function text(value, fallback = "Not recorded") {
    return typeof value === "string" && value.trim() ? value : fallback;
  }

  function safePath(path) {
    return typeof path === "string" && path.length > 0 && !path.startsWith("/") && !path.includes("\\") && !path.split("/").some(part => part === ".." || part === ".") && !/[\u0000-\u001f\u007f?#]/.test(path);
  }

  function sourceUrl(path, commit = SOURCE_COMMIT) {
    if (!safePath(path) || !/^[a-f0-9]{40}$/.test(commit)) return null;
    return `${REPO_BASE}blob/${commit}/${path.split("/").map(encodeURIComponent).join("/")}`;
  }

  function safeHistoricalUrl(value) {
    if (typeof value !== "string") return null;
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || url.hostname !== "github.com" || url.port || url.username || url.password || url.search || url.hash) return null;
      if (!/^\/robertashworth1986-debug\/lumen-core-public\/blob\/[a-f0-9]{40}\/.+/.test(url.pathname)) return null;
      const parts = url.pathname.split("/");
      if (!safePath(decodeURIComponent(parts.slice(5).join("/")))) return null;
      return url.href;
    } catch (_) { return null; }
  }

  function sourceLink(label, url, className = "") {
    if (!url) return element("span", className, label);
    const link = element("a", className, label);
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  }

  document.querySelectorAll("[data-source-path]").forEach(link => {
    const url = sourceUrl(link.dataset.sourcePath);
    if (url) {
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  });

  function showView(view, moveFocus = false, updateHash = true) {
    if (!views.includes(view)) view = "overview";
    tabs.forEach(tab => {
      const active = tab.dataset.view === view;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    views.forEach(name => { document.getElementById(`panel-${name}`).hidden = name !== view; });
    document.getElementById("view-title").textContent = viewTitles[view];
    if (updateHash && location.hash !== `#${view}`) {
      try { history.replaceState(null, "", `#${view}`); } catch (_) { /* file previews may deny history updates */ }
    }
    if (moveFocus) document.getElementById(`panel-${view}`).focus({ preventScroll: true });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showView(tab.dataset.view));
    tab.addEventListener("keydown", event => {
      let next = null;
      if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== null) {
        event.preventDefault();
        tabs[next].focus();
        showView(tabs[next].dataset.view);
      }
    });
  });
  document.querySelectorAll("[data-open-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.openView, true)));
  window.addEventListener("hashchange", () => showView(location.hash.slice(1), false, false));
  showView(location.hash.slice(1), false, false);

  function closeEvidence() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else {
      dialog.removeAttribute("open");
      dialog.classList.remove("fallback-dialog");
      if (dialogOpener) dialogOpener.focus();
    }
  }

  function openEvidence(record, opener) {
    dialogOpener = opener;
    detail.replaceChildren();
    detail.append(element("span", "record-group", text(record.group)), element("h2", "", text(record.name)));
    detail.lastElementChild.id = "evidence-title";
    detail.append(element("span", "stage-tag", text(record.stage)), element("p", "", text(record.summary)));
    const limitations = Array.isArray(record.limitations) ? record.limitations.filter(item => typeof item === "string") : [];
    const boundary = element("section", "record-boundary");
    boundary.append(element("h3", "", "Limitations & claim boundary"));
    if (limitations.length) {
      const list = element("ul");
      limitations.forEach(item => list.append(element("li", "", item)));
      boundary.append(list);
    } else boundary.append(element("p", "", "This catalogue record does not supply a separate limitation list. Source presence alone does not establish performance, independent validation or revenue."));
    detail.append(boundary, element("h3", "", "Pinned source references"));
    const sources = Array.isArray(record.sources) ? record.sources : [];
    if (!sources.length) detail.append(element("p", "", "No pinned source reference is recorded."));
    sources.forEach(source => {
      if (!source || typeof source !== "object") return;
      const sourceNode = element("div", "source-record");
      const url = safeHistoricalUrl(source.url) || sourceUrl(source.path, source.commit);
      sourceNode.append(sourceLink(text(source.path), url));
      sourceNode.append(element("small", "", `Coverage: ${text(source.coverage)} · Source commit: ${text(source.commit)}`));
      if (typeof source.sha256 === "string" && /^[a-f0-9]{64}$/.test(source.sha256)) sourceNode.append(element("small", "", `Stored SHA-256: ${source.sha256}`));
      if (!url) sourceNode.append(element("small", "", "A valid pinned source URL is not recorded; no external link was created."));
      detail.append(sourceNode);
    });
    if (typeof dialog.showModal === "function") dialog.showModal();
    else {
      dialog.setAttribute("open", "");
      dialog.classList.add("fallback-dialog");
      dialog.setAttribute("role", "dialog");
      dialog.setAttribute("aria-modal", "true");
    }
    document.getElementById("close-evidence").focus();
  }

  document.getElementById("close-evidence").addEventListener("click", closeEvidence);
  dialog.addEventListener("close", () => { if (dialogOpener) dialogOpener.focus(); });
  dialog.addEventListener("click", event => { if (event.target === dialog && (event.clientX < dialog.getBoundingClientRect().left || event.clientX > dialog.getBoundingClientRect().right || event.clientY < dialog.getBoundingClientRect().top || event.clientY > dialog.getBoundingClientRect().bottom)) closeEvidence(); });
  dialog.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); closeEvidence(); }
    if (event.key === "Tab") {
      const focusable = Array.from(dialog.querySelectorAll("button,a[href],[tabindex='0']"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });

  function searchableRecord(record) {
    const terms = [record.name, record.group, record.stage, record.summary];
    if (Array.isArray(record.limitations)) terms.push(...record.limitations);
    if (Array.isArray(record.sources)) terms.push(...record.sources.map(source => source && source.path));
    return terms.filter(value => typeof value === "string").join(" ").toLocaleLowerCase();
  }

  function renderCatalogue() {
    const query = document.getElementById("portfolio-query").value.trim().toLocaleLowerCase();
    const group = document.getElementById("portfolio-group").value;
    const terms = query.split(/\s+/).filter(Boolean);
    const records = catalogue.filter(record => (!group || record.group === group) && terms.every(term => searchableRecord(record).includes(term)));
    const container = document.getElementById("portfolio-results");
    container.replaceChildren();
    const fragment = document.createDocumentFragment();
    records.forEach(record => {
      const card = element("article", "portfolio-card");
      card.append(element("span", "record-group", text(record.group)), element("h4", "", text(record.name)), element("span", "stage-tag", text(record.stage)), element("p", "", text(record.summary)));
      const button = element("button", "card-button");
      button.type = "button";
      button.setAttribute("aria-label", `Inspect evidence for ${text(record.name)}`);
      const count = Array.isArray(record.sources) ? record.sources.length : 0;
      button.append(element("span", "", "Inspect evidence ↗"), element("span", "", `${count} source${count === 1 ? "" : "s"}`));
      button.addEventListener("click", () => openEvidence(record, button));
      card.append(button);
      fragment.append(card);
    });
    container.append(fragment);
    document.getElementById("portfolio-empty").hidden = records.length !== 0;
    document.getElementById("search-status").textContent = `${records.length} of ${catalogue.length} catalogue records${query || group ? " match the current filters" : " · select a record to inspect its sources and limitations"}.`;
  }

  document.getElementById("catalogue-search").addEventListener("submit", event => event.preventDefault());
  document.getElementById("portfolio-query").addEventListener("input", renderCatalogue);
  document.getElementById("portfolio-group").addEventListener("change", renderCatalogue);
  document.getElementById("catalogue-search").addEventListener("reset", () => {
    document.getElementById("portfolio-query").value = "";
    document.getElementById("portfolio-group").value = "";
    renderCatalogue();
  });

  function requireCount(value) {
    if (!Number.isSafeInteger(value) || value < 0) throw new Error("Invalid inventory count");
    return value.toLocaleString("en-US");
  }

  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error("Missing source snapshot date");
    return value;
  }

  async function readSnapshot(path) {
    const response = await fetch(path, { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error(`Snapshot unavailable (${response.status})`);
    return response.json();
  }

  function renderPacket(packet) {
    if (!packet || !packet.summary || !Array.isArray(packet.evidence_assets)) throw new Error("Invalid review packet");
    const date = validDate(packet.generated_at_utc);
    const count = requireCount(packet.summary.evidence_asset_count);
    if (packet.summary.evidence_asset_count !== packet.evidence_assets.length) throw new Error("Packet inventory mismatch");
    const container = document.getElementById("packet-assets");
    packet.evidence_assets.forEach(asset => {
      const row = element("div", "asset-item");
      row.append(sourceLink(text(asset.path), sourceUrl(asset.path)), element("p", "", text(asset.purpose)));
      if (typeof asset.sha256 === "string" && /^[a-f0-9]{64}$/.test(asset.sha256)) {
        const metadata = element("details");
        metadata.append(element("summary", "", "Packet snapshot digest"), element("code", "", asset.sha256));
        row.append(metadata);
      }
      container.append(row);
    });
    document.getElementById("evidence-count").textContent = count;
    document.getElementById("packet-asset-count").textContent = `${count} ASSETS`;
    document.getElementById("packet-load-status").textContent = `Packet generated ${date}. This is a dated public review packet, not completed external validation.`;
    return `Review packet: ${date}`;
  }

  function renderAudit(audit) {
    if (!audit || audit.scope !== "tracked_file_presence_only" || !audit.summary || !Array.isArray(audit.engines) || audit.execution_verified_by_this_audit !== false) throw new Error("Invalid tracked-file audit");
    const date = validDate(audit.generated_at_utc);
    const count = requireCount(audit.summary.portfolio_lane_count);
    if (audit.summary.portfolio_lane_count !== audit.engines.length) throw new Error("Audit inventory mismatch");
    const container = document.getElementById("engine-list");
    audit.engines.forEach(engine => {
      const row = element("details", "engine-detail");
      const summary = element("summary", "", text(engine.name));
      summary.append(element("small", "", text(engine.inventory_label, text(engine.observed_maturity).replace(/_/g, " "))));
      row.append(summary, element("p", "", text(engine.safe_description)));
      if (typeof engine.claim_boundary === "string") row.append(element("p", "", `Boundary: ${engine.claim_boundary}`));
      if (typeof engine.acceptance_gate === "string") row.append(element("p", "", `Next gate: ${engine.acceptance_gate}`));
      row.append(sourceLink("Inspect audit source ↗", sourceUrl("dashboard/data/lumencore_engine_portfolio_audit.json"), "text-link"));
      container.append(row);
    });
    document.getElementById("lane-count").textContent = count;
    document.getElementById("engine-audit-count").textContent = `${count} LANES`;
    document.getElementById("engine-load-status").textContent = `Audit generated ${date}. Execution and customer acceptance are not verified by this audit.`;
    return `Engine audit: ${date}`;
  }

  function loadCatalogue(records) {
    if (!Array.isArray(records) || !records.length || !records.every(record => record && typeof record === "object" && typeof record.id === "string" && typeof record.name === "string" && typeof record.group === "string")) throw new Error("Invalid public catalogue");
    catalogue = records;
    const groups = [...new Set(catalogue.map(record => record.group))].sort((a, b) => a.localeCompare(b));
    const select = document.getElementById("portfolio-group");
    groups.forEach(group => {
      const option = element("option", "", group);
      option.value = group;
      select.append(option);
    });
    document.getElementById("catalogue-count").textContent = requireCount(catalogue.length);
    renderCatalogue();
    return `Catalogue: ${catalogue.length} records; review date 2026-10-04`;
  }

  const tasks = [
    { name: "Review packet", path: "./data/external_technical_review_packet.json", render: renderPacket, fail: () => { document.getElementById("packet-assets").replaceChildren(); document.getElementById("packet-asset-count").textContent = "UNAVAILABLE"; document.getElementById("packet-load-status").textContent = "The public packet could not be loaded or verified. Its asset count is unavailable."; } },
    { name: "Engine audit", path: "./data/lumencore_engine_portfolio_audit.json", render: renderAudit, fail: () => { document.getElementById("engine-list").replaceChildren(); document.getElementById("engine-audit-count").textContent = "UNAVAILABLE"; document.getElementById("engine-load-status").textContent = "The tracked-file audit could not be loaded or verified. Its lane count is unavailable."; } },
    { name: "Catalogue", path: "./portfolio/data/portfolio.json", render: loadCatalogue, fail: () => { document.getElementById("search-status").textContent = "The public catalogue could not be loaded. Serve this page with its relative JSON files over HTTP to use search. No substitute records have been generated."; } }
  ];
  Promise.allSettled(tasks.map(async task => {
    try { return task.render(await readSnapshot(task.path)); }
    catch (error) { task.fail(); throw error; }
  })).then(results => {
    const status = results.map((result, index) => result.status === "fulfilled" ? result.value : `${tasks[index].name}: unavailable`);
    document.getElementById("snapshot-status").textContent = status.join(" · ") + ". No polling or runtime connections.";
  });

  // Fixed, source-pinned historical observations; never treated as a live feed.
  const comparisons = {
    original: { baseline: 17874.171755209874, candidate: 15979.086850308855, rows: 1176, authorities: 8, window: "2026-01-01–2026-07-12", source: "evidence/reproducibility/eia_constraint_review_20260921/benchmark.json" },
    later: { baseline: 19765.54376351574, candidate: 16107.043528292354, rows: 285, authorities: 7, window: "2026-07-13–2026-09-08", source: "evidence/reproducibility/eia_constraint_later_window_20260921/benchmark.json" }
  };
  function renderComparison() {
    const comparison = comparisons[document.getElementById("comparison-window").value];
    if (!comparison) return;
    const reduction = 100 * (comparison.baseline - comparison.candidate) / comparison.baseline;
    const number = value => value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById("baseline-improvement").textContent = `${number(reduction)}%`;
    document.getElementById("baseline-mae").textContent = `${number(comparison.baseline)} MWh`;
    document.getElementById("candidate-mae").textContent = `${number(comparison.candidate)} MWh`;
    document.getElementById("candidate-error-bar").style.width = `${100 * comparison.candidate / comparison.baseline}%`;
    document.getElementById("comparison-coverage").textContent = `${comparison.rows.toLocaleString("en-US")} paired authority-days · ${comparison.authorities} authorities · ${comparison.window}`;
    document.getElementById("baseline-source-note").textContent = `Window: ${comparison.window}. Reduction = 100 × (baseline MAE − candidate MAE) / baseline MAE. Both windows remain on promotion HOLD. This is not an as-issued comparison, buyer-accepted baseline or independent validation.`;
    document.getElementById("comparison-source").href = sourceUrl(comparison.source);
  }
  document.getElementById("comparison-window").addEventListener("change", renderComparison);
  renderComparison();

  const presentationButton = document.getElementById("presentation-button");
  const presentationStatus = document.getElementById("presentation-status");
  function setPresentation(active) {
    document.body.classList.toggle("presentation-mode", active);
    presentationButton.setAttribute("aria-pressed", String(active));
    presentationButton.textContent = active ? "Exit presentation" : "⛶ Present";
  }
  presentationButton.addEventListener("click", async () => {
    const active = document.body.classList.contains("presentation-mode");
    if (active) {
      if (document.fullscreenElement && typeof document.exitFullscreen === "function") {
        try { await document.exitFullscreen(); } catch (_) { /* retain a usable compact layout */ }
      }
      setPresentation(false);
      presentationStatus.textContent = "Presentation mode closed.";
      return;
    }
    setPresentation(true);
    try {
      if (typeof document.documentElement.requestFullscreen !== "function") throw new Error("Fullscreen unavailable");
      await document.documentElement.requestFullscreen();
      presentationStatus.textContent = "Fullscreen presentation started. Press Escape or Exit presentation to return.";
    } catch (_) { presentationStatus.textContent = "Expanded presentation layout started. Browser fullscreen is unavailable; use Exit presentation to return."; }
  });
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) setPresentation(false);
  });
})();
