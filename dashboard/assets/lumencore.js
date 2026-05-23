// =====================================================================
// LumenCore Mission Control — shared cinematic chrome
// Loads on every reskinned page; injects:
//   - WebGL particle field + harmonic rings (Three.js via CDN)
//   - boot sequence overlay
//   - top bar (logo, title, nav, clock, LIVE pill)
//   - holographic grid + scanlines
// =====================================================================
(function () {
  // Detect if we're rendered inside the Quant Lab iframe — if so, the parent
  // already provides the topbar, boot sequence, and WebGL field. Skip duplicates.
  const IN_IFRAME = (function () {
    try { return window.self !== window.top; } catch (_) { return true; }
  })();

  const IS_FILE_PROTOCOL = location.protocol === 'file:';
  const USER_API_BASE = (typeof window.LUMA_API_BASE === 'string' && window.LUMA_API_BASE.trim())
    ? window.LUMA_API_BASE.trim().replace(/\/$/, '')
    : '';

  function prefersReducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (_) {
      return false;
    }
  }

  function resolveVisualProfile() {
    const mem = Number(navigator.deviceMemory || 0);
    const cores = Number(navigator.hardwareConcurrency || 0);
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const saveData = Boolean(conn && conn.saveData);
    const reducedMotion = prefersReducedMotion();
    const compactViewport = Math.min(window.innerWidth || 0, window.innerHeight || 0) < 760;

    let tier = 'ultra';
    if (saveData || reducedMotion || compactViewport || (mem && mem <= 4) || (cores && cores <= 4)) {
      tier = 'balanced';
    }
    if (saveData || reducedMotion || (mem && mem <= 2) || (cores && cores <= 2)) {
      tier = 'lite';
    }

    const profile = {
      ultra: {
        maxPixelRatio: 2,
        webglParticles: 1200,
        ringSegments: 320,
        fallbackParticles: 220,
        pointerScale: 1,
        motionScale: 1,
        ringPulse: true,
        frameStride: 1,
      },
      balanced: {
        maxPixelRatio: 1.7,
        webglParticles: 760,
        ringSegments: 224,
        fallbackParticles: 140,
        pointerScale: 0.72,
        motionScale: 0.82,
        ringPulse: true,
        frameStride: 1,
      },
      lite: {
        maxPixelRatio: 1.3,
        webglParticles: 420,
        ringSegments: 128,
        fallbackParticles: 80,
        pointerScale: 0.42,
        motionScale: 0.55,
        ringPulse: false,
        frameStride: 2,
      },
    };

    return {
      tier,
      saveData,
      reducedMotion,
      ...profile[tier],
    };
  }

  const PERF = resolveVisualProfile();

  function normalizeDashboardHref(href) {
    if (!href) return href;
    if (/^(https?:|mailto:|#|javascript:)/i.test(href)) return href;
    if (IS_FILE_PROTOCOL && href.startsWith('/')) return '.' + href;
    return href;
  }

  function uniq(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  function normalizeLegacyPath(path) {
    const raw = String(path || '');
    if (raw.startsWith('/INSTITUTIONAL_STACK_V2/out/')) {
      return '/out/' + raw.slice('/INSTITUTIONAL_STACK_V2/out/'.length);
    }
    if (raw.startsWith('/INSTITUTIONAL_STACK_V2/dashboard/')) {
      return '/' + raw.slice('/INSTITUTIONAL_STACK_V2/dashboard/'.length);
    }
    return raw;
  }

  function resolveWsUrl(path = '/ws/live') {
    if (USER_API_BASE) {
      const wsBase = USER_API_BASE
        .replace(/^https:\/\//i, 'wss://')
        .replace(/^http:\/\//i, 'ws://');
      return wsBase + path;
    }
    if (IS_FILE_PROTOCOL || !location.host) return '';
    return (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + path;
  }

  // 1. Inject overlay layers
  function el(tag, attrs = {}, parent = document.body) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'html') e.innerHTML = v;
      else if (k === 'text') e.textContent = v;
      else e.setAttribute(k, v);
    });
    parent.appendChild(e);
    return e;
  }

  // Underlay: WebGL canvas + grid + scanlines (prepend so they sit at z-index 0..2)
  const layers = document.createDocumentFragment();
  const canvas = document.createElement('canvas'); canvas.id = 'bg-canvas';
  const grid = document.createElement('div'); grid.id = 'grid-overlay';
  const scan = document.createElement('div'); scan.id = 'scanlines';
  // Inside an iframe we keep a transparent body so the parent's WebGL shows through
  if (IN_IFRAME) {
    document.documentElement.style.background = 'transparent';
    document.body.style.background = 'transparent';
  } else {
    layers.append(canvas, grid, scan);
    document.body.prepend(layers);
  }

  // Boot overlay — only outside iframes (parent owns its own boot)
  const cfg = (window.LC_CONFIG || {});
  const pageTitle = cfg.title || 'LUMENCORE';
  let boot = null;
  if (!IN_IFRAME) {
    boot = document.createElement('div');
    boot.id = 'lc-boot';
    boot.innerHTML = `
      <div class="ring"></div>
      <div class="lc-boot-title">${pageTitle.toUpperCase()}</div>
      <div class="lc-boot-lines" id="lc-boot-lines"></div>`;
    document.body.appendChild(boot);

    const lines = cfg.bootLines || [
      '> initializing webgl harmonic field …',
      '> mounting evidence chain (sha-256) …',
      '> loading frozen benchmark …',
      '> handshake: meta-router · stacker · blender …',
      '> calibration · anomaly · regime channels online',
      '> entering command fabric',
    ];
    const host = document.getElementById('lc-boot-lines');
    lines.forEach((l, i) => {
      const d = document.createElement('div');
      d.textContent = l;
      d.style.animationDelay = (i * 0.16) + 's';
      host.appendChild(d);
    });
    setTimeout(() => boot.classList.add('done'),
      Math.max(1400, 250 + lines.length * 200));
  }

  // 2. Top bar — skipped inside iframes (parent cockpit owns the chrome)
  if (!IN_IFRAME && !document.getElementById('lc-topbar')) {
    const stage = document.querySelector('.lc-stage') ||
      (() => {
        const s = document.createElement('div'); s.className = 'lc-stage';
        // Move all body children into stage (except our injected layers/boot)
        const skip = new Set([canvas, grid, scan, boot]);
        Array.from(document.body.children).forEach(c => {
          if (!skip.has(c) && c !== s) s.appendChild(c);
        });
        document.body.appendChild(s);
        return s;
      })();

    const navItems = cfg.nav || [
      ['/mission_control.html', 'Mission'],
      ['/grants.html', 'Grants'],
      ['/forecast.html', 'Forecast'],
      ['/anomalies.html', 'Anomalies'],
      ['/explain.html', 'Explain'],
      ['/lab.html', 'Lab'],
    ];
    const herePath = location.pathname.replace(/\\/g, '/');
    const hereFile = herePath.split('/').pop() || '';
    const navHtml = navItems.map(([h, l]) => {
      const href = normalizeDashboardHref(h);
      const targetFile = String(h || '').split('/').pop() || '';
      const isActive = targetFile ? hereFile === targetFile : false;
      return `<a href="${href}" class="${isActive ? 'active' : ''}">${l}</a>`;
    }).join('');

    const bar = document.createElement('div');
    bar.id = 'lc-topbar';
    bar.className = 'lc-topbar';
    bar.innerHTML = `
      <div class="lc-brand">
        <div class="lc-logo"></div>
        <div>
          <h1>${cfg.title || 'LUMENCORE'}</h1>
          <div class="lc-sub">${cfg.subtitle || 'Mission Control · v3'}</div>
        </div>
      </div>
      <nav class="lc-nav">${navHtml}</nav>
      <div class="lc-clock">
        <div><span class="lc-label">UTC</span><span class="lc-val" id="lc-clock-utc">—</span></div>
        <div><span class="lc-live">LIVE</span></div>
      </div>`;
    stage.prepend(bar);
  }

  // Live UTC clock
  function tick() {
    const e = document.getElementById('lc-clock-utc');
    if (e) e.textContent = new Date().toISOString().slice(11, 19);
  }
  setInterval(tick, 1000); tick();

  // 3. WebGL field — load Three.js once
  function startWebGL() {
    const THREE = window.THREE;
    if (!THREE || !canvas) return;
    const pointer = { x: 0, y: 0 };
    if (!PERF.reducedMotion) {
      const onPointerMove = (ev) => {
        const w = Math.max(1, window.innerWidth);
        const h = Math.max(1, window.innerHeight);
        pointer.x = (ev.clientX / w) * 2 - 1;
        pointer.y = (ev.clientY / h) * 2 - 1;
      };
      window.addEventListener('pointermove', onPointerMove, { passive: true });
    }

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, PERF.maxPixelRatio));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x04060f, 0.04);
    const camera = new THREE.PerspectiveCamera(60,
      window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 0, 18);

    const N = PERF.webglParticles;
    const positions = new Float32Array(N * 3);
    const colors = new Float32Array(N * 3);
    const speeds = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      positions[i*3]   = (Math.random() - 0.5) * 80;
      positions[i*3+1] = (Math.random() - 0.5) * 50;
      positions[i*3+2] = (Math.random() - 0.5) * 80;
      const t = Math.random();
      colors[i*3]   = 0.13 + t * 0.5;
      colors[i*3+1] = 0.83 - t * 0.5;
      colors[i*3+2] = 0.94;
      speeds[i] = (0.005 + Math.random() * 0.02) * PERF.motionScale;
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const points = new THREE.Points(geom, new THREE.PointsMaterial({
      size: 0.08, vertexColors: true, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, sizeAttenuation: true,
    }));
    scene.add(points);

    const ringGeom = new THREE.TorusGeometry(7, 0.04, 24, PERF.ringSegments);
    const r1 = new THREE.Mesh(ringGeom, new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0.45,
      blending: THREE.AdditiveBlending }));
    const r2 = new THREE.Mesh(ringGeom, new THREE.MeshBasicMaterial({
      color: 0xa855f7, transparent: true, opacity: 0.35,
      blending: THREE.AdditiveBlending }));
    r2.rotation.x = Math.PI / 3; r2.scale.setScalar(0.7);
    const r3 = new THREE.Mesh(ringGeom, new THREE.MeshBasicMaterial({
      color: 0x34d399, transparent: true, opacity: 0.3,
      blending: THREE.AdditiveBlending }));
    r3.rotation.y = Math.PI / 4; r3.scale.setScalar(1.4);
    scene.add(r1, r2, r3);

    const clock = new THREE.Clock();
    let frame = 0;
    function loop() {
      requestAnimationFrame(loop);
      frame += 1;
      if (PERF.frameStride > 1 && (frame % PERF.frameStride) !== 0) return;

      const t = clock.getElapsedTime() * PERF.motionScale;
      const pos = points.geometry.attributes.position.array;
      for (let i = 0; i < N; i++) {
        pos[i*3+2] += speeds[i];
        if (pos[i*3+2] > 30) pos[i*3+2] = -30;
      }
      points.geometry.attributes.position.needsUpdate = true;
      points.rotation.y = t * 0.02;
      r1.rotation.x = t * 0.18;  r1.rotation.y = t * 0.10;
      r2.rotation.x = -t * 0.15 + Math.PI / 3; r2.rotation.z = t * 0.12;
      r3.rotation.y = t * 0.08 + Math.PI / 4;  r3.rotation.z = -t * 0.06;
      if (PERF.ringPulse) {
        r1.material.opacity = 0.33 + Math.sin(t * 0.9) * 0.12;
        r2.material.opacity = 0.26 + Math.cos(t * 0.7) * 0.10;
        r3.material.opacity = 0.24 + Math.sin(t * 0.5 + 0.7) * 0.08;
      } else {
        r1.material.opacity = 0.28;
        r2.material.opacity = 0.24;
        r3.material.opacity = 0.2;
      }
      const pointerX = PERF.reducedMotion ? 0 : pointer.x * PERF.pointerScale;
      const pointerY = PERF.reducedMotion ? 0 : pointer.y * PERF.pointerScale;
      camera.position.x = Math.sin(t * 0.1) * 0.6 + pointerX * 0.7;
      camera.position.y = Math.cos(t * 0.08) * 0.4 - pointerY * 0.45;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    }
    loop();

    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  let fallbackRunning = false;
  function startCanvasFallback() {
    if (!canvas || fallbackRunning) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    fallbackRunning = true;

    const pointer = { x: 0, y: 0 };
    if (!PERF.reducedMotion) {
      const onPointerMove = (ev) => {
        const w = Math.max(1, window.innerWidth);
        const h = Math.max(1, window.innerHeight);
        pointer.x = (ev.clientX / w) * 2 - 1;
        pointer.y = (ev.clientY / h) * 2 - 1;
      };
      window.addEventListener('pointermove', onPointerMove, { passive: true });
    }

    const particles = Array.from({ length: PERF.fallbackParticles }, () => ({
      x: Math.random(),
      y: Math.random(),
      z: Math.random(),
      vx: (Math.random() - 0.5) * 0.00035 * PERF.motionScale,
      vy: (Math.random() - 0.5) * 0.00035 * PERF.motionScale,
      r: 0.4 + Math.random() * 2.1,
      hue: 170 + Math.random() * 120,
      alpha: 0.12 + Math.random() * 0.35,
    }));

    const resize = () => {
      const w = Math.max(1, window.innerWidth);
      const h = Math.max(1, window.innerHeight);
      canvas.width = Math.floor(w * Math.min(window.devicePixelRatio || 1, 2));
      canvas.height = Math.floor(h * Math.min(window.devicePixelRatio || 1, 2));
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(canvas.width / w, canvas.height / h);
    };
    resize();
    window.addEventListener('resize', resize);

    let t0 = performance.now();
    let frame = 0;
    const render = (now) => {
      requestAnimationFrame(render);
      frame += 1;

      const dtRaw = Math.min(48, now - t0);
      t0 = now;
      if (PERF.frameStride > 1 && (frame % PERF.frameStride) !== 0) return;

      const dt = dtRaw * PERF.motionScale;
      const w = Math.max(1, window.innerWidth);
      const h = Math.max(1, window.innerHeight);

      ctx.clearRect(0, 0, w, h);
      const pointerX = PERF.reducedMotion ? 0 : pointer.x;
      const pointerY = PERF.reducedMotion ? 0 : pointer.y;
      const glowX = w * (0.5 + pointerX * 0.08);
      const glowY = h * (0.45 - pointerY * 0.08);
      const grad = ctx.createRadialGradient(glowX, glowY, 0, glowX, glowY, Math.max(w, h) * 0.66);
      grad.addColorStop(0, 'rgba(34,211,238,0.10)');
      grad.addColorStop(0.5, 'rgba(168,85,247,0.08)');
      grad.addColorStop(1, 'rgba(4,6,15,0.0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      for (const p of particles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.x < -0.05) p.x = 1.05;
        if (p.x > 1.05) p.x = -0.05;
        if (p.y < -0.05) p.y = 1.05;
        if (p.y > 1.05) p.y = -0.05;

        const px = p.x * w + pointerX * PERF.pointerScale * (8 + p.z * 24);
        const py = p.y * h - pointerY * PERF.pointerScale * (8 + p.z * 24);
        const radius = p.r * (0.65 + p.z * 0.9);
        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${Math.round(p.hue)}, 92%, 68%, ${p.alpha})`;
        ctx.fill();
      }
    };
    requestAnimationFrame(render);
  }

  function loadThreeWithFallback(urls) {
    const queue = Array.from(new Set(urls.filter(Boolean)));
    const tryNext = () => {
      if (!queue.length) {
        console.warn('three.js failed to load from all sources; chrome will run without webgl field');
        startCanvasFallback();
        return;
      }
      const src = queue.shift();
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = () => {
        if (window.THREE) startWebGL();
        else tryNext();
      };
      s.onerror = tryNext;
      document.head.appendChild(s);
    };
    tryNext();
  }

  if (window.THREE) {
    if (!IN_IFRAME) startWebGL();
  } else if (!IN_IFRAME) {
    if (!IS_FILE_PROTOCOL) {
      loadThreeWithFallback([
        './assets/vendor/three.min.js',
        '/assets/vendor/three.min.js',
        'https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.min.js',
        'https://unpkg.com/three@0.162.0/build/three.min.js',
      ]);
    } else {
      startCanvasFallback();
    }
  }

  // 4. WebSocket bridge: surface grants events as a toast (Mission Control feel)
  try {
    const wsUrl = resolveWsUrl('/ws/live');
    if (wsUrl) {
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        try {
          const m = JSON.parse(e.data);
          if (m.type && m.type.startsWith('grants_')) lcToast(m);
        } catch {}
      };
    }
  } catch {}

  function lcToast(m) {
    let host = document.getElementById('lc-toasts');
    if (!host) {
      host = document.createElement('div');
      host.id = 'lc-toasts';
      host.style.cssText = `position:fixed; right:24px; bottom:24px; z-index:500;
                            display:flex; flex-direction:column; gap:8px;`;
      document.body.appendChild(host);
    }
    const t = document.createElement('div');
    const isApprove = m.type === 'grants_approved';
    t.style.cssText = `
      padding: 12px 16px; border-radius: 8px;
      background: rgba(15,23,50,0.85); backdrop-filter: blur(14px);
      border: 1px solid ${isApprove ? 'var(--neon-c)' : 'var(--neon-g)'};
      box-shadow: 0 0 20px ${isApprove ? 'rgba(34,211,238,0.4)' : 'rgba(52,211,153,0.4)'};
      color: var(--ink); font-family: 'JetBrains Mono', monospace; font-size: 12px;
      min-width: 280px; animation: lc-toast-in 0.3s;
      transform-origin: right;`;
    t.innerHTML = `
      <div style="font-family:'Orbitron',sans-serif; font-size:10px; letter-spacing:2px;
                  color: ${isApprove ? 'var(--neon-c)' : 'var(--neon-g)'}; margin-bottom: 4px">
        ${m.type.replace('grants_', 'GRANT ').toUpperCase()}
      </div>
      <div><b>${m.grant_id || ''}</b></div>
      ${m.queue_summary ? `<div style="color:var(--ink-dim); margin-top:4px; font-size:11px">
        ${m.queue_summary.n_draft || 0} draft · ${m.queue_summary.n_approved || 0} approved · ${m.queue_summary.n_submitted || 0} submitted
      </div>` : ''}`;
    host.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; t.style.transition = 'all 0.4s'; }, 5000);
    setTimeout(() => t.remove(), 5500);
  }

  // 5. Helpers exposed for pages
  window.LC = {
    api: async (path, opts = {}) => {
      const pathStr = normalizeLegacyPath(path);
      const directHttp = /^https?:\/\//i.test(pathStr);
      const candidates = [];

      if (directHttp) {
        candidates.push(pathStr);
      } else {
        if (USER_API_BASE && pathStr.startsWith('/')) {
          candidates.push(USER_API_BASE + pathStr);
        }
        if (IS_FILE_PROTOCOL && !USER_API_BASE && pathStr.startsWith('/api/')) {
          candidates.push('http://127.0.0.1:8787' + pathStr);
          candidates.push('http://127.0.0.1:8000' + pathStr);
        } else {
          candidates.push(pathStr);
        }
      }

      let lastErr = null;
      for (const url of uniq(candidates)) {
        try {
          const r = await fetch(url, opts);
          if (!r.ok) {
            lastErr = new Error(`${r.status} ${await r.text()}`);
            continue;
          }
          const ct = r.headers.get('content-type') || '';
          return ct.includes('json') ? r.json() : r.text();
        } catch (e) {
          lastErr = e;
        }
      }

      throw lastErr || new Error('request failed');
    },
    href: normalizeDashboardHref,
    toast: lcToast,
    performance: {
      tier: PERF.tier,
      saveData: PERF.saveData,
      reducedMotion: PERF.reducedMotion,
      frameStride: PERF.frameStride,
    },
    fmt: {
      num: (n, d = 0) => (n === null || n === undefined || isNaN(n)) ? '—'
        : Number(n).toLocaleString(undefined, { maximumFractionDigits: d }),
      pct: (n, d = 1) => (n === null || n === undefined || isNaN(n)) ? '—'
        : (n * 100).toFixed(d) + '%',
      usd: (n) => '$' + Number(n || 0).toLocaleString(),
    },
  };

  // CSS keyframe for toast
  const kf = document.createElement('style');
  kf.textContent = '@keyframes lc-toast-in { from { transform: translateX(40px); opacity: 0 } to { transform: translateX(0); opacity: 1 } }';
  document.head.appendChild(kf);
})();
