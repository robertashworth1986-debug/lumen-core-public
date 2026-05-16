(function () {
  'use strict';

  function unique(items) {
    var seen = new Set();
    var out = [];
    for (var i = 0; i < items.length; i += 1) {
      var value = items[i];
      if (!value || seen.has(value)) {
        continue;
      }
      seen.add(value);
      out.push(value);
    }
    return out;
  }

  function cleanRel(path) {
    return String(path || '')
      .replace(/^\/+/, '')
      .replace(/\\/g, '/')
      .replace(/^\.\//, '');
  }

  function join(base, rel) {
    var tail = cleanRel(rel);
    return tail ? String(base).replace(/\/$/, '') + '/' + tail : String(base).replace(/\/$/, '');
  }

  function build(opts) {
    opts = opts || {};
    var locationPath = String(opts.locationPath || (typeof location !== 'undefined' ? location.pathname : '')).replace(/\\/g, '/');
    var protocol = String(opts.protocol || (typeof location !== 'undefined' ? location.protocol : ''));
    var isFileProtocol = protocol === 'file:';
    var inInstitutionalDashboard = /\/INSTITUTIONAL_STACK_V2\/dashboard\//i.test(locationPath);

    var outBase = '../out';
    var mirrorOutBase = inInstitutionalDashboard ? '../../out' : '../INSTITUTIONAL_STACK_V2/out';

    var evidenceBase = './evidence';
    var mirrorEvidenceBase = inInstitutionalDashboard ? '../../dashboard/evidence' : '../INSTITUTIONAL_STACK_V2/dashboard/evidence';

    function outCandidates(rel) {
      return unique([
        join(outBase, rel),
        join(mirrorOutBase, rel),
        join(inInstitutionalDashboard ? '/INSTITUTIONAL_STACK_V2/out' : '/out', rel),
        join(inInstitutionalDashboard ? '/out' : '/INSTITUTIONAL_STACK_V2/out', rel),
      ]);
    }

    function evidenceCandidates(rel) {
      return unique([
        join(evidenceBase, rel),
        join(mirrorEvidenceBase, rel),
        join('/evidence', rel),
        join('/INSTITUTIONAL_STACK_V2/dashboard/evidence', rel),
      ]);
    }

    function dashboardCandidates(rel) {
      var clean = cleanRel(rel);
      return unique([
        './' + clean,
        '../' + clean,
        (inInstitutionalDashboard ? '../../dashboard/' : '../INSTITUTIONAL_STACK_V2/dashboard/') + clean,
        '/' + clean,
        (inInstitutionalDashboard ? '/dashboard/' : '/INSTITUTIONAL_STACK_V2/dashboard/') + clean,
      ]);
    }

    function resolvePaneSrc(src) {
      if (!src) {
        return '';
      }
      if (/^(https?:|file:|about:|data:|blob:|#)/i.test(src)) {
        return src;
      }
      if (isFileProtocol && src.charAt(0) === '/') {
        return '.' + src;
      }
      return src;
    }

    function resolveApiPath(path, apiBase) {
      if (/^https?:\/\//i.test(path)) {
        return path;
      }
      var base = String(apiBase || '').trim();
      if (base && path.charAt(0) === '/') {
        return base.replace(/\/$/, '') + path;
      }
      return path;
    }

    return {
      isFileProtocol: isFileProtocol,
      inInstitutionalDashboard: inInstitutionalDashboard,
      outBase: outBase,
      grantsBase: outBase + '/grants',
      evidenceBase: evidenceBase,
      evidenceRunsBase: evidenceBase + '/runs',
      outCandidates: outCandidates,
      evidenceCandidates: evidenceCandidates,
      dashboardCandidates: dashboardCandidates,
      resolvePaneSrc: resolvePaneSrc,
      resolveApiPath: resolveApiPath,
    };
  }

  window.LumaPathResolver = {
    build: build,
  };
})();
