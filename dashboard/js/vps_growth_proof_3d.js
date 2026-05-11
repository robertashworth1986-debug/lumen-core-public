import * as THREE from "three";
import { gsap } from "gsap";
import {
  BrightnessContrastEffect,
  BloomEffect,
  ChromaticAberrationEffect,
  DepthOfFieldEffect,
  EffectComposer,
  EffectPass,
  HueSaturationEffect,
  NoiseEffect,
  RenderPass,
  ScanlineEffect,
  VignetteEffect,
  BlendFunction,
} from "postprocessing";

const SOURCES = [
  "./data/vps_growth_proof.json",
  "../out/execution/vps_growth_proof.json",
  "/out/execution/vps_growth_proof.json",
  "./vps_growth_proof.json",
];

const canvas = document.getElementById("proofCanvas");
const statusPill = document.getElementById("statusPill");
const refreshBtn = document.getElementById("refreshBtn");
const cinematicBtn = document.getElementById("cinematicBtn");
const directorBtn = document.getElementById("directorBtn");
const rendererModeNode = document.getElementById("rendererMode");
const directorStateNode = document.getElementById("directorState");
const fpsNode = document.getElementById("fpsValue");
const frameBudgetNode = document.getElementById("frameBudget");

const quality = {
  ultra: true,
  auto: true,
  fps: 60,
  frameSamples: [],
  lastAutoAdjustAt: 0,
  lastHudSampleAt: 0,
  lockUntil: 0,
};

const director = {
  auto: true,
  shotIndex: 0,
  shotTime: 0,
};

const shotDeck = [
  { x: -2.8, y: 3.2, z: 12.6, lookY: -0.4, duration: 7.2 },
  { x: 2.9, y: 4.1, z: 13.8, lookY: 0.0, duration: 8.6 },
  { x: 0.1, y: 6.0, z: 15.5, lookY: 0.3, duration: 7.8 },
  { x: -0.2, y: 2.9, z: 11.2, lookY: -0.8, duration: 6.5 },
];

const pulse = { energy: 0 };

function targetPixelRatio() {
  const device = window.devicePixelRatio || 1;
  const isMobile = window.innerWidth < 900;
  const cap = quality.ultra ? (isMobile ? 1.75 : 2.35) : (isMobile ? 1.2 : 1.5);
  return Math.min(device, cap);
}

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(targetPixelRatio());
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.physicallyCorrectLights = true;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x040812);
scene.fog = new THREE.FogExp2(0x040812, 0.085);

const camera = new THREE.PerspectiveCamera(52, window.innerWidth / window.innerHeight, 0.1, 180);
camera.position.set(0, 3.6, 14);

const ambient = new THREE.AmbientLight(0x4ad9ff, 0.24);
const key = new THREE.PointLight(0x63f0ff, 28, 65, 2);
key.position.set(5.5, 6, 8);
const rim = new THREE.PointLight(0xffcf88, 20, 80, 2);
rim.position.set(-7.5, -2.2, -8);
const hemi = new THREE.HemisphereLight(0x86eeff, 0x061120, 0.32);
const follow = new THREE.SpotLight(0xc8f7ff, 32, 90, Math.PI / 6, 0.45, 1.25);
follow.position.set(0, 12, 8);
follow.castShadow = true;
follow.shadow.mapSize.set(1024, 1024);
follow.shadow.bias = -0.00015;
scene.add(ambient, key, rim, hemi, follow, follow.target);

