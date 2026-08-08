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
    ICE: 0xc8fbff,
    BLUE: 0x6298ff,
    MINT: 0x6ff2bb,
    GRAPHITE: 0x24434b,
    INK: 0x07131b,
  });

  const TESSERACT_VERTICES = Object.freeze(Array.from({ length: 16 }, (_unused, index) => Object.freeze([
    index & 1 ? 1 : -1,
    index & 2 ? 1 : -1,
    index & 4 ? 1 : -1,
    index & 8 ? 1 : -1,
  ])));
  const TESSERACT_EDGES = Object.freeze(TESSERACT_VERTICES.flatMap((_vertex, start) => (
    [0, 1, 2, 3]
      .map((dimension) => [start, start ^ (1 << dimension), dimension])
      .filter(([_start, end]) => end > start)
      .map((edge) => Object.freeze(edge))
  )));

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
    hyperFrames: [],
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

  function rotatePair(first, second, angle) {
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    return [first * cosine - second * sine, first * sine + second * cosine];
  }

  function projectTesseract(angle = 0, scale = 1, phase = 0) {
    const vertices = TESSERACT_VERTICES.map((source) => {
      let [x, y, z, w] = source;
      [x, w] = rotatePair(x, w, angle * 0.91 + phase);
      [y, w] = rotatePair(y, w, angle * 0.67 + phase * 0.71);
      [z, w] = rotatePair(z, w, angle * 0.47 - phase * 0.37);
      [x, y] = rotatePair(x, y, angle * 0.11 + phase * 0.19);
      const perspective = 3.35 / Math.max(1.65, 4.15 - w);
      return Object.freeze({
        x: x * perspective * scale,
        y: y * perspective * scale,
        z: z * perspective * scale,
      });
    });
    return Object.freeze({ vertices, edges: TESSERACT_EDGES });
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
        x: -1.72 + ratio * 3.44 + jitter * 0.55,
        y: Math.sin(ratio * Math.PI * 1.5 - 0.7) * 0.62 + (random() - 0.5) * 0.18,
        z: Math.cos(ratio * Math.PI * 1.9) * 0.72 + (random() - 0.5) * 0.18,
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
    return "Integrity verified. The amber authority torus holds promotion at open gates.";
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
    runtime.hyperFrames = [];
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
    const geometry = new THREE.TubeGeometry(curve, runtime.profile.curveSegments, 0.026, 6, false);
    const material = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.62,
      metalness: 0.5,
      roughness: 0.24,
      transparent: true,
      opacity,
    });
    group.add(new THREE.Mesh(geometry, material));
  }

  function createHyperFrame(THREE, group, model, options) {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(TESSERACT_EDGES.length * 6);
    const colors = new Float32Array(TESSERACT_EDGES.length * 6);
    const dimensionColors = [COLORS.CYAN, COLORS.BLUE, COLORS.MINT, colorForStatus(model.state)];
    TESSERACT_EDGES.forEach(([_start, _end, dimension], edgeIndex) => {
      const color = new THREE.Color(dimensionColors[dimension]);
      const offset = edgeIndex * 6;
      colors.set([color.r, color.g, color.b, color.r, color.g, color.b], offset);
    });
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const material = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: options.opacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const frame = new THREE.LineSegments(geometry, material);
    frame.name = `hyperframe-${options.label}`;
    frame.userData = {
      phase: options.phase,
      scale: options.scale,
      speed: options.speed,
    };
    runtime.hyperFrames.push(frame);
    group.add(frame);
    return frame;
  }

  function updateHyperFrames(now = 0) {
    runtime.hyperFrames.forEach((frame) => {
      const motion = runtime.profile?.animate ? now * frame.userData.speed : 0.72;
      const projection = projectTesseract(motion, frame.userData.scale, frame.userData.phase);
      const positions = frame.geometry.getAttribute("position");
      projection.edges.forEach(([start, end], edgeIndex) => {
        const first = projection.vertices[start];
        const second = projection.vertices[end];
        const offset = edgeIndex * 6;
        positions.array.set([first.x, first.y, first.z, second.x, second.y, second.z], offset);
      });
      positions.needsUpdate = true;
    });
  }

  function addPolyhedralContainment(THREE, group, model) {
    const solid = new THREE.DodecahedronGeometry(3.08, 0);
    const geometry = new THREE.EdgesGeometry(solid, 1);
    solid.dispose();
    const shell = new THREE.LineSegments(
      geometry,
      new THREE.LineBasicMaterial({
        color: colorForStatus(model.state),
        transparent: true,
        opacity: model.state === "FAIL" ? 0.18 : 0.28,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    );
    shell.name = "containment-shell";
    shell.scale.set(1, 0.78, 0.92);
    shell.rotation.set(0.18, 0.28, 0.08);
    group.add(shell);
  }

  function addAuthorityRing(THREE, group, model) {
    const ring = new THREE.Group();
    ring.name = "authority-ring";
    ring.rotation.set(0.92, 0.18, -0.2);
    const guide = new THREE.Mesh(
      new THREE.TorusGeometry(2.72, 0.012, 4, 96),
      new THREE.MeshBasicMaterial({ color: COLORS.GRAPHITE, transparent: true, opacity: 0.72 }),
    );
    ring.add(guide);
    const gateCount = Math.max(model.gates.length, 1);
    model.gates.forEach((gate, index) => {
      const full = (Math.PI * 2) / gateCount;
      const gap = gate.status === "PASS" ? 0.08 : 0.19;
      const arc = Math.max(0.12, full - gap);
      const segment = new THREE.Mesh(
        new THREE.TorusGeometry(2.72, gate.status === "PASS" ? 0.022 : 0.04, 5, 28, arc),
        new THREE.MeshBasicMaterial({
          color: colorForStatus(gate.status),
          transparent: true,
          opacity: gate.status === "PASS" ? 0.68 : 0.96,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        }),
      );
      segment.rotation.z = index * full + gap * 0.5;
      ring.add(segment);
    });
    group.add(ring);
  }

  function addDecisionCore(THREE, group, model) {
    const color = colorForStatus(model.state);
    const core = new THREE.Group();
    core.name = "decision-core";
    const outerSolid = new THREE.OctahedronGeometry(0.54, 0);
    const outerEdges = new THREE.EdgesGeometry(outerSolid);
    outerSolid.dispose();
    core.add(new THREE.LineSegments(
      outerEdges,
      new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.96 }),
    ));
    const innerSolid = new THREE.IcosahedronGeometry(0.24, 0);
    const innerEdges = new THREE.EdgesGeometry(innerSolid);
    innerSolid.dispose();
    core.add(new THREE.LineSegments(
      innerEdges,
      new THREE.LineBasicMaterial({ color: COLORS.ICE, transparent: true, opacity: 0.82 }),
    ));
    [
      [Math.PI / 2, 0, 0],
      [0, Math.PI / 2, 0],
      [Math.PI / 4, Math.PI / 4, 0],
    ].forEach((rotation, index) => {
      const orbit = new THREE.Mesh(
        new THREE.TorusGeometry(0.72 + index * 0.08, 0.01, 4, 56),
        new THREE.MeshBasicMaterial({ color: index === 2 ? color : COLORS.CYAN, transparent: true, opacity: 0.48 }),
      );
      orbit.rotation.set(...rotation);
      core.add(orbit);
    });
    group.add(core);
  }

  function addArtifactSpine(THREE, group, model) {
    const fallbackPoints = [
      { x: -1.7, y: -0.38, z: 0.18 },
      { x: -0.58, y: 0.48, z: 0.62 },
      { x: 0.58, y: 0.42, z: -0.48 },
      { x: 1.7, y: -0.24, z: 0.2 },
    ];
    const points = model.artifacts.length > 1 ? model.artifacts : fallbackPoints;
    const primaryColor = colorForStatus(model.state);
    addRibbon(THREE, group, points, primaryColor, model.state === "FAIL" ? 0.66 : 0.9);
    addRibbon(THREE, group, points, COLORS.CYAN, model.state === "FAIL" ? 0.18 : 0.36, 0.1);

    model.artifacts.forEach((artifact, index) => {
      const node = new THREE.Group();
      node.position.set(artifact.x, artifact.y, artifact.z);
      const color = colorForStatus(artifact.status);
      const solid = new THREE.IcosahedronGeometry(0.17 + (index % 2) * 0.025, 0);
      const edges = new THREE.EdgesGeometry(solid);
      solid.dispose();
      node.add(new THREE.LineSegments(
        edges,
        new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.96 }),
      ));
      const halo = new THREE.Mesh(
        new THREE.TorusGeometry(0.28, 0.009, 4, 36),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.56 }),
      );
      halo.rotation.x = Math.PI / 2;
      node.add(halo);
      group.add(node);
    });
  }

  function addScaleField(THREE, group, model) {
    createHyperFrame(THREE, group, model, { label: "macro", scale: 2.08, opacity: 0.34, phase: 0.08, speed: 0.000055 });
    createHyperFrame(THREE, group, model, { label: "meso", scale: 1.26, opacity: 0.64, phase: 0.62, speed: -0.000082 });
    createHyperFrame(THREE, group, model, { label: "micro", scale: 0.62, opacity: 0.92, phase: 1.12, speed: 0.00012 });
    updateHyperFrames(0);

    const random = seededRandom(model.seed ^ 0xa5a5a5a5);
    const particlePositions = new Float32Array(runtime.profile.particleCount * 3);
    const shellRadii = [0.78, 1.58, 2.72];
    for (let index = 0; index < runtime.profile.particleCount; index += 1) {
      const shell = shellRadii[index % shellRadii.length];
      const radius = shell + (random() - 0.5) * 0.18;
      const angle = random() * Math.PI * 2;
      const elevation = (random() - 0.5) * Math.PI;
      particlePositions[index * 3] = Math.cos(angle) * Math.cos(elevation) * radius;
      particlePositions[index * 3 + 1] = Math.sin(elevation) * radius * 0.72;
      particlePositions[index * 3 + 2] = Math.sin(angle) * Math.cos(elevation) * radius;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({ color: COLORS.ICE, size: 0.018, transparent: true, opacity: 0.34 }),
    );
    particles.name = "proof-particles";
    group.add(particles);
  }

  function rebuildThree(model) {
    const THREE = root.THREE;
    if (!THREE || !runtime.scene) return;
    clearThreeScene();
    const group = new THREE.Group();
    group.rotation.x = -0.08;
    runtime.scene.add(group);
    runtime.sceneGroup = group;
    addScaleField(THREE, group, model);
    addPolyhedralContainment(THREE, group, model);
    addAuthorityRing(THREE, group, model);
    addArtifactSpine(THREE, group, model);
    addDecisionCore(THREE, group, model);
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
    context.fillStyle = "#061014";
    context.fillRect(0, 0, width, height);

    const compact = width / Math.max(height, 1) < 1.25;
    const centerX = width * (compact ? 0.5 : 0.67);
    const centerY = height * (compact ? 0.58 : 0.51);
    const scale = Math.min(width / (compact ? 7.2 : 10.2), height / 7.2);
    const pulse = runtime.profile.animate ? 1 + Math.sin(now * 0.0012) * 0.012 : 1;
    const stateColor = model.state === "FAIL" ? "#ff5368" : model.state === "PROMOTE" ? "#55e0a3" : "#f3b84b";
    const dimensionColors = ["#49d9e8", "#6298ff", "#6ff2bb", stateColor];

    context.save();
    context.translate(centerX, centerY);
    context.scale(pulse, pulse);

    [
      { scale: 2.08, phase: 0.08, alpha: 0.32 },
      { scale: 1.26, phase: 0.62, alpha: 0.58 },
      { scale: 0.62, phase: 1.12, alpha: 0.88 },
    ].forEach((layer) => {
      const angle = runtime.profile.animate ? now * 0.00006 : 0.72;
      const projection = projectTesseract(angle, layer.scale, layer.phase);
      projection.edges.forEach(([start, end, dimension]) => {
        const first = projection.vertices[start];
        const second = projection.vertices[end];
        context.strokeStyle = dimensionColors[dimension];
        context.lineWidth = Math.max(1, scale * (dimension === 3 ? 0.018 : 0.011));
        context.globalAlpha = layer.alpha;
        context.beginPath();
        context.moveTo(first.x * scale, -first.y * scale);
        context.lineTo(second.x * scale, -second.y * scale);
        context.stroke();
      });
    });

    context.globalAlpha = 0.82;
    context.strokeStyle = stateColor;
    context.lineWidth = Math.max(2, scale * 0.026);
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
      context.shadowBlur = 8;
      context.beginPath();
      const x = artifact.x * scale;
      const y = -artifact.y * scale;
      const radius = Math.max(5, scale * 0.11);
      context.moveTo(x, y - radius);
      context.lineTo(x + radius, y);
      context.lineTo(x, y + radius);
      context.lineTo(x - radius, y);
      context.closePath();
      context.strokeStyle = context.fillStyle;
      context.lineWidth = Math.max(1, scale * 0.014);
      context.stroke();
    });
    context.shadowBlur = 0;

    const gateCount = Math.max(model.gates.length, 1);
    model.gates.forEach((gate, index) => {
      const arc = (Math.PI * 2) / gateCount;
      const gap = gate.status === "PASS" ? 0.055 : 0.18;
      context.strokeStyle = gate.status === "PASS" ? "#55e0a3" : gate.status === "FAIL" ? "#ff5368" : "#f3b84b";
      context.lineWidth = Math.max(2, scale * 0.032);
      context.beginPath();
      context.arc(0, 0, scale * 2.72, index * arc + gap, (index + 1) * arc - gap);
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
      const compact = rect.width < 700;
      runtime.camera.position.set(0, compact ? 0.12 : 0.28, compact ? 9.8 : 9.1);
      runtime.camera.updateProjectionMatrix();
      if (runtime.sceneGroup) {
        runtime.sceneGroup.position.x = compact ? 0 : 1.08;
        runtime.sceneGroup.position.y = compact ? -0.62 : 0;
        runtime.sceneGroup.scale.setScalar(compact ? 0.82 : 1);
      }
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
        updateHyperFrames(now);
        const phaseSpeed = runtime.phase === "authority" ? 1.5 : 1;
        runtime.sceneGroup.rotation.y = 0.13 + Math.sin(now * 0.00012 * phaseSpeed) * 0.15 + runtime.pointer.x * 0.07;
        runtime.sceneGroup.rotation.x = -0.08 + runtime.pointer.y * 0.035;
        const authorityRing = runtime.sceneGroup.getObjectByName("authority-ring");
        if (authorityRing) authorityRing.rotation.z = -0.2 + now * 0.000045 * phaseSpeed;
        const decisionCore = runtime.sceneGroup.getObjectByName("decision-core");
        if (decisionCore) {
          decisionCore.rotation.x = now * 0.00011;
          decisionCore.rotation.y = -now * 0.00015;
        }
        const containment = runtime.sceneGroup.getObjectByName("containment-shell");
        if (containment) containment.rotation.y = 0.28 - now * 0.000018;
        const compact = runtime.canvas.getBoundingClientRect().width < 700;
        const baseX = compact ? 0 : 1.08;
        runtime.sceneGroup.position.x = baseX + (runtime.model.state === "FAIL" ? Math.sin(now * 0.006) * 0.025 : 0);
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
        if (THREE.ACESFilmicToneMapping) runtime.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        runtime.renderer.toneMappingExposure = 1.08;
        runtime.scene = new THREE.Scene();
        runtime.scene.fog = new THREE.FogExp2(COLORS.INK, 0.038);
        runtime.camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
        runtime.camera.position.set(0, 0.28, 9.1);
        runtime.scene.add(new THREE.AmbientLight(0xb7dce1, 1.05));
        const keyLight = new THREE.PointLight(COLORS.CYAN, 20, 28);
        keyLight.position.set(2.5, 3, 5);
        runtime.scene.add(keyLight);
        const rimLight = new THREE.PointLight(COLORS.OPEN, 12, 22);
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
    runtime.hyperFrames = [];
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
    projectTesseract,
    resolveQualityProfile,
    resume,
    runGuidedProof,
    setPhase,
    setState,
  });
}));
