(function () {
  'use strict';

  async function readJson(path) {
    try {
      var url = path + (path.indexOf('?') >= 0 ? '&' : '?') + 't=' + Date.now();
      var resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) {
        return null;
      }
      return await resp.json();
    } catch (err) {
      return null;
    }
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.textContent = value;
  }

  function num(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return 'n/a';
    }
    return Number(value).toFixed(digits);
  }

  async function refresh() {
    var data = await Promise.all([
      readJson('../out/sports_intelligence/_dk_alpha_board.json'),
      readJson('../out/sports_intelligence/_dk_advanced_stack_report.json'),
      readJson('../out/sports_intelligence/_dk_macro_regime.json'),
      readJson('../execution_status.json'),
      readJson('../infra_live_status.json')
    ]);

    var board = data[0] || {};
    var stack = data[1] || {};
    var macro = data[2] || {};
    var execStatus = data[3] || {};
    var infraStatus = data[4] || {};

    var rows = Array.isArray(board.rows) ? board.rows : [];
    var topPick = rows.length > 0 ? rows[0] : (board.top_pick || null);

    var picksCount = rows.length || board.count || 0;
    var topPickName = topPick && topPick.pick ? String(topPick.pick) : 'n/a';
    var topEdge = topPick && topPick.edge_pct !== undefined ? num(topPick.edge_pct, 2) + '%' : 'n/a';

    var stackInstalled = stack.installed_count;
    var stackTotal = stack.total_checked;
    var stackHealth = (stackInstalled !== undefined && stackTotal !== undefined)
      ? String(stackInstalled) + '/' + String(stackTotal)
      : 'n/a';

    var regime = macro.regime || (board.macro && board.macro.regime) || 'unknown';
    var vix = macro.vix;
    if (vix === undefined && board.macro) {
      vix = board.macro.vix;
    }

    var mode = execStatus.execution_mode || execStatus.mode || execStatus.runtime_mode || 'n/a';
    var infraHealth = infraStatus.health || infraStatus.status || execStatus.status || 'n/a';

    setText('liveRegistryStamp', new Date().toLocaleString());
    setText('livePicksCount', String(picksCount));
    setText('liveTopPick', topPickName);
    setText('liveTopEdge', topEdge);
    setText('liveStackHealth', stackHealth);
    setText('liveRegime', String(regime));
    setText('liveVix', vix === null || vix === undefined ? 'n/a' : String(vix));
    setText('liveExecMode', String(mode));
    setText('liveInfraHealth', String(infraHealth));
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
