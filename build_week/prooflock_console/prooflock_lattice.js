"use strict";

(function exposeProofLockLattice(root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ProofLockLattice = api;
}(typeof globalThis !== "undefined" ? globalThis : window, (root) => {
  const COLORS = Object.freeze({
    PASS: 0x55e0a3,
    OPEN: 0xf3b84b,
    FAIL: 0xff5368,
    HOLD: 0xf3b84b,
    PROMOTE: 0x55e0a3,
    CYAN: 0x49d9e8,
    INK: 0x07131b,
  });

  const runtime = {
    canvas: null,
    context2d: null,
    renderer: null,
    scene: null,
    camera: null,
    sceneGroup: null,
    resizeObserver: null,
    statusElement: null,
    model: null,
    profile: null,
    frameRequest: 0,
    frameTimes: [],
    previousFrame: 0,
    frameNumber: 0,
    frameStride: 1,
    paused: true,
    hidden: false,
    pointer: { x: 0, y: 0 },
    phase: "idle",
    guidedRunning: false,
    listeners: [],
  };

  function deriveSeed(hash) {
    const normalized = String(hash || "0").replace(/[^0-9a-f]/gi, "").padEnd(64, "0").slice(0, 64);
    let seed = 0x6d2b79f5;
    for (let index = 0; index < normalized.length; index += 8) {
      seed = (seed ^ Number.parseInt(normalized.slice(index, index + 8), 16)) >>> 0;
      seed = Math.imul(seed ^ (seed >>> 15), 1 | seed) >>> 0;
    }
    return seed || 1;
  }

  function seededRandom(seed) {
    let value = seed >>> 0;
    return () => {
      value = (value + 0x6d2b79f5) >>> 0;
      let mixed = value;
      mixed = Math.imul(mixed ^ (mixed >>> 15), mixed | 1);
      mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61);
      return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
    };
  }

  function deriveVisualState(report) {
    if (!report?.integrity_valid) return "FAIL";
    if (report.promotion_allowed) return "PROMOTE";
    return "HOLD";
  }

  function resolveQualityProfile(overrides = {}) {
    const navigatorRef = overrides.navigator || root.navigator || {};
    const matchMediaRef = overrides.matchMedia || root.matchMedia?.bind(root);
    const reducedMotion = overrides.reducedMotion ?? Boolean(matchMediaRef?.("(prefers-reduced-motion: reduce)")?.matches);
    const saveData = overrides.saveData ?? Boolean(navigatorRef.connection?.saveData);
    const memory = Number(overrides.deviceMemory ?? navigatorRef.deviceMemory ?? 0);
    const cores = Number(overrides.hardwareConcurrency ?? navigatorRef.hardwareConcurrency ?? 0);
    const width = Number(overrides.width ?? root.innerWidth ?? 1280);
    let tier = "high";
    if (saveData || reducedMotion || width < 760 || (memory && memory <= 4) || (cores && cores <= 4)) tier = "balanced";
    if (saveData || (memory && memory <= 2) || (cores && cores <= 2)) tier = "lite";
    return {
      tier,
      reducedMotion,
      saveData,
      animate: !reducedMotion && !saveData,
      maxPixelRatio: tier === "high" ? 1.6 : tier === "balanced" ? 1.25 : 1,
      particleCount: tier === "high" ? 220 : tier === "balanced" ? 110 : 40,
      curveSegments: tier === "high" ? 96 : tier === "balanced" ? 64 : 40,
    };
  }

  function buildVisualModel({ receipt, report }) {
    const hash = report?.receipt_hash?.computed || report?.receipt_hash?.expected || receipt?.receipt_sha256 || "";
    const seed = deriveSeed(hash);
    const random = seededRandom(seed);
    const state = deriveVisualState(report);
    const artifacts = (report?.artifacts || receipt?.artifacts || []).map((artifact, index, rows) => {
      const ratio = rows.length <= 1 ? 0.5 : index / (rows.length - 1);
      const jitter = state === "FAIL" ? (random() - 0.5) * 1.35 : (random() - 0.5) * 0.16;
      return {
        id: String(artifact.artifact_id || `artifact-${index + 1}`),
        status: artifact.hash_matches ? "PASS" : "FAIL",
        x: -2.9 + ratio * 5.8 + jitter,
        y: Math.sin(ratio * Math.PI * 1.4 - 0.6) * 0.8 + (random() - 0.5) * 0.25,
        z: Math.cos(ratio * Math.PI * 1.8) * 0.55 + (random() - 0.5) * 0.22,
      };
    });
    const gates = (report?.gates || receipt?.gates || []).map((gate, index) => ({
      id: String(gate.gate_id || `gate-${index + 1}`),
      status: String(gate.effective_status || gate.status || "OPEN"),
      required: Boolean(gate.required_for_promotion),
      index,
    }));
    return { hash, seed, state, artifacts, gates };
  }

  function setReadableStatus(text) {
    if (runtime.statusElement) runtime.statusElement.textContent = text;
  }

  function phaseStatus(model, phase = runtime.phase) {
    if (phase === "lineage") return "Lineage focused: declared V2 to V3 custody path.";
    if (phase === "gates") return `${model.gates.filter((gate) => gate.required && gate.status !== "PASS").length} required authority gates remain open.`;
    if (phase === "authority") return "Authority escalation blocked: a resealed receipt cannot mint approval.";
    if (phase === "restored") return "Canonical receipt restored and verified; promotion remains held.";
    if (model.state === "FAIL") return "Integrity failed. The evidence lattice is fractured.";
    if (model.state === "PROMOTE") return "Integrity verified and all required gates are clear.";
    return "Integrity verified. The amber containment ring holds promotion at open gates.";
  }

  function disposeMaterial(material) {
    if (Array.isArray(material)) material.forEach(disposeMaterial);
    else material?.dispose?.();
  }

  function disposeObject(object) {
    object?.traverse?.((child) => {
      child.geometry?.dispose?.();
      disposeMaterial(child.material);
    });
  }

  function clearThreeScene() {
    if (!runtime.sceneGroup || !runtime.scene) return;
    runtime.scene.remove(runtime.sceneGroup);
    disposeObject(runtime.sceneGroup);
    runtime.sceneGroup = null;
  }

  function colorForStatus(status) {
    if (status === "PASS" || status === "PROMOTE") return COLORS.PASS;
    if (status === "FAIL" || status === "REJECT") return COLORS.FAIL;
    return COLORS.OPEN;
  }

  function addRibbon(THREE, group, points, color, opacity, offset = 0) {
    if (points.length < 2) return;
    const curvePoints = points.map((point) => new THREE.Vector3(point.x, point.y + offset, point.z));
    const curve = new THREE.CatmullRomCurve3(curvePoints, false, "catmullrom", 0.35);
    const geometry = new THREE.TubeGeometry(curve, runtime.profile.curveSegments, 0.045, 8, false);
    const material = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.38,
      metalness: 0.35,
      roughness: 0.32,
      transparent: true,
      opacity,
    });
    group.add(new THREE.Mesh(geometry, material));
  }

  function rebuildThree(model) {
    const THREE = root.THREE;
    if (!THREE || !runtime.scene) return;
    clearThreeScene();
    const group = new THREE.Group();
    group.rotation.x = -0.16;
    runtime.scene.add(group);
    runtime.sceneGroup = group;

    const fallbackPoints = [
      { x: -2.9, y: -0.4, z: 0.1 },
      { x: -1.0, y: 0.6, z: 0.5 },
      { x: 1.0, y: 0.4, z: -0.35 },
      { x: 2.9, y: -0.25, z: 0.15 },
    ];
    const points = model.artifacts.length > 1 ? model.artifacts : fallbackPoints;
    const primaryColor = colorForStatus(model.state);
    addRibbon(THREE, group, points, primaryColor, model.state === "FAIL" ? 0.62 : 0.88);
    addRibbon(THREE, group, points, COLORS.CYAN, model.state === "FAIL" ? 0.18 : 0.34, 0.15);

    if (model.artifacts.length > 1) {
      const positions = [];
      model.artifacts.forEach((artifact) => positions.push(artifact.x, artifact.y, artifact.z));
      const lineGeometry = new THREE.BufferGeometry();
      lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      const lineMaterial = new THREE.LineBasicMaterial({ color: primaryColor, transparent: true, opacity: 0.5 });
      group.add(new THREE.Line(lineGeometry, lineMaterial));
    }

    model.artifacts.forEach((artifact, index) => {
      const node = new THREE.Group();
      node.position.set(artifact.x, artifact.y, artifact.z);
      const color = colorForStatus(artifact.status);
      const geometry = new THREE.IcosahedronGeometry(0.22 + (index % 2) * 0.04, 1);
      const material = new THREE.MeshPhysicalMaterial({
        color,
        emissive: color,
        emissiveIntensity: artifact.status === "PASS" ? 0.45 : 0.7,
        metalness: 0.45,
        roughness: 0.2,
        clearcoat: 0.6,
      });
      node.add(new THREE.Mesh(geometry, material));
      const halo = new THREE.Mesh(
        new THREE.TorusGeometry(0.34, 0.012, 6, 40),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7 }),
      );
      halo.rotation.x = Math.PI / 2;
      node.add(halo);
      group.add(node);
    });

    const gateCount = Math.max(model.gates.length, 1);
    model.gates.forEach((gate, index) => {
      const full = (Math.PI * 2) / gateCount;
      const start = index * full + 0.055;
      const length = Math.max(0.12, full - (gate.status === "PASS" ? 0.075 : 0.2));
      const color = colorForStatus(gate.status);
      const segment = new THREE.Mesh(
        new THREE.RingGeometry(3.28, 3.36, 56, 1, start, length),
        new THREE.MeshBasicMaterial({
          color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: gate.status === "PASS" ? 0.7 : 0.95,
        }),
      );
      segment.rotation.x = -0.42;
      segment.rotation.z = 0.16;
      group.add(segment);
    });

    const containment = new THREE.Mesh(
      new THREE.SphereGeometry(3.65, 32, 20),
      new THREE.MeshBasicMaterial({
        color: primaryColor,
        wireframe: true,
        transparent: true,
        opacity: model.state === "PROMOTE" ? 0.14 : model.state === "FAIL" ? 0.1 : 0.075,
      }),
    );
    containment.scale.y = 0.56;
    group.add(containment);

    const random = seededRandom(model.seed ^ 0xa5a5a5a5);
    const particlePositions = new Float32Array(runtime.profile.particleCount * 3);
    for (let index = 0; index < runtime.profile.particleCount; index += 1) {
      const radius = 1.2 + random() * 3.2;
      const angle = random() * Math.PI * 2;
      particlePositions[index * 3] = Math.cos(angle) * radius;
      particlePositions[index * 3 + 1] = (random() - 0.5) * 3.2;
      particlePositions[index * 3 + 2] = Math.sin(angle) * radius;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({ color: COLORS.CYAN, size: 0.025, transparent: true, opacity: 0.38 }),
    );
    particles.name = "proof-particles";
    group.add(particles);
  }

  function canvasSize() {
    const rect = runtime.canvas.getBoundingClientRect();
    const ratio = Math.min(root.devicePixelRatio || 1, runtime.profile.maxPixelRatio);
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (runtime.canvas.width !== width || runtime.canvas.height !== height) {
      runtime.canvas.width = width;
      runtime.canvas.height = height;
    }
    return { width, height, ratio };
  }

  function drawCanvas(now = 0) {
    const context = runtime.context2d;
    const model = runtime.model;
    if (!context || !model) return;
    const { width, height } = canvasSize();
    context.clearRect(0, 0, width, height);
    const gradient = context.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#07131b");
    gradient.addColorStop(0.58, "#0b2028");
    gradient.addColorStop(1, "#071117");
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    const centerX = width * 0.5;
    const centerY = height * 0.52;
    const scale = Math.min(width / 9.5, height / 5.2);
    const pulse = runtime.profile.animate ? 1 + Math.sin(now * 0.0018) * 0.025 : 1;
    const stateColor = model.state === "FAIL" ? "#ff5368" : model.state === "PROMOTE" ? "#55e0a3" : "#f3b84b";

    context.save();
    context.translate(centerX, centerY);
    context.scale(pulse, pulse);
    context.strokeStyle = stateColor;
    context.lineWidth = Math.max(2, scale * 0.028);
    context.globalAlpha = 0.8;
    context.beginPath();
    model.artifacts.forEach((artifact, index) => {
      const x = artifact.x * scale;
      const y = -artifact.y * scale;
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();

    model.artifacts.forEach((artifact) => {
      context.fillStyle = artifact.status === "PASS" ? "#55e0a3" : "#ff5368";
      context.shadowColor = context.fillStyle;
      context.shadowBlur = 16;
      context.beginPath();
      context.arc(artifact.x * scale, -artifact.y * scale, Math.max(5, scale * 0.12), 0, Math.PI * 2);
      context.fill();
    });
    context.shadowBlur = 0;

    const gateCount = Math.max(model.gates.length, 1);
    model.gates.forEach((gate, index) => {
      const arc = (Math.PI * 2) / gateCount;
      const gap = gate.status === "PASS" ? 0.055 : 0.18;
      context.strokeStyle = gate.status === "PASS" ? "#55e0a3" : gate.status === "FAIL" ? "#ff5368" : "#f3b84b";
      context.lineWidth = Math.max(2, scale * 0.04);
      context.beginPath();
      context.arc(0, 0, scale * 3.25, index * arc + gap, (index + 1) * arc - gap);
      context.stroke();
    });
    context.restore();
  }

  function resize() {
    if (!runtime.canvas || !runtime.profile) return;
    if (runtime.renderer && runtime.camera) {
      const rect = runtime.canvas.getBoundingClientRect();
      runtime.renderer.setPixelRatio(Math.min(root.devicePixelRatio || 1, runtime.profile.maxPixelRatio));
      runtime.renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
      runtime.camera.aspect = Math.max(1, rect.width) / Math.max(1, rect.height);
      runtime.camera.updateProjectionMatrix();
      runtime.renderer.render(runtime.scene, runtime.camera);
    } else {
      drawCanvas(performance.now());
    }
  }

  function adaptPerformance(frameTime) {
    runtime.frameTimes.push(frameTime);
    if (runtime.frameTimes.length > 90) runtime.frameTimes.shift();
    if (runtime.frameTimes.length < 60) return;
    const average = runtime.frameTimes.reduce((sum, value) => sum + value, 0) / runtime.frameTimes.length;
    if (average > 50) runtime.frameStride = 3;
    else if (average > 34) runtime.frameStride = 2;
    else runtime.frameStride = 1;
    const particles = runtime.sceneGroup?.getObjectByName?.("proof-particles");
    if (particles) particles.visible = runtime.frameStride === 1;
  }

  function renderFrame(now) {
    runtime.frameRequest = 0;
    if (runtime.paused || runtime.hidden || !runtime.model) return;
    const elapsed = runtime.previousFrame ? Math.min(80, now - runtime.previousFrame) : 16;
    runtime.previousFrame = now;
    runtime.frameNumber += 1;
    adaptPerformance(elapsed);

    if (runtime.frameNumber % runtime.frameStride === 0) {
      if (runtime.renderer && runtime.sceneGroup) {
        const speed = runtime.phase === "authority" ? 0.00022 : 0.00009;
        runtime.sceneGroup.rotation.y = now * speed + runtime.pointer.x * 0.08;
        runtime.sceneGroup.rotation.x = -0.16 + runtime.pointer.y * 0.04;
        if (runtime.model.state === "FAIL") {
          runtime.sceneGroup.position.x = Math.sin(now * 0.006) * 0.025;
        } else {
          runtime.sceneGroup.position.x = 0;
        }
        runtime.renderer.render(runtime.scene, runtime.camera);
      } else {
        drawCanvas(now);
      }
    }
    if (runtime.profile.animate) runtime.frameRequest = root.requestAnimationFrame(renderFrame);
  }

  function pause() {
    runtime.paused = true;
    if (runtime.frameRequest) root.cancelAnimationFrame?.(runtime.frameRequest);
    runtime.frameRequest = 0;
  }

  function resume() {
    if (!runtime.canvas || runtime.hidden) return;
    runtime.paused = false;
    runtime.previousFrame = 0;
    resize();
    if (runtime.profile.animate && !runtime.frameRequest) runtime.frameRequest = root.requestAnimationFrame(renderFrame);
  }

  function initialize(options = {}) {
    if (!options.canvas) throw new Error("ProofLock lattice requires a canvas");
    destroy();
    runtime.canvas = options.canvas;
    runtime.statusElement = options.statusElement || null;
    runtime.profile = resolveQualityProfile(options.profile || {});
    runtime.canvas.setAttribute("aria-hidden", "true");

    const THREE = root.THREE;
    if (THREE) {
      try {
        runtime.renderer = new THREE.WebGLRenderer({ canvas: runtime.canvas, antialias: runtime.profile.tier === "high", alpha: true });
        runtime.renderer.setClearColor(COLORS.INK, 1);
        runtime.renderer.outputColorSpace = THREE.SRGBColorSpace || runtime.renderer.outputColorSpace;
        runtime.scene = new THREE.Scene();
        runtime.scene.fog = new THREE.FogExp2(COLORS.INK, 0.055);
        runtime.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
        runtime.camera.position.set(0, 0.35, 8.4);
        runtime.scene.add(new THREE.AmbientLight(0xb7dce1, 1.25));
        const keyLight = new THREE.PointLight(COLORS.CYAN, 16, 24);
        keyLight.position.set(2.5, 3, 5);
        runtime.scene.add(keyLight);
        const rimLight = new THREE.PointLight(COLORS.OPEN, 10, 18);
        rimLight.position.set(-3, -1, 3);
        runtime.scene.add(rimLight);
      } catch (_error) {
        runtime.renderer?.dispose?.();
        runtime.renderer = null;
        runtime.scene = null;
        runtime.camera = null;
      }
    }
    if (!runtime.renderer) runtime.context2d = runtime.canvas.getContext("2d", { alpha: false });

    const onPointerMove = (event) => {
      const rect = runtime.canvas.getBoundingClientRect();
      runtime.pointer.x = ((event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 2;
      runtime.pointer.y = ((event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 2;
    };
    const onVisibility = () => {
      runtime.hidden = Boolean(root.document?.hidden);
      if (runtime.hidden) pause();
      else resume();
    };
    runtime.canvas.addEventListener("pointermove", onPointerMove, { passive: true });
    root.document?.addEventListener("visibilitychange", onVisibility);
    runtime.listeners.push([runtime.canvas, "pointermove", onPointerMove], [root.document, "visibilitychange", onVisibility]);
    if (root.ResizeObserver) {
      runtime.resizeObserver = new root.ResizeObserver(resize);
      runtime.resizeObserver.observe(runtime.canvas);
    } else {
      root.addEventListener?.("resize", resize);
      runtime.listeners.push([root, "resize", resize]);
    }
    resize();
    resume();
    return { mode: runtime.renderer ? "webgl" : "canvas2d", profile: { ...runtime.profile } };
  }

  function setState({ receipt, report }) {
    runtime.model = buildVisualModel({ receipt, report });
    runtime.phase = !report?.integrity_valid ? "tamper" : report?.policy_valid ? "verified" : "authority";
    if (runtime.renderer) rebuildThree(runtime.model);
    else drawCanvas(performance.now());
    setReadableStatus(phaseStatus(runtime.model));
    resize();
    return runtime.model;
  }

  function setPhase(phase) {
    runtime.phase = phase;
    if (runtime.model) setReadableStatus(phaseStatus(runtime.model, phase));
  }

  async function runGuidedProof(options = {}) {
    if (runtime.guidedRunning) return { status: "already_running" };
    if (typeof options.loadSample !== "function" || typeof options.verify !== "function") {
      throw new Error("Guided proof requires loadSample and verify callbacks");
    }
    if (typeof options.seal !== "function") throw new Error("Guided proof requires a canonical reseal callback");
    runtime.guidedRunning = true;
    const delayMs = Math.max(0, Number(options.delayMs ?? (runtime.profile?.reducedMotion ? 180 : 900)));
    const wait = (multiplier) => new Promise((resolve) => root.setTimeout(resolve, delayMs * multiplier));
    try {
      setPhase("custody");
      const canonical = await options.loadSample();
      if (!canonical?.receipt || typeof canonical.text !== "string") throw new Error("Canonical sample callback returned no receipt text");
      await options.verify({ ...canonical, stage: "custody" });
      await wait(1);

      setPhase("lineage");
      await wait(1.15);
      setPhase("gates");
      await wait(1.15);

      const authorityAttack = JSON.parse(JSON.stringify(canonical.receipt));
      authorityAttack.gates.forEach((gate) => {
        if (gate.required_for_promotion) gate.status = "PASS";
      });
      authorityAttack.decision = "PROMOTE";
      authorityAttack.receipt_sha256 = await options.seal(authorityAttack);
      setPhase("authority");
      const attackReport = await options.verify({
        receipt: authorityAttack,
        text: `${JSON.stringify(authorityAttack, null, 2)}\n`,
        stage: "authority_attack",
      });
      if (!attackReport?.integrity_valid || attackReport?.policy_valid || attackReport?.promotion_allowed) {
        throw new Error("Resealed authority escalation did not fail closed");
      }
      await wait(1.35);

      setPhase("restored");
      const restored = { receipt: JSON.parse(canonical.text), text: canonical.text, stage: "restored" };
      await options.verify(restored);
      await wait(0.7);
      return { status: "restored", canonical_text: canonical.text };
    } finally {
      runtime.guidedRunning = false;
    }
  }

  function destroy() {
    pause();
    runtime.resizeObserver?.disconnect?.();
    runtime.resizeObserver = null;
    runtime.listeners.forEach(([target, eventName, listener]) => target?.removeEventListener?.(eventName, listener));
    runtime.listeners = [];
    clearThreeScene();
    runtime.renderer?.dispose?.();
    runtime.canvas = null;
    runtime.context2d = null;
    runtime.renderer = null;
    runtime.scene = null;
    runtime.camera = null;
    runtime.statusElement = null;
    runtime.model = null;
    runtime.profile = null;
    runtime.frameTimes = [];
    runtime.previousFrame = 0;
    runtime.phase = "idle";
    runtime.guidedRunning = false;
  }

  return Object.freeze({
    buildVisualModel,
    deriveSeed,
    deriveVisualState,
    destroy,
    initialize,
    pause,
    resolveQualityProfile,
    resume,
    runGuidedProof,
    setPhase,
    setState,
  });
}));