const droneGroup = new THREE.Group();
const drones = [];
for (let i = 0; i < 4; i += 1) {
  const color = i % 2 ? 0xffd49b : 0x89e8ff;
  const drone = new THREE.Mesh(
    new THREE.SphereGeometry(0.14, 20, 20),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.88,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  const glow = new THREE.PointLight(color, 7.5, 9, 2);
  drone.add(glow);
  droneGroup.add(drone);
  drones.push({
    mesh: drone,
    radius: 3.8 + i * 1.15,
    speed: 0.24 + i * 0.07,
    phase: i * 1.4,
    y: -0.6 + (i % 3) * 0.95,
  });
}
scene.add(droneGroup);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(12, 96),
  new THREE.MeshPhysicalMaterial({
    color: 0x0a1f36,
    transparent: true,
    opacity: 0.38,
    roughness: 0.42,
    metalness: 0.2,
    clearcoat: 0.8,
    clearcoatRoughness: 0.35,
  })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -2.8;
floor.receiveShadow = true;
scene.add(floor);

const platform = new THREE.Mesh(
  new THREE.CylinderGeometry(6.2, 6.4, 0.32, 96),
  new THREE.MeshPhysicalMaterial({
    color: 0x0f2a45,
    emissive: 0x0f2a45,
    emissiveIntensity: 0.2,
    roughness: 0.32,
    metalness: 0.56,
    transparent: true,
    opacity: 0.78,
  })
);
platform.position.y = -2.96;
platform.castShadow = true;
platform.receiveShadow = true;
scene.add(platform);

const stageWire = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.CylinderGeometry(6.22, 6.42, 0.32, 64)),
  new THREE.LineBasicMaterial({ color: 0x78e8ff, transparent: true, opacity: 0.42 })
);
stageWire.position.y = -2.96;
scene.add(stageWire);

