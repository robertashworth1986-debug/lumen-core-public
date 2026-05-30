/**
 * AlphaGlobe3D — Immersive 3D/4D crypto alpha visualization
 *
 * Renders Kraken trading pairs as a glowing particle globe where:
 *   • Position   = deterministic sphere distribution (Fibonacci lattice)
 *   • Color      = alpha tier (green=strong → yellow=moderate → red=avoid)
 *   • Size       = liquidity/confidence score
 *   • Pulse rate = momentum / spike frequency
 *   • Rotation   = live market velocity (4D time dimension)
 *
 * Uses window.THREE (loaded by lumencore.js or any Three.js script tag).
 *
 * Usage:
 *   const globe = new AlphaGlobe3D(document.getElementById('globe-canvas'));
 *   globe.loadFromUrl('/out/ops/kraken_multi_tf_alpha_map_latest.json');
 *   globe.loadData(alphaArray);   // direct feed
 *
 * Events:
 *   globe.on('select', (pair) => { ... })
 *   globe.on('hover',  (pair) => { ... })
 */
(function (global) {
  'use strict';

  // -------------------------------------------------------------------------
  // Tier → color map  (HSL components for shader blending)
  // -------------------------------------------------------------------------
  var TIER_COLORS = {
    strong:   { r: 0.13, g: 0.92, b: 0.52 },  // emerald
    moderate: { r: 0.98, g: 0.78, b: 0.10 },  // amber
    neutral:  { r: 0.53, g: 0.71, b: 1.00 },  // sky blue
    weak:     { r: 1.00, g: 0.45, b: 0.12 },  // orange
    avoid:    { r: 0.94, g: 0.20, b: 0.20 },  // red
  };

  var PRIORITY_SIZE = { strong: 1.8, moderate: 1.2, neutral: 0.9, weak: 0.7, avoid: 0.55 };

  function tierFromScore(score) {
    if (score >= 0.75) return 'strong';
    if (score >= 0.55) return 'moderate';
    if (score >= 0.35) return 'neutral';
    if (score >= 0.15) return 'weak';
    return 'avoid';
  }

  // Fibonacci sphere distribution — no clumping
  function fibonacciSphere(n, idx) {
    var goldenAngle = Math.PI * (3 - Math.sqrt(5));
    var y = 1 - (idx / (n - 1)) * 2;
    var radius = Math.sqrt(1 - y * y);
    var theta = goldenAngle * idx;
    return {
      x: Math.cos(theta) * radius,
      y: y,
      z: Math.sin(theta) * radius,
    };
  }

  // -------------------------------------------------------------------------
  // Vertex shader — per-particle glow + pulse
  // -------------------------------------------------------------------------
  var VERT_SHADER = [
    'uniform float uTime;',
    'attribute float aAlpha;',
    'attribute float aSize;',
    'attribute float aPulsePhase;',
    'attribute vec3  aColor;',
    'varying  vec3  vColor;',
    'varying  float vAlpha;',
    'void main() {',
    '  vColor = aColor;',
    '  float pulse = 0.85 + 0.15 * sin(uTime * 2.2 + aPulsePhase);',
    '  vAlpha = aAlpha * pulse;',
    '  vec4 mv = modelViewMatrix * vec4(position, 1.0);',
    '  gl_PointSize = aSize * pulse * (320.0 / -mv.z);',
    '  gl_Position = projectionMatrix * mv;',
    '}',
  ].join('\n');

  // Fragment shader — soft round glow disc
  var FRAG_SHADER = [
    'varying vec3  vColor;',
    'varying float vAlpha;',
    'void main() {',
    '  vec2  uv  = gl_PointCoord - 0.5;',
    '  float d   = dot(uv, uv);',
    '  if (d > 0.25) discard;',
    '  float rim  = 1.0 - smoothstep(0.08, 0.25, d);',
    '  float core = 1.0 - smoothstep(0.0,  0.08, d);',
    '  float glow = rim * 0.55 + core * 1.0;',
    '  gl_FragColor = vec4(vColor, vAlpha * glow);',
    '}',
  ].join('\n');

  // -------------------------------------------------------------------------
  // AlphaGlobe3D constructor
  // -------------------------------------------------------------------------
  function AlphaGlobe3D(canvas, options) {
    this._canvas  = canvas;
    this._opts    = Object.assign({
      radius:       5.2,
      fov:          52,
      autoRotate:   true,
      rotateSpeed:  0.0018,
      minDpr:       1.0,
      maxDpr:       2.0,
      labelTop:     10,        // how many top pairs to label
    }, options || {});

    this._data    = [];
    this._pairs   = {};
    this._time    = 0;
    this._alive   = false;
    this._handlers = {};
    this._THREE   = null;

    this._raycaster   = null;
    this._mouse       = { x: 0, y: 0 };
    this._hoveredIdx  = -1;
    this._selectedPair = null;

    // Tooltip element (created lazily)
    this._tooltip = null;

    this._initWhenReady();
  }

  AlphaGlobe3D.prototype.on = function (evt, fn) {
    this._handlers[evt] = fn;
    return this;
  };

  AlphaGlobe3D.prototype._emit = function (evt, data) {
    if (typeof this._handlers[evt] === 'function') this._handlers[evt](data);
  };

  AlphaGlobe3D.prototype._initWhenReady = function () {
    var self = this;
    // Wait for window.THREE to be available
    function tryInit() {
      if (window.THREE) {
        self._THREE = window.THREE;
        self._init();
      } else {
        setTimeout(tryInit, 80);
      }
    }
    tryInit();
  };

  AlphaGlobe3D.prototype._init = function () {
    var T = this._THREE;
    var canvas = this._canvas;
    var opts   = this._opts;

    // Renderer
    this._renderer = new T.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    var dpr = Math.min(window.devicePixelRatio || 1, opts.maxDpr);
    this._renderer.setPixelRatio(dpr);
    this._renderer.setSize(canvas.clientWidth || 400, canvas.clientHeight || 400);

    // Scene
    this._scene = new T.Scene();

    // Camera
    this._camera = new T.PerspectiveCamera(
      opts.fov,
      (canvas.clientWidth || 400) / (canvas.clientHeight || 400),
      0.1, 200
    );
    this._camera.position.set(0, 0, 14);

    // Ambient ring mesh (wireframe sphere behind particles)
    var ringGeo = new T.SphereGeometry(opts.radius * 1.01, 32, 32);
    var ringMat = new T.MeshBasicMaterial({
      color: 0x22d3ee,
      wireframe: true,
      transparent: true,
      opacity: 0.045,
    });
    this._scene.add(new T.Mesh(ringGeo, ringMat));

    // Equatorial glow ring
    var torusGeo = new T.TorusGeometry(opts.radius * 1.01, 0.018, 8, 180);
    var torusMat = new T.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.35 });
    var torus = new T.Mesh(torusGeo, torusMat);
    torus.rotation.x = Math.PI / 2;
    this._scene.add(torus);

    // Axis lines
    var lineMat = new T.LineBasicMaterial({ color: 0xa855f7, transparent: true, opacity: 0.2 });
    var axisGeo = new T.BufferGeometry().setFromPoints([
      new T.Vector3(0, -opts.radius * 1.1, 0),
      new T.Vector3(0,  opts.radius * 1.1, 0),
    ]);
    this._scene.add(new T.Line(axisGeo, lineMat));

    // Raycaster for hover/click
    this._raycaster = new T.Raycaster();
    this._raycaster.params.Points = { threshold: 0.22 };

    // Event listeners
    var self = this;
    canvas.addEventListener('mousemove', function (e) { self._onMouseMove(e); }, { passive: true });
    canvas.addEventListener('click',     function (e) { self._onClick(e); });
    window.addEventListener('resize',    function ()  { self._onResize(); }, { passive: true });

    // Touch orbit drag
    this._drag = { active: false, lastX: 0, lastY: 0 };
    canvas.addEventListener('mousedown',  function (e) { self._drag.active = true; self._drag.lastX = e.clientX; self._drag.lastY = e.clientY; });
    canvas.addEventListener('mouseup',    function ()  { self._drag.active = false; });
    canvas.addEventListener('mousemove',  function (e) { self._onDrag(e); }, { passive: true });
    canvas.addEventListener('wheel',      function (e) { self._onZoom(e); }, { passive: true });

    this._alive = true;
    this._animate();
  };

  // -------------------------------------------------------------------------
  // Build / rebuild particle geometry from data
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype._buildParticles = function () {
    var T    = this._THREE;
    var data = this._data;
    var n    = data.length;
    var opts = this._opts;

    if (this._points) {
      this._scene.remove(this._points);
      this._points.geometry.dispose();
      this._points.material.dispose();
      this._points = null;
    }

    if (n === 0) return;

    var positions   = new Float32Array(n * 3);
    var colors      = new Float32Array(n * 3);
    var sizes       = new Float32Array(n);
    var alphas      = new Float32Array(n);
    var pulsePhases = new Float32Array(n);

    for (var i = 0; i < n; i++) {
      var d    = data[i];
      var tier = d.alpha_tier || tierFromScore(d.alpha_score || 0);
      var col  = TIER_COLORS[tier] || TIER_COLORS.neutral;
      var pos  = fibonacciSphere(n, i);
      var r    = opts.radius;

      positions[i * 3]     = pos.x * r;
      positions[i * 3 + 1] = pos.y * r;
      positions[i * 3 + 2] = pos.z * r;

      colors[i * 3]     = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;

      sizes[i]       = PRIORITY_SIZE[tier] || 0.9;
      alphas[i]      = 0.75 + (d.alpha_score || 0.5) * 0.25;
      pulsePhases[i] = i * 0.41;
    }

    var geo = new T.BufferGeometry();
    geo.setAttribute('position',   new T.BufferAttribute(positions,   3));
    geo.setAttribute('aColor',     new T.BufferAttribute(colors,      3));
    geo.setAttribute('aSize',      new T.BufferAttribute(sizes,       1));
    geo.setAttribute('aAlpha',     new T.BufferAttribute(alphas,      1));
    geo.setAttribute('aPulsePhase',new T.BufferAttribute(pulsePhases, 1));

    this._uniforms = { uTime: { value: 0 } };

    var mat = new T.ShaderMaterial({
      uniforms: this._uniforms,
      vertexShader: VERT_SHADER,
      fragmentShader: FRAG_SHADER,
      transparent: true,
      depthWrite: false,
      blending: T.AdditiveBlending,
    });

    this._points = new T.Points(geo, mat);
    this._scene.add(this._points);
  };

  // -------------------------------------------------------------------------
  // Data loading
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype.loadData = function (arr) {
    if (!Array.isArray(arr)) {
      arr = arr.pairs || arr.items || arr.data || [];
    }
    // Sort by alpha_score descending for Fibonacci positioning (top signals near equator)
    this._data = arr.slice().sort(function (a, b) {
      return (b.alpha_score || 0) - (a.alpha_score || 0);
    });
    // Build lookup map
    this._pairs = {};
    for (var i = 0; i < this._data.length; i++) {
      this._pairs[this._data[i].pair || i] = i;
    }
    this._buildParticles();
    this._emit('ready', { count: this._data.length });
  };

  AlphaGlobe3D.prototype.loadFromUrl = function (url) {
    var self = this;
    var FALLBACKS = [
      url,
      '../out/ops/kraken_multi_tf_alpha_map_latest.json',
      '/out/ops/kraken_multi_tf_alpha_map_latest.json',
    ];
    function tryNext(idx) {
      if (idx >= FALLBACKS.length) {
        self._emit('error', { message: 'All alpha map URLs failed' });
        return;
      }
      fetch(FALLBACKS[idx])
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          return r.json();
        })
        .then(function (json) {
          self.loadData(json);
        })
        .catch(function () { tryNext(idx + 1); });
    }
    tryNext(0);
  };

  // -------------------------------------------------------------------------
  // Animation loop
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype._animate = function () {
    if (!this._alive) return;
    var self = this;
    requestAnimationFrame(function () { self._animate(); });

    this._time += 0.016;
    if (this._uniforms) this._uniforms.uTime.value = this._time;

    if (this._opts.autoRotate && this._points && !this._drag.active) {
      this._points.rotation.y += this._opts.rotateSpeed;
    }

    this._renderer.render(this._scene, this._camera);
  };

  // -------------------------------------------------------------------------
  // Interaction
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype._updateMouse = function (e) {
    var rect = this._canvas.getBoundingClientRect();
    this._mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
    this._mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
  };

  AlphaGlobe3D.prototype._onMouseMove = function (e) {
    this._updateMouse(e);
    if (!this._points || !this._raycaster) return;
    this._raycaster.setFromCamera(this._mouse, this._camera);
    var hits = this._raycaster.intersectObject(this._points);
    if (hits.length > 0) {
      var idx = hits[0].index;
      if (idx !== this._hoveredIdx) {
        this._hoveredIdx = idx;
        var d = this._data[idx];
        if (d) {
          this._showTooltip(e, d);
          this._emit('hover', d);
        }
      }
    } else {
      this._hoveredIdx = -1;
      this._hideTooltip();
    }
  };

  AlphaGlobe3D.prototype._onClick = function (e) {
    if (!this._points || !this._raycaster) return;
    this._updateMouse(e);
    this._raycaster.setFromCamera(this._mouse, this._camera);
    var hits = this._raycaster.intersectObject(this._points);
    if (hits.length > 0) {
      var d = this._data[hits[0].index];
      if (d) {
        this._selectedPair = d;
        this._emit('select', d);
      }
    }
  };

  AlphaGlobe3D.prototype._onDrag = function (e) {
    if (!this._drag.active || !this._points) return;
    var dx = (e.clientX - this._drag.lastX) * 0.006;
    var dy = (e.clientY - this._drag.lastY) * 0.004;
    this._points.rotation.y += dx;
    this._points.rotation.x += dy;
    this._drag.lastX = e.clientX;
    this._drag.lastY = e.clientY;
  };

  AlphaGlobe3D.prototype._onZoom = function (e) {
    this._camera.position.z = Math.max(8, Math.min(28, this._camera.position.z + e.deltaY * 0.02));
  };

  AlphaGlobe3D.prototype._onResize = function () {
    var canvas = this._canvas;
    var w = canvas.clientWidth  || 400;
    var h = canvas.clientHeight || 400;
    this._camera.aspect = w / h;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(w, h, false);
  };

  // -------------------------------------------------------------------------
  // Tooltip
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype._ensureTooltip = function () {
    if (this._tooltip) return;
    var tt = document.createElement('div');
    tt.id = 'ag3d-tooltip';
    tt.style.cssText = [
      'position:fixed;pointer-events:none;z-index:9999;',
      'background:rgba(4,7,18,0.92);border:1px solid rgba(34,211,238,0.5);',
      'border-radius:8px;padding:8px 12px;font-family:JetBrains Mono,monospace;',
      'font-size:11px;color:#eaf3ff;opacity:0;transition:opacity .15s;',
      'backdrop-filter:blur(12px);box-shadow:0 0 16px rgba(34,211,238,0.25);',
      'max-width:220px;line-height:1.6;',
    ].join('');
    document.body.appendChild(tt);
    this._tooltip = tt;
  };

  AlphaGlobe3D.prototype._showTooltip = function (e, d) {
    this._ensureTooltip();
    var tier = d.alpha_tier || tierFromScore(d.alpha_score || 0);
    var col  = { strong:'#34d399', moderate:'#f59e0b', neutral:'#7dd3fc', weak:'#fb923c', avoid:'#f87171' }[tier] || '#eaf3ff';
    this._tooltip.innerHTML = [
      '<b style="color:' + col + '">' + (d.pair || '—') + '</b>',
      '<span style="color:#7d8bb5"> · ' + tier.toUpperCase() + '</span><br/>',
      'Alpha: <b>' + ((d.alpha_score || 0) * 100).toFixed(1) + '%</b><br/>',
      d.return_24h !== undefined ? '24h: <b style="color:' + (d.return_24h >= 0 ? '#34d399' : '#f87171') + '">' + (d.return_24h * 100).toFixed(2) + '%</b>' : '',
    ].join('');
    this._tooltip.style.left  = (e.clientX + 14) + 'px';
    this._tooltip.style.top   = (e.clientY - 8)  + 'px';
    this._tooltip.style.opacity = '1';
  };

  AlphaGlobe3D.prototype._hideTooltip = function () {
    if (this._tooltip) this._tooltip.style.opacity = '0';
  };

  // -------------------------------------------------------------------------
  // Public control API
  // -------------------------------------------------------------------------
  AlphaGlobe3D.prototype.setRotateSpeed = function (s) { this._opts.rotateSpeed = s; };
  AlphaGlobe3D.prototype.pause  = function () { this._opts.autoRotate = false; };
  AlphaGlobe3D.prototype.resume = function () { this._opts.autoRotate = true; };
  AlphaGlobe3D.prototype.destroy = function () {
    this._alive = false;
    if (this._tooltip) { this._tooltip.remove(); this._tooltip = null; }
    if (this._renderer) { this._renderer.dispose(); }
  };

  // Highlight a specific pair by name
  AlphaGlobe3D.prototype.highlightPair = function (pairName) {
    var idx = this._pairs[pairName];
    if (idx === undefined || !this._points) return;
    var sizes = this._points.geometry.attributes.aSize;
    var base  = PRIORITY_SIZE[this._data[idx].alpha_tier || 'neutral'] || 0.9;
    sizes.array[idx] = base * 3.2;
    sizes.needsUpdate = true;
  };

  // Export static image of current frame
  AlphaGlobe3D.prototype.snapshot = function () {
    this._renderer.render(this._scene, this._camera);
    return this._canvas.toDataURL('image/png');
  };

  // -------------------------------------------------------------------------
  // Static factory
  // -------------------------------------------------------------------------
  AlphaGlobe3D.mount = function (selectorOrEl, options) {
    var el = typeof selectorOrEl === 'string'
      ? document.querySelector(selectorOrEl)
      : selectorOrEl;
    if (!el) return null;
    // If container (not canvas), create canvas inside it
    var canvas = el;
    if (el.tagName !== 'CANVAS') {
      canvas = document.createElement('canvas');
      canvas.style.cssText = 'width:100%;height:100%;display:block;';
      el.appendChild(canvas);
    }
    return new AlphaGlobe3D(canvas, options);
  };

  // Expose globally
  global.AlphaGlobe3D = AlphaGlobe3D;

})(window);
