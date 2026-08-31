(function () {
  "use strict";

  if (window.__LUMA_INSTITUTIONAL_SURFACE__) return;
  window.__LUMA_INSTITUTIONAL_SURFACE__ = true;

  var surface = String(document.body && document.body.dataset.lumaSurface || "").toLowerCase();
  var localOperator = location.protocol === "file:"
    || ["127.0.0.1", "localhost", "::1"].indexOf(location.hostname) >= 0;
  var publicReview = !localOperator;

  document.documentElement.classList.toggle("luma-public-review", publicReview);
  document.documentElement.setAttribute("data-luma-audience", publicReview ? "public-review" : "local-operator");
  window.LUMA_PUBLIC_REVIEW = publicReview;

  function makeProofline(config) {
    var rail = document.createElement("aside");
    rail.className = "lis-proofline";
    rail.setAttribute("role", "note");
    rail.setAttribute("aria-label", "Evidence and authority posture");
    rail.innerHTML = [
      "<span>", config.label, "</span>",
      '<span data-tone="', config.evidenceTone || "good", '"><small>Evidence class</small><strong>', config.evidence, "</strong></span>",
      '<span data-tone="', config.runtimeTone || "paper", '"><small>Runtime boundary</small><strong>', config.runtime, "</strong></span>",
      '<span data-tone="warn"><small>Authority</small><strong>', config.authority, "</strong></span>",
    ].join("");
    return rail;
  }

  var configs = {
    home: {
      label: "Decision fabric",
      evidence: "First-party · replayable",
      runtime: "Public review surface",
      authority: "Pilot and promotion human-gated",
    },
    mission: {
      label: "Mission truth",
      evidence: "Measured · source-labeled",
      runtime: "Observation and review",
      authority: "No automatic promotion",
    },
    quant: {
      label: "Research control",
      evidence: "Replay · paper · modeled",
      runtime: "No live order authority",
      authority: "Claims remain bounded",
    },
    grants: {
      label: "Funding evidence",
      evidence: "Discovery · draft · receipt",
      runtime: publicReview ? "Public review · read-only" : "Local operator workspace",
      authority: "Final submission human-only",
    },
    trade: {
      label: "Trading evidence",
      evidence: "Paper/shadow + historical receipts",
      runtime: "Read-only public posture",
      authority: "Live orders not authorized here",
    },
    review: {
      label: "Reviewer path",
      evidence: "First-party · source-bounded",
      runtime: "Static public review",
      authority: "Promotion and submission human-only",
    },
  };

  function insertProofline() {
    var config = configs[surface];
    if (!config || document.querySelector(".lis-proofline")) return;
    var rail = makeProofline(config);
    var anchor = null;

    if (surface === "home") anchor = document.querySelector(".home .nav");
    if (surface === "mission") anchor = document.querySelector(".stage .top-bar");
    if (surface === "grants") anchor = document.querySelector(".lc-stage .lc-topbar");
    if (surface === "trade") anchor = document.querySelector(".luma-statusbar");
    if (surface === "review") anchor = document.querySelector(".lis-review-header");

    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(rail, anchor.nextSibling);
    } else if (surface === "grants") {
      var stage = document.querySelector(".lc-stage");
      if (stage) stage.insertBefore(rail, stage.firstChild);
    }
  }

  function enforcePublicReview() {
    if (!publicReview || surface !== "grants") return;
    var mutationIds = [
      "draft-all", "opps-autopilot", "regenerate", "approve-btn", "regen-btn",
      "prepare-btn", "autofill-btn", "submitted-btn",
    ];
    mutationIds.forEach(function (id) {
      var button = document.getElementById(id);
      if (!button) return;
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", "Local authenticated operator action only");
    });
  }

  function repairStaticRoutes() {
    var replacements = {
      "social_pro_dashboard.html": "/proof_to_pilot.html",
      "lumaq_brain_command_center.html": "/quant_lab.html",
      "vps_growth_proof_3d.html": "/evidence/",
    };
    document.querySelectorAll("a[href]").forEach(function (link) {
      var raw = link.getAttribute("href") || "";
      var clean = raw.split("#")[0].split("?")[0].replace(/^\.\//, "");
      if (Object.prototype.hasOwnProperty.call(replacements, clean)) {
        link.setAttribute("href", replacements[clean]);
        link.setAttribute("data-route-repaired", clean);
      }
    });
  }

  function makeDeterministicRandom(seed) {
    var state = seed >>> 0;
    return function () {
      state = (state * 1664525 + 1013904223) >>> 0;
      return state / 4294967296;
    };
  }

  var proofLatticeStates = [
    {
      label: "AUTHORIZED SOURCE",
      detail: "Named origin, rights status, and preserved input enter the chain.",
    },
    {
      label: "LOCKED BASELINE",
      detail: "The accepted incumbent comparator is selected before scoring begins.",
    },
    {
      label: "PREDECLARED METRIC",
      detail: "Threshold, window, and failure rules are frozen before the run.",
    },
    {
      label: "REPLAY CUSTODY",
      detail: "SHA-256 receipts bind the preserved artifacts to the reviewable record.",
    },
    {
      label: "BOUNDED DECISION",
      detail: "Promote, rerun, review, hold, or reject without widening the claim.",
    },
  ];

  function updateProofLatticeStep(stage, activeIndex) {
    stage.querySelectorAll("[data-lattice-step]").forEach(function (step) {
      var active = Number(step.dataset.latticeStep) === activeIndex;
      step.dataset.active = String(active);
      step.setAttribute("aria-pressed", String(active));
    });
    var state = proofLatticeStates[activeIndex];
    var readoutLabel = stage.querySelector("[data-lattice-readout-label]");
    var readoutDetail = stage.querySelector("[data-lattice-readout-detail]");
    if (state && readoutLabel) readoutLabel.textContent = state.label;
    if (state && readoutDetail) readoutDetail.textContent = state.detail;
  }

  function bindProofLatticeControls(stage, onSelect) {
    stage.querySelectorAll("[data-lattice-step]").forEach(function (step) {
      step.addEventListener("click", function () {
        onSelect(Number(step.dataset.latticeStep));
      });
    });
  }

  function mountWebGLProofLattice(stage, viewport, canvas, modeLabel, weakDevice) {
    if (!window.THREE || !window.WebGLRenderingContext) return false;

    var THREE = window.THREE;
    var renderer = null;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        alpha: true,
        antialias: !weakDevice,
        powerPreference: "high-performance",
      });
    } catch (_) {
      return false;
    }

    try {
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, weakDevice ? 1.15 : 1.55));
      if (THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;

      var scene = new THREE.Scene();
      scene.fog = new THREE.FogExp2(0x020713, 0.085);
      var camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0, 0.08, 8.7);

      var spaceUniforms = { uTime: { value: 0 } };
      var spaceDome = new THREE.Mesh(
        new THREE.SphereGeometry(34, weakDevice ? 24 : 40, weakDevice ? 16 : 28),
        new THREE.ShaderMaterial({
          uniforms: spaceUniforms,
          side: THREE.BackSide,
          depthWrite: false,
          fog: false,
          vertexShader: [
            "varying vec3 vRay;",
            "void main() {",
            "  vRay = normalize(position);",
            "  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);",
            "}",
          ].join("\n"),
          fragmentShader: [
            "uniform float uTime;",
            "varying vec3 vRay;",
            "float hash3(vec3 p) {",
            "  p = fract(p * 0.3183099 + vec3(0.11, 0.17, 0.13));",
            "  p *= 17.0;",
            "  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));",
            "}",
            "float noise3(vec3 p) {",
            "  vec3 i = floor(p);",
            "  vec3 f = fract(p);",
            "  f = f * f * (3.0 - 2.0 * f);",
            "  return mix(",
            "    mix(mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), f.x),",
            "        mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),",
            "    mix(mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x),",
            "        mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x), f.y), f.z);",
            "}",
            "float fbm(vec3 p) {",
            "  float value = 0.0;",
            "  float amplitude = 0.52;",
            "  for (int octave = 0; octave < 4; octave++) {",
            "    value += amplitude * noise3(p);",
            "    p = p * 2.03 + vec3(7.1, 3.7, 5.9);",
            "    amplitude *= 0.48;",
            "  }",
            "  return value;",
            "}",
            "void main() {",
            "  vec3 ray = normalize(vRay);",
            "  vec3 drift = vec3(uTime * 0.002, -uTime * 0.001, uTime * 0.0015);",
            "  float cloud = fbm(ray * 3.4 + drift);",
            "  float filament = fbm(ray * 9.5 - drift * 1.7);",
            "  float nebula = smoothstep(0.49, 0.83, cloud * 0.76 + filament * 0.31);",
            "  float dust = smoothstep(0.62, 0.88, fbm(ray * 25.0 + 4.0));",
            "  vec3 voidColor = vec3(0.0015, 0.0035, 0.014);",
            "  vec3 blueCloud = vec3(0.015, 0.115, 0.22);",
            "  vec3 violetCloud = vec3(0.18, 0.035, 0.26);",
            "  float colorMix = smoothstep(-0.55, 0.65, ray.y + cloud * 0.22);",
            "  vec3 color = voidColor + mix(blueCloud, violetCloud, colorMix) * nebula * 0.48;",
            "  color += vec3(0.025, 0.075, 0.12) * dust * 0.18;",
            "  float vignette = 0.76 + 0.24 * max(0.0, ray.z);",
            "  gl_FragColor = vec4(color * vignette, 1.0);",
            "}",
          ].join("\n"),
        })
      );
      spaceDome.renderOrder = -20;
      scene.add(spaceDome);

      function makeDeepStarField(count, minimumRadius, maximumRadius, pointSize, opacity, seed) {
        var starRandom = makeDeterministicRandom(seed);
        var starPositions = new Float32Array(count * 3);
        var starColors = new Float32Array(count * 3);
        for (var starIndex = 0; starIndex < count; starIndex += 1) {
          var starLongitude = starRandom() * Math.PI * 2;
          var starLatitude = Math.acos(2 * starRandom() - 1);
          var starRadius = minimumRadius + starRandom() * (maximumRadius - minimumRadius);
          starPositions[starIndex * 3] = Math.sin(starLatitude) * Math.cos(starLongitude) * starRadius;
          starPositions[starIndex * 3 + 1] = Math.cos(starLatitude) * starRadius;
          starPositions[starIndex * 3 + 2] = Math.sin(starLatitude) * Math.sin(starLongitude) * starRadius;
          var temperature = starRandom();
          starColors[starIndex * 3] = temperature > 0.94 ? 1 : 0.58 + temperature * 0.32;
          starColors[starIndex * 3 + 1] = temperature > 0.94 ? 0.76 : 0.72 + temperature * 0.24;
          starColors[starIndex * 3 + 2] = temperature > 0.94 ? 0.48 : 1;
        }
        var starGeometry = new THREE.BufferGeometry();
        starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
        starGeometry.setAttribute("color", new THREE.BufferAttribute(starColors, 3));
        return new THREE.Points(
          starGeometry,
          new THREE.PointsMaterial({
            size: pointSize,
            sizeAttenuation: true,
            transparent: true,
            opacity: opacity,
            depthWrite: false,
            fog: false,
            vertexColors: true,
            blending: THREE.AdditiveBlending,
          })
        );
      }

      var farStars = makeDeepStarField(weakDevice ? 420 : 980, 12, 30, weakDevice ? 0.085 : 0.065, 0.86, 2718281828);
      var nearStars = makeDeepStarField(weakDevice ? 90 : 220, 6, 12, weakDevice ? 0.105 : 0.085, 0.68, 3141592653);
      scene.add(farStars);
      scene.add(nearStars);

      var lattice = new THREE.Group();
      lattice.rotation.x = -0.08;
      scene.add(lattice);

      var colors = [0x66f6df, 0x72aaff, 0xbd8cff, 0x61f3ad, 0xffc96b];
      var labels = ["SOURCE", "BASELINE", "METRIC", "HASH", "DECISION"];
      var nodePositions = [
        new THREE.Vector3(-2.24, 0.28, -0.22),
        new THREE.Vector3(-1.13, -0.77, 0.5),
        new THREE.Vector3(0, 0.82, 0.82),
        new THREE.Vector3(1.13, -0.68, 0.46),
        new THREE.Vector3(2.25, 0.26, -0.18),
      ];

      var energyUniforms = {
        uTime: { value: 0 },
        uColorA: { value: new THREE.Color(0x66f6df) },
        uColorB: { value: new THREE.Color(0xbd8cff) },
      };
      var energyMaterial = new THREE.ShaderMaterial({
        uniforms: energyUniforms,
        transparent: true,
        wireframe: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: [
          "uniform float uTime;",
          "varying float vEnergy;",
          "varying vec3 vNormalView;",
          "void main() {",
          "  float wave = sin(position.y * 5.0 + uTime * 1.5) * 0.025;",
          "  vec3 displaced = position + normal * wave;",
          "  vEnergy = 0.5 + 0.5 * sin(position.x * 4.0 - position.z * 3.0 + uTime * 2.0);",
          "  vNormalView = normalize(normalMatrix * normal);",
          "  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);",
          "}",
        ].join("\n"),
        fragmentShader: [
          "uniform vec3 uColorA;",
          "uniform vec3 uColorB;",
          "varying float vEnergy;",
          "varying vec3 vNormalView;",
          "void main() {",
          "  float edge = pow(1.0 - abs(vNormalView.z), 1.6);",
          "  vec3 color = mix(uColorA, uColorB, vEnergy);",
          "  gl_FragColor = vec4(color * (1.15 + edge), 0.17 + edge * 0.42);",
          "}",
        ].join("\n"),
      });
      var energyCore = new THREE.Mesh(
        new THREE.IcosahedronGeometry(1.2, weakDevice ? 2 : 3),
        energyMaterial
      );
      lattice.add(energyCore);

      var coreGlowUniforms = {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(0x5fe8ff) },
      };
      var coreGlow = new THREE.Mesh(
        new THREE.SphereGeometry(0.86, weakDevice ? 20 : 32, weakDevice ? 14 : 22),
        new THREE.ShaderMaterial({
          uniforms: coreGlowUniforms,
          transparent: true,
          depthWrite: false,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          vertexShader: [
            "varying vec3 vNormalView;",
            "varying vec3 vViewPosition;",
            "void main() {",
            "  vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);",
            "  vViewPosition = -viewPosition.xyz;",
            "  vNormalView = normalize(normalMatrix * normal);",
            "  gl_Position = projectionMatrix * viewPosition;",
            "}",
          ].join("\n"),
          fragmentShader: [
            "uniform float uTime;",
            "uniform vec3 uColor;",
            "varying vec3 vNormalView;",
            "varying vec3 vViewPosition;",
            "void main() {",
            "  float fresnel = pow(1.0 - abs(dot(normalize(vNormalView), normalize(vViewPosition))), 2.25);",
            "  float beat = 0.82 + 0.18 * sin(uTime * 2.2);",
            "  gl_FragColor = vec4(uColor * (0.8 + fresnel * 1.7), (0.035 + fresnel * 0.29) * beat);",
            "}",
          ].join("\n"),
        })
      );
      lattice.add(coreGlow);

      var shellGeometry = new THREE.IcosahedronGeometry(2.12, 1);
      var shell = new THREE.LineSegments(
        new THREE.EdgesGeometry(shellGeometry),
        new THREE.LineBasicMaterial({
          color: 0x72aaff,
          transparent: true,
          opacity: 0.3,
          blending: THREE.AdditiveBlending,
        })
      );
      lattice.add(shell);

      var ringColors = [0x66f6df, 0x72aaff, 0xbd8cff];
      var rings = [];
      [2.65, 2.38, 1.92].forEach(function (radius, index) {
        var ring = new THREE.Mesh(
          new THREE.TorusGeometry(radius, index === 2 ? 0.009 : 0.013, 5, weakDevice ? 90 : 150),
          new THREE.MeshBasicMaterial({
            color: ringColors[index],
            transparent: true,
            opacity: 0.34 - index * 0.055,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
          })
        );
        ring.rotation.set(0.65 + index * 0.48, 0.3 + index * 0.61, index * 0.72);
        rings.push(ring);
        lattice.add(ring);
      });

      var random = makeDeterministicRandom(1618033988);
      var particleCount = weakDevice ? 150 : 360;
      var particlePositions = new Float32Array(particleCount * 3);
      var particleSizes = new Float32Array(particleCount);
      var particlePhases = new Float32Array(particleCount);
      for (var particleIndex = 0; particleIndex < particleCount; particleIndex += 1) {
        var longitude = random() * Math.PI * 2;
        var latitude = Math.acos(2 * random() - 1);
        var radius = 1.65 + Math.pow(random(), 0.65) * 3.5;
        particlePositions[particleIndex * 3] = Math.sin(latitude) * Math.cos(longitude) * radius;
        particlePositions[particleIndex * 3 + 1] = Math.cos(latitude) * radius;
        particlePositions[particleIndex * 3 + 2] = Math.sin(latitude) * Math.sin(longitude) * radius;
        particleSizes[particleIndex] = 2.4 + random() * 4.8;
        particlePhases[particleIndex] = random() * Math.PI * 2;
      }
      var particleGeometry = new THREE.BufferGeometry();
      particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
      particleGeometry.setAttribute("aSize", new THREE.BufferAttribute(particleSizes, 1));
      particleGeometry.setAttribute("aPhase", new THREE.BufferAttribute(particlePhases, 1));
      var particleUniforms = {
        uTime: { value: 0 },
        uPixelRatio: { value: renderer.getPixelRatio() },
      };
      var particleCloud = new THREE.Points(
        particleGeometry,
        new THREE.ShaderMaterial({
          uniforms: particleUniforms,
          transparent: true,
          depthWrite: false,
          vertexColors: false,
          blending: THREE.AdditiveBlending,
          vertexShader: [
            "attribute float aSize;",
            "attribute float aPhase;",
            "uniform float uTime;",
            "uniform float uPixelRatio;",
            "varying float vPhase;",
            "void main() {",
            "  vPhase = aPhase;",
            "  vec3 p = position;",
            "  p.y += sin(uTime * 0.55 + aPhase + position.x) * 0.035;",
            "  vec4 viewPosition = modelViewMatrix * vec4(p, 1.0);",
            "  gl_PointSize = aSize * uPixelRatio * (6.5 / max(2.0, -viewPosition.z));",
            "  gl_Position = projectionMatrix * viewPosition;",
            "}",
          ].join("\n"),
          fragmentShader: [
            "varying float vPhase;",
            "void main() {",
            "  vec2 center = gl_PointCoord - vec2(0.5);",
            "  float distanceToCenter = length(center);",
            "  float alpha = smoothstep(0.5, 0.04, distanceToCenter);",
            "  vec3 cyan = vec3(0.4, 0.965, 0.875);",
            "  vec3 blue = vec3(0.45, 0.67, 1.0);",
            "  vec3 color = mix(cyan, blue, step(3.14159, vPhase));",
            "  gl_FragColor = vec4(color * 1.35, alpha * 0.72);",
            "}",
          ].join("\n"),
        })
      );
      lattice.add(particleCloud);

      var nodeMeshes = [];
      var nodeHalos = [];
      var labelSprites = [];
      function makeLabelSprite(text, color) {
        var labelCanvas = document.createElement("canvas");
        labelCanvas.width = 256;
        labelCanvas.height = 64;
        var labelContext = labelCanvas.getContext("2d");
        labelContext.clearRect(0, 0, 256, 64);
        labelContext.fillStyle = "rgba(2, 7, 18, 0.82)";
        labelContext.strokeStyle = "rgba(150, 211, 255, 0.34)";
        labelContext.lineWidth = 2;
        labelContext.beginPath();
        labelContext.roundRect(16, 8, 224, 45, 12);
        labelContext.fill();
        labelContext.stroke();
        labelContext.fillStyle = color;
        labelContext.font = "700 18px Arial, sans-serif";
        labelContext.textAlign = "center";
        labelContext.textBaseline = "middle";
        labelContext.fillText(text, 128, 31);
        var texture = new THREE.CanvasTexture(labelCanvas);
        if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
        var sprite = new THREE.Sprite(new THREE.SpriteMaterial({
          map: texture,
          transparent: true,
          depthWrite: false,
          opacity: 0.78,
        }));
        sprite.scale.set(1.18, 0.295, 1);
        return sprite;
      }

      nodePositions.forEach(function (position, index) {
        var nodeMaterial = new THREE.MeshBasicMaterial({
          color: colors[index],
          transparent: true,
          opacity: 0.96,
        });
        var node = new THREE.Mesh(new THREE.IcosahedronGeometry(0.105, 1), nodeMaterial);
        node.position.copy(position);
        nodeMeshes.push(node);
        lattice.add(node);

        var halo = new THREE.Mesh(
          new THREE.RingGeometry(0.18, 0.27, 32),
          new THREE.MeshBasicMaterial({
            color: colors[index],
            transparent: true,
            opacity: 0.34,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
          })
        );
        halo.position.copy(position);
        halo.lookAt(camera.position);
        nodeHalos.push(halo);
        lattice.add(halo);

        var labelColor = "#" + new THREE.Color(colors[index]).getHexString();
        var label = makeLabelSprite(labels[index], labelColor);
        label.position.copy(position).add(new THREE.Vector3(0, 0.32, 0));
        labelSprites.push(label);
        lattice.add(label);
      });

      var pathMaterials = [];
      var pathPulses = [];
      for (var edgeIndex = 0; edgeIndex < nodePositions.length - 1; edgeIndex += 1) {
        var pathGeometry = new THREE.BufferGeometry().setFromPoints([
          nodePositions[edgeIndex],
          nodePositions[edgeIndex + 1],
        ]);
        var pathMaterial = new THREE.LineBasicMaterial({
          color: colors[edgeIndex],
          transparent: true,
          opacity: 0.72,
          blending: THREE.AdditiveBlending,
        });
        pathMaterials.push(pathMaterial);
        lattice.add(new THREE.Line(pathGeometry, pathMaterial));

        var pulse = new THREE.Mesh(
          new THREE.SphereGeometry(0.055, 10, 8),
          new THREE.MeshBasicMaterial({
            color: colors[edgeIndex],
            transparent: true,
            opacity: 1,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
          })
        );
        pathPulses.push(pulse);
        lattice.add(pulse);
      }

      var polarGrid = new THREE.PolarGridHelper(4.6, 10, 7, 64, 0x72aaff, 0x17436b);
      polarGrid.material.transparent = true;
      polarGrid.material.opacity = 0.11;
      polarGrid.material.blending = THREE.AdditiveBlending;
      polarGrid.rotation.x = Math.PI / 2;
      polarGrid.position.z = -1.9;
      scene.add(polarGrid);

      var width = 1;
      var height = 1;
      var targetPointerX = 0;
      var targetPointerY = 0;
      var pointerX = 0;
      var pointerY = 0;
      var inView = true;
      var frameId = null;
      var lastFrame = 0;
      var frameInterval = weakDevice ? 34 : 16;
      var manualStep = -1;
      var manualStepUntil = 0;
      var qualitySampleStart = performance.now();
      var qualityFrames = 0;
      var adaptiveQuality = false;

      function setActiveStep(activeIndex) {
        updateProofLatticeStep(stage, activeIndex);
      }

      function resize() {
        var bounds = viewport.getBoundingClientRect();
        width = Math.max(1, Math.round(bounds.width));
        height = Math.max(1, Math.round(bounds.height));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      }

      function render(timestamp) {
        var time = timestamp * 0.001;
        var activeIndex = manualStep >= 0 && timestamp < manualStepUntil
          ? manualStep
          : Math.floor(timestamp / 1400) % nodePositions.length;
        setActiveStep(activeIndex);

        pointerX += (targetPointerX - pointerX) * 0.045;
        pointerY += (targetPointerY - pointerY) * 0.045;
        lattice.rotation.y = time * 0.075 + pointerX * 0.17;
        lattice.rotation.x = -0.07 + Math.sin(time * 0.16) * 0.035 + pointerY * 0.1;
        lattice.position.y = Math.sin(time * 0.38) * 0.035;
        shell.rotation.y = -time * 0.12;
        shell.rotation.z = time * 0.035;
        energyCore.rotation.y = time * 0.14;
        energyCore.rotation.x = -time * 0.08;
        energyUniforms.uTime.value = time;
        coreGlowUniforms.uTime.value = time;
        spaceUniforms.uTime.value = time;
        particleUniforms.uTime.value = time;
        particleCloud.rotation.y = -time * 0.018;
        polarGrid.rotation.z = time * 0.012;
        spaceDome.rotation.y = time * 0.00035;
        farStars.rotation.y = time * 0.0016;
        farStars.rotation.x = Math.sin(time * 0.011) * 0.012;
        nearStars.rotation.y = -time * 0.0034;

        rings.forEach(function (ring, index) {
          ring.rotation.z += (index % 2 === 0 ? 1 : -1) * 0.00045 * (weakDevice ? 1.2 : 1);
        });

        nodeMeshes.forEach(function (node, index) {
          var active = index === activeIndex;
          var scale = active ? 1.75 + Math.sin(time * 4.2) * 0.18 : 1;
          node.scale.setScalar(scale);
          nodeHalos[index].scale.setScalar(active ? 1.5 : 1);
          nodeHalos[index].material.opacity = active ? 0.75 : 0.28;
          labelSprites[index].material.opacity = active ? 1 : 0.62;
        });

        pathPulses.forEach(function (pulse, index) {
          var progress = (time * 0.27 + index * 0.19) % 1;
          pulse.position.lerpVectors(nodePositions[index], nodePositions[index + 1], progress);
          var pulseScale = 0.8 + Math.sin(time * 5 + index) * 0.22;
          pulse.scale.setScalar(pulseScale);
          pathMaterials[index].opacity = index === activeIndex || index + 1 === activeIndex ? 1 : 0.55;
        });

        camera.position.x = pointerX * 0.16 + Math.sin(time * 0.09) * 0.07;
        camera.position.y = 0.08 - pointerY * 0.1 + Math.cos(time * 0.08) * 0.035;
        camera.position.z = 8.7 + Math.sin(time * 0.055) * 0.055;
        camera.lookAt(0, 0, 0);
        renderer.render(scene, camera);
      }

      function requestFrame() {
        if (frameId !== null || !inView || document.hidden) return;
        frameId = window.requestAnimationFrame(frame);
      }

      function frame(timestamp) {
        frameId = null;
        if (!inView || document.hidden) return;
        if (timestamp - lastFrame >= frameInterval) {
          lastFrame = timestamp;
          render(timestamp);
          qualityFrames += 1;
          if (!weakDevice && !adaptiveQuality && timestamp - qualitySampleStart >= 5000) {
            var deliveredFps = qualityFrames * 1000 / (timestamp - qualitySampleStart);
            if (deliveredFps < 28) {
              adaptiveQuality = true;
              frameInterval = 34;
              renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.05));
              particleGeometry.setDrawRange(0, Math.floor(particleCount * 0.58));
              farStars.geometry.setDrawRange(0, 520);
              nearStars.geometry.setDrawRange(0, 120);
              viewport.dataset.quality = "adaptive";
              if (modeLabel) modeLabel.textContent = "DEEP SPACE / ADAPTIVE GPU";
              resize();
            } else {
              viewport.dataset.quality = "high";
            }
            qualitySampleStart = timestamp;
            qualityFrames = 0;
          }
        }
        requestFrame();
      }

      bindProofLatticeControls(stage, function (selectedIndex) {
        manualStep = selectedIndex;
        manualStepUntil = performance.now() + 15000;
        render(performance.now());
      });

      canvas.addEventListener("webglcontextlost", function (event) {
        event.preventDefault();
        if (frameId !== null) window.cancelAnimationFrame(frameId);
        frameId = null;
        viewport.dataset.quality = "recovery";
        if (modeLabel) modeLabel.textContent = "GPU CONTEXT / RESTORING";
      });
      canvas.addEventListener("webglcontextrestored", function () {
        renderer.resetState();
        viewport.dataset.quality = adaptiveQuality ? "adaptive" : (weakDevice ? "efficient" : "high");
        if (modeLabel) {
          modeLabel.textContent = adaptiveQuality
            ? "DEEP SPACE / ADAPTIVE GPU"
            : "DEEP SPACE / WEBGL MODEL";
        }
        resize();
        requestFrame();
      });

      viewport.addEventListener("pointermove", function (event) {
        var bounds = viewport.getBoundingClientRect();
        targetPointerX = ((event.clientX - bounds.left) / Math.max(1, bounds.width) - 0.5) * 2;
        targetPointerY = ((event.clientY - bounds.top) / Math.max(1, bounds.height) - 0.5) * 2;
      }, { passive: true });
      viewport.addEventListener("pointerleave", function () {
        targetPointerX = 0;
        targetPointerY = 0;
      }, { passive: true });

      if ("ResizeObserver" in window) {
        new ResizeObserver(resize).observe(viewport);
      } else {
        window.addEventListener("resize", resize, { passive: true });
      }
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
          inView = Boolean(entries[0] && entries[0].isIntersecting);
          if (inView) requestFrame();
        }, { rootMargin: "120px" }).observe(stage);
      }
      document.addEventListener("visibilitychange", function () {
        if (!document.hidden) requestFrame();
      });

      viewport.dataset.mode = "webgl";
      viewport.dataset.quality = weakDevice ? "efficient" : "measuring";
      if (modeLabel) modeLabel.textContent = "DEEP SPACE / WEBGL MODEL";
      resize();
      render(720);
      requestFrame();
      return true;
    } catch (_) {
      try {
        renderer.dispose();
      } catch (__) {
        // The two-dimensional deterministic fallback remains available.
      }
      return false;
    }
  }

  function mountProofLattice() {
    if (surface !== "home") return;
    var stage = document.querySelector("[data-proof-lattice]");
    if (!stage || stage.dataset.latticeMounted === "true") return;

    var viewport = stage.querySelector(".lis-lattice-viewport");
    var webglCanvas = stage.querySelector(".lis-lattice-webgl-canvas");
    var canvas = stage.querySelector(".lis-lattice-canvas");
    var modeLabel = stage.querySelector("[data-lattice-mode]");
    if (!viewport || !canvas) return;

    var webglPending = document.documentElement.dataset.lumaWebglPending === "true";
    if (webglPending && !window.THREE) {
      viewport.dataset.mode = "pending";
      if (modeLabel) modeLabel.textContent = "DEEP SPACE / INITIALIZING";
      return;
    }

    var reducedMotion = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    var saveData = Boolean(connection && connection.saveData);
    var weakDevice = (navigator.deviceMemory && navigator.deviceMemory < 4)
      || (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4);
    var staticMode = Boolean(reducedMotion || saveData);
    if (!staticMode && webglCanvas
      && mountWebGLProofLattice(stage, viewport, webglCanvas, modeLabel, weakDevice)) {
      stage.dataset.latticeMounted = "true";
      return;
    }

    var context = null;
    try {
      context = canvas.getContext("2d", { alpha: true, desynchronized: true });
    } catch (_) {
      context = canvas.getContext("2d");
    }
    if (!context) {
      viewport.dataset.mode = "static";
      if (modeLabel) modeLabel.textContent = "CSS-SAFE";
      return;
    }

    stage.dataset.latticeMounted = "true";
    var frameInterval = weakDevice ? 50 : 32;
    var particleCount = weakDevice ? 34 : 68;
    viewport.dataset.mode = staticMode ? "static" : "dynamic";
    if (modeLabel) modeLabel.textContent = staticMode ? "STATIC-SAFE" : "PROJECTED-3D";

    var phi = 1.61803398875;
    var labels = ["SOURCE", "BASELINE", "METRIC", "HASH", "DECISION"];
    var colors = ["#66f6df", "#72aaff", "#bd8cff", "#61f3ad", "#ffc96b"];
    var coreNodes = [
      { x: -2.05, y: 0.22, z: -0.2 },
      { x: -1.08, y: -0.72, z: 0.52 },
      { x: 0, y: 0.72, z: 0.78 },
      { x: 1.08, y: -0.62, z: 0.42 },
      { x: 2.06, y: 0.2, z: -0.16 },
    ];
    var shellNodes = [
      [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
      [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
      [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
    ].map(function (point) {
      return { x: point[0] * 0.92, y: point[1] * 0.92, z: point[2] * 0.92 };
    });
    var shellEdges = [];
    shellNodes.forEach(function (a, left) {
      shellNodes.forEach(function (b, right) {
        if (right <= left) return;
        var distance = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
        if (distance < 1.9) shellEdges.push([left, right]);
      });
    });

    var random = makeDeterministicRandom(1618033988);
    var particles = Array.from({ length: particleCount }, function () {
      var longitude = random() * Math.PI * 2;
      var latitude = Math.acos(2 * random() - 1);
      var radius = 1.8 + random() * 2.3;
      return {
        x: Math.sin(latitude) * Math.cos(longitude) * radius,
        y: Math.cos(latitude) * radius,
        z: Math.sin(latitude) * Math.sin(longitude) * radius,
        size: 0.35 + random() * 1.15,
        phase: random() * Math.PI * 2,
      };
    });

    var width = 1;
    var height = 1;
    var pixelRatio = 1;
    var pointerX = 0;
    var pointerY = 0;
    var targetPointerX = 0;
    var targetPointerY = 0;
    var inView = true;
    var frameId = null;
    var lastFrame = 0;
    var manualStep = -1;
    var manualStepUntil = 0;

    function resize() {
      var bounds = viewport.getBoundingClientRect();
      width = Math.max(1, Math.round(bounds.width));
      height = Math.max(1, Math.round(bounds.height));
      pixelRatio = Math.min(window.devicePixelRatio || 1, weakDevice ? 1.25 : 1.6);
      canvas.width = Math.max(1, Math.round(width * pixelRatio));
      canvas.height = Math.max(1, Math.round(height * pixelRatio));
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      draw(performance.now());
    }

    function rotate(point, angleY, angleX, angleZ) {
      var cosY = Math.cos(angleY);
      var sinY = Math.sin(angleY);
      var x1 = point.x * cosY - point.z * sinY;
      var z1 = point.x * sinY + point.z * cosY;
      var cosX = Math.cos(angleX);
      var sinX = Math.sin(angleX);
      var y2 = point.y * cosX - z1 * sinX;
      var z2 = point.y * sinX + z1 * cosX;
      var cosZ = Math.cos(angleZ);
      var sinZ = Math.sin(angleZ);
      return {
        x: x1 * cosZ - y2 * sinZ,
        y: x1 * sinZ + y2 * cosZ,
        z: z2,
      };
    }

    function project(point) {
      var camera = 7.2;
      var depth = Math.max(2.4, camera - point.z);
      var perspective = camera / depth;
      var unit = Math.min(width, height) * 0.145;
      return {
        x: width * 0.52 + point.x * unit * perspective,
        y: height * 0.54 + point.y * unit * perspective,
        z: point.z,
        scale: perspective,
      };
    }

    function lineBetween(a, b, stroke, alpha, lineWidth) {
      context.beginPath();
      context.moveTo(a.x, a.y);
      context.lineTo(b.x, b.y);
      context.strokeStyle = stroke;
      context.globalAlpha = alpha;
      context.lineWidth = lineWidth;
      context.stroke();
    }

    function drawRing(angleY, angleX, angleZ, radius, stroke, alpha) {
      context.beginPath();
      for (var index = 0; index <= 80; index += 1) {
        var theta = (index / 80) * Math.PI * 2;
        var point = rotate(
          { x: Math.cos(theta) * radius, y: Math.sin(theta) * radius, z: 0 },
          angleY,
          angleX,
          angleZ
        );
        var projected = project(point);
        if (index === 0) context.moveTo(projected.x, projected.y);
        else context.lineTo(projected.x, projected.y);
      }
      context.strokeStyle = stroke;
      context.globalAlpha = alpha;
      context.lineWidth = 0.85;
      context.stroke();
    }

    function setActiveStep(activeIndex) {
      updateProofLatticeStep(stage, activeIndex);
    }

    function draw(timestamp) {
      context.clearRect(0, 0, width, height);
      pointerX += (targetPointerX - pointerX) * 0.045;
      pointerY += (targetPointerY - pointerY) * 0.045;

      var time = staticMode ? 0.72 : timestamp * 0.00016;
      var angleY = time + pointerX * 0.18;
      var angleX = -0.18 + Math.sin(time * 0.7) * 0.08 + pointerY * 0.13;
      var angleZ = Math.sin(time * 0.42) * 0.06;
      var activeIndex = manualStep >= 0 && (staticMode || timestamp < manualStepUntil)
        ? manualStep
        : (staticMode ? 4 : Math.floor(timestamp / 1400) % coreNodes.length);
      setActiveStep(activeIndex);

      particles.forEach(function (particle) {
        var rotated = rotate(particle, angleY * 0.38 + particle.phase * 0.025, angleX, angleZ);
        var projected = project(rotated);
        var pulse = staticMode ? 0.7 : 0.58 + Math.sin(timestamp * 0.0012 + particle.phase) * 0.24;
        context.beginPath();
        context.arc(projected.x, projected.y, particle.size * projected.scale, 0, Math.PI * 2);
        context.fillStyle = particle.phase > Math.PI ? "#72aaff" : "#66f6df";
        context.globalAlpha = Math.max(0.06, pulse * (0.34 + rotated.z * 0.035));
        context.fill();
      });

      drawRing(angleY, angleX + 1.18, angleZ, 2.55, "#66f6df", 0.21);
      drawRing(angleY + 1.04, angleX, angleZ + 0.52, 2.22, "#72aaff", 0.18);
      drawRing(angleY - 0.62, angleX + 0.55, angleZ - 0.36, 1.78, "#bd8cff", 0.16);

      var projectedShell = shellNodes.map(function (point) {
        return project(rotate(point, angleY, angleX, angleZ));
      });
      shellEdges.forEach(function (edge) {
        var averageDepth = (projectedShell[edge[0]].z + projectedShell[edge[1]].z) / 2;
        lineBetween(
          projectedShell[edge[0]],
          projectedShell[edge[1]],
          averageDepth > 0 ? "#66f6df" : "#72aaff",
          Math.max(0.08, 0.2 + averageDepth * 0.025),
          averageDepth > 0 ? 1 : 0.7
        );
      });

      projectedShell
        .slice()
        .sort(function (a, b) { return a.z - b.z; })
        .forEach(function (point) {
          context.beginPath();
          context.arc(point.x, point.y, Math.max(1.2, 2.2 * point.scale), 0, Math.PI * 2);
          context.fillStyle = point.z > 0 ? "#66f6df" : "#72aaff";
          context.globalAlpha = Math.max(0.18, 0.48 + point.z * 0.04);
          context.fill();
        });

      var projectedCore = coreNodes.map(function (point) {
        return project(rotate(point, angleY * 0.22, angleX * 0.38, angleZ));
      });
      for (var edgeIndex = 0; edgeIndex < projectedCore.length - 1; edgeIndex += 1) {
        var gradient = context.createLinearGradient(
          projectedCore[edgeIndex].x,
          projectedCore[edgeIndex].y,
          projectedCore[edgeIndex + 1].x,
          projectedCore[edgeIndex + 1].y
        );
        gradient.addColorStop(0, colors[edgeIndex]);
        gradient.addColorStop(1, colors[edgeIndex + 1]);
        lineBetween(projectedCore[edgeIndex], projectedCore[edgeIndex + 1], gradient, 0.8, 1.45);

        var progress = staticMode ? 0.72 : ((timestamp * 0.00034 + edgeIndex * 0.19) % 1);
        var pulseX = projectedCore[edgeIndex].x
          + (projectedCore[edgeIndex + 1].x - projectedCore[edgeIndex].x) * progress;
        var pulseY = projectedCore[edgeIndex].y
          + (projectedCore[edgeIndex + 1].y - projectedCore[edgeIndex].y) * progress;
        var pulseGradient = context.createRadialGradient(pulseX, pulseY, 0, pulseX, pulseY, 12);
        pulseGradient.addColorStop(0, "rgba(255,255,255,0.95)");
        pulseGradient.addColorStop(0.25, colors[edgeIndex]);
        pulseGradient.addColorStop(1, "rgba(102,246,223,0)");
        context.beginPath();
        context.arc(pulseX, pulseY, 12, 0, Math.PI * 2);
        context.fillStyle = pulseGradient;
        context.globalAlpha = 0.72;
        context.fill();
      }

      projectedCore.forEach(function (point, index) {
        var active = index === activeIndex;
        var radius = (active ? 6.6 : 4.5) * point.scale;
        var glow = context.createRadialGradient(point.x, point.y, 0, point.x, point.y, radius * 4.2);
        glow.addColorStop(0, colors[index]);
        glow.addColorStop(0.22, colors[index]);
        glow.addColorStop(1, "rgba(3,8,20,0)");
        context.beginPath();
        context.arc(point.x, point.y, radius * 4.2, 0, Math.PI * 2);
        context.fillStyle = glow;
        context.globalAlpha = active ? 0.5 : 0.24;
        context.fill();

        context.beginPath();
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
        context.fillStyle = colors[index];
        context.globalAlpha = 0.95;
        context.fill();
        context.strokeStyle = "rgba(232,246,255,0.9)";
        context.lineWidth = active ? 1.4 : 0.7;
        context.stroke();

        context.globalAlpha = active ? 0.98 : 0.72;
        context.fillStyle = active ? "#f4fbff" : colors[index];
        context.font = (active ? "700 " : "600 ") + (active ? "10px" : "8px")
          + " 'JetBrains Mono', Consolas, monospace";
        context.textAlign = "center";
        context.textBaseline = "bottom";
        context.fillText(labels[index], point.x, point.y - radius - 8);
      });

      context.globalAlpha = 1;
    }

    function requestFrame() {
      if (staticMode || frameId !== null || !inView || document.hidden) return;
      frameId = window.requestAnimationFrame(frame);
    }

    function frame(timestamp) {
      frameId = null;
      if (!inView || document.hidden) return;
      if (timestamp - lastFrame >= frameInterval) {
        lastFrame = timestamp;
        draw(timestamp);
      }
      requestFrame();
    }

    bindProofLatticeControls(stage, function (selectedIndex) {
      manualStep = selectedIndex;
      manualStepUntil = performance.now() + 15000;
      draw(performance.now());
    });

    viewport.addEventListener("pointermove", function (event) {
      if (staticMode) return;
      var bounds = viewport.getBoundingClientRect();
      targetPointerX = ((event.clientX - bounds.left) / Math.max(1, bounds.width) - 0.5) * 2;
      targetPointerY = ((event.clientY - bounds.top) / Math.max(1, bounds.height) - 0.5) * 2;
    }, { passive: true });
    viewport.addEventListener("pointerleave", function () {
      targetPointerX = 0;
      targetPointerY = 0;
    }, { passive: true });

    if ("ResizeObserver" in window) {
      new ResizeObserver(resize).observe(viewport);
    } else {
      window.addEventListener("resize", resize, { passive: true });
    }

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        inView = Boolean(entries[0] && entries[0].isIntersecting);
        if (inView) requestFrame();
      }, { rootMargin: "120px" }).observe(stage);
    }

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) requestFrame();
    });

    resize();
    requestFrame();
  }

  function start() {
    insertProofline();
    enforcePublicReview();
    repairStaticRoutes();
    window.addEventListener("luma:three-ready", mountProofLattice, { once: true });
    mountProofLattice();

    if (surface === "grants" && publicReview) {
      var observer = new MutationObserver(function () {
        enforcePublicReview();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