const bladeGroup = new THREE.Group();
for (let i = 0; i < 24; i += 1) {
  const blade = new THREE.Mesh(
    new THREE.PlaneGeometry(0.08, 3.6),
    new THREE.MeshBasicMaterial({
      color: i % 2 ? 0x7be8ff : 0xffd08d,
      transparent: true,
      opacity: 0.09,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  const angle = (i / 24) * Math.PI * 2;
  const radius = 7.4 + (i % 4) * 0.2;
  blade.position.set(Math.cos(angle) * radius, -1.0, Math.sin(angle) * radius);
  blade.lookAt(0, -1.0, 0);
  bladeGroup.add(blade);
}
scene.add(bladeGroup);

const metricGroup = new THREE.Group();
scene.add(metricGroup);

const barSpecs = [
  { name: "proof", color: 0x74ecff, x: -4.2 },
  { name: "txids", color: 0x8cffca, x: -2.1 },
  { name: "submits", color: 0xffd68e, x: 0.0 },
  { name: "winrate", color: 0x9bb4ff, x: 2.1 },
  { name: "freshness", color: 0xff917b, x: 4.2 },
];

const bars = {};
barSpecs.forEach((spec) => {
  const geom = new THREE.CylinderGeometry(0.42, 0.52, 1, 20, 1, false);
  const mat = new THREE.MeshPhysicalMaterial({
    color: spec.color,
    emissive: spec.color,
    emissiveIntensity: 0.2,
    roughness: 0.25,
    metalness: 0.16,
    transmission: 0.25,
    transparent: true,
    opacity: 0.85,
  });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(spec.x, -2.3, 0);
  mesh.castShadow = true;

  const pedestal = new THREE.Mesh(
    new THREE.CylinderGeometry(0.56, 0.62, 0.22, 24),
    new THREE.MeshPhysicalMaterial({
      color: 0x1b314f,
      roughness: 0.34,
      metalness: 0.62,
      emissive: 0x102236,
      emissiveIntensity: 0.2,
      transparent: true,
      opacity: 0.92,
    })
  );
  pedestal.position.set(spec.x, -2.95, 0);
  pedestal.receiveShadow = true;

  const crown = new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 20, 20),
    new THREE.MeshBasicMaterial({
      color: spec.color,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  crown.position.set(spec.x, -1.82, 0);

  const halo = new THREE.Mesh(
    new THREE.TorusGeometry(0.62, 0.03, 12, 64),
    new THREE.MeshBasicMaterial({
      color: spec.color,
      transparent: true,
      opacity: 0.28,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  halo.rotation.x = Math.PI / 2;
  halo.position.set(spec.x, -2.78, 0);

  metricGroup.add(mesh, pedestal, halo, crown);
  bars[spec.name] = { mesh, pedestal, halo, crown, targetHeight: 1.0 };
});

const rings = new THREE.Group();
for (let i = 0; i < 4; i += 1) {
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(5 + i * 0.68, 0.02, 10, 160),
    new THREE.MeshBasicMaterial({
      color: i % 2 === 0 ? 0x79edff : 0xffc56f,
      transparent: true,
      opacity: 0.17 - i * 0.02,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  ring.rotation.x = Math.PI / 2;
  ring.position.y = -2.75;
  rings.add(ring);
}
scene.add(rings);

const orbitalGroup = new THREE.Group();
const orbitals = [];
for (let i = 0; i < 3; i += 1) {
  const orbital = new THREE.Mesh(
    new THREE.TorusGeometry(3.8 + i * 1.25, 0.015 + i * 0.006, 8, 200),
    new THREE.MeshBasicMaterial({
      color: i === 1 ? 0xffcb86 : 0x7be8ff,
      transparent: true,
      opacity: 0.2 - i * 0.04,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  orbital.rotation.x = Math.PI / 2 + i * 0.22;
  orbital.rotation.y = i * 0.35;
  orbital.position.y = -1.6 + i * 0.34;
  orbitalGroup.add(orbital);
  orbitals.push(orbital);
}
scene.add(orbitalGroup);

const nebulaCore = new THREE.Mesh(
  new THREE.SphereGeometry(19, 40, 40),
  new THREE.MeshBasicMaterial({
    color: 0x2a5e9f,
    transparent: true,
    opacity: 0.08,
    side: THREE.BackSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })
);
const nebulaOuter = new THREE.Mesh(
  new THREE.SphereGeometry(28, 36, 36),
  new THREE.MeshBasicMaterial({
    color: 0x1b365f,
    transparent: true,
    opacity: 0.06,
    side: THREE.BackSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })
);
scene.add(nebulaCore, nebulaOuter);

const pointCount = 5200;
const ptsGeo = new THREE.BufferGeometry();
const ptsPos = new Float32Array(pointCount * 3);
for (let i = 0; i < pointCount; i += 1) {
  const span = 60;
  ptsPos[i * 3] = (Math.random() - 0.5) * span;
  ptsPos[i * 3 + 1] = (Math.random() - 0.5) * span;
  ptsPos[i * 3 + 2] = (Math.random() - 0.5) * span;
}
ptsGeo.setAttribute("position", new THREE.BufferAttribute(ptsPos, 3));
const pts = new THREE.Points(
  ptsGeo,
  new THREE.PointsMaterial({
    color: 0x89dcff,
    transparent: true,
    opacity: 0.42,
    size: 0.06,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
);
scene.add(pts);

const dustCount = 1800;
const dustGeo = new THREE.BufferGeometry();
const dustPos = new Float32Array(dustCount * 3);
for (let i = 0; i < dustCount; i += 1) {
  const radius = 8 + Math.random() * 18;
  const theta = Math.random() * Math.PI * 2;
  const phi = Math.acos(2 * Math.random() - 1);
  dustPos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
  dustPos[i * 3 + 1] = radius * Math.cos(phi);
  dustPos[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
}
dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
const dust = new THREE.Points(
  dustGeo,
  new THREE.PointsMaterial({
    color: 0xffd9a6,
    transparent: true,
    opacity: 0.22,
    size: 0.09,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
);
scene.add(dust);

const composer = new EffectComposer(renderer, { multisampling: 0 });
composer.addPass(new RenderPass(scene, camera));

const bloom = new BloomEffect({
  intensity: 1.15,
  luminanceThreshold: 0.14,
  luminanceSmoothing: 0.24,
  mipmapBlur: true,
  radius: 0.72,
});
const dof = new DepthOfFieldEffect(camera, {
  focusDistance: 0.015,
  focalLength: 0.03,
  bokehScale: 1.9,
  height: 720,
});
dof.blendMode.opacity.value = 0.72;
const chroma = new ChromaticAberrationEffect({
  offset: new THREE.Vector2(0.00065, 0.00065),
  radialModulation: true,
  modulationOffset: 0.16,
});
const grade = new HueSaturationEffect({ hue: 0, saturation: 0.08 });
const contrast = new BrightnessContrastEffect({ brightness: 0.02, contrast: 0.13 });
const scanline = new ScanlineEffect({ density: 1.1 });
scanline.blendMode.opacity.value = 0.1;
const noise = new NoiseEffect({ blendFunction: BlendFunction.SOFT_LIGHT, premultiply: true });
const vignette = new VignetteEffect({ eskil: false, offset: 0.19, darkness: 0.63 });
composer.addPass(new EffectPass(camera, bloom, dof, chroma, grade, contrast, scanline, noise, vignette));

function syncControlLabels() {
  if (cinematicBtn) cinematicBtn.textContent = quality.ultra ? "Ultra FX: ON" : "Ultra FX: BALANCED";
  if (directorBtn) directorBtn.textContent = `Director Cam: ${director.auto ? "AUTO" : "MANUAL"}`;
  if (rendererModeNode) {
    if (quality.auto) {
      rendererModeNode.textContent = quality.ultra ? "AUTO ULTRA" : "AUTO BALANCED";
    } else {
      rendererModeNode.textContent = quality.ultra ? "ULTRA" : "BALANCED";
    }
  }
  if (directorStateNode) directorStateNode.textContent = director.auto ? "AUTO" : "MANUAL";
}

function applyQualityProfile() {
  renderer.setPixelRatio(targetPixelRatio());

  if (quality.ultra) {
    bloom.intensity = 1.15;
    bloom.radius = 0.72;
    dof.blendMode.opacity.value = 0.72;
    scanline.blendMode.opacity.value = 0.095;
    scanline.scrollSpeed = 0.045;
    noise.blendMode.opacity.value = 0.34;
    vignette.darkness = 0.63;
    renderer.toneMappingExposure = 1.12;
  } else {
    bloom.intensity = 0.85;
    bloom.radius = 0.58;
    dof.blendMode.opacity.value = 0.42;
    scanline.blendMode.opacity.value = 0.045;
    scanline.scrollSpeed = 0.025;
    noise.blendMode.opacity.value = 0.22;
    vignette.darkness = 0.52;
    renderer.toneMappingExposure = 1.02;
  }

  syncControlLabels();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
}

function setUltraMode(enabled, source = "manual") {
  quality.ultra = enabled;
  applyQualityProfile();
}

function setDirectorMode(enabled) {
  director.auto = enabled;
  syncControlLabels();
}

applyQualityProfile();
updateFrameTelemetry(60);

const pointer = new THREE.Vector2();
const pointerTarget = new THREE.Vector2();
window.addEventListener("pointermove", (event) => {
  pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
  pointer.y = -((event.clientY / window.innerHeight) * 2 - 1);
});

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  applyQualityProfile();
});

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function setStatus(text, tone = "idle") {
  if (!statusPill) return;
  statusPill.textContent = text;

  const palette = {
    idle: "linear-gradient(125deg, rgba(129, 246, 200, 0.16), rgba(123, 235, 255, 0.14))",
    sync: "linear-gradient(125deg, rgba(255, 215, 150, 0.2), rgba(123, 235, 255, 0.12))",
    live: "linear-gradient(125deg, rgba(129, 246, 200, 0.2), rgba(123, 235, 255, 0.16))",
    warn: "linear-gradient(125deg, rgba(255, 151, 127, 0.22), rgba(255, 215, 150, 0.16))",
    off: "linear-gradient(125deg, rgba(255, 151, 127, 0.22), rgba(140, 169, 255, 0.12))",
  };

  statusPill.style.background = palette[tone] || palette.idle;
}

function updateFrameTelemetry(fps) {
  const boundedFps = Math.max(1, Math.min(240, fps));
  quality.fps = boundedFps;
  if (fpsNode) fpsNode.textContent = `${boundedFps.toFixed(1)} FPS`;
  if (frameBudgetNode) frameBudgetNode.textContent = `${(1000 / boundedFps).toFixed(1)}ms`;
}

function maybeAutoAdjustQuality(nowSeconds) {
  if (!quality.auto) return;
  if (nowSeconds < quality.lockUntil) return;
  if (nowSeconds - quality.lastAutoAdjustAt < 3.2) return;

  if (quality.fps < 44 && quality.ultra) {
    setUltraMode(false, "auto");
    setStatus("Auto Balance", "warn");
  } else if (quality.fps > 57 && !quality.ultra) {
    setUltraMode(true, "auto");
    setStatus("Ultra Restored", "live");
  }

  quality.lastAutoAdjustAt = nowSeconds;
}

function triggerDataPulse(intensity = 1) {
  const target = Math.max(0.2, Math.min(1.8, intensity));
  gsap.to(pulse, { energy: target, duration: 0.18, ease: "power2.out", overwrite: true });
  gsap.to(pulse, { energy: 0, duration: 1.45, delay: 0.14, ease: "expo.out", overwrite: true });
  gsap.fromTo(
    rings.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.08, y: 1.08, z: 1.08, duration: 0.3, yoyo: true, repeat: 1, ease: "power2.out" }
  );
}

function fmtNumber(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return n.toFixed(digits);
}

function fmtUsd(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

async function fetchFirst(urls) {
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) continue;
      return await response.json();
    } catch {
      // try next source
    }
  }
  return null;
}

function setBarHeight(name, normalized) {
  const item = bars[name];
  if (!item) return;
  const clamped = Math.max(0.05, Math.min(1.0, normalized));
  item.targetHeight = 0.8 + clamped * 5.5;
}

function renderTxids(rows) {
  const host = document.getElementById("txidList");
  if (!host) return;
  if (!rows || !rows.length) {
    host.innerHTML = "<li class='empty'>No TXIDs found in current evidence window.</li>";
    return;
  }
  host.innerHTML = rows
    .slice(0, 10)
    .map((tx) => `<li><span class='mono'>${tx}</span></li>`)
    .join("");
}

function renderScenarios(payload) {
  const host = document.getElementById("projectionRows");
  if (!host) return;
  const scenarios = payload?.compounding_projection?.scenarios || {};
  const order = ["conservative", "base", "aggressive"];
  const lines = [];

  order.forEach((name) => {
    const row = scenarios[name];
    if (!row) return;
    lines.push(
      `<li>
        <div class='name'>${name.toUpperCase()}</div>
        <div class='mono'>Daily ${fmtNumber(row.daily_rate_pct, 3)}%</div>
        <div class='mono'>30d ${fmtUsd(row.equity_30d_usd)}</div>
        <div class='mono'>90d ${fmtUsd(row.equity_90d_usd)}</div>
      </li>`
    );
  });

  host.innerHTML = lines.length ? lines.join("") : "<li class='empty'>Projection unavailable.</li>";
}

async function refresh() {
  setStatus("Syncing", "sync");
  const payload = await fetchFirst(SOURCES);
  if (!payload) {
    setStatus("Offline", "off");
    return;
  }

  const score = payload.integrity_score || {};
  const ev = payload.kraken_execution_evidence || {};
  const recon = payload.kraken_fill_reconciliation || {};
  const perf = payload.live_trade_performance || {};
  const cap = payload.capital_state || {};
  const hb = payload.runtime_heartbeat || {};

  const proofScore = Number(score.score_0_100 || 0);
  const txidCount = Number(ev.txid_count || 0);
  const submit7d = Number(ev.recent_7d_live_submit || 0);
  const closedCount = Number(recon.closed_count || 0);
  const queriedCount = Number(recon.txids_queried || 0);
  const fillSync = Number(recon.fill_sync_pct || 0);
  const reconEnabled = !!recon.query_enabled;
  const winRate = Number(perf.win_rate_pct || 0);
  const heartbeatFresh = hb.fresh ? 100 : 8;
  const reconErrors = Array.isArray(recon.query_errors) ? recon.query_errors : [];

  setBarHeight("proof", proofScore / 100);
  setBarHeight("txids", Math.min(1, txidCount / 20));
  setBarHeight("submits", Math.min(1, submit7d / 20));
  setBarHeight("winrate", Math.min(1, winRate / 100));
  setBarHeight("freshness", heartbeatFresh / 100);

  setText("proofScore", fmtNumber(proofScore, 2));
  setText("txidCount", String(txidCount));
  setText("closedCount", reconEnabled ? `${closedCount}/${queriedCount}` : "DISABLED");
  setText("submit7d", String(submit7d));
  setText("fillSync", reconEnabled ? `${fmtNumber(fillSync, 1)}%` : "DISABLED");
  setText("winRate", `${fmtNumber(winRate, 2)}%`);
  setText("realizedNet", fmtUsd(perf.realized_net_usd));
  setText("portfolioEst", fmtUsd(cap.portfolio_est_total_usd));
  setText("drawdown", `${fmtNumber(perf.max_drawdown_pct, 2)}%`);
  setText("heartbeat", hb.fresh ? "FRESH" : `STALE (${fmtNumber(hb.age_minutes, 1)}m)`);
  setText("generatedAt", payload.generated_utc || "--");
  setText("reconSource", reconEnabled ? String(recon.query_source || "enabled") : "disabled");
  setText("reconErrors", reconErrors.length ? reconErrors.slice(0, 2).join(" | ") : (reconEnabled ? "none" : "n/a"));
  setText("guardrail", payload.guardrail || "Evidence telemetry only.");

  renderTxids(ev.txids || []);
  renderScenarios(payload);

  const scoreBlend = Math.max(0, Math.min(1, proofScore / 100));
  key.color.setHSL(0.53 + scoreBlend * 0.03, 0.9, 0.58);
  rim.color.setHSL(0.08 + (1 - scoreBlend) * 0.03, 0.88, 0.56);
  grade.saturation = 0.05 + scoreBlend * 0.1;
  contrast.contrast = 0.08 + scoreBlend * 0.14;
  triggerDataPulse(0.52 + scoreBlend * 1.05);

  const isWarn = !hb.fresh || (reconEnabled && fillSync < 80);
  setStatus("Live", isWarn ? "warn" : "live");
}

refreshBtn?.addEventListener("click", () => {
  void refresh();
});

cinematicBtn?.addEventListener("click", () => {
  quality.lockUntil = elapsed + 20;
  setUltraMode(!quality.ultra, "manual");
  setStatus(quality.ultra ? "Ultra Locked" : "Balanced Locked", "sync");
});

directorBtn?.addEventListener("click", () => {
  setDirectorMode(!director.auto);
  setStatus(director.auto ? "Director Auto" : "Director Manual", "sync");
});

window.addEventListener("keydown", (event) => {
  const keyName = event.key.toLowerCase();
  if (keyName === "f") {
    quality.lockUntil = elapsed + 20;
    setUltraMode(!quality.ultra, "manual");
    setStatus(quality.ultra ? "Ultra Locked" : "Balanced Locked", "sync");
  } else if (keyName === "d") {
    setDirectorMode(!director.auto);
    setStatus(director.auto ? "Director Auto" : "Director Manual", "sync");
  } else if (keyName === "r") {
    void refresh();
  }
});

void refresh();

const energy = { pulse: 0, beat: 0 };
gsap.to(energy, { pulse: 1, duration: 2.8, repeat: -1, yoyo: true, ease: "sine.inOut" });
gsap.to(energy, { beat: 1, duration: 1.35, repeat: -1, yoyo: true, ease: "sine.inOut" });

let last = performance.now();
let elapsed = 0;

function animate(now) {
  const dt = Math.min((now - last) / 1000, 0.08);
  last = now;
  elapsed += dt;

  const fpsInstant = 1 / Math.max(dt, 0.0001);
  quality.frameSamples.push(fpsInstant);
  if (quality.frameSamples.length > 120) quality.frameSamples.shift();

  if (elapsed - quality.lastHudSampleAt >= 0.35) {
    const avgFps = quality.frameSamples.reduce((sum, value) => sum + value, 0) / Math.max(1, quality.frameSamples.length);
    updateFrameTelemetry(avgFps);
    quality.lastHudSampleAt = elapsed;
  }

  maybeAutoAdjustQuality(elapsed);

  pointerTarget.x += (pointer.x - pointerTarget.x) * 0.06;
  pointerTarget.y += (pointer.y - pointerTarget.y) * 0.06;

  let baseX;
  let baseY;
  let baseZ;
  let lookY;

  if (director.auto) {
    const current = shotDeck[director.shotIndex];
    const nextIndex = (director.shotIndex + 1) % shotDeck.length;
    const next = shotDeck[nextIndex];
    director.shotTime += dt;
    const tRaw = Math.min(1, director.shotTime / current.duration);
    const t = tRaw * tRaw * (3 - 2 * tRaw);

    baseX = THREE.MathUtils.lerp(current.x, next.x, t);
    baseY = THREE.MathUtils.lerp(current.y, next.y, t);
    baseZ = THREE.MathUtils.lerp(current.z, next.z, t);
    lookY = THREE.MathUtils.lerp(current.lookY, next.lookY, t);

    if (tRaw >= 1) {
      director.shotIndex = nextIndex;
      director.shotTime = 0;
    }
  } else {
    baseX = Math.sin(elapsed * 0.17) * 1.3;
    baseY = 3.6;
    baseZ = 14 + Math.cos(elapsed * 0.12) * 0.6;
    lookY = 0;
  }

  camera.position.x += ((baseX + pointerTarget.x * 2.2) - camera.position.x) * 0.03;
  camera.position.y += ((baseY + pointerTarget.y * 1.4) - camera.position.y) * 0.03;
  camera.position.z += ((baseZ + pointerTarget.x * 0.35) - camera.position.z) * 0.03;
  camera.lookAt(0, lookY, 0);
  follow.position.x = Math.sin(elapsed * 0.34) * 2.1;
  follow.position.z = 7.2 + Math.cos(elapsed * 0.28) * 1.0;
  follow.target.position.set(0, -1.1 + Math.sin(elapsed * 0.42) * 0.2, 0);

  rings.rotation.y += dt * 0.08;
  rings.rotation.z = Math.sin(elapsed * 0.25) * 0.06;
  rings.children.forEach((ring, idx) => {
    const baseOpacity = Math.max(0.05, 0.17 - idx * 0.02);
    ring.material.opacity = baseOpacity + pulse.energy * 0.03;
  });
  orbitalGroup.rotation.y += dt * 0.11;
  orbitalGroup.rotation.x = Math.sin(elapsed * 0.19) * 0.06;
  orbitals.forEach((orbital, idx) => {
    orbital.rotation.z += dt * (0.2 + idx * 0.08);
    orbital.position.y = -1.6 + idx * 0.34 + Math.sin(elapsed * (0.8 + idx * 0.2)) * 0.06;
  });
  bladeGroup.rotation.y += dt * 0.07;
  nebulaCore.rotation.y += dt * 0.012;
  nebulaOuter.rotation.y -= dt * 0.008;
  pts.rotation.y += dt * 0.012;
  dust.rotation.y -= dt * 0.009;
  dust.rotation.x = Math.sin(elapsed * 0.1) * 0.04;

  drones.forEach((drone, idx) => {
    const angle = elapsed * drone.speed + drone.phase;
    drone.mesh.position.x = Math.cos(angle) * drone.radius;
    drone.mesh.position.z = Math.sin(angle) * drone.radius;
    drone.mesh.position.y = drone.y + Math.sin(angle * 1.6) * 0.45;
    drone.mesh.scale.setScalar(0.82 + Math.sin(angle * 2.5) * 0.12 + pulse.energy * 0.08);
    drone.mesh.material.opacity = 0.76 + Math.sin(angle * 1.4 + idx) * 0.12 + pulse.energy * 0.06;
  });

  key.intensity = 24 + energy.beat * 10 + pulse.energy * 3;
  rim.intensity = 18 + energy.pulse * 8 + pulse.energy * 2;
  follow.intensity = quality.ultra ? 30 + energy.beat * 7 : 22 + energy.beat * 5;

  Object.values(bars).forEach((item, idx) => {
    const target = item.targetHeight;
    item.mesh.scale.y += (target - item.mesh.scale.y) * 0.08;
    item.mesh.position.y = -2.8 + (item.mesh.scale.y * 0.5);
    item.pedestal.scale.y = 0.95 + Math.sin(elapsed * (1 + idx * 0.2)) * 0.04;
    item.halo.position.y = -2.8 + Math.sin(elapsed * (0.8 + idx * 0.15)) * 0.05;
    item.halo.rotation.z += dt * (0.5 + idx * 0.09);
    item.crown.position.y = item.mesh.position.y + item.mesh.scale.y * 0.48;
    item.crown.scale.setScalar(0.86 + Math.sin(elapsed * (1.6 + idx * 0.25)) * 0.1);
  });

  const bloomBase = quality.ultra ? 1.05 : 0.78;
  const bloomLift = quality.ultra ? 0.33 : 0.22;
  bloom.intensity = bloomBase + energy.pulse * bloomLift + pulse.energy * 0.08;
  dof.blendMode.opacity.value = (quality.ultra ? 0.72 : 0.42) + pulse.energy * (quality.ultra ? 0.05 : 0.03);
  chroma.offset.setScalar((quality.ultra ? 0.00048 : 0.00036) + energy.beat * 0.00024);

  composer.render(dt);
  requestAnimationFrame(animate);
}

requestAnimationFrame(animate);
