(function () {
  'use strict';

  const STYLE_ID = 'luma-healthcare-embed-style';
  const THEMES = new Set(['host', 'mindwise', 'clinical', 'executive']);
  const DENSITIES = new Set(['cozy', 'compact']);
  const ROUTE_LABELS = {
    grants_gov_detail: 'Grants.gov Detail',
    simpler_opportunity: 'Simpler Listing',
    hello_skip: 'Hello Skip',
    smartsimple: 'SmartSimple',
    uuid_listing: 'UUID Listing',
    opp_number_detail: 'Opportunity Detail',
    source_url: 'Source Portal',
    grants_search: 'Grants Search',
  };
  const ACTION_LABELS = {
    IMMEDIATE_SUBMIT: 'Urgent Review',
    FAST_TRACK: 'Priority Review',
    ACTIVE_PIPELINE: 'Review Queue',
    WATCHLIST: 'Watchlist',
    MANUAL_REVIEW: 'Manual Review',
  };

  function esc(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function toNum(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function pick(value, allowed, fallback) {
    const token = String(value || '').trim().toLowerCase();
    return allowed.has(token) ? token : fallback;
  }

  function titleCase(value) {
    return String(value || '')
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  function normalizeTag(value) {
    return String(value || '').trim().replace(/_/g, ' ');
  }

  function labelForRoute(value) {
    const token = String(value || '').trim().toLowerCase();
    if (ROUTE_LABELS[token]) return ROUTE_LABELS[token];
    return titleCase(normalizeTag(token || 'route unknown'));
  }

  function labelForAction(value) {
    const token = String(value || '').trim().toUpperCase();
    if (ACTION_LABELS[token]) return ACTION_LABELS[token];
    return titleCase(normalizeTag(token || 'manual review'));
  }

  function closingWindow(days) {
    const n = toNum(days, 9999);
    if (n <= 7) return { label: 'closes <= 7d', tone: 'critical' };
    if (n <= 14) return { label: 'closes <= 14d', tone: 'hot' };
    if (n <= 30) return { label: `closes ${n}d`, tone: 'warm' };
    return { label: `closes ${n}d`, tone: 'steady' };
  }

  function scoreBand(score) {
    const n = toNum(score, 0);
    if (n >= 80) return 'High Relevance';
    if (n >= 65) return 'Moderate Relevance';
    if (n >= 50) return 'Review Relevance';
    return 'Low Relevance';
  }

  function formatGeneratedAt(value) {
    const raw = String(value || '').trim();
    if (!raw) return 'n/a';
    const date = new Date(raw);
    if (!Number.isFinite(date.getTime())) return raw;
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .luma-hc-wrap {
        --lh-font: "Geist", "Geist Fallback", "Manrope", "Avenir Next", "Segoe UI", sans-serif;
        --lh-text: #0f172a;
        --lh-muted: #334155;
        --lh-surface: #ffffff;
        --lh-border: #dce5ee;
        --lh-card-bg: #ffffff;
        --lh-card-border: #dbe7f0;
        --lh-head-from: #0b4a69;
        --lh-head-to: #0f766e;
        --lh-head-text: #f8fafc;
        --lh-pill-bg: #e2e8f0;
        --lh-pill-text: #0f172a;
        --lh-button-bg: #eff6ff;
        --lh-button-text: #0f3f67;
        --lh-button-border: #8db5d3;
        --lh-primary-bg: #dcfce7;
        --lh-primary-text: #14532d;
        --lh-primary-border: #34d399;
        --lh-ai-bg: #fff4de;
        --lh-ai-text: #9a3412;
        --lh-ai-border: #fdba74;
        --lh-danger-bg: #fee2e2;
        --lh-danger-text: #991b1b;
        --lh-danger-border: #fca5a5;
        --lh-hot-bg: #fff1da;
        --lh-hot-text: #9a3412;
        --lh-hot-border: #fdba74;
        --lh-warm-bg: #ecfeff;
        --lh-warm-text: #155e75;
        --lh-warm-border: #67e8f9;
        --lh-steady-bg: #f1f5f9;
        --lh-steady-text: #1e293b;
        --lh-steady-border: #cbd5e1;
        position: relative;
        overflow: hidden;
        border: 1px solid var(--lh-border);
        border-radius: 8px;
        color: var(--lh-text);
        font-family: var(--lh-font);
        background: var(--lh-surface);
        box-shadow: 0 16px 42px rgba(2, 6, 23, 0.09);
      }
      .luma-hc-theme-host {
        --lh-head-from: var(--mindwise-primary, var(--mw-navy, var(--brand-primary, #0b4a69)));
        --lh-head-to: var(--mindwise-secondary, var(--mw-blue-dark, var(--brand-secondary, #0f766e)));
        --lh-border: var(--mindwise-border, #dce5ee);
        --lh-button-bg: var(--mindwise-link-bg, var(--mw-light-blue-tint, #eff6ff));
        --lh-button-text: var(--mindwise-link-text, var(--mw-text, #0f3f67));
        --lh-button-border: var(--mindwise-link-border, var(--mw-blue, #8db5d3));
        --lh-primary-bg: var(--mindwise-primary-bg, var(--mw-coral, #ff6c52));
        --lh-primary-text: var(--mindwise-primary-text, #ffffff);
        --lh-primary-border: var(--mindwise-primary-border, var(--mw-coral-hover, #e85a42));
      }
      .luma-hc-theme-mindwise {
        --lh-font: "Geist", "Geist Fallback", Arial, Helvetica, sans-serif;
        --lh-text: var(--mw-text, #0d2a3d);
        --lh-muted: var(--mw-text-light, #5a6d7a);
        --lh-surface: #ffffff;
        --lh-border: #d7e4ee;
        --lh-card-bg: var(--mw-off-white, #f9fbf7);
        --lh-card-border: #dbe8f1;
        --lh-head-from: var(--mw-navy, #0d2a3d);
        --lh-head-to: var(--mw-blue-dark, #4f8bc9);
        --lh-head-text: #ffffff;
        --lh-pill-bg: #e2ebf2;
        --lh-pill-text: var(--mw-text, #0d2a3d);
        --lh-button-bg: #eef6fb;
        --lh-button-text: var(--mw-text, #0d2a3d);
        --lh-button-border: var(--mw-blue, #48afe5);
        --lh-primary-bg: var(--mw-coral, #ff6c52);
        --lh-primary-text: #ffffff;
        --lh-primary-border: var(--mw-coral-hover, #e85a42);
        --lh-ai-bg: #ebf4ff;
        --lh-ai-text: #1f4a7a;
        --lh-ai-border: #9ac5ef;
        --lh-danger-bg: #ffe5e2;
        --lh-danger-text: #a73122;
        --lh-danger-border: #ffb4a8;
        --lh-hot-bg: #fff0ed;
        --lh-hot-text: #a73c25;
        --lh-hot-border: #ffc4b8;
        --lh-warm-bg: #edf6fc;
        --lh-warm-text: #1d5374;
        --lh-warm-border: #b0d4ec;
        --lh-steady-bg: #f2f5f7;
        --lh-steady-text: #334e60;
        --lh-steady-border: #d5dee5;
      }
      .luma-hc-theme-clinical {
        --lh-head-from: #0f4c81;
        --lh-head-to: #0f766e;
      }
      .luma-hc-theme-executive {
        --lh-head-from: #1f2937;
        --lh-head-to: #0f766e;
        --lh-border: #d6dee8;
      }
      .luma-hc-density-cozy .luma-hc-head {
        padding: 16px 18px;
      }
      .luma-hc-density-cozy .luma-hc-list {
        gap: 10px;
        padding: 12px;
      }
      .luma-hc-density-compact .luma-hc-head {
        padding: 12px 14px;
      }
      .luma-hc-density-compact .luma-hc-list {
        gap: 8px;
        padding: 10px;
      }
      .luma-hc-head {
        background: var(--lh-head-from);
        color: var(--lh-head-text);
      }
      .luma-hc-head h3 {
        margin: 0;
        font-size: 16px;
        line-height: 1.25;
        letter-spacing: 0;
        font-weight: 800;
      }
      .luma-hc-sub {
        margin-top: 5px;
        font-size: 12px;
        line-height: 1.35;
        opacity: 0.95;
      }
      .luma-hc-list {
        display: grid;
      }
      .luma-hc-item {
        border: 1px solid var(--lh-card-border);
        border-radius: 8px;
        padding: 11px;
        background: var(--lh-card-bg);
        transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
      }
      .luma-hc-item:hover {
        transform: translateY(-2px);
        border-color: #9cc4de;
        box-shadow: 0 10px 24px rgba(2, 6, 23, 0.08);
      }
      .luma-hc-title-row {
        display: flex;
        gap: 8px;
        align-items: flex-start;
      }
      .luma-hc-rank {
        margin-top: 1px;
        font-size: 11px;
        font-weight: 800;
        color: #0f766e;
        border: 1px solid #9fe2cf;
        background: #ecfdf5;
        border-radius: 999px;
        padding: 2px 7px;
        flex: 0 0 auto;
      }
      .luma-hc-title {
        margin: 0;
        font-size: 14px;
        line-height: 1.35;
        font-weight: 700;
        color: var(--lh-text);
      }
      .luma-hc-meta {
        margin: 7px 0 8px 0;
        font-size: 12px;
        line-height: 1.35;
        color: var(--lh-muted);
      }
      .luma-hc-badges {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 9px;
      }
      .luma-hc-badge {
        font-size: 11px;
        line-height: 1.2;
        border-radius: 999px;
        padding: 3px 8px;
        border: 1px solid transparent;
        background: var(--lh-pill-bg);
        color: var(--lh-pill-text);
      }
      .luma-hc-badge--critical {
        background: var(--lh-danger-bg);
        border-color: var(--lh-danger-border);
        color: var(--lh-danger-text);
      }
      .luma-hc-badge--hot {
        background: var(--lh-hot-bg);
        border-color: var(--lh-hot-border);
        color: var(--lh-hot-text);
      }
      .luma-hc-badge--warm {
        background: var(--lh-warm-bg);
        border-color: var(--lh-warm-border);
        color: var(--lh-warm-text);
      }
      .luma-hc-badge--steady {
        background: var(--lh-steady-bg);
        border-color: var(--lh-steady-border);
        color: var(--lh-steady-text);
      }
      .luma-hc-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .luma-hc-btn {
        text-decoration: none;
        font-size: 12px;
        line-height: 1.2;
        border-radius: 6px;
        padding: 6px 10px;
        border: 1px solid var(--lh-button-border);
        color: var(--lh-button-text);
        background: var(--lh-button-bg);
        transition: transform 100ms ease, box-shadow 100ms ease, opacity 100ms ease;
      }
      .luma-hc-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 14px rgba(2, 6, 23, 0.08);
      }
      .luma-hc-btn:focus-visible {
        outline: 2px solid #0ea5e9;
        outline-offset: 2px;
      }
      .luma-hc-btn--primary {
        border-color: var(--lh-primary-border);
        color: var(--lh-primary-text);
        background: var(--lh-primary-bg);
      }
      .luma-hc-btn--ai {
        border-color: var(--lh-ai-border);
        color: var(--lh-ai-text);
        background: var(--lh-ai-bg);
      }
      .luma-hc-btn--disabled {
        opacity: 0.45;
        pointer-events: none;
      }
      .luma-hc-foot {
        padding: 10px 14px;
        font-size: 11px;
        line-height: 1.35;
        color: #475569;
        border-top: 1px solid var(--lh-border);
        background: rgba(248, 250, 252, 0.82);
      }
      .luma-hc-boundary {
        margin: 0;
        padding: 10px 14px 0;
        font-size: 11px;
        line-height: 1.4;
        color: #475569;
      }
      .luma-hc-empty {
        padding: 12px;
        color: #64748b;
        font-size: 12px;
      }
      .luma-hc-item--skeleton {
        animation: lumaHcPulse 1.6s ease-in-out infinite;
      }
      .luma-hc-skeleton-line {
        height: 10px;
        border-radius: 4px;
        background: linear-gradient(90deg, #e2e8f0 0%, #f8fafc 50%, #e2e8f0 100%);
        background-size: 220px 100%;
        animation: lumaHcShimmer 1.3s linear infinite;
        margin-bottom: 8px;
      }
      .luma-hc-skeleton-line:last-child {
        margin-bottom: 0;
      }
      .luma-hc-skeleton-line.short {
        width: 58%;
      }
      @keyframes lumaHcShimmer {
        0% { background-position: -220px 0; }
        100% { background-position: 220px 0; }
      }
      @keyframes lumaHcPulse {
        0% { opacity: 0.86; }
        50% { opacity: 1; }
        100% { opacity: 0.86; }
      }
      @media (max-width: 700px) {
        .luma-hc-actions {
          display: grid;
          grid-template-columns: 1fr;
        }
        .luma-hc-btn {
          text-align: center;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .luma-hc-item,
        .luma-hc-btn,
        .luma-hc-item--skeleton,
        .luma-hc-skeleton-line {
          animation: none !important;
          transition: none !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function joinUrl(base, query) {
    const q = String(query || '').trim();
    const b = String(base || '').trim();
    const fallbackBase = b || 'grants.html';
    if (!q) return fallbackBase;
    try {
      const u = new URL(fallbackBase, window.location.href);
      u.search = q.startsWith('?') ? q.slice(1) : q;
      return u.toString();
    } catch {
      const baseWithoutQuery = fallbackBase.replace(/\?.*$/, '');
      if (q.startsWith('?')) return `${baseWithoutQuery}${q}`;
      return `${baseWithoutQuery}?${q}`;
    }
  }

  function renderLoading(el, opts) {
    const slots = clamp(toNum(opts.max, 8), 1, 12);
    const rows = new Array(Math.min(3, slots)).fill(0).map(() => `
      <article class="luma-hc-item luma-hc-item--skeleton">
        <div class="luma-hc-skeleton-line"></div>
        <div class="luma-hc-skeleton-line short"></div>
        <div class="luma-hc-skeleton-line"></div>
      </article>
    `).join('');
    el.innerHTML = `
      <section class="luma-hc-wrap luma-hc-theme-${esc(opts.theme)} luma-hc-density-${esc(opts.density)}">
        <header class="luma-hc-head">
          <h3>${esc(opts.title || 'Healthcare Opportunity Radar')}</h3>
          <div class="luma-hc-sub">Loading candidate opportunities...</div>
        </header>
        <div class="luma-hc-list">${rows}</div>
      </section>
    `;
  }

  function renderWidget(el, payload, opts) {
    const records = Array.isArray(payload.records) ? payload.records : [];
    const maxRows = clamp(toNum(opts.max, 8), 1, 30);
    const rows = records.slice(0, maxRows);

    const summary = payload.summary || {};
    const close7 = toNum(summary.close_7_days, 0);
    const close14 = toNum(summary.close_14_days, 0);
    const immediate = toNum(summary.immediate_or_fast, 0);
    const headlineMetrics = `${close7} close <=7d | ${close14} close <=14d | ${immediate} urgent/priority review`;
    const linkTarget = opts.newTab ? '_blank' : '_self';
    const linkRel = opts.newTab ? 'noopener noreferrer' : '';

    const itemsHtml = rows.length
      ? rows.map((row, index) => {
          const links = row.links || {};
          const submitUrl = String(links.primary_submit_url || '').trim();
          const aiUrl = joinUrl(opts.consoleBase, links.ai_fill_query);
          const consoleUrl = joinUrl(opts.consoleBase, links.grant_console_query);
          const route = labelForRoute(links.submit_route || 'route_unknown');
          const score = toNum((row.scores || {}).composite, 0).toFixed(1);
          const days = toNum(row.days_to_close, 0);
          const action = labelForAction(row.action || 'manual_review');
          const number = String(row.number || '').trim();
          const rank = toNum(row.rank, index + 1);
          const close = closingWindow(days);
          const submitDisabledClass = submitUrl ? '' : ' luma-hc-btn--disabled';
          const submitHref = submitUrl || '#';

          return `
            <article class="luma-hc-item">
              <div class="luma-hc-title-row">
                <span class="luma-hc-rank">#${esc(rank)}</span>
                <h4 class="luma-hc-title">${esc(row.title || 'Untitled Opportunity')}</h4>
              </div>
              <p class="luma-hc-meta">${esc(row.agency || 'Agency n/a')}${number ? ` · ${esc(number)}` : ''}</p>
              <div class="luma-hc-badges">
                <span class="luma-hc-badge">${esc(action || 'Manual Review')}</span>
                <span class="luma-hc-badge luma-hc-badge--${esc(close.tone)}">${esc(close.label)}</span>
                <span class="luma-hc-badge">relevance ${score}</span>
                <span class="luma-hc-badge">${esc(scoreBand(score))}</span>
                <span class="luma-hc-badge">${esc(route)}</span>
              </div>
              <div class="luma-hc-actions">
                <a class="luma-hc-btn luma-hc-btn--primary${submitDisabledClass}" href="${esc(submitHref)}" target="${esc(linkTarget)}" rel="${esc(linkRel)}" aria-disabled="${submitUrl ? 'false' : 'true'}">Review Official Source</a>
                <a class="luma-hc-btn luma-hc-btn--ai" href="${esc(aiUrl)}" target="${esc(linkTarget)}" rel="${esc(linkRel)}">Draft Workspace</a>
                <a class="luma-hc-btn" href="${esc(consoleUrl)}" target="${esc(linkTarget)}" rel="${esc(linkRel)}">Opportunity Console</a>
              </div>
            </article>
          `;
        }).join('')
      : '<div class="luma-hc-empty">No candidate healthcare opportunities are available in this feed yet.</div>';

    const selected = toNum((payload.source || {}).healthcare_engine_metrics?.n_selected, 0);
    const generatedAt = formatGeneratedAt(payload.generated_utc);
    el.innerHTML = `
      <section class="luma-hc-wrap luma-hc-theme-${esc(opts.theme)} luma-hc-density-${esc(opts.density)}">
        <header class="luma-hc-head">
          <h3>${esc(opts.title || 'Healthcare Opportunity Radar')}</h3>
          <div class="luma-hc-sub">${esc(headlineMetrics)}</div>
        </header>
        <p class="luma-hc-boundary">Discovery candidates only. Verify organizational eligibility, current requirements, and the official deadline before deciding to pursue.</p>
        <div class="luma-hc-list">${itemsHtml}</div>
        <footer class="luma-hc-foot">
          source feed refreshed: ${esc(generatedAt)} · candidates selected: ${esc(selected)}
        </footer>
      </section>
    `;
  }

  async function loadFeed(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`feed request failed: ${res.status}`);
    return res.json();
  }

  async function mount(el) {
    const feedUrl = String(el.getAttribute('data-luma-healthcare-feed') || '').trim();
    if (!feedUrl) {
      el.textContent = 'Missing data-luma-healthcare-feed URL.';
      return;
    }

    const opts = {
      title: el.getAttribute('data-luma-title') || 'Healthcare Opportunity Radar',
      max: el.getAttribute('data-luma-max') || '8',
      consoleBase: el.getAttribute('data-luma-grants-console') || '',
      theme: pick(el.getAttribute('data-luma-theme'), THEMES, 'host'),
      density: pick(el.getAttribute('data-luma-density'), DENSITIES, 'cozy'),
      newTab: String(el.getAttribute('data-luma-new-tab') || '1').trim() !== '0',
    };

    try {
      renderLoading(el, opts);
      const payload = await loadFeed(feedUrl);
      renderWidget(el, payload, opts);
      el.setAttribute('data-luma-mounted', '1');
    } catch (err) {
      const msg = (err && err.message) ? err.message : 'Unknown error loading feed';
      el.innerHTML = `<div class="luma-hc-empty">Feed unavailable: ${esc(msg)}</div>`;
    }
  }

  function init(force) {
    ensureStyle();
    const hosts = document.querySelectorAll('[data-luma-healthcare-feed]');
    hosts.forEach((el) => {
      if (!force && el.getAttribute('data-luma-mounted') === '1') return;
      mount(el);
    });
  }

  window.LumaHealthcareEmbed = window.LumaHealthcareEmbed || {};
  window.LumaHealthcareEmbed.refresh = function refreshLumaHealthcareWidgets() {
    init(true);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
