(function () {
  'use strict';

  var STYLE_ID = 'luma-cinematic-style';

  function clamp(value, min, max) {
    var num = Number(value);
    if (!Number.isFinite(num)) {
      return min;
    }
    return Math.max(min, Math.min(max, num));
  }

  function preferredReducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (_) {
      return false;
    }
  }

  function resolveProfile() {
    var mem = Number(navigator.deviceMemory || 0);
    var cores = Number(navigator.hardwareConcurrency || 0);
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    var saveData = !!(conn && conn.saveData);
    var reducedMotion = preferredReducedMotion();
    var compactViewport = Math.min(window.innerWidth || 0, window.innerHeight || 0) < 900;

    var tier = 'ultra';
    if (saveData || reducedMotion || compactViewport || (mem > 0 && mem <= 4) || (cores > 0 && cores <= 4)) {
      tier = 'balanced';
    }
    if (saveData || reducedMotion || (mem > 0 && mem <= 2) || (cores > 0 && cores <= 2)) {
      tier = 'lite';
    }

    var map = {
      ultra: {
        maxDpr: 1.9,
        laneSegments: 38,
        gridRows: 12,
        gridCols: 14,
        frameStride: 1,
        motionScale: 1,
        pointerScale: 1,
      },
      balanced: {
        maxDpr: 1.6,
        laneSegments: 30,
        gridRows: 10,
        gridCols: 10,
        frameStride: 1,
        motionScale: 0.82,
        pointerScale: 0.72,
      },
      lite: {
        maxDpr: 1.25,
        laneSegments: 20,
        gridRows: 8,
        gridCols: 7,
        frameStride: 2,
        motionScale: 0.58,
        pointerScale: 0.35,
      },
    };

    return {
      tier: tier,
      reducedMotion: reducedMotion,
      saveData: saveData,
      config: map[tier],
    };
  }

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) {
      return;
    }

    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = [
      '.luma-cinematic-host { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }',
      '.luma-cinematic-canvas { width: 100%; height: 100%; display: block; opacity: 0.88; }',
      '.luma-cinematic-hud {',
      '  position: fixed; right: 16px; top: 90px; z-index: 7; pointer-events: none;',
      '  display: grid; grid-template-columns: repeat(2, minmax(72px, 1fr)); gap: 7px;',
      '  width: min(264px, 46vw);',
      '}',
      '.luma-cinematic-chip {',
      '  border: 1px solid rgba(34, 211, 238, 0.25);',
      '  background: linear-gradient(180deg, rgba(8, 14, 32, 0.82), rgba(8, 14, 32, 0.46));',
      '  border-radius: 8px; padding: 5px 7px;',
      '  box-shadow: 0 0 12px rgba(34, 211, 238, 0.14);',
      '  backdrop-filter: blur(8px);',
      '}',
      '.luma-cinematic-chip .k {',
      '  display: block; color: rgba(156, 163, 175, 0.9); font: 600 9px/1.2 "JetBrains Mono", monospace;',
      '  letter-spacing: 1.2px; text-transform: uppercase;',
      '}',
      '.luma-cinematic-chip .v {',
      '  display: block; color: #dbeafe; font: 700 12px/1.2 "Orbitron", sans-serif; letter-spacing: 0.7px;',
      '}',
      '.luma-cinematic-chip.warn .v { color: #f59e0b; }',
      '.luma-cinematic-chip.alert .v { color: #ef4444; }',
      '.luma-cinematic-chip[data-chip="confidence"] .v { color: #22d3ee; }',
      '.luma-cinematic-meta {',
      '  grid-column: span 2; border: 1px solid rgba(168, 85, 247, 0.28); border-radius: 8px;',
      '  padding: 6px 8px; background: rgba(17, 24, 39, 0.72);',
      '  font: 600 9px/1.35 "JetBrains Mono", monospace; letter-spacing: 1px; text-transform: uppercase;',
      '  color: #a5b4fc;',
      '}',
      '@media (max-width: 940px) {',
      '  .luma-cinematic-hud { right: 10px; top: 72px; width: min(220px, 62vw); opacity: 0.9; }',
      '  .luma-cinematic-chip .v { font-size: 11px; }',
      '}',
      '@media (max-width: 760px) {',
      '  .luma-cinematic-hud { grid-template-columns: 1fr 1fr; width: min(190px, 76vw); top: 108px; }',
      '  .luma-cinematic-meta { display: none; }',
      '}',
    ].join('\n');

    document.head.appendChild(style);
  }

  function mount(options) {
    options = options || {};

    var host = options.host || document.body;
    if (!host || !host.appendChild) {
      return null;
    }

    ensureStyle();

    if (!host.classList.contains('luma-cinematic-host')) {
      host.classList.add('luma-cinematic-host');
    }

    var profile = resolveProfile();
    var cfg = profile.config;

    var canvas = document.createElement('canvas');
    canvas.className = 'luma-cinematic-canvas';
    host.appendChild(canvas);

    var hud = document.createElement('div');
    hud.className = 'luma-cinematic-hud';
    hud.innerHTML = [
      '<div class="luma-cinematic-chip" data-chip="pulse"><span class="k">Pulse</span><span class="v" data-v="pulse">52%</span></div>',
      '<div class="luma-cinematic-chip" data-chip="integrity"><span class="k">Integrity</span><span class="v" data-v="integrity">74%</span></div>',
      '<div class="luma-cinematic-chip" data-chip="throughput"><span class="k">Throughput</span><span class="v" data-v="throughput">45%</span></div>',
      '<div class="luma-cinematic-chip" data-chip="anomaly"><span class="k">Anomaly</span><span class="v" data-v="anomaly">12%</span></div>',
      '<div class="luma-cinematic-chip" data-chip="confidence"><span class="k">Confidence</span><span class="v" data-v="confidence">66%</span></div>',
      '<div class="luma-cinematic-meta" data-v="meta">MODE SYNC · SOURCE ARTIFACT</div>',
    ].join('');
    host.appendChild(hud);

    var ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
    if (!ctx) {
      hud.remove();
      canvas.remove();
      return null;
    }

    var metrics = {
      pulse: 52,
      integrity: 74,
      anomaly: 12,
      throughput: 45,
      confidence: 66,
    };

    var meta = {
      mode: String(options.mode || 'SYNC').toUpperCase(),
      source: String(options.source || 'ARTIFACT').toUpperCase(),
      cue: '',
    };

    var bars = [];
    for (var i = 0; i < cfg.laneSegments; i += 1) {
      bars.push(0.18 + Math.random() * 0.45);
    }

    var pointer = { x: 0, y: 0 };
    var pointerMove = null;
    if (!profile.reducedMotion) {
      pointerMove = function (ev) {
        var w = Math.max(1, window.innerWidth || 1);
        var h = Math.max(1, window.innerHeight || 1);
        pointer.x = ((ev.clientX / w) * 2 - 1) * cfg.pointerScale;
        pointer.y = ((ev.clientY / h) * 2 - 1) * cfg.pointerScale;
      };
      window.addEventListener('pointermove', pointerMove, { passive: true });
    }

    var running = true;
    var rafId = 0;
    var timerId = 0;
    var width = 1;
    var height = 1;
    var dpr = 1;
    var last = performance.now();
    var phase = 0;
    var frame = 0;

    function byValue(key) {
      return hud.querySelector('[data-v="' + key + '"]');
    }

    function byChip(key) {
      return hud.querySelector('[data-chip="' + key + '"]');
    }

    function refreshHud() {
      var keys = ['pulse', 'integrity', 'throughput', 'anomaly', 'confidence'];
      for (var i = 0; i < keys.length; i += 1) {
        var key = keys[i];
        var valueNode = byValue(key);
        if (valueNode) {
          valueNode.textContent = String(Math.round(metrics[key])) + '%';
        }
      }

      var anomalyChip = byChip('anomaly');
      var integrityChip = byChip('integrity');
      var confidenceChip = byChip('confidence');
      if (anomalyChip) {
        anomalyChip.classList.toggle('warn', metrics.anomaly >= 25 && metrics.anomaly < 50);
        anomalyChip.classList.toggle('alert', metrics.anomaly >= 50);
      }
      if (integrityChip) {
        integrityChip.classList.toggle('warn', metrics.integrity < 62 && metrics.integrity >= 45);
        integrityChip.classList.toggle('alert', metrics.integrity < 45);
      }
      if (confidenceChip) {
        confidenceChip.classList.toggle('warn', metrics.confidence < 55 && metrics.confidence >= 38);
        confidenceChip.classList.toggle('alert', metrics.confidence < 38);
      }

      var metaNode = byValue('meta');
      if (metaNode) {
        var text = 'MODE ' + meta.mode + ' · SOURCE ' + meta.source + ' · TIER ' + String(profile.tier).toUpperCase();
        if (meta.cue) {
          text += ' · CUE ' + meta.cue;
        }
        metaNode.textContent = text;
      }
    }

    function resize() {
      var rect = host.getBoundingClientRect();
      var safeW = Math.max(320, Math.round(rect.width || window.innerWidth || 1280));
      var safeH = Math.max(220, Math.round(rect.height || window.innerHeight || 720));
      dpr = Math.min(window.devicePixelRatio || 1, cfg.maxDpr);
      width = safeW;
      height = safeH;
      canvas.width = Math.round(safeW * dpr);
      canvas.height = Math.round(safeH * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function drawFrame(now) {
      var dt = Math.max(0, Math.min(0.08, (now - last) / 1000));
      last = now;
      phase += dt * cfg.motionScale;

      var pulse = metrics.pulse / 100;
      var anomaly = metrics.anomaly / 100;
      var throughput = metrics.throughput / 100;
      var confidence = metrics.confidence / 100;

      ctx.clearRect(0, 0, width, height);

      var bg = ctx.createRadialGradient(
        width * (0.55 + pointer.x * 0.02),
        height * (0.34 - pointer.y * 0.025),
        40,
        width * 0.5,
        height * 0.7,
        width * 0.92
      );
      bg.addColorStop(0, 'rgba(14, 165, 233, 0.16)');
      bg.addColorStop(0.42, 'rgba(6, 8, 24, 0.11)');
      bg.addColorStop(1, 'rgba(0, 0, 0, 0.02)');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, width, height);

      var horizonY = height * (0.32 + Math.sin(phase * 0.13) * 0.014 - pointer.y * 0.01);
      var centerX = width * 0.5 + Math.sin(phase * 0.4) * width * 0.03 + pointer.x * width * 0.04;

      ctx.lineWidth = 1;
      for (var g = 0; g < cfg.gridRows; g += 1) {
        var t = (g + 1) / cfg.gridRows;
        var y = horizonY + Math.pow(t, 1.7) * (height - horizonY - 8);
        ctx.strokeStyle = 'rgba(34, 211, 238,' + (0.055 + t * 0.09) + ')';
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      for (var v = -cfg.gridCols; v <= cfg.gridCols; v += 1) {
        var ratio = v / cfg.gridCols;
        var xTop = centerX + ratio * width * 0.06;
        var xBottom = centerX + ratio * width * 0.76;
        ctx.strokeStyle = 'rgba(99, 102, 241,' + (0.038 + Math.abs(ratio) * 0.036) + ')';
        ctx.beginPath();
        ctx.moveTo(xTop, horizonY);
        ctx.lineTo(xBottom, height);
        ctx.stroke();
      }

      var laneWidth = width * 0.88;
      var laneStart = (width - laneWidth) / 2;
      var baseY = height - 10;
      var spread = laneWidth / bars.length;

      for (var i = 0; i < bars.length; i += 1) {
        var depth = i / Math.max(1, bars.length - 1);
        var perspective = 1 - depth * 0.78;
        var nudge = Math.sin(phase * 2.3 + i * 0.8) * 0.045;
        var target = 0.11 + throughput * 0.5 + pulse * 0.16 + nudge;
        bars[i] += (target - bars[i]) * 0.08;

        var barH = Math.max(2, height * 0.42 * clamp(bars[i], 0.05, 0.92) * perspective);
        var barW = Math.max(2, spread * 0.62 * perspective);
        var x = laneStart + i * spread;
        var yTop = baseY - barH;

        var glow = 0.14 + (1 - depth) * 0.14 + confidence * 0.24;
        var r = Math.round(34 + 86 * anomaly);
        var gCol = Math.round(211 - 70 * anomaly + 44 * confidence);
        var b = Math.round(238 - 32 * anomaly + 24 * pulse);

        ctx.fillStyle = 'rgba(' + r + ',' + gCol + ',' + b + ',' + clamp(glow, 0.12, 0.82) + ')';
        ctx.fillRect(x - barW * 0.5, yTop, barW, barH);

        ctx.fillStyle = 'rgba(168, 85, 247,' + clamp(0.08 + pulse * 0.22, 0.08, 0.38) + ')';
        ctx.fillRect(x - barW * 0.55, yTop - 2, barW * 1.1, 2);
      }

      var ringR = Math.min(width, height) * 0.15;
      var ringPulse = 1 + Math.sin(phase * 2.8) * (0.038 + pulse * 0.05);
      ctx.save();
      ctx.translate(centerX, horizonY + height * 0.14 - pointer.y * 12);
      ctx.scale(1.6, 0.52);
      ctx.lineWidth = 1.25;
      ctx.strokeStyle = 'rgba(34, 211, 238,' + clamp(0.34 + pulse * 0.36, 0.3, 0.8) + ')';
      ctx.beginPath();
      ctx.arc(0, 0, ringR * ringPulse, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = 'rgba(168, 85, 247,' + clamp(0.24 + confidence * 0.24, 0.18, 0.62) + ')';
      ctx.beginPath();
      ctx.arc(0, 0, ringR * (0.72 + anomaly * 0.25), 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    function animate(now) {
      if (!running) {
        return;
      }
      rafId = requestAnimationFrame(animate);
      frame += 1;
      if (cfg.frameStride > 1 && (frame % cfg.frameStride) !== 0) {
        return;
      }
      if (document.visibilityState === 'hidden') {
        return;
      }
      drawFrame(now);
    }

    function setMetrics(nextMetrics) {
      if (!nextMetrics || typeof nextMetrics !== 'object') {
        return;
      }
      var keys = ['pulse', 'integrity', 'anomaly', 'throughput', 'confidence'];
      for (var i = 0; i < keys.length; i += 1) {
        var key = keys[i];
        if (Object.prototype.hasOwnProperty.call(nextMetrics, key)) {
          metrics[key] = clamp(nextMetrics[key], 0, 100);
        }
      }
      refreshHud();
    }

    function setMeta(key, value) {
      if (!key) {
        return;
      }
      var norm = String(key).toLowerCase();
      if (norm === 'mode' || norm === 'source') {
        meta[norm] = String(value || '').toUpperCase().slice(0, 24) || meta[norm];
        refreshHud();
        return;
      }
      if (norm === 'cue') {
        meta.cue = String(value || '').toUpperCase().replace(/[^A-Z0-9_\- ]+/g, '').slice(0, 20);
        refreshHud();
      }
    }

    function destroy() {
      running = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
      if (timerId) {
        clearInterval(timerId);
      }
      window.removeEventListener('resize', resize);
      if (pointerMove) {
        window.removeEventListener('pointermove', pointerMove);
      }
      hud.remove();
      canvas.remove();
    }

    resize();
    refreshHud();
    window.addEventListener('resize', resize, { passive: true });

    if (profile.reducedMotion) {
      drawFrame(performance.now());
      timerId = window.setInterval(function () {
        if (!running) {
          return;
        }
        drawFrame(performance.now());
      }, 1200);
    } else {
      rafId = requestAnimationFrame(animate);
    }

    return {
      setMetrics: setMetrics,
      setMeta: setMeta,
      destroy: destroy,
      profile: {
        tier: profile.tier,
        reducedMotion: profile.reducedMotion,
        saveData: profile.saveData,
      },
    };
  }

  window.LumaCinematic = {
    mount: mount,
  };
})();
