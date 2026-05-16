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

  function normalizeDashboardHref(href) {
    if (!href) return href;
    if (/^(https?:|mailto:|#|javascript:)/i.test(href)) return href;
    if (IS_FILE_PROTOCOL && href.startsWith('/')) return '.' + href;
    return href;
  }

  function uniq(values) {
    return Array.from(new Set(values.filter(Boolean)));
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
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x04060f, 0.04);
    const camera = new THREE.PerspectiveCamera(60,
      window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 0, 18);

    const N = 900;
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
      speeds[i] = 0.005 + Math.random() * 0.02;
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const points = new THREE.Points(geom, new THREE.PointsMaterial({
      size: 0.08, vertexColors: true, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, sizeAttenuation: true,
    }));
    scene.add(points);

    const ringGeom = new THREE.TorusGeometry(7, 0.04, 32, 256);
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
    function loop() {
      const t = clock.getElapsedTime();
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
      camera.position.x = Math.sin(t * 0.1) * 0.6;
      camera.position.y = Math.cos(t * 0.08) * 0.4;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    }
    loop();

    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  function loadThreeWithFallback(urls) {
    const queue = Array.from(new Set(urls.filter(Boolean)));
    const tryNext = () => {
      if (!queue.length) {
        console.warn('three.js failed to load from all sources; chrome will run without webgl field');
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
  } else if (!IN_IFRAME && !IS_FILE_PROTOCOL) {
    loadThreeWithFallback([
      './assets/vendor/three.min.js',
      '/assets/vendor/three.min.js',
      'https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.min.js',
      'https://unpkg.com/three@0.162.0/build/three.min.js',
    ]);
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
      const pathStr = String(path || '');
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
