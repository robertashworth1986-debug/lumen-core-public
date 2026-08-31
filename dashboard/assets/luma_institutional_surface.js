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

  function mountProofLattice() {
    if (surface !== "home") return;
    var stage = document.querySelector("[data-proof-lattice]");
    if (!stage || stage.dataset.latticeMounted === "true") return;

    var viewport = stage.querySelector(".lis-lattice-viewport");
    var canvas = stage.querySelector(".lis-lattice-canvas");
    var modeLabel = stage.querySelector("[data-lattice-mode]");
    if (!viewport || !canvas) return;

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
    var reducedMotion = window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    var saveData = Boolean(connection && connection.saveData);
    var weakDevice = (navigator.deviceMemory && navigator.deviceMemory < 4)
      || (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4);
    var staticMode = Boolean(reducedMotion || saveData);
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
      stage.querySelectorAll("[data-lattice-step]").forEach(function (step) {
        step.dataset.active = String(Number(step.dataset.latticeStep) === activeIndex);
      });
    }

    function draw(timestamp) {
      context.clearRect(0, 0, width, height);
      pointerX += (targetPointerX - pointerX) * 0.045;
      pointerY += (targetPointerY - pointerY) * 0.045;

      var time = staticMode ? 0.72 : timestamp * 0.00016;
      var angleY = time + pointerX * 0.18;
      var angleX = -0.18 + Math.sin(time * 0.7) * 0.08 + pointerY * 0.13;
      var angleZ = Math.sin(time * 0.42) * 0.06;
      var activeIndex = staticMode ? 4 : Math.floor(timestamp / 1400) % coreNodes.length;
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
