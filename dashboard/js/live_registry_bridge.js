(function () {
  'use strict';

  // This is a display-retention limit for report generation, not a claim about
  // the age of underlying market observations, broker state or infrastructure.
  var MAX_REPORT_AGE_MS = 300000;

  function record(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  async function readJson(path) {
    try {
      var url = path + (path.indexOf('?') >= 0 ? '&' : '?') + 't=' + Date.now();
      var resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) {
        return null;
      }
      var value = await resp.json();
      return record(value) ? value : null;
    } catch (err) {
      return null;
    }
  }

  function setText(id, value, report) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.textContent = value;
    el.title = (report ? 'Report generated: ' + report.generated + '; ' : 'No usable report; ') +
      'source observation/freshness unknown. ' +
      '300s maximum report age; report generation does not establish execution authority.';
  }

  function recentReport(payload, now) {
    if (!record(payload) || (payload.error !== undefined && payload.error !== null)) {
      return null;
    }
    // These legacy producers write generated_utc, not a source-observation
    // timestamp. Accept only their explicit UTC timestamp format for report age.
    var stamp = payload.generated_utc;
    if (typeof stamp !== 'string' ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(stamp)) {
      return null;
    }
    var time = Date.parse(stamp);
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 19) !== stamp.slice(0, 19) ||
        time > now || now - time > MAX_REPORT_AGE_MS) {
      return null;
    }
    return { data: payload, generated: new Date(time).toISOString() };
  }

  function num(value, digits) {
    return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : null;
  }

  function count(value) {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
  }

  function text(value) {
    return typeof value === 'string' && value.trim() ? value.trim() : null;
  }

  function reported(value) {
    return value === null || value === undefined ? 'n/a' : 'Reported: ' + value;
  }

  function clearValues() {
    ['livePicksCount', 'liveTopPick', 'liveTopEdge', 'liveStackHealth',
      'liveVix', 'liveExecMode', 'liveInfraHealth'].forEach(function (id) {
      setText(id, 'n/a');
    });
    setText('liveRegime', 'unknown');
  }

  async function refresh() {
    var attempted = new Date().toISOString();
    // A new poll must not leave previously displayed values looking current
    // while requests are pending or when a source is unavailable.
    clearValues();
    setText('liveRegistryStamp', 'Poll attempted: ' + attempted +
      ' | Source observation: unknown | Freshness: unknown');
    var data = await Promise.all([
      readJson('../out/sports_intelligence/_dk_alpha_board.json'),
      readJson('../out/sports_intelligence/_dk_advanced_stack_report.json'),
      readJson('../out/sports_intelligence/_dk_macro_regime.json'),
      readJson('../execution_status.json'),
      readJson('../infra_live_status.json')
    ]);

    var now = Date.now();
    var reports = data.map(function (payload) { return recentReport(payload, now); });
    var boardReport = reports[0];
    var stackReport = reports[1];
    var macroReport = reports[2];
    var execReport = reports[3];
    var infraReport = reports[4];

    if (boardReport) {
      var board = boardReport.data;
      var rows = board.rows;
      if (Array.isArray(rows) && rows.every(record) &&
          (board.count === undefined || (count(board.count) && board.count === rows.length))) {
        setText('livePicksCount', reported(rows.length), boardReport);
        var topPick = rows.length ? rows[0] : null;
        setText('liveTopPick', reported(topPick ? text(topPick.pick) : null), boardReport);
        var edge = topPick ? num(topPick.edge_pct, 2) : null;
        setText('liveTopEdge', reported(edge === null ? null : edge + '%'), boardReport);
      }
    }

    if (stackReport) {
      var stack = stackReport.data;
      if (count(stack.installed_count) && count(stack.total_checked) &&
          stack.total_checked > 0 && stack.installed_count <= stack.total_checked) {
        setText('liveStackHealth', reported(stack.installed_count + '/' + stack.total_checked), stackReport);
      }
    }

    if (macroReport) {
      var macro = macroReport.data;
      var regime = text(macro.regime);
      setText('liveRegime', regime ? reported(regime) : 'unknown', macroReport);
      setText('liveVix', reported(num(macro.vix, 2)), macroReport);
    }

    if (execReport) {
      var execStatus = execReport.data;
      var mode = text(execStatus.execution_mode) || text(execStatus.mode) || text(execStatus.runtime_mode);
      setText('liveExecMode', reported(mode), execReport);
    }
    if (infraReport) {
      var infraStatus = infraReport.data;
      setText('liveInfraHealth', reported(text(infraStatus.health) || text(infraStatus.status)), infraReport);
    }
  }

  function mount(intervalSec) {
    var sec = Number(intervalSec);
    if (!Number.isFinite(sec) || sec <= 0) {
      sec = 20;
    }
    refresh();
    setInterval(refresh, sec * 1000);
  }

  window.LumaLiveBridge = {
    refresh: refresh,
    mount: mount
  };
})();
